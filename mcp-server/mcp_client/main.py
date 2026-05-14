# main.py
import asyncio
import logging

import config
from stomp_manager import UIController
from mcp_client import MCPToolManager, MCPError
from intent_analyzer import IntentAnalyzer
from session_manager import SessionManager
from ai_client import AIClient, AIClientError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("kiosk.main")


# ──────────────────────────────────────────────────────────
#  음성 안내 문구 상수
# ──────────────────────────────────────────────────────────
GUIDE_TEXT = {
    "SESSION_START": {
        "NORMAL":      "안녕하세요. 무엇을 도와드릴까요?",
        "ELDERLY":     "안녕하세요. 천천히 도와드리겠습니다. 원하시는 서비스를 말씀해 주세요.",
        "WHEELCHAIR":  "안녕하세요. 화면이 낮게 조정되었습니다. 편하게 이용하세요.",
    },
    "SERVICE_ENTER": {
        "NORMAL":      "서비스 화면으로 이동합니다.",
        "ELDERLY":     "서비스 화면으로 이동합니다. 글자 크기를 크게 설정했습니다.",
        "WHEELCHAIR":  "서비스 화면으로 이동합니다. 낮은 화면 모드로 전환되었습니다.",
    },
    "MODE_CHANGE": {
        "NORMAL":      "일반 모드로 전환되었습니다.",
        "ELDERLY":     "어르신 모드로 전환되었습니다. 큰 글씨와 고대비 화면으로 설정됩니다.",
        "WHEELCHAIR":  "휠체어 모드로 전환되었습니다. 낮은 화면 모드로 설정됩니다.",
    },
    "HOME": {
        "NORMAL":      "처음 화면으로 돌아갑니다.",
        "ELDERLY":     "처음 화면으로 돌아갑니다. 감사합니다.",
        "WHEELCHAIR":  "처음 화면으로 돌아갑니다. 감사합니다.",
    },
    "SESSION_END": {
        "NORMAL":      "이용해 주셔서 감사합니다.",
        "ELDERLY":     "이용해 주셔서 감사합니다. 안녕히 가세요.",
        "WHEELCHAIR":  "이용해 주셔서 감사합니다. 안녕히 가세요.",
    },

    # ── 주민등록등본 발급 (serviceId: 102) ──────────────────
    "CERTIFICATE_SELECT_PURPOSE": {
        "NORMAL":     "등본 용도를 선택해 주세요.",
        "ELDERLY":    "등본을 어디에 쓰실 건지 선택해 주세요. 천천히 골라 주세요.",
        "WHEELCHAIR": "등본 용도를 선택해 주세요.",
    },
    "CERTIFICATE_SELECT_COUNT": {
        "NORMAL":     "발급 매수를 선택해 주세요.",
        "ELDERLY":    "몇 장 필요하신지 선택해 주세요.",
        "WHEELCHAIR": "발급 매수를 선택해 주세요.",
    },
    "CERTIFICATE_SELECT_SCOPE": {
        "NORMAL":     "주민등록번호 공개 범위를 선택해 주세요.",
        "ELDERLY":    "주민등록번호를 어디까지 보여줄지 선택해 주세요.",
        "WHEELCHAIR": "주민등록번호 공개 범위를 선택해 주세요.",
    },
    "CERTIFICATE_CONFIRM": {
        "NORMAL":     "입력하신 내용을 확인해 주세요. 맞으면 발급 버튼을 눌러 주세요.",
        "ELDERLY":    "내용을 천천히 확인해 주세요. 맞으시면 발급 버튼을 눌러 주세요.",
        "WHEELCHAIR": "입력하신 내용을 확인해 주세요. 맞으면 발급 버튼을 눌러 주세요.",
    },
    "CERTIFICATE_PRINTING": {
        "NORMAL":     "출력 중입니다. 잠시 기다려 주세요.",
        "ELDERLY":    "출력 중입니다. 잠깐만 기다려 주세요.",
        "WHEELCHAIR": "출력 중입니다. 서류가 아래 출력구에서 나옵니다.",
    },
    "CERTIFICATE_COMPLETE": {
        "NORMAL":     "등본 출력이 완료되었습니다. 서류를 가져가 주세요.",
        "ELDERLY":    "등본이 나왔습니다. 서류를 꼭 챙겨 가세요.",
        "WHEELCHAIR": "등본 출력이 완료되었습니다. 아래 출력구에서 서류를 가져가 주세요.",
    },

    # ── 전입신고 (serviceId: 101) ────────────────────────────
    "MOVEIN_INPUT_PREV_ADDRESS": {
        "NORMAL":     "이전 주소를 입력해 주세요.",
        "ELDERLY":    "이사 오시기 전 살던 주소를 입력해 주세요.",
        "WHEELCHAIR": "이전 주소를 입력해 주세요.",
    },
    "MOVEIN_INPUT_NEW_ADDRESS": {
        "NORMAL":     "새로운 주소를 입력해 주세요.",
        "ELDERLY":    "이사 오신 새 주소를 입력해 주세요.",
        "WHEELCHAIR": "새로운 주소를 입력해 주세요.",
    },
    "MOVEIN_SELECT_DATE": {
        "NORMAL":     "전입일을 선택해 주세요.",
        "ELDERLY":    "이사 오신 날짜를 선택해 주세요.",
        "WHEELCHAIR": "전입일을 선택해 주세요.",
    },
    "MOVEIN_INPUT_MEMBERS": {
        "NORMAL":     "전입 세대원 정보를 입력해 주세요.",
        "ELDERLY":    "함께 이사 오신 가족이 있으면 입력해 주세요.",
        "WHEELCHAIR": "전입 세대원 정보를 입력해 주세요.",
    },
    "MOVEIN_CONFIRM": {
        "NORMAL":     "입력하신 내용을 확인해 주세요. 맞으면 신고 버튼을 눌러 주세요.",
        "ELDERLY":    "내용을 천천히 확인해 주세요. 맞으시면 신고 버튼을 눌러 주세요.",
        "WHEELCHAIR": "입력하신 내용을 확인해 주세요. 맞으면 신고 버튼을 눌러 주세요.",
    },
    "MOVEIN_COMPLETE": {
        "NORMAL":     "전입신고가 완료되었습니다.",
        "ELDERLY":    "전입신고가 완료되었습니다. 고생하셨습니다.",
        "WHEELCHAIR": "전입신고가 완료되었습니다.",
    },

    # ── 공통 오류 ────────────────────────────────────────────
    "ERROR_RETRY": {
        "NORMAL":     "오류가 발생했습니다. 다시 시도해 주세요.",
        "ELDERLY":    "잠깐 문제가 생겼습니다. 다시 한번 눌러 주세요.",
        "WHEELCHAIR": "오류가 발생했습니다. 다시 시도해 주세요.",
    },
    "ERROR_TIMEOUT": {
        "NORMAL":     "시간이 초과되었습니다. 처음 화면으로 돌아갑니다.",
        "ELDERLY":    "시간이 지났습니다. 처음 화면으로 돌아갑니다. 천천히 다시 시작해 주세요.",
        "WHEELCHAIR": "시간이 초과되었습니다. 처음 화면으로 돌아갑니다.",
    },
}


def _guide_text(context: str, user_type: str) -> str:
    """context + user_type 조합으로 안내 문구를 반환한다. 없으면 빈 문자열."""
    return GUIDE_TEXT.get(context, {}).get(user_type, "")


# ──────────────────────────────────────────────────────────
#  메인 컨트롤러
# ──────────────────────────────────────────────────────────

class KioskMainController:
    """
    변경 이력
    ─────────────────────────────────────────────────────────
    - start_session / start_service / end_session 분리 적용
    - 모든 세션 종료 경로(완료·취소·만료·오류)에서 end_session 호출
    - voice_guide를 5개 맥락(SESSION_START / SERVICE_ENTER /
      MODE_CHANGE / HOME / SESSION_END)에서 MCP 서버에 요청 후
      STOMP VOICE_GUIDE 커맨드로 프론트에 전달
    - _handle_voice 내 들여쓰기 버그 수정 (기존 코드)
    ─────────────────────────────────────────────────────────
    """

    def __init__(self):
        self.ui = UIController()
        self.mcp = MCPToolManager()
        self.ai = IntentAnalyzer()
        self.ai_http = AIClient()
        self.sessions = SessionManager()
        self.current_user_type = "NORMAL"
        self._loop: asyncio.AbstractEventLoop | None = None

        self.ui.register_handler("USER_TOUCH", self._on_user_touch)
        self.ui.register_handler("SERVICE_COMPLETE", self._on_service_complete)
        self.ui.register_handler("UI_ACK", self._on_ui_ack)
        self.ui.register_handler("USER_CANCEL", self._on_user_cancel)
        self.ui.register_handler("VOICE_INPUT", self._on_voice_input)
        self.ui.register_handler("STEP_CHANGE", self._on_step_change)
        self.sessions.set_timeout_callback(self._on_session_timeout)

    # ── 생명주기 ────────────────────────────────

    async def start(self):
        self._loop = asyncio.get_running_loop()
        self.ui.connect(loop=self._loop)
        self.sessions.start()
        logger.info("키오스크 컨트롤러 기동 완료")

    async def shutdown(self):
        await self.sessions.stop()
        await self.mcp.disconnect()
        self.ui.disconnect()
        logger.info("키오스크 컨트롤러 종료 완료")

    # ── 외부 진입점 ─────────────────────────────

    async def handle_request(self, trigger_type: str, data):
        if trigger_type == "CHANGE_MODE":
            await self._change_mode(data)
        elif trigger_type == "VOICE_INPUT":
            await self._handle_voice(data)
        elif trigger_type == "TOUCH_SERVICE":
            await self._handle_touch(data)
        else:
            logger.warning("알 수 없는 trigger_type: %s", trigger_type)

    # ── 모드 전환 ────────────────────────────────

    async def _change_mode(self, user_type: str):
        """
        UI 모드를 전환하고 STOMP ADAPT_UI 커맨드를 전송한다.
        모드 전환 후 MCP voice_guide(MODE_CHANGE)를 호출해 안내 음성을 발화한다.
        """
        if user_type not in config.USER_CONFIGS:
            logger.warning("미지원 사용자 유형 '%s' → NORMAL 대체", user_type)
            user_type = "NORMAL"

        self.current_user_type = user_type
        success = self.ui.adapt_mode(self.current_user_type, wait_ack=True)
        logger.info(
            "모드 변경: %s [%s]",
            self.current_user_type,
            "ACK 수신" if success else "ACK 실패/큐 대기",
        )

        # 모드 전환 음성 안내 (세션 무관 → session_id="global")
        await self._send_voice_guide(
            session_id="global",
            context="MODE_CHANGE",
            user_type=user_type,
        )

    # ── 음성 입력 처리 ───────────────────────────

    async def _handle_voice(self, data):
        """
        data 예시:
        - str  : "주민등록등본 발급받고 싶어요"
        - dict : {"text": "...", "sessionId": "...", "locale": "ko-KR"}
        """
        try:
            if isinstance(data, str):
                user_text = data
                session_id_hint = "string"
                locale = "ko-KR"
            elif isinstance(data, dict):
                user_text = str(data.get("text", ""))
                session_id_hint = str(data.get("sessionId", "string"))
                locale = str(data.get("locale", "ko-KR"))
            else:
                logger.warning("VOICE_INPUT 형식 오류: %s", type(data).__name__)
                return

            if not user_text.strip():
                logger.warning("VOICE_INPUT text가 비어 있음")
                return

            # 1) AI 서버 HTTP 호출
            ai_raw = await asyncio.to_thread(
                self.ai_http.classify_service,
                user_text,
                session_id_hint,
                locale,
            )

            # 2) IntentAnalyzer 정규화
            ai_res = self.ai.parse_voice_intent(ai_raw)

        except AIClientError as e:
            logger.error("[AI 서버 호출 실패] %s", e)
            return
        except Exception as e:
            logger.error("[AI 분석 실패] %s", e)
            return

        if not ai_res or ai_res.get("confidence", 0) < 0.6:
            logger.info("AI 분석 신뢰도 부족 — 요청 무시")
            return

        await self._change_mode(ai_res.get("userType", "NORMAL"))

        service_id = ai_res.get("serviceId")
        if service_id is None:
            logger.info("AI 응답에 serviceId 없음 — 서비스 진입 생략")
            return

        await self._execute_service(service_id)

    # ── 터치 입력 처리 ───────────────────────────

    async def _handle_touch(self, service_id):
        if service_id is None:
            logger.warning("service_id 비어 있음 — 요청 무시")
            return
        await self._execute_service(service_id)

    # ══════════════════════════════════════════════
    #  서비스 실행 핵심 흐름
    #
    #  start_session → voice_guide(SESSION_START)
    #    → start_service → voice_guide(SERVICE_ENTER)
    #      → STOMP MOVE_PAGE
    # ══════════════════════════════════════════════

    async def _execute_service(self, service_id: int):
        # ── 1. start_session ────────────────────
        try:
            session_result = await self.mcp.start_session(self.current_user_type)
        except ConnectionError as e:
            logger.error("[MCP start_session 연결 실패] %s", e)
            return
        except MCPError as e:
            logger.error("[MCP start_session 응답 오류] %s", e)
            return
        except Exception as e:
            logger.error("[MCP start_session 예외] %s", e)
            return

        session_id = session_result["sessionId"]
        settings = session_result.get("settings") or config.USER_CONFIGS[self.current_user_type]

        # 로컬 SessionManager에도 등록
        self.sessions.create(session_id, self.current_user_type)

        # ── 2. voice_guide — SESSION_START ───────
        await self._send_voice_guide(
            session_id=session_id,
            context="SESSION_START",
            user_type=self.current_user_type,
        )

        # ── 3. start_service ─────────────────────
        try:
            service_result = await self.mcp.start_service(
                session_id=session_id,
                service_id=service_id,
                user_type=self.current_user_type,
            )
        except ConnectionError as e:
            logger.error("[MCP start_service 연결 실패] %s", e)
            await self._end_session_safe(session_id, reason="ERROR")
            return
        except MCPError as e:
            logger.error("[MCP start_service 응답 오류] %s", e)
            await self._end_session_safe(session_id, reason="ERROR")
            return
        except Exception as e:
            logger.error("[MCP start_service 예외] %s", e)
            await self._end_session_safe(session_id, reason="ERROR")
            return

        # 서비스 메타데이터 (서버가 내려주면 활용, 없으면 로컬 값 사용)
        resolved_service_id = service_result.get("serviceId", service_id)
        service_name = service_result.get("serviceName", "")

        # 로컬 세션 활성화
        self.sessions.activate(session_id, resolved_service_id)

        # ── 4. voice_guide — SERVICE_ENTER ───────
        await self._send_voice_guide(
            session_id=session_id,
            context="SERVICE_ENTER",
            user_type=self.current_user_type,
        )

        # ── 5. STOMP MOVE_PAGE ───────────────────
        self.ui.reset_navigation()

        def _move():
            success = self.ui.send_command(
                session_id,
                "MOVE_PAGE",
                {
                    "serviceId": resolved_service_id,
                    "serviceName": service_name,
                    "userType": self.current_user_type,
                    "settings": settings,
                },
                wait_ack=True,
                ack_timeout_sec=3.0,
            )
            if success:
                logger.info(
                    "서비스 진입: %d '%s' (세션: %s, 모드: %s)",
                    resolved_service_id, service_name,
                    session_id, self.current_user_type,
                )
            else:
                logger.warning("페이지 이동 명령 전송 실패/ACK 실패 (세션: %s)", session_id)

        self.ui.run_delayed(0.05, _move)

    # ══════════════════════════════════════════════
    #  음성 안내 공통 헬퍼
    # ══════════════════════════════════════════════

    async def _send_voice_guide(
        self,
        session_id: str,
        context: str,
        user_type: str,
    ):
        """
        MCP voice_guide를 호출한 뒤 결과를 STOMP VOICE_GUIDE 커맨드로 전송한다.

        - audioUrl이 있으면 프론트가 오디오 파일을 직접 재생한다.
        - audioUrl이 없으면 guideText를 받아 프론트(또는 OS TTS)가 읽어준다.
        - MCP 호출 실패 시 로컬 fallback 텍스트로 VOICE_GUIDE를 전송한다.
        """
        fallback_text = _guide_text(context, user_type)

        try:
            guide_result = await self.mcp.voice_guide(
                session_id=session_id,
                text=fallback_text,
                user_type=user_type,
                context=context,
            )
            guide_text = guide_result.get("guideText", fallback_text)
            audio_url = guide_result.get("audioUrl")
            lang = guide_result.get("lang", "ko-KR")
        except Exception as e:
            logger.warning("[voice_guide MCP 실패 → fallback 사용] %s", e)
            guide_text = fallback_text
            audio_url = None
            lang = "ko-KR"

        if not guide_text and not audio_url:
            logger.debug("voice_guide: 안내 내용 없음 — 전송 생략 (context=%s)", context)
            return

        self.ui.send_command(
            session_id if session_id != "global" else None,
            "VOICE_GUIDE",
            {
                "context": context,
                "guideText": guide_text,
                "audioUrl": audio_url,
                "lang": lang,
                "userType": user_type,
            },
            wait_ack=False,  # 음성 안내는 비blocking
        )
        logger.info(
            "VOICE_GUIDE 전송 — context=%s userType=%s text=%.40s… audioUrl=%s",
            context, user_type, guide_text, audio_url,
        )

    # ══════════════════════════════════════════════
    #  세션 종료 공통 헬퍼
    # ══════════════════════════════════════════════

    async def _end_session_safe(self, session_id: str, reason: str = "COMPLETED"):
        """
        MCP end_session을 호출한다.
        실패해도 예외를 전파하지 않는다 (best-effort).
        """
        try:
            await self.mcp.end_session(session_id=session_id, reason=reason)
        except Exception as e:
            logger.warning("[MCP end_session 실패 — 무시] sessionId=%s reason=%s err=%s",
                           session_id, reason, e)

    # ══════════════════════════════════════════════
    #  STOMP 이벤트 핸들러
    # ══════════════════════════════════════════════

    def _on_voice_input(self, payload: dict):
        """
        프론트 → 백엔드 STOMP VOICE_INPUT 이벤트 핸들러

        프론트가 STT(음성 인식) 결과를 STOMP로 전송하면 이 핸들러가 수신해
        기존 _handle_voice() 흐름으로 위임한다.

        예상 payload:
        {
            "action": "VOICE_INPUT",
            "data": {
                "text":      "주민등록등본 발급받고 싶어요",  # STT 인식 결과 (필수)
                "sessionId": "abc-123",                      # 선택
                "locale":    "ko-KR"                         # 선택
            }
        }
        """
        data = payload.get("data", {})
        text = str(data.get("text", "")).strip()

        if not text:
            logger.warning("VOICE_INPUT payload에 text 없음 — 무시: %s", payload)
            return

        logger.info("STOMP VOICE_INPUT 수신 — text=%.60s…", text)

        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(
                lambda: self._loop.create_task(
                    self._handle_voice(data)
                )
            )
        else:
            logger.error("VOICE_INPUT 수신 시 asyncio 루프 없음 — 처리 불가")
    # 핸들러 구현
    def _on_step_change(self, payload: dict):
        data = payload.get("data", {})
        session_id = data.get("sessionId")
        step = data.get("step")
    
        if not step or not session_id:
            return

        self.sessions.touch(session_id)  # 활동 시각 갱신

        if self._loop:
            self._loop.call_soon_threadsafe(
                lambda: self._loop.create_task(
                    self._send_voice_guide(
                        session_id=session_id,
                        context=step,        # GUIDE_TEXT 키로 바로 사용
                        user_type=self.current_user_type,
                    )
                )
            )
    def _on_user_touch(self, payload: dict):
        session_id = payload.get("data", {}).get("sessionId")
        if session_id:
            self.sessions.touch(session_id)
            logger.info("사용자 활동 수신 (세션: %s)", session_id)

    def _on_service_complete(self, payload: dict):
        session_id = payload.get("data", {}).get("sessionId")
        if session_id:
            self.sessions.complete(session_id)
            logger.info("서비스 완료 수신 (세션: %s)", session_id)
            # 비동기 컨텍스트가 필요한 작업은 loop에 위임
            if self._loop:
                self._loop.call_soon_threadsafe(
                    lambda: self._loop.create_task(
                        self._on_service_complete_async(session_id)
                    )
                )
        else:
            self._return_to_home()

    async def _on_service_complete_async(self, session_id: str):
        await self._send_voice_guide(
            session_id=session_id,
            context="SESSION_END",
            user_type=self.current_user_type,
        )
        await self._end_session_safe(session_id, reason="COMPLETED")
        self._return_to_home()

    def _on_ui_ack(self, payload: dict):
        action = payload.get("data", {}).get("appliedAction")
        command_id = payload.get("data", {}).get("commandId")
        logger.info("프론트 ACK 수신: %s 적용 완료 (commandId=%s)", action, command_id)

    def _on_user_cancel(self, payload: dict):
        session_id = payload.get("data", {}).get("sessionId")
        if session_id:
            self.sessions.fail(session_id)
            logger.info("사용자 취소 (세션: %s)", session_id)
            if self._loop:
                self._loop.call_soon_threadsafe(
                    lambda: self._loop.create_task(
                        self._on_user_cancel_async(session_id)
                    )
                )
        else:
            self._return_to_home()

    async def _on_user_cancel_async(self, session_id: str):
        await self._end_session_safe(session_id, reason="CANCELLED")
        self._return_to_home()

    def _on_session_timeout(self, session):
        logger.warning("세션 만료 처리: %s — 홈 복귀", session.session_id)
        self.ui.reset_navigation()
        self.ui.send_command(
            session.session_id,
            "SESSION_EXPIRED",
            {"message": "시간이 초과되었습니다. 처음 화면으로 돌아갑니다."},
            wait_ack=True,
            ack_timeout_sec=2.0,
        )
        if self._loop:
            self._loop.call_soon_threadsafe(
                lambda: self._loop.create_task(
                    self._on_session_timeout_async(session.session_id)
                )
            )

    async def _on_session_timeout_async(self, session_id: str):
        await self._end_session_safe(session_id, reason="TIMEOUT")
        self._return_to_home()

    # ── 홈 복귀 ──────────────────────────────────

    def _return_to_home(self):
        """
        홈 화면 이동.
        - stale delayed navigation 무효화
        - GO_HOME ACK 대기
        - voice_guide(HOME) 는 비동기이므로 loop에 위임
        - 모드는 유지 (프론트가 page/mode 상태를 분리 관리)
        """
        self.ui.reset_navigation()
        success = self.ui.send_command(
            None,
            "GO_HOME",
            {"message": "처음 화면으로 돌아갑니다."},
            wait_ack=True,
            ack_timeout_sec=3.0,
        )
        logger.info(
            "홈 화면 복귀 완료 (모드 유지: %s, ack=%s)",
            self.current_user_type, success,
        )

        # HOME 음성 안내 (loop에 위임)
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(
                lambda: self._loop.create_task(
                    self._send_voice_guide(
                        session_id="global",
                        context="HOME",
                        user_type=self.current_user_type,
                    )
                )
            )


# ──────────────────────────────────────────────────────────
#  엔트리포인트
# ──────────────────────────────────────────────────────────

async def main():
    controller = KioskMainController()
    await controller.start()

    try:
        await asyncio.Event().wait()
    finally:
        await controller.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
