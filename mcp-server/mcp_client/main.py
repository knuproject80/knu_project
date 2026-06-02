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
#  음성 안내 문구 상수 (AI 호출 실패 시 폴백 전용)
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
    # 실제 단계 순서: PURPOSE → RRN → SCOPE → COUNT → CONFIRM → PRINTING → COMPLETE
    "CERTIFICATE_SELECT_PURPOSE": {
        "NORMAL":     "발급할 증명서 종류를 선택해 주세요.",
        "ELDERLY":    "발급받으실 증명서 종류를 선택해 주세요.",
        "WHEELCHAIR": "발급할 증명서 종류를 선택해 주세요.",
    },
    "CERTIFICATE_SELECT_RRN": {
        "NORMAL":     "주민등록번호를 입력해 주세요.",
        "ELDERLY":    "주민등록번호 앞자리와 뒷자리를 천천히 입력해 주세요.",
        "WHEELCHAIR": "주민등록번호를 입력해 주세요.",
    },
    "CERTIFICATE_SELECT_SCOPE": {
        "NORMAL":     "발급 형태를 선택해 주세요.",
        "ELDERLY":    "발급 형태를 선택해 주세요.",
        "WHEELCHAIR": "발급 형태를 선택해 주세요.",
    },
    "CERTIFICATE_SELECT_COUNT": {
        "NORMAL":     "발급 매수를 선택해 주세요.",
        "ELDERLY":    "몇 장 필요하신지 선택해 주세요.",
        "WHEELCHAIR": "발급 매수를 선택해 주세요.",
    },
    "CERTIFICATE_CONFIRM": {
        "NORMAL":     "입력하신 내용을 확인해 주세요. 맞으면 제출 버튼을 눌러 주세요.",
        "ELDERLY":    "내용을 천천히 확인해 주세요. 맞으시면 제출 버튼을 눌러 주세요.",
        "WHEELCHAIR": "입력하신 내용을 확인해 주세요. 맞으면 제출 버튼을 눌러 주세요.",
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
    "MOVEIN_INPUT_BASIC_INFO": {
        "NORMAL":     "본인확인 및 기본정보를 입력해 주세요.",
        "ELDERLY":    "본인확인 및 기본정보를 천천히 입력해 주세요.",
        "WHEELCHAIR": "본인확인 및 기본정보를 입력해 주세요.",
    },
    "MOVEIN_SELECT_REASON": {
        "NORMAL":     "전입사유를 선택해 주세요.",
        "ELDERLY":    "이사 오신 사유를 선택해 주세요.",
        "WHEELCHAIR": "전입사유를 선택해 주세요.",
    },
    "MOVEIN_INPUT_PREV_ADDRESS": {
        "NORMAL":     "이사 전 주소를 확인하고, 이사 가는 사람을 선택해 주세요.",
        "ELDERLY":    "이사 오시기 전 살던 주소를 확인하고, 이사 가는 분을 선택해 주세요.",
        "WHEELCHAIR": "이사 전 주소를 확인하고, 이사 가는 사람을 선택해 주세요.",
    },
    "MOVEIN_INPUT_NEW_ADDRESS": {
        "NORMAL":     "이사 후 주소를 입력해 주세요.",
        "ELDERLY":    "이사 오신 새 주소를 입력해 주세요.",
        "WHEELCHAIR": "이사 후 주소를 입력해 주세요.",
    },
    "MOVEIN_SELECT_HOUSEHOLD": {
        "NORMAL":     "이사 후 세대 구성을 선택해 주세요.",
        "ELDERLY":    "이사 후 세대 구성을 선택해 주세요.",
        "WHEELCHAIR": "이사 후 세대 구성을 선택해 주세요.",
    },
    "MOVEIN_SELECT_EXTRA_SERVICE": {
        "NORMAL":     "추가 신청 서비스를 선택해 주세요.",
        "ELDERLY":    "추가로 신청하실 서비스가 있으면 선택해 주세요.",
        "WHEELCHAIR": "추가 신청 서비스를 선택해 주세요.",
    },
    "MOVEIN_CONFIRM": {
        "NORMAL":     "입력하신 전입신고 내용을 확인해 주세요. 맞으면 제출 버튼을 눌러 주세요.",
        "ELDERLY":    "전입신고 내용을 천천히 확인해 주세요. 맞으시면 제출 버튼을 눌러 주세요.",
        "WHEELCHAIR": "입력하신 전입신고 내용을 확인해 주세요. 맞으면 제출 버튼을 눌러 주세요.",
    },
    "MOVEIN_COMPLETE": {
        "NORMAL":     "전입신고가 완료되었습니다.",
        "ELDERLY":    "전입신고가 완료되었습니다. 고생하셨습니다.",
        "WHEELCHAIR": "전입신고가 완료되었습니다.",
    },

    # ── 미지원 서비스 ─────────────────────────────────────────
    "UNSUPPORTED_SERVICE": {
        "NORMAL":     "죄송합니다. 현재 제공되지 않는 서비스입니다. 다른 서비스를 이용해 주세요.",
        "ELDERLY":    "죄송합니다. 지금은 해당 서비스를 제공하지 않습니다. 다른 서비스를 말씀해 주세요.",
        "WHEELCHAIR": "죄송합니다. 현재 제공되지 않는 서비스입니다. 다른 서비스를 이용해 주세요.",
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
    """context + user_type 조합으로 폴백 안내 문구를 반환한다. 없으면 빈 문자열."""
    return GUIDE_TEXT.get(context, {}).get(user_type, "")


def _step_to_prompt(step: str, user_type: str) -> str:
    """
    STEP_CHANGE 키를 AI /chat 호출용 자연어 프롬프트로 변환한다.
    AI가 어느 화면·단계인지 파악할 수 있도록 충분한 컨텍스트를 제공한다.
    """
    step_descriptions = {
        # 주민등록등본/초본 발급 (실제 단계 순서)
        # 1.증명서종류 -> 2.주민번호입력 -> 3.발급형태 -> 4.발급매수 -> 5.확인 -> 6.출력 -> 7.완료
        "CERTIFICATE_SELECT_PURPOSE":  "발급할 증명서 종류(등본/초본) 선택 화면에 진입했습니다.",
        "CERTIFICATE_SELECT_RRN":      "주민등록번호 입력 화면에 진입했습니다. 주민등록번호 13자리를 입력해 주세요.",
        "CERTIFICATE_SELECT_SCOPE":    "발급 형태(등본/초본) 선택 화면에 진입했습니다.",
        "CERTIFICATE_SELECT_COUNT":    "발급 매수 선택 화면에 진입했습니다.",
        "CERTIFICATE_CONFIRM":         "발급 내용 최종 확인 화면에 진입했습니다. 맞으면 제출 버튼을 눌러 주세요.",
        "CERTIFICATE_PRINTING":        "등본 출력이 시작되었습니다.",
        "CERTIFICATE_COMPLETE":        "등본 출력이 완료되었습니다.",
        # 전입신고
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
        "ELDERLY":    "사용자는 어르신입니다. 쉽고 친절하게 안내해 주세요.",
        "WHEELCHAIR": "사용자는 휠체어 이용자입니다. 동작을 최소화하는 방향으로 안내해 주세요.",
        "NORMAL":     "",
    }.get(user_type, "")

    prompt = f"[단계 안내 요청] {description} 이 화면에서 사용자가 해야 할 행동을 2문장 이내로 안내해 주세요."
    if user_type_hint:
        prompt += f" {user_type_hint}"
    return prompt


# ──────────────────────────────────────────────────────────
#  메인 컨트롤러
# ──────────────────────────────────────────────────────────

class KioskMainController:
    """
    변경 이력
    ─────────────────────────────────────────────────────────
    - AI /chat 엔드포인트 연동: 의도 분류 + 자연어 답변 동시 수신
    - AI answer를 MCP voice_guide → STOMP VOICE_GUIDE 경로로 Frontend 전달
    - _handle_voice: ai_answer / conversation_history 추출 후 하위 메서드로 전달
    - _execute_service: session_start_text / conversation_history 파라미터 추가
    - _send_voice_guide: override_text 파라미터 추가 (AI 답변 우선, 없으면 GUIDE_TEXT 폴백)
    - _on_step_change: GUIDE_TEXT 직접 조회 → AI /chat 호출(_handle_step_with_ai)로 교체
    - GUIDE_TEXT 딕셔너리: AI 호출 실패 시 폴백 전용으로 역할 축소
    - SessionManager: conversation_history 저장/조회 지원 가정
      (sessions.get_history / sessions.update_history)
    ─────────────────────────────────────────────────────────
    v6.0 추가
    ─────────────────────────────────────────────────────────
    - _handle_voice: AI entities 추출 후 sessions.set_prefilled() 호출
    - _on_step_change: prefilled 단계 여부를 먼저 확인
      · prefilled → _send_auto_advance() (AI/MCP 호출 없이 autoAdvance 전송)
      · 미충족   → _handle_step_with_ai() (기존 AI 호출 흐름)
    - _send_auto_advance: autoAdvance=True VOICE_GUIDE 전송 신규 메서드
      · ELDERLY 모드는 짧은 확인 음성(autoAdvanceGuide) 포함
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

        self.ui.register_handler("USER_TOUCH",       self._on_user_touch)
        self.ui.register_handler("SERVICE_COMPLETE", self._on_service_complete)
        self.ui.register_handler("UI_ACK",           self._on_ui_ack)
        self.ui.register_handler("USER_CANCEL",      self._on_user_cancel)
        self.ui.register_handler("VOICE_INPUT",      self._on_voice_input)
        self.ui.register_handler("STEP_CHANGE",      self._on_step_change)
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

        # 모드 전환 음성 안내 — 모드 전환은 세션 시작 전이므로 AI 맥락 없음
        # GUIDE_TEXT 폴백 그대로 사용 (override_text 미전달)
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

        변경사항:
        - AI /chat 호출로 교체 (의도 분류 + answer 동시 수신)
        - ai_answer, conversation_history를 추출해 하위 메서드로 전달
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

            # ── 1. AI /chat 호출 (mode="classify" — 의도 분류 + 자연어 답변) ──
            # 기본 mode가 "classify"이므로 명시적 전달은 생략
            ai_raw = await asyncio.to_thread(
                self.ai_http.chat,
                user_text,
                session_id_hint,
                locale,
            )

            # ── 2. IntentAnalyzer 정규화 ──────────────────────────────
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

        # ── 3. AI 답변 및 대화 기록 추출 ─────────────────────────────
        ai_answer = ai_res.get("answer", "")
        conversation_history = ai_res.get("conversation_history", [])

        # ── 3-1. entities 추출 (v6.0) ────────────────────────────────
        # AI 서버가 반환한 entities를 raw 응답에서 직접 읽는다.
        # IntentAnalyzer는 entities를 가공하지 않으므로 ai_raw에서 추출한다.
        entities: dict = ai_raw.get("entities", {}) if isinstance(ai_raw, dict) else {}

        logger.info(
            "AI 응답 수신: intent=%s serviceId=%s confidence=%.2f answer=%.40s…",
            ai_res.get("intent"), ai_res.get("serviceId"),
            ai_res.get("confidence", 0), ai_answer,
        )

        # ── 4. serviceId 분기 ─────────────────────────────────────────
        # 주의: _change_mode는 내부에서 ADAPT_UI + MODE_CHANGE voice_guide를 전송한다.
        # serviceId가 없는 모드 변경 케이스(ELDERLY/WHEELCHAIR)에서 _change_mode를
        # 이중 호출하면 ADAPT_UI 2회, voice_guide 3회가 나가는 버그가 생기므로
        # 반드시 분기 이후에 한 번만 호출한다.
        service_id = ai_res.get("serviceId")
        detected_user_type = ai_res.get("userType", "NORMAL")

        if service_id is None:
            # 접근성 모드 변경 발화("글씨 크게", "확대" 등):
            # serviceId가 없어도 ELDERLY/WHEELCHAIR면 모드 변경으로 처리한다.
            if detected_user_type in ("ELDERLY", "WHEELCHAIR"):
                logger.info(
                    "serviceId 없음 + userType=%s → 모드 변경 요청으로 처리",
                    detected_user_type,
                )
                # _change_mode 내부에서 ADAPT_UI + MODE_CHANGE voice_guide를 전송.
                # AI answer가 있으면 override_text로 사용하도록 내부 voice_guide 호출을
                # 대체하기 위해 직접 분리 처리한다.
                self.current_user_type = detected_user_type
                self.ui.adapt_mode(detected_user_type, wait_ack=True)
                logger.info("모드 변경: %s", detected_user_type)
                await self._send_voice_guide(
                    session_id="global",
                    context="MODE_CHANGE",
                    user_type=detected_user_type,
                    override_text=ai_answer,
                )
            else:
                logger.info("AI 응답에 serviceId 없음 — 미지원 서비스 안내")
                await self._send_voice_guide(
                    session_id="global",
                    context="UNSUPPORTED_SERVICE",
                    user_type=self.current_user_type,
                    override_text=ai_answer,
                )
            return

        # serviceId 있는 경우: 모드 전환 후 서비스 실행
        # (서비스 진입 전에 한 번만 _change_mode 호출)
        await self._change_mode(detected_user_type)

        # ── 6. 서비스 실행 — AI answer를 SESSION_START 안내로 전달 ────
        await self._execute_service(
            service_id,
            session_start_text=ai_answer,
            conversation_history=conversation_history,
            entities=entities,                      # v6.0: prefilled 저장용
        )

    # ── 터치 입력 처리 ───────────────────────────

    async def _handle_touch(self, service_id):
        if service_id is None:
            logger.warning("service_id 비어 있음 — 요청 무시")
            return
        # 터치 입력은 AI 답변 없이 진행 (GUIDE_TEXT 폴백 사용)
        await self._execute_service(service_id)

    # ══════════════════════════════════════════════
    #  서비스 실행 핵심 흐름
    #
    #  start_session
    #    → SESSION_ASSIGNED (/topic/ui/global, ACK 대기)
    #      → voice_guide(SESSION_START, AI answer 우선)
    #        → start_service → voice_guide(SERVICE_ENTER)
    #          → STOMP MOVE_PAGE
    #
    #  SESSION_ASSIGNED를 먼저 보내는 이유:
    #    프론트는 앱 시작 시 /topic/ui/global 만 구독한 상태.
    #    SESSION_ASSIGNED를 받아야 /topic/ui/{sessionId}를 추가 구독하므로,
    #    이 명령 전에 해당 토픽으로 보낸 VOICE_GUIDE/MOVE_PAGE는 프론트가 수신 불가.
    # ══════════════════════════════════════════════

    async def _execute_service(
        self,
        service_id: int,
        session_start_text: str = "",           # AI answer (없으면 GUIDE_TEXT 폴백)
        conversation_history: list | None = None,
        entities: dict | None = None,           # v6.0: AI가 추출한 prefilled 필드
    ):
        if conversation_history is None:
            conversation_history = []
        if entities is None:
            entities = {}

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

        # 로컬 SessionManager에 등록 + 대화 기록 저장
        self.sessions.create(session_id, self.current_user_type)
        if conversation_history:
            self.sessions.update_history(session_id, conversation_history)

        # ── 1-1. prefilled entities 세션 저장 (v6.0) ──────────────
        # None/빈 값 필터링은 session_manager.set_prefilled 내부에서 처리
        if entities:
            self.sessions.set_prefilled(session_id, entities)

        # ── 2. SESSION_ASSIGNED → /topic/ui/global ───────────────
        # 프론트가 새 sessionId 토픽을 추가 구독할 수 있도록
        # 다른 UI 명령보다 반드시 먼저 전송한다.
        # ACK(UI_ACK)를 기다려 프론트 구독 완료를 확인한 뒤 다음 단계로 진행한다.
        ack_ok = self.ui.send_command(
            None,                               # → /topic/ui/global
            "SESSION_ASSIGNED",
            {"sessionId": session_id},
            wait_ack=True,
            ack_timeout_sec=3.0,
        )
        if not ack_ok:
            logger.warning(
                "SESSION_ASSIGNED ACK 미수신 — 프론트 구독 지연 가능성 있음 "
                "(sessionId=%s). 계속 진행합니다.",
                session_id,
            )

        # ── 3. voice_guide — SESSION_START ───────
        # SESSION_ASSIGNED ACK 이후 전송 → 프론트가 이미 sessionId 토픽 구독 완료
        # AI answer 우선 사용, 없으면 GUIDE_TEXT 폴백
        await self._send_voice_guide(
            session_id=session_id,
            context="SESSION_START",
            user_type=self.current_user_type,
            override_text=session_start_text,
        )

        # ── 4. start_service ─────────────────────
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

        resolved_service_id = service_result.get("serviceId", service_id)
        service_name = service_result.get("serviceName", "")

        self.sessions.activate(session_id, resolved_service_id)

        # ── 5. voice_guide — SERVICE_ENTER ───────
        # 서비스 진입 안내는 AI 맥락 없이 GUIDE_TEXT 그대로 사용
        await self._send_voice_guide(
            session_id=session_id,
            context="SERVICE_ENTER",
            user_type=self.current_user_type,
        )

        # ── 6. STOMP MOVE_PAGE ───────────────────
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
    #  STEP_CHANGE — AI 답변 생성 후 VOICE_GUIDE 전송
    # ══════════════════════════════════════════════

    async def _handle_step_with_ai(self, session_id: str, step: str):
        """
        STEP_CHANGE 수신 시 AI /chat (mode="step_guide") 호출로
        맥락 기반 단계 안내 문구를 받아 VOICE_GUIDE로 전송한다.

        흐름:
          STEP_CHANGE
            → AI /chat (mode="step_guide", step, userType, serviceId, retryCount)
              → answer 수신 (맥락 반영된 단계 안내)
                → MCP voice_guide(text=answer)
                  → STOMP VOICE_GUIDE → Frontend TTS

        AI 호출 실패 또는 빈 answer 수신 시 GUIDE_TEXT 딕셔너리로 폴백한다.

        설계 배경:
          이전 구현은 mode 구분 없이 /chat을 호출했기 때문에 AI 서버가
          STEP 프롬프트를 서비스 선택 요청으로 오해해 "무엇을 도와드릴까요?"
          같은 범용 응답을 돌려주는 문제가 있었다.
          mode="step_guide"는 AI 서버에서 의도 분류를 건너뛰고
          단계 안내 문구 생성에만 집중하도록 한다.
        """
        # 세션에서 누적 대화 기록 + 재시도 카운트 조회
        conversation_history = self.sessions.get_history(session_id)
        session_info = self.sessions.get(session_id) if hasattr(self.sessions, "get") else None
        service_id = getattr(session_info, "service_id", None) if session_info else None

        # extra_context — 재시도 횟수, 이전 단계 등 부가 맥락
        # SessionManager가 retry/prevStep을 지원하지 않으면 빈 dict로 전달
        extra_context: dict = {}
        if hasattr(self.sessions, "get_step_context"):
            try:
                extra_context = self.sessions.get_step_context(session_id, step) or {}
            except Exception:
                extra_context = {}

        ai_answer = ""
        try:
            ai_raw = await asyncio.to_thread(
                self.ai_http.chat,
                "",                              # text는 step_guide 모드에서 미사용
                session_id,
                "ko-KR",
                conversation_history,
                "step_guide",                    # mode
                step,                            # step
                self.current_user_type,          # user_type
                service_id,                      # service_id
                extra_context,                   # extra_context
            )
            if isinstance(ai_raw, dict):
                ai_answer = str(ai_raw.get("answer", "")).strip()

                # 대화 기록 갱신 (AI 서버가 반환한 경우)
                updated_history = ai_raw.get("conversation_history")
                if isinstance(updated_history, list):
                    self.sessions.update_history(session_id, updated_history)

            logger.info(
                "STEP_CHANGE AI 응답 — step=%s userType=%s answer=%.60s…",
                step, self.current_user_type, ai_answer if ai_answer else "(GUIDE_TEXT 폴백)",
            )

        except AIClientError as e:
            logger.warning(
                "[STEP_CHANGE AI 호출 실패 → GUIDE_TEXT 폴백] step=%s err=%s",
                step, e,
            )
        except Exception as e:
            logger.warning(
                "[STEP_CHANGE AI 처리 예외 → GUIDE_TEXT 폴백] step=%s err=%s",
                step, e,
            )

        # AI answer가 비어있으면 GUIDE_TEXT 폴백 경로로 진입
        # _send_voice_guide 내부에서 override_text가 빈 문자열이면 GUIDE_TEXT 조회
        await self._send_voice_guide(
            session_id=session_id,
            context=step,
            user_type=self.current_user_type,
            override_text=ai_answer,
        )

    # ══════════════════════════════════════════════
    #  autoAdvance 전송 (prefilled 단계 스킵) v6.0
    # ══════════════════════════════════════════════

    async def _send_auto_advance(
        self,
        session_id: str,
        step: str,
        prefilled_value,
    ):
        """
        AI 서버가 발화에서 미리 추출한 값이 있는 단계에 대해,
        AI /chat 및 MCP voice_guide 호출 없이 Frontend에 autoAdvance 신호를 전송한다.

        ELDERLY 모드에서는 즉시 스킵하지 않고 짧은 확인 음성(autoAdvanceGuide)을
        포함하여 전송한다. Frontend는 TTS 완료 후 다음 단계로 진행해야 한다.

        Parameters
        ----------
        session_id : str
        step : str
            prefilled로 판정된 STEP_CHANGE 키
        prefilled_value : Any
            세션에 저장된 해당 step의 값 (예: 1, "CASH")
        """
        user_type = self.current_user_type

        # ELDERLY 모드: 확인 음성 문구 생성 (즉시 스킵 금지)
        auto_advance_guide = ""
        if user_type == "ELDERLY":
            auto_advance_guide = self._make_elderly_auto_advance_guide(
                step, prefilled_value
            )

        self.ui.send_command(
            session_id,
            "VOICE_GUIDE",
            {
                "context":           step,
                "guideText":         "",             # 스킵 단계는 안내 문구 없음
                "autoAdvance":       True,           # Frontend에 즉시 다음 단계 신호
                "prefilledValue":    prefilled_value, # UI 자동 입력값
                "autoAdvanceGuide":  auto_advance_guide,  # ELDERLY 전용 확인 음성
                "audioUrl":          None,
                "lang":              "ko-KR",
                "userType":          user_type,
            },
            wait_ack=False,
        )
        logger.info(
            "autoAdvance 전송 — session_id=%s step=%s value=%s elderly_guide=%.40s…",
            session_id, step, prefilled_value, auto_advance_guide,
        )

    @staticmethod
    def _make_elderly_auto_advance_guide(step: str, value) -> str:
        """
        ELDERLY 모드 자동입력 확인 문구를 반환한다.

        step별로 사람이 이해하기 쉬운 문구를 생성하며,
        매핑이 없는 step은 범용 문구로 대체한다.

        Parameters
        ----------
        step : str
        value : Any
            prefilled_value (표시용)

        Returns
        -------
        str
            TTS로 읽어줄 확인 문구
        """
        templates: dict[str, str] = {
            "CERTIFICATE_SELECT_COUNT":   f"{value}부로 자동 설정했습니다.",
            "CERTIFICATE_SELECT_SCOPE":   f"공개 범위를 {value}(으)로 자동 설정했습니다.",
        }
        return templates.get(step, f"{value}(으)로 자동 설정했습니다.")

    # ══════════════════════════════════════════════
    #  음성 안내 공통 헬퍼
    # ══════════════════════════════════════════════

    async def _send_voice_guide(
        self,
        session_id: str,
        context: str,
        user_type: str,
        override_text: str = "",            # AI 생성 답변 (있으면 우선 사용)
    ):
        """
        MCP voice_guide를 호출한 뒤 결과를 STOMP VOICE_GUIDE 커맨드로 전송한다.

        우선순위:
          1. override_text (AI /chat 이 생성한 answer)
          2. MCP voice_guide 가 반환한 guideText
          3. GUIDE_TEXT 딕셔너리 폴백

        - audioUrl이 있으면 프론트가 오디오 파일을 직접 재생한다.
        - audioUrl이 없으면 guideText를 프론트(또는 OS TTS)가 읽어준다.
        - MCP 호출 실패 시 로컬 fallback 텍스트로 VOICE_GUIDE를 전송한다.
        """
        # override_text 가 있으면 그것을, 없으면 GUIDE_TEXT 폴백을 MCP에 전달
        fallback_text = override_text or _guide_text(context, user_type)

        try:
            guide_result = await self.mcp.voice_guide(
                session_id=session_id,
                text=fallback_text,             # AI answer 또는 폴백 문구 전달
                user_type=user_type,
                context=context,
            )
            # MCP가 별도 guideText를 내려주면 그것을 우선 사용
            # 단, override_text가 있을 때는 AI 답변을 보존
            guide_text = (
                override_text
                or guide_result.get("guideText", fallback_text)
            )
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
                "context":   context,
                "guideText": guide_text,
                "audioUrl":  audio_url,
                "lang":      lang,
                "userType":  user_type,
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
        try:
            await self.mcp.end_session(session_id=session_id, reason=reason)
        except Exception as e:
            logger.warning(
                "[MCP end_session 실패 — 무시] sessionId=%s reason=%s err=%s",
                session_id, reason, e,
            )

    # ══════════════════════════════════════════════
    #  STOMP 이벤트 핸들러
    # ══════════════════════════════════════════════

    def _on_voice_input(self, payload: dict):
        """
        프론트 → STOMP VOICE_INPUT 수신.
        STT 결과를 _handle_voice() 로 위임한다.
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

    def _on_step_change(self, payload: dict):
        """
        프론트 → STOMP STEP_CHANGE 수신.

        v6.0 변경사항:
          1. prefilled 확인 먼저 수행
             · 채워진 단계 → _send_auto_advance (AI/MCP 호출 없이 autoAdvance 전송)
             · 미충족 단계 → _handle_step_with_ai (기존 AI /chat 호출 흐름)
          2. 기존 흐름:
             GUIDE_TEXT 딕셔너리 직접 조회 → MCP voice_guide 전달
             변경: AI /chat 호출(_handle_step_with_ai) → answer → MCP voice_guide 전달
                  AI 실패 시 GUIDE_TEXT 폴백은 _handle_step_with_ai 내부에서 처리
        """
        data = payload.get("data", {})
        session_id = data.get("sessionId")
        step = data.get("step")

        if not step or not session_id:
            logger.warning("STEP_CHANGE payload 누락 — session_id=%s step=%s", session_id, step)
            return

        self.sessions.touch(session_id)  # 활동 시각 갱신

        if self._loop and not self._loop.is_closed():
            # v6.0: prefilled 여부에 따라 처리 경로 분기
            if self.sessions.is_step_prefilled(session_id, step):
                prefilled_value = self.sessions.get_prefilled_value(session_id, step)
                logger.info(
                    "prefilled 스킵: session_id=%s step=%s value=%s",
                    session_id, step, prefilled_value,
                )
                self._loop.call_soon_threadsafe(
                    lambda: self._loop.create_task(
                        self._send_auto_advance(session_id, step, prefilled_value)
                    )
                )
            else:
                self._loop.call_soon_threadsafe(
                    lambda: self._loop.create_task(
                        self._handle_step_with_ai(session_id, step)
                    )
                )
        else:
            logger.error("STEP_CHANGE 수신 시 asyncio 루프 없음 — 처리 불가")

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
