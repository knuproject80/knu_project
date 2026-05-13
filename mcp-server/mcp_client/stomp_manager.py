import asyncio
import json
import logging
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

import websocket

import config

logger = logging.getLogger(__name__)


@dataclass
class PendingAck:
    command_id: str
    action: str
    event: threading.Event
    created_at: float


class UIController:
    """
    Spring WebSocket + STOMP 클라이언트

    특징
    - 순수 WebSocket endpoint(/ws) 연결
    - STOMP CONNECT / SUBSCRIBE / SEND 프레임 직접 처리
    - send/close/socket 교체 구간 lock 보호
    - 자동 재연결(exponential backoff)
    - 대기 큐(flush 지원)
    - UI_ACK 기반 ACK 추적
    - stale delayed 작업 방지용 navigation token 지원
    - outgoing heartbeat 전송 지원
    """

    def __init__(self):
        self._connected = False
        self._reconnecting = False
        self._stopping = False

        self._loop: asyncio.AbstractEventLoop | None = None
        self._handlers: dict[str, Callable] = {}

        self._pending_queue: deque[tuple[str, str]] = deque(maxlen=200)

        self._ws_lock = threading.Lock()
        self._ack_lock = threading.Lock()
        self._token_lock = threading.Lock()

        self.ws: websocket.WebSocket | None = None
        self._receiver_thread: threading.Thread | None = None
        self._heartbeat_thread: threading.Thread | None = None

        self._recv_buffer = ""
        self._nav_token = 0

        self._pending_acks: dict[str, PendingAck] = {}
        self._last_send_time = 0.0

        self._ws_url = getattr(config, "WS_URL", "ws://localhost:8080/ws")
        self._reconnect_delay = getattr(config, "WS_RECONNECT_DELAY", 3)
        self._max_reconnect_tries = getattr(config, "WS_MAX_RECONNECT_TRIES", 10)

        self._sub_front_events = getattr(config, "STOMP_SUB_FRONT_EVENTS", "/topic/front/events")
        self._sub_front_ack = getattr(config, "STOMP_SUB_FRONT_ACK", "/topic/front/ack")
        self._pub_ui_prefix = getattr(config, "STOMP_PUB_UI_PREFIX", "/topic/ui")

        # STOMP CONNECT에서 heart-beat: 10000,10000 사용
        self._heartbeat_interval_sec = 10.0

    # ─────────────────────────────────────────
    # 연결 / 종료
    # ─────────────────────────────────────────
    def connect(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop
        self._stopping = False
        self._do_connect()

    def _do_connect(self):
        try:
            logger.info("WebSocket 연결 시도: %s", self._ws_url)
            new_ws = websocket.create_connection(self._ws_url, timeout=10)

            with self._ws_lock:
                self.ws = new_ws
                self._recv_buffer = ""

            self._send_frame(
                "CONNECT",
                {
                    "accept-version": "1.2",
                    "host": "localhost",
                    "heart-beat": "10000,10000",
                },
            )

            frame = self._recv_frame_blocking()
            if frame != "CONNECTED" and not frame.startswith("CONNECTED\n"):
                raise ConnectionError(f"STOMP CONNECT 실패: {frame[:200]}")

            self._connected = True
            logger.info("WebSocket/STOMP 연결 성공")

            self._subscribe_all()
            self._flush_pending_queue()
            self._cleanup_stale_acks()
            self._start_heartbeat_loop()

            if self._receiver_thread is None or not self._receiver_thread.is_alive():
                self._receiver_thread = threading.Thread(
                    target=self._receive_loop,
                    name="stomp-receiver",
                    daemon=True,
                )
                self._receiver_thread.start()

        except Exception as e:
            logger.error("WebSocket/STOMP 연결 실패: %s", e)
            self._connected = False
            self._schedule_reconnect()

    def _schedule_reconnect(self):
        if self._stopping or self._reconnecting:
            return
        self._reconnecting = True

        def _reconnect_loop():
            delay = max(1, self._reconnect_delay)

            for attempt in range(1, self._max_reconnect_tries + 1):
                if self._stopping or self._connected:
                    break

                logger.info(
                    "WebSocket 재연결 시도 %d/%d (%ds 후)",
                    attempt,
                    self._max_reconnect_tries,
                    delay,
                )
                time.sleep(delay)

                try:
                    self._close_socket()
                    self._do_connect()
                    if self._connected:
                        break
                except Exception as e:
                    logger.warning("재연결 실패: %s", e)
                    delay = min(delay * 2, 30)
            else:
                logger.critical("WebSocket 재연결 최대 시도 초과 — 수동 점검 필요")

            self._reconnecting = False

        threading.Thread(target=_reconnect_loop, name="stomp-reconnect", daemon=True).start()

    def disconnect(self):
        self._stopping = True
        self._connected = False
        self._fail_all_pending_acks()
        self._close_socket()
        self._loop = None
        logger.info("WebSocket/STOMP 연결 종료")

    def _close_socket(self):
        with self._ws_lock:
            ws = self.ws
            self.ws = None

        if ws is None:
            return

        try:
            try:
                ws.send("DISCONNECT\n\n\x00")
            except Exception:
                pass
            ws.close()
        except Exception:
            pass

    # ─────────────────────────────────────────
    # Heartbeat
    # ─────────────────────────────────────────
    def _start_heartbeat_loop(self):
        if self._heartbeat_thread is not None and self._heartbeat_thread.is_alive():
            return

        def _heartbeat_loop():
            while not self._stopping:
                time.sleep(self._heartbeat_interval_sec)

                if self._stopping or not self._connected:
                    continue

                try:
                    now = time.time()
                    if now - self._last_send_time < self._heartbeat_interval_sec:
                        continue

                    with self._ws_lock:
                        if self.ws is None:
                            continue
                        self.ws.send("\n")
                        self._last_send_time = time.time()

                    logger.debug("heartbeat 전송")
                except Exception as e:
                    logger.warning("heartbeat 전송 실패: %s", e)
                    self._connected = False
                    if not self._stopping:
                        self._schedule_reconnect()

        self._heartbeat_thread = threading.Thread(
            target=_heartbeat_loop,
            name="stomp-heartbeat",
            daemon=True,
        )
        self._heartbeat_thread.start()

    # ─────────────────────────────────────────
    # STOMP 프레임 송수신
    # ─────────────────────────────────────────
    def _send_frame(self, command: str, headers: dict | None = None, body: str = ""):
        headers = headers or {}
        frame = command + "\n"
        for k, v in headers.items():
            frame += f"{k}:{v}\n"
        frame += "\n"
        frame += body
        frame += "\x00"

        with self._ws_lock:
            if self.ws is None:
                raise ConnectionError("WebSocket이 연결되어 있지 않습니다.")
            self.ws.send(frame)
            self._last_send_time = time.time()

    def _recv_frame_blocking(self) -> str:
        while True:
            if "\x00" in self._recv_buffer:
                frame, self._recv_buffer = self._recv_buffer.split("\x00", 1)
                return frame

            ws = self.ws
            if ws is None:
                raise ConnectionError("WebSocket이 연결되어 있지 않습니다.")

            data = ws.recv()
            if isinstance(data, bytes):
                data = data.decode("utf-8", errors="ignore")

            # heartbeat 또는 공백 프레임
            if data.strip() == "":
                return "\n"

            self._recv_buffer += data

    @staticmethod
    def _parse_frame(raw_frame: str):
        raw_frame = raw_frame.replace("\r\n", "\n")
        parts = raw_frame.split("\n\n", 1)
        header_part = parts[0]
        body = parts[1] if len(parts) > 1 else ""

        lines = header_part.split("\n")
        command = lines[0].strip()
        headers: dict[str, str] = {}

        for line in lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip()] = v.strip()

        return command, headers, body

    def _receive_loop(self):
        try:
            while not self._stopping:
                raw = self._recv_frame_blocking()

                if raw == "\n":
                    continue

                command, headers, body = self._parse_frame(raw)

                if command == "MESSAGE":
                    dest = headers.get("destination", "")
                    try:
                        payload = json.loads(body)
                    except json.JSONDecodeError:
                        logger.warning("수신 메시지 JSON 파싱 실패: %s", body[:200])
                        continue

                    logger.info("수신 ← [%s] action=%s", dest, payload.get("action"))
                    self._handle_message(dest, payload)

                elif command == "ERROR":
                    logger.error("STOMP ERROR: %s", body)

        except Exception as e:
            if not self._stopping and self._connected:
                logger.warning("WebSocket 연결 끊김 — 자동 재연결 시도: %s", e)
            self._connected = False
            if not self._stopping:
                self._schedule_reconnect()

    # ─────────────────────────────────────────
    # 구독 / 핸들러
    # ─────────────────────────────────────────
    def _subscribe_all(self):
        subs = [
            (self._sub_front_events, "sub-events"),
            (self._sub_front_ack, "sub-ack"),
        ]
        for dest, sub_id in subs:
            try:
                self._send_frame(
                    "SUBSCRIBE",
                    {
                        "id": sub_id,
                        "destination": dest,
                        "ack": "auto",
                    },
                )
                logger.info("구독 등록: %s", dest)
            except Exception as e:
                logger.error("구독 실패 [%s]: %s", dest, e)

    def register_handler(self, action: str, callback):
        self._handlers[action] = callback
        logger.info("핸들러 등록: action='%s'", action)

    def _handle_message(self, destination: str, payload: dict):
        action = payload.get("action")

        if action == "UI_ACK":
            self._resolve_ack(payload)
            # 의도적으로 return하지 않음.
            # UI_ACK는 내부 ACK 해소 후에도 외부 로깅/모니터링 핸들러로 전달 가능.

        handler = self._handlers.get(action)
        if not handler:
            logger.debug("미등록 action 수신 무시: %s", action)
            return

        self._dispatch_message(destination, payload)

    def _dispatch_message(self, destination: str, payload: dict):
        action = payload.get("action")
        handler = self._handlers.get(action)
        if not handler:
            return

        if self._loop is None or self._loop.is_closed():
            logger.warning("asyncio 루프 미설정 — 현재 스레드에서 직접 실행: %s", action)
            try:
                handler(payload)
            except Exception as e:
                logger.error("핸들러 오류 [%s]: %s", action, e)
            return

        if asyncio.iscoroutinefunction(handler):
            def _schedule_coro():
                self._loop.create_task(self._safe_async_handler(action, handler, payload))
            self._loop.call_soon_threadsafe(_schedule_coro)
        else:
            def _run_sync():
                try:
                    handler(payload)
                except Exception as e:
                    logger.error("핸들러 오류 [%s]: %s", action, e)
            self._loop.call_soon_threadsafe(_run_sync)

    @staticmethod
    async def _safe_async_handler(action: str, handler, payload: dict):
        try:
            await handler(payload)
        except Exception as e:
            logger.error("비동기 핸들러 오류 [%s]: %s", action, e)

    # ─────────────────────────────────────────
    # ACK 추적
    # ─────────────────────────────────────────
    def _register_ack(self, command_id: str, action: str) -> PendingAck:
        pending = PendingAck(
            command_id=command_id,
            action=action,
            event=threading.Event(),
            created_at=time.time(),
        )
        with self._ack_lock:
            self._pending_acks[command_id] = pending
        return pending

    def _resolve_ack(self, payload: dict):
        data = payload.get("data", {}) or {}
        command_id = data.get("commandId")
        applied_action = data.get("appliedAction")

        if not command_id:
            logger.debug("UI_ACK에 commandId 없음")
            return

        with self._ack_lock:
            pending = self._pending_acks.pop(command_id, None)

        if pending:
            logger.info("ACK 수신: commandId=%s action=%s", command_id, applied_action or pending.action)
            pending.event.set()
        else:
            logger.debug("대기 중이지 않은 ACK 수신: %s", command_id)

    def _fail_all_pending_acks(self):
        with self._ack_lock:
            pendings = list(self._pending_acks.values())
            self._pending_acks.clear()

        for pending in pendings:
            pending.event.set()

    def _cleanup_stale_acks(self, ttl_sec: int = 30):
        now = time.time()
        stale_ids = []

        with self._ack_lock:
            for command_id, pending in self._pending_acks.items():
                if now - pending.created_at > ttl_sec:
                    stale_ids.append(command_id)

            for command_id in stale_ids:
                pending = self._pending_acks.pop(command_id, None)
                if pending:
                    pending.event.set()

        if stale_ids:
            logger.warning("오래된 ACK 대기 항목 제거: %d건", len(stale_ids))

    # ─────────────────────────────────────────
    # 송신 / 큐
    # ─────────────────────────────────────────
    def _flush_pending_queue(self):
        sent = 0
        while self._pending_queue:
            dest, body = self._pending_queue.popleft()
            try:
                self._send_frame(
                    "SEND",
                    {
                        "destination": dest,
                        "content-type": "application/json",
                    },
                    body,
                )
                sent += 1
            except Exception as e:
                self._pending_queue.appendleft((dest, body))
                logger.warning("큐 플러시 중 전송 실패: %s", e)
                break

        if sent:
            logger.info("대기 큐 메시지 %d건 전송 완료", sent)

    def send_command(
        self,
        session_id: str | None,
        action: str,
        payload: dict | None = None,
        *,
        wait_ack: bool = False,
        ack_timeout_sec: float = 3.0,
    ) -> bool:
        command_id = str(uuid.uuid4())
        message = {
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "commandId": command_id,
            "data": payload or {},
        }
        dest = f"{self._pub_ui_prefix}/{session_id}" if session_id else f"{self._pub_ui_prefix}/global"
        body = json.dumps(message, ensure_ascii=False)

        pending: PendingAck | None = None
        if wait_ack:
            pending = self._register_ack(command_id, action)

        if not self._connected:
            logger.warning("WebSocket 미연결 — 대기 큐 보관: %s", action)
            self._pending_queue.append((dest, body))

            # 현재 호출 컨텍스트에서는 즉시 실패로 간주하므로 orphan ACK 제거
            if wait_ack and pending is not None:
                with self._ack_lock:
                    self._pending_acks.pop(command_id, None)

            return False

        try:
            self._send_frame(
                "SEND",
                {
                    "destination": dest,
                    "content-type": "application/json",
                },
                body,
            )
            logger.info("송신 → [%s] action=%s commandId=%s", dest, action, command_id)

            if not wait_ack or pending is None:
                return True

            ok = pending.event.wait(timeout=ack_timeout_sec)
            if not ok:
                with self._ack_lock:
                    self._pending_acks.pop(command_id, None)
                logger.warning("ACK 타임아웃: action=%s commandId=%s", action, command_id)
                return False

            return True

        except Exception as e:
            logger.error("메시지 전송 오류: %s — 대기 큐 보관", e)
            self._pending_queue.append((dest, body))
            self._connected = False

            if wait_ack and pending is not None:
                with self._ack_lock:
                    self._pending_acks.pop(command_id, None)

            self._schedule_reconnect()
            return False

    def adapt_mode(self, user_type: str, *, wait_ack: bool = False) -> bool:
        settings = config.USER_CONFIGS.get(user_type, config.USER_CONFIGS["NORMAL"])
        success = self.send_command(
            None,
            "ADAPT_UI",
            {
                "userType": user_type,
                "settings": settings,
            },
            wait_ack=wait_ack,
        )
        logger.info("UI 모드 송출: %s [%s]", user_type, "성공" if success else "실패/큐 대기")
        return success

    # ─────────────────────────────────────────
    # stale delayed 작업 방지
    # ─────────────────────────────────────────
    def reset_navigation(self):
        with self._token_lock:
            self._nav_token += 1
            logger.debug("navigation token 증가: %s", self._nav_token)

    def get_navigation_token(self) -> int:
        with self._token_lock:
            return self._nav_token

    def run_delayed(self, delay_sec: float, callback: Callable[[], Any]):
        token = self.get_navigation_token()

        def _wrapper():
            current = self.get_navigation_token()
            if token != current:
                logger.info("stale delayed 작업 무시")
                return
            try:
                callback()
            except Exception as e:
                logger.error("delayed 작업 오류: %s", e)

        timer = threading.Timer(delay_sec, _wrapper)
        timer.daemon = True
        timer.start()
        return timer