# main.py
import asyncio
import logging

import config
from stomp_manager import UIController
from mcp_client import MCPToolManager, MCPError
from intent_analyzer import IntentAnalyzer
from session_manager import SessionManager, SessionState
from ai_client import AIClient, AIClientError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("kiosk.main")


# ──────────────────────────────────────────────────────────
#  음성 안내 문구 상수 (AI 호출 실패 시 폴백 전용)
# ──────────────────────────────────────────────────────────
GUIDE_TEXT = {
    "SESSION_START": {
        "NORMAL":        "안녕하세요. 무엇을 도와드릴까요?",
        "ELDERLY":       "안녕하세요. 천천히 도와드리겠습니다. 원하시는 서비스를 말씀해 주세요.",
        "HIGH_CONTRAST": "안녕하세요. 고대비 모드로 이용하실 수 있습니다. 무엇을 도와드릴까요?",
        "WHEELCHAIR":    "안녕하세요. 화면이 낮게 조정되었습니다. 편하게 이용하세요.",
    },
    "SERVICE_ENTER": {
        "NORMAL":        "서비스 화면으로 이동합니다.",
        "ELDERLY":       "서비스 화면으로 이동합니다. 글자 크기를 크게 설정했습니다.",
        "HIGH_CONTRAST": "서비스 화면으로 이동합니다. 고대비 모드로 표시됩니다.",
        "WHEELCHAIR":    "서비스 화면으로 이동합니다. 낮은 화면 모드로 전환되었습니다.",
    },
    "MODE_CHANGE": {
        "NORMAL":        "일반 모드로 전환되었습니다.",
        "ELDERLY":       "어르신 모드로 전환되었습니다. 글자 크기를 크게 설정합니다.",
        "HIGH_CONTRAST": "고대비 모드로 전환되었습니다. 화면 대비를 높게 설정합니다.",
        "WHEELCHAIR":    "휠체어 모드로 전환되었습니다. 낮은 화면 모드로 설정됩니다.",
    },
    "HOME": {
        "NORMAL":        "처음 화면으로 돌아갑니다.",
        "ELDERLY":       "처음 화면으로 돌아갑니다. 감사합니다.",
        "HIGH_CONTRAST": "처음 화면으로 돌아갑니다.",
        "WHEELCHAIR":    "처음 화면으로 돌아갑니다. 감사합니다.",
    },
    "SESSION_END": {
        "NORMAL":        "이용해 주셔서 감사합니다.",
        "ELDERLY":       "이용해 주셔서 감사합니다. 안녕히 가세요.",
        "HIGH_CONTRAST": "이용해 주셔서 감사합니다.",
        "WHEELCHAIR":    "이용해 주셔서 감사합니다. 안녕히 가세요.",
    },

    "CERTIFICATE_SELECT_PURPOSE": {
        "NORMAL":        "발급할 증명서 종류를 선택해 주세요.",
        "ELDERLY":       "발급받으실 증명서 종류를 선택해 주세요.",
        "HIGH_CONTRAST": "발급할 증명서 종류를 선택해 주세요.",
        "WHEELCHAIR":    "발급할 증명서 종류를 선택해 주세요.",
    },
    "CERTIFICATE_SELECT_RRN": {
        "NORMAL":        "주민등록번호를 입력해 주세요.",
        "ELDERLY":       "주민등록번호 앞자리와 뒷자리를 천천히 입력해 주세요.",
        "HIGH_CONTRAST": "주민등록번호를 입력해 주세요.",
        "WHEELCHAIR":    "주민등록번호를 입력해 주세요.",
    },
    "CERTIFICATE_SELECT_SCOPE": {
        "NORMAL":        "발급 형태를 선택해 주세요.",
        "ELDERLY":       "발급 형태를 선택해 주세요.",
        "HIGH_CONTRAST": "발급 형태를 선택해 주세요.",
        "WHEELCHAIR":    "발급 형태를 선택해 주세요.",
    },
    "CERTIFICATE_SELECT_COUNT": {
        "NORMAL":        "발급 매수를 선택해 주세요.",
        "ELDERLY":       "몇 장 필요하신지 선택해 주세요.",
        "HIGH_CONTRAST": "발급 매수를 선택해 주세요.",
        "WHEELCHAIR":    "발급 매수를 선택해 주세요.",
    },
    "CERTIFICATE_CONFIRM": {
        "NORMAL":        "입력하신 내용을 확인해 주세요. 맞으면 제출 버튼을 눌러 주세요.",
        "ELDERLY":       "내용을 천천히 확인해 주세요. 맞으시면 제출 버튼을 눌러 주세요.",
        "HIGH_CONTRAST": "입력하신 내용을 확인해 주세요. 맞으면 제출 버튼을 눌러 주세요.",
        "WHEELCHAIR":    "입력하신 내용을 확인해 주세요. 맞으면 제출 버튼을 눌러 주세요.",
    },
    "CERTIFICATE_PRINTING": {
        "NORMAL":        "출력 중입니다. 잠시 기다려 주세요.",
        "ELDERLY":       "출력 중입니다. 잠깐만 기다려 주세요.",
        "HIGH_CONTRAST": "출력 중입니다. 잠시 기다려 주세요.",
        "WHEELCHAIR":    "출력 중입니다. 서류가 아래 출력구에서 나옵니다.",
    },
    "CERTIFICATE_COMPLETE": {
        "NORMAL":        "등본 출력이 완료되었습니다. 서류를 가져가 주세요.",
        "ELDERLY":       "등본이 나왔습니다. 서류를 꼭 챙겨 가세요.",
        "HIGH_CONTRAST": "등본 출력이 완료되었습니다. 서류를 가져가 주세요.",
        "WHEELCHAIR":    "등본 출력이 완료되었습니다. 아래 출력구에서 서류를 가져가 주세요.",
    },

    "MOVEIN_INPUT_BASIC_INFO": {
        "NORMAL":        "본인확인 및 기본정보를 입력해 주세요.",
        "ELDERLY":       "본인확인 및 기본정보를 천천히 입력해 주세요.",
        "HIGH_CONTRAST": "본인확인 및 기본정보를 입력해 주세요.",
        "WHEELCHAIR":    "본인확인 및 기본정보를 입력해 주세요.",
    },
    "MOVEIN_SELECT_REASON": {
        "NORMAL":        "전입사유를 선택해 주세요.",
        "ELDERLY":       "이사 오신 사유를 선택해 주세요.",
        "HIGH_CONTRAST": "전입사유를 선택해 주세요.",
        "WHEELCHAIR":    "전입사유를 선택해 주세요.",
    },
    "MOVEIN_INPUT_PREV_ADDRESS": {
        "NORMAL":        "이사 전 주소를 확인하고, 이사 가는 사람을 선택해 주세요.",
        "ELDERLY":       "이사 오시기 전 살던 주소를 확인하고, 이사 가는 분을 선택해 주세요.",
        "HIGH_CONTRAST": "이사 전 주소를 확인하고, 이사 가는 사람을 선택해 주세요.",
        "WHEELCHAIR":    "이사 전 주소를 확인하고, 이사 가는 사람을 선택해 주세요.",
    },
    "MOVEIN_INPUT_NEW_ADDRESS": {
        "NORMAL":        "이사 후 주소를 입력해 주세요.",
        "ELDERLY":       "이사 오신 새 주소를 입력해 주세요.",
        "HIGH_CONTRAST": "이사 후 주소를 입력해 주세요.",
        "WHEELCHAIR":    "이사 후 주소를 입력해 주세요.",
    },
    "MOVEIN_SELECT_HOUSEHOLD": {
        "NORMAL":        "이사 후 세대 구성을 선택해 주세요.",
        "ELDERLY":       "이사 후 세대 구성을 선택해 주세요.",
        "HIGH_CONTRAST": "이사 후 세대 구성을 선택해 주세요.",
        "WHEELCHAIR":    "이사 후 세대 구성을 선택해 주세요.",
    },
    "MOVEIN_SELECT_EXTRA_SERVICE": {
        "NORMAL":        "추가 신청 서비스를 선택해 주세요.",
        "ELDERLY":       "추가로 신청하실 서비스가 있으면 선택해 주세요.",
        "HIGH_CONTRAST": "추가 신청 서비스를 선택해 주세요.",
        "WHEELCHAIR":    "추가 신청 서비스를 선택해 주세요.",
    },
    "MOVEIN_CONFIRM": {
        "NORMAL":        "입력하신 전입신고 내용을 확인해 주세요. 맞으면 제출 버튼을 눌러 주세요.",
        "ELDERLY":       "전입신고 내용을 천천히 확인해 주세요. 맞으시면 제출 버튼을 눌러 주세요.",
        "HIGH_CONTRAST": "입력하신 전입신고 내용을 확인해 주세요. 맞으면 제출 버튼을 눌러 주세요.",
        "WHEELCHAIR":    "입력하신 전입신고 내용을 확인해 주세요. 맞으면 제출 버튼을 눌러 주세요.",
    },
    "MOVEIN_COMPLETE": {
        "NORMAL":        "전입신고가 완료되었습니다.",
        "ELDERLY":       "전입신고가 완료되었습니다. 고생하셨습니다.",
        "HIGH_CONTRAST": "전입신고가 완료되었습니다.",
        "WHEELCHAIR":    "전입신고가 완료되었습니다.",
    },

    "UNSUPPORTED_SERVICE": {
        "NORMAL":        "죄송합니다. 현재 제공되지 않는 서비스입니다. 다른 서비스를 이용해 주세요.",
        "ELDERLY":       "죄송합니다. 지금은 해당 서비스를 제공하지 않습니다. 다른 서비스를 말씀해 주세요.",
        "HIGH_CONTRAST": "죄송합니다. 현재 제공되지 않는 서비스입니다. 다른 서비스를 이용해 주세요.",
        "WHEELCHAIR":    "죄송합니다. 현재 제공되지 않는 서비스입니다. 다른 서비스를 이용해 주세요.",
    },
    "ERROR_RETRY": {
        "NORMAL":        "오류가 발생했습니다. 다시 시도해 주세요.",
        "ELDERLY":       "잠깐 문제가 생겼습니다. 다시 한번 눌러 주세요.",
        "HIGH_CONTRAST": "오류가 발생했습니다. 다시 시도해 주세요.",
        "WHEELCHAIR":    "오류가 발생했습니다. 다시 시도해 주세요.",
    },
    "ERROR_TIMEOUT": {
        "NORMAL":        "시간이 초과되었습니다. 처음 화면으로 돌아갑니다.",
        "ELDERLY":       "시간이 지났습니다. 처음 화면으로 돌아갑니다. 천천히 다시 시작해 주세요.",
        "HIGH_CONTRAST": "시간이 초과되었습니다. 처음 화면으로 돌아갑니다.",
        "WHEELCHAIR":    "시간이 초과되었습니다. 처음 화면으로 돌아갑니다.",
    },
}


def _guide_text(context: str, user_type: str) -> str:
    bucket = GUIDE_TEXT.get(context, {})
    # 해당 user_type 키가 없으면 NORMAL 문구로 폴백하여 음성이 소멸하지 않도록 한다.
    # (예: 신규 모드 추가 시 GUIDE_TEXT에 키가 누락된 경우 대비)
    return bucket.get(user_type) or bucket.get("NORMAL", "")


def _step_to_prompt(step: str, user_type: str) -> str:
    step_descriptions = {
        "CERTIFICATE_SELECT_PURPOSE":  "발급할 증명서 종류(등본/초본) 선택 화면에 진입했습니다.",
        "CERTIFICATE_SELECT_RRN":      "주민등록번호 입력 화면에 진입했습니다. 주민등록번호 13자리를 입력해 주세요.",
        "CERTIFICATE_SELECT_SCOPE":    "발급 형태(등본/초본) 선택 화면에 진입했습니다.",
        "CERTIFICATE_SELECT_COUNT":    "발급 매수 선택 화면에 진입했습니다.",
        "CERTIFICATE_CONFIRM":         "발급 내용 최종 확인 화면에 진입했습니다. 맞으면 제출 버튼을 눌러 주세요.",
        "CERTIFICATE_PRINTING":        "등본 출력이 시작되었습니다.",
        "CERTIFICATE_COMPLETE":        "등본 출력이 완료되었습니다.",
        "MOVEIN_INPUT_BASIC_INFO":     "본인확인 및 기본정보 입력 화면에 진입했습니다.",
        "MOVEIN_SELECT_REASON":        "전입사유 선택 화면에 진입했습니다.",
        "MOVEIN_INPUT_PREV_ADDRESS":   "이사 전 주소 확인 및 이사 가는 사람 선택 화면에 진입했습니다.",
        "MOVEIN_INPUT_NEW_ADDRESS":    "이사 후 새 주소 입력 화면에 진입했습니다.",
        "MOVEIN_SELECT_HOUSEHOLD":     "이사 후 세대 구성 선택 화면에 진입했습니다.",
        "MOVEIN_SELECT_EXTRA_SERVICE": "추가 신청 서비스 선택 화면에 진입했습니다.",
        "MOVEIN_CONFIRM":              "전입신고 내용 최종 확인 화면에 진입했습니다. 맞으면 제출 버튼을 눌러 주세요.",
        "MOVEIN_COMPLETE":             "전입신고가 완료되었습니다.",
    }
    description = step_descriptions.get(step, f"{step} 단계에 진입했습니다.")
    user_type_hint = {
        "ELDERLY":       "사용자는 어르신입니다. 쉽고 친절하게 안내해 주세요.",
        "HIGH_CONTRAST": "사용자는 고대비 모드 이용자입니다. 일반 모드와 동일하게 안내해 주세요.",
        "WHEELCHAIR":    "사용자는 휠체어 이용자입니다. 동작을 최소화하는 방향으로 안내해 주세요.",
        "NORMAL":        "",
    }.get(user_type, "")

    prompt = f"[단계 안내 요청] {description} 이 화면에서 사용자가 해야 할 행동을 2문장 이내로 안내해 주세요."
    if user_type_hint:
        prompt += f" {user_type_hint}"
    return prompt


class KioskMainController:
    def __init__(self):
        self.ui = UIController()
        self.mcp = MCPToolManager()
        self.ai = IntentAnalyzer()
        self.ai_http = AIClient()
        self.sessions = SessionManager()
        self.current_user_type = "NORMAL"
        self._loop: asyncio.AbstractEventLoop | None = None
        self._mode_change_lock: asyncio.Lock | None = None
        self._home_idle_task: asyncio.Task | None = None

        self.ui.register_handler("USER_TOUCH",       self._on_user_touch)
        self.ui.register_handler("SERVICE_COMPLETE", self._on_service_complete)
        self.ui.register_handler("UI_ACK",           self._on_ui_ack)
        self.ui.register_handler("USER_CANCEL",      self._on_user_cancel)
        self.ui.register_handler("VOICE_INPUT",      self._on_voice_input)
        self.ui.register_handler("STEP_CHANGE",      self._on_step_change)
        self.sessions.set_timeout_callback(self._on_session_timeout)

    async def start(self):
        self._loop = asyncio.get_running_loop()
        self._mode_change_lock = asyncio.Lock()
        self.ui.connect(loop=self._loop)
        self.sessions.start()
        try:
            await self.mcp.connect()
            logger.info("MCP 서버 사전 연결 완료")
        except Exception as e:
            logger.warning("MCP 서버 사전 연결 실패 (기동 계속): %s", e)
        logger.info("키오스크 컨트롤러 기동 완료")

    async def shutdown(self):
        await self.sessions.stop()
        await self.mcp.disconnect()
        self.ui.disconnect()
        logger.info("키오스크 컨트롤러 종료 완료")

    async def handle_request(self, trigger_type: str, data):
        if trigger_type == "CHANGE_MODE":
            await self._change_mode(data)
        elif trigger_type == "VOICE_INPUT":
            await self._handle_voice(data)
        elif trigger_type == "TOUCH_SERVICE":
            await self._handle_touch(data)
        else:
            logger.warning("알 수 없는 trigger_type: %s", trigger_type)

    async def _change_mode(self, user_type: str, *, announce: bool = True):
        if user_type not in config.USER_CONFIGS:
            logger.warning("미지원 사용자 유형 '%s' → NORMAL 대체", user_type)
            user_type = "NORMAL"

        if user_type == self.current_user_type:
            logger.info("모드 변경 요청 무시 — 이미 %s 모드", user_type)
            return

        if self._mode_change_lock is None:
            logger.warning("_mode_change_lock 미초기화 — start() 전 호출 의심")
            return

        if self._mode_change_lock.locked():
            logger.info("모드 변경 진행 중 — 중복 요청 무시: %s", user_type)
            return

        async with self._mode_change_lock:
            if user_type == self.current_user_type:
                logger.info("모드 변경 요청 무시 — Lock 획득 후 이미 %s 모드", user_type)
                return

            self.current_user_type = user_type
            success = self.ui.adapt_mode(self.current_user_type, wait_ack=True)
            logger.info(
                "모드 변경: %s [%s]",
                self.current_user_type,
                "ACK 수신" if success else "ACK 실패/큐 대기",
            )

            if announce:
                await self._send_voice_guide(
                    session_id="global",
                    context="MODE_CHANGE",
                    user_type=user_type,
                )

    async def _resume_active_session_guide(self):
        """
        모드 변경 완료 후, 진행 중이던 세션이 있으면 해당 단계의 음성을 다시 재생한다.

        ※ run_delayed() 를 사용하면 navigation token 이 갱신된 경우 stale 판정으로
          콜백이 무시되어 음성이 간헐적으로 소멸하는 문제가 발생한다.
          음성 복구는 화면 내비게이션과 무관하므로 asyncio.sleep 태스크로 대체한다.
        """
        active_ids = self.sessions.get_active_session_ids()
        for sid in active_ids:
            session = self.sessions.get(sid)
            if session and getattr(session, "last_step", ""):
                logger.info(
                    "모드 변경 후 단계(%s) 음성 복구 예약 — session_id=%s",
                    session.last_step, sid,
                )

                async def _delayed_guide(s: str = sid, st: str = session.last_step):
                    # 모드 전환 UI 애니메이션이 완료될 시간을 확보한 뒤 음성 재생
                    await asyncio.sleep(0.5)
                    # 태스크 실행 시점에 세션이 여전히 ACTIVE 상태인지 재확인
                    _s = self.sessions.get(s)
                    if _s is None or _s.state.value not in ("WAITING", "ACTIVE"):
                        logger.debug(
                            "음성 복구 스킵 — 세션이 이미 종료됨: session_id=%s", s
                        )
                        return
                    await self._handle_step_with_ai(s, st)

                asyncio.create_task(_delayed_guide())

    async def _handle_voice(self, data):
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
        except Exception as e:
            logger.error("[VOICE_INPUT 전처리 실패] %s", e)
            return

        # ── 0. 원문 키워드 선제 스캔 ──
        # AI 호출 전에 발화 원문을 직접 키워드 스캔하여 모드 변경을 즉시 처리한다.
        # STT 오인식(불규칙 띄어쓰기)도 _resolve_user_type 내부에서 공백 제거 매칭으로 방어된다.
        # AI 서버가 느리거나 실패하더라도 모드 변경이 묵살되지 않도록 하는 가장 중요한 방어선이다.
        early_type, early_explicit_normal = self.ai._resolve_user_type(user_text)
        if early_type in ("ELDERLY", "HIGH_CONTRAST", "WHEELCHAIR"):
            logger.info("원문 키워드 선제 감지 → AI 호출 없이 즉시 모드 변경: %s", early_type)
            await self._change_mode(early_type)
            await self._resume_active_session_guide()
            return
        if early_explicit_normal:
            logger.info("원문 키워드 선제 감지 → AI 호출 없이 즉시 NORMAL 복귀 (현재=%s)", self.current_user_type)
            await self._change_mode("NORMAL")
            await self._resume_active_session_guide()
            return

        try:
            ai_raw = await asyncio.to_thread(self.ai_http.chat, user_text, session_id_hint, locale)
            ai_res = self.ai.parse_voice_intent(ai_raw, original_text=user_text)
        except AIClientError as e:
            logger.error("[AI 서버 호출 실패] %s", e)
            # 선제 스캔(Step 0)을 통과했다면 이미 return 되었으므로,
            # 이 시점은 선제 스캔에서도 모드 변경 키워드가 없던 경우다 — 정상적으로 무시
            return
        except Exception as e:
            logger.error("[AI 분석 실패] %s", e)
            return

        # ── 모드 변경 의도는 confidence와 무관하게 최우선 처리 ──────────
        # 선제 스캔이 잡지 못한 표현(예: AI가 의미 기반으로 감지한 경우)을
        # AI 응답의 userType으로 처리한다. confidence 체크 이전에 수행한다.
        if ai_res:
            _pre_user_type = ai_res.get("userType", "NORMAL")
            _pre_explicit_normal = ai_res.get("explicit_normal", False)
            if _pre_user_type in ("ELDERLY", "HIGH_CONTRAST", "WHEELCHAIR"):
                logger.info("AI userType=%s 감지 → confidence 무관 모드 변경 처리", _pre_user_type)
                await self._change_mode(_pre_user_type)
                await self._resume_active_session_guide()
                return
            elif _pre_user_type == "NORMAL" and _pre_explicit_normal:
                logger.info("AI 일반 모드 복귀 감지 → confidence 무관 NORMAL 전환 (현재=%s)", self.current_user_type)
                await self._change_mode("NORMAL")
                await self._resume_active_session_guide()
                return

        if not ai_res or ai_res.get("confidence", 0) < 0.6:
            logger.info("AI 분석 신뢰도 부족 — 요청 무시")
            return

        ai_answer = ai_res.get("answer", "")
        conversation_history = ai_res.get("conversation_history", [])
        entities: dict = ai_raw.get("entities", {}) if isinstance(ai_raw, dict) else {}

        logger.info(
            "AI 응답 수신: intent=%s serviceId=%s confidence=%.2f answer=%.40s…",
            ai_res.get("intent"), ai_res.get("serviceId"), ai_res.get("confidence", 0), ai_answer,
        )

        # ── 서비스 진입 처리 ────────────────────────────────────────────
        # 모드 변경 의도는 위(Step 0 / AI pre-check)에서 모두 처리 후 return 되었으므로
        # 여기까지 도달한 경우는 반드시 서비스 진입 의도다.

        service_id = ai_res.get("serviceId")
        if service_id is None:
            logger.info("AI 응답에 serviceId 없음 — 미지원 서비스 안내")
            await self._send_voice_guide(
                session_id="global", context="UNSUPPORTED_SERVICE",
                user_type=self.current_user_type, override_text=ai_answer,
            )
            return

        active_ids = self.sessions.get_active_session_ids()
        if active_ids:
            logger.info("새 서비스 요청 — 기존 활성 세션 %d개 종료 처리: %s", len(active_ids), active_ids)
            for orphan_id in active_ids:
                await self._end_session_safe(orphan_id, reason="CANCELLED")

        await self._execute_service(
            service_id, session_start_text=ai_answer,
            conversation_history=conversation_history, entities=entities,
        )

    async def _handle_touch(self, service_id):
        if service_id is None:
            logger.warning("service_id 비어 있음 — 요청 무시")
            return
        await self._execute_service(service_id)

    async def _execute_service(
        self, service_id: int, session_start_text: str = "",
        conversation_history: list | None = None, entities: dict | None = None,
    ):
        if conversation_history is None:
            conversation_history = []
        if entities is None:
            entities = {}

        self._cancel_home_idle_timer()

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

        self.sessions.create(session_id, self.current_user_type)
        if conversation_history:
            self.sessions.update_history(session_id, conversation_history)
        if entities:
            self.sessions.set_prefilled(session_id, entities)

        ack_ok = self.ui.send_command(
            None, "SESSION_ASSIGNED", {"sessionId": session_id},
            wait_ack=True, ack_timeout_sec=3.0,
        )
        if not ack_ok:
            logger.warning("SESSION_ASSIGNED ACK 미수신 (sessionId=%s). 계속 진행합니다.", session_id)

        session_start_guide = session_start_text or _guide_text("SESSION_START", self.current_user_type)
        if session_start_guide:
            await self._send_voice_guide(
                session_id=session_id, context="SESSION_START",
                user_type=self.current_user_type, override_text=session_start_guide,
            )
        else:
            await self._send_voice_guide(
                session_id=session_id, context="SERVICE_ENTER", user_type=self.current_user_type,
            )

        try:
            service_result = await self.mcp.start_service(
                session_id=session_id, service_id=service_id, user_type=self.current_user_type,
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

        resolved_service_id = service_result.get("serviceId", service_id)
        service_name = service_result.get("serviceName", "")

        self.ui.reset_navigation()

        def _move():
            success = self.ui.send_command(
                session_id, "MOVE_PAGE",
                {
                    "serviceId": resolved_service_id, "serviceName": service_name,
                    "userType": self.current_user_type, "settings": settings,
                },
                wait_ack=True, ack_timeout_sec=3.0,
            )
            if success:
                self.sessions.activate(session_id, resolved_service_id)
                logger.info(
                    "서비스 진입 및 세션 ACTIVE 전환: %d '%s' (세션: %s, 모드: %s)",
                    resolved_service_id, service_name, session_id, self.current_user_type,
                )
            else:
                logger.warning("페이지 이동 명령 전송 실패/ACK 실패 (세션: %s)", session_id)

        self.ui.run_delayed(0.05, _move)

    async def _handle_step_with_ai(self, session_id: str, step: str):
        conversation_history = self.sessions.get_history(session_id)
        session_info = self.sessions.get(session_id) if hasattr(self.sessions, "get") else None
        service_id = getattr(session_info, "service_id", None) if session_info else None

        extra_context: dict = {}
        if hasattr(self.sessions, "get_step_context"):
            try: extra_context = self.sessions.get_step_context(session_id, step) or {}
            except Exception: extra_context = {}

        ai_answer = ""
        try:
            ai_raw = await asyncio.to_thread(
                self.ai_http.chat, "", session_id, "ko-KR", conversation_history,
                "step_guide", step, self.current_user_type, service_id, extra_context,
            )
            if isinstance(ai_raw, dict):
                ai_answer = str(ai_raw.get("answer", "")).strip()
                updated_history = ai_raw.get("conversation_history")
                if isinstance(updated_history, list):
                    self.sessions.update_history(session_id, updated_history)
            logger.info(
                "STEP_CHANGE AI 응답 — step=%s userType=%s answer=%.60s…",
                step, self.current_user_type, ai_answer if ai_answer else "(GUIDE_TEXT 폴백)",
            )
        except AIClientError as e:
            logger.warning("[STEP_CHANGE AI 호출 실패 → GUIDE_TEXT 폴백] step=%s err=%s", step, e)
        except Exception as e:
            logger.warning("[STEP_CHANGE AI 처리 예외 → GUIDE_TEXT 폴백] step=%s err=%s", step, e)

        await self._send_voice_guide(
            session_id=session_id, context=step, user_type=self.current_user_type, override_text=ai_answer,
        )

    async def _send_auto_advance(self, session_id: str, step: str, prefilled_value):
        user_type = self.current_user_type
        auto_advance_guide = ""
        if user_type == "ELDERLY":
            auto_advance_guide = self._make_elderly_auto_advance_guide(step, prefilled_value)

        self.ui.send_command(
            session_id, "VOICE_GUIDE",
            {
                "context": step, "guideText": "", "autoAdvance": True,
                "prefilledValue": prefilled_value, "autoAdvanceGuide": auto_advance_guide,
                "audioUrl": None, "lang": "ko-KR", "userType": user_type,
            },
            wait_ack=False,
        )
        logger.info("autoAdvance 전송 — session_id=%s step=%s value=%s", session_id, step, prefilled_value)
        self.sessions.clear_prefilled_field(session_id, step)

    @staticmethod
    def _make_elderly_auto_advance_guide(step: str, value) -> str:
        templates: dict[str, str] = {
            "CERTIFICATE_SELECT_COUNT":   f"{value}부로 자동 설정했습니다.",
            "CERTIFICATE_SELECT_SCOPE":   f"공개 범위를 {value}(으)로 자동 설정했습니다.",
        }
        return templates.get(step, f"{value}(으)로 자동 설정했습니다.")

    async def _send_voice_guide(self, session_id: str, context: str, user_type: str, override_text: str = ""):
        guide_text = override_text or _guide_text(context, user_type)
        if not guide_text:
            logger.debug("voice_guide: 안내 내용 없음 — 전송 생략 (context=%s)", context)
            return

        self.ui.send_command(
            session_id if session_id != "global" else None, "VOICE_GUIDE",
            {
                "context": context, "guideText": guide_text, "audioUrl": None,
                "lang": "ko-KR", "userType": user_type,
            },
            wait_ack=False,
        )
        logger.info("VOICE_GUIDE 전송 — context=%s userType=%s text=%.40s…", context, user_type, guide_text)

    async def _end_session_safe(self, session_id: str, reason: str = "COMPLETED"):
        try: await self.mcp.end_session(session_id=session_id, reason=reason)
        except Exception as e: logger.warning("[MCP end_session 실패] sessionId=%s err=%s", session_id, e)

    def _on_voice_input(self, payload: dict):
        data = payload.get("data", {})
        text = str(data.get("text", "")).strip()
        if not text:
            logger.warning("VOICE_INPUT payload에 text 없음 — 무시")
            return

        logger.info("STOMP VOICE_INPUT 수신 — text=%.60s…", text)
        self._cancel_home_idle_timer()

        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(lambda d=data: self._loop.create_task(self._handle_voice(d)))
        else:
            logger.error("VOICE_INPUT 수신 시 asyncio 루프 없음")

    def _on_step_change(self, payload: dict):
        data = payload.get("data", {})
        session_id = data.get("sessionId")
        step = data.get("step")

        if not step or not session_id:
            logger.warning("STEP_CHANGE payload 누락 — session_id=%s step=%s", session_id, step)
            return

        session = self.sessions.get(session_id)
        if session is None or session.state != SessionState.ACTIVE:
            logger.warning("STEP_CHANGE 수신 — 세션 부재 또는 ACTIVE 상태 아님, 무시: session_id=%s", session_id)
            return

        session.last_step = step  # [추가] 모드 전환 도중 음성이 증발할 경우 복구하기 위해 현재 단계를 세션에 캐싱

        if step not in GUIDE_TEXT:
            logger.warning("알 수 없는 step 수신 (TC-FE-10): %s", step)
            if self._loop and not self._loop.is_closed():
                self._loop.call_soon_threadsafe(
                    lambda sid=session_id, ut=self.current_user_type: self._loop.create_task(
                        self._send_voice_guide(session_id=sid, context="ERROR_RETRY", user_type=ut)
                    )
                )
            return

        self.sessions.touch(session_id)

        if self._loop and not self._loop.is_closed():
            if self.sessions.is_step_prefilled(session_id, step):
                prefilled_value = self.sessions.get_prefilled_value(session_id, step)
                logger.info("prefilled 스킵: session_id=%s step=%s", session_id, step)
                self._loop.call_soon_threadsafe(
                    lambda sid=session_id, st=step, pv=prefilled_value: self._loop.create_task(
                        self._send_auto_advance(sid, st, pv)
                    )
                )
            else:
                self._loop.call_soon_threadsafe(
                    lambda sid=session_id, st=step: self._loop.create_task(self._handle_step_with_ai(sid, st))
                )
        else:
            logger.error("STEP_CHANGE 수신 시 asyncio 루프 없음")

    def _on_user_touch(self, payload: dict):
        session_id = payload.get("data", {}).get("sessionId")
        self._cancel_home_idle_timer()
        if session_id:
            self.sessions.touch(session_id)
            logger.info("사용자 활동 수신 (세션: %s)", session_id)

    def _on_service_complete(self, payload: dict):
        session_id = payload.get("data", {}).get("sessionId")
        if session_id:
            self.sessions.complete(session_id)
            logger.info("서비스 완료 수신 (세션: %s)", session_id)
            if self._loop:
                self._loop.call_soon_threadsafe(lambda sid=session_id: self._loop.create_task(self._on_service_complete_async(sid)))
        else:
            self._return_to_home()

    async def _on_service_complete_async(self, session_id: str):
        await self._send_voice_guide(session_id=session_id, context="SESSION_END", user_type=self.current_user_type)
        await self._end_session_safe(session_id, reason="COMPLETED")
        self._return_to_home_silent()

    def _return_to_home_silent(self):
        self.ui.reset_navigation()
        success = self.ui.send_command(None, "GO_HOME", {}, wait_ack=True, ack_timeout_sec=3.0)
        if self.current_user_type != "NORMAL":
            self.ui.adapt_mode(self.current_user_type, wait_ack=False)
        logger.info("홈 화면 복귀 완료 (모드: %s, ack=%s)", self.current_user_type, success)
        self._start_home_idle_timer()

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
                self._loop.call_soon_threadsafe(lambda sid=session_id: self._loop.create_task(self._on_user_cancel_async(sid)))
        else:
            self._return_to_home()

    async def _on_user_cancel_async(self, session_id: str):
        await self._end_session_safe(session_id, reason="CANCELLED")
        self._return_to_home()

    def _on_session_timeout(self, session):
        logger.warning("세션 만료 처리: %s — 홈 복귀", session.session_id)
        self.ui.reset_navigation()
        self.ui.send_command(
            session.session_id, "SESSION_EXPIRED",
            {"message": "시간이 초과되었습니다. 처음 화면으로 돌아갑니다."},
            wait_ack=True, ack_timeout_sec=2.0,
        )
        if self._loop:
            self._loop.call_soon_threadsafe(lambda sid=session.session_id: self._loop.create_task(self._on_session_timeout_async(sid)))

    async def _on_session_timeout_async(self, session_id: str):
        await self._end_session_safe(session_id, reason="TIMEOUT")
        self._return_to_home_silent()

    def _start_home_idle_timer(self):
        self._cancel_home_idle_timer()
        if self.current_user_type == "NORMAL": return
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._schedule_home_idle_timer)

    def _schedule_home_idle_timer(self):
        if self._loop and not self._loop.is_closed():
            self._home_idle_task = self._loop.create_task(self._home_idle_countdown())

    async def _home_idle_countdown(self):
        timeout = config.IDLE_TIMEOUT_SEC
        logger.info("홈 idle 타이머 시작 — %ds 후 NORMAL 복귀", timeout)
        try:
            await asyncio.sleep(timeout)
            if self.current_user_type != "NORMAL":
                logger.info("홈 idle 타임아웃 — NORMAL 모드로 복귀")
                await self._change_mode("NORMAL", announce=False)
        except asyncio.CancelledError:
            logger.debug("홈 idle 타이머 취소됨")

    def _cancel_home_idle_timer(self):
        if self._home_idle_task and not self._home_idle_task.done():
            self._home_idle_task.cancel()
            self._home_idle_task = None

    def _return_to_home(self):
        self.ui.reset_navigation()
        success = self.ui.send_command(None, "GO_HOME", {}, wait_ack=True, ack_timeout_sec=3.0)
        if self.current_user_type != "NORMAL":
            self.ui.adapt_mode(self.current_user_type, wait_ack=False)
        logger.info("홈 화면 복귀 완료 (모드 유지: %s, ack=%s)", self.current_user_type, success)
        self._start_home_idle_timer()

        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(
                lambda ut=self.current_user_type: self._loop.create_task(
                    self._send_voice_guide(session_id="global", context="HOME", user_type=ut)
                )
            )


async def main():
    controller = KioskMainController()
    await controller.start()
    try: await asyncio.Event().wait()
    finally: await controller.shutdown()


if __name__ == "__main__":
    asyncio.run(main())