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
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("kiosk.main")


class KioskMainController:
    """
    핵심 변경점
    - 홈 복귀 전 navigation token 증가
    - 중요 UI 명령은 wait_ack=True 사용
    - stale delayed 작업은 ui.run_delayed() 사용
    - 앱 전역 idle timer 제거 (프론트 페이지 단위 타이머와 충돌 방지)
    - 홈 복귀 시 mode를 강제로 NORMAL로 돌리지 않음
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

        self.sessions.set_timeout_callback(self._on_session_timeout)

        
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

    async def handle_request(self, trigger_type, data):
        if trigger_type == "CHANGE_MODE":
            self._change_mode(data)
        elif trigger_type == "VOICE_INPUT":
            await self._handle_voice(data)
        elif trigger_type == "TOUCH_SERVICE":
            await self._handle_touch(data)
        else:
            logger.warning("알 수 없는 trigger_type: %s", trigger_type)

    def _change_mode(self, user_type: str):
        if user_type not in config.USER_CONFIGS:
            logger.warning("미지원 사용자 유형 '%s' → NORMAL 대체", user_type)
            user_type = "NORMAL"

        self.current_user_type = user_type
        success = self.ui.adapt_mode(self.current_user_type, wait_ack=True)
        logger.info("모드 변경: %s [%s]", self.current_user_type, "ACK 수신" if success else "ACK 실패/큐 대기")

async def _handle_voice(self, data):
    """
    data 예시:
    - 문자열: "주민등록등본 발급받고 싶어요"
    - dict: {"text": "...", "sessionId": "...", "locale": "ko-KR"}
    """
    try:
        if isinstance(data, str):
            user_text = data
            session_id = "string"
            locale = "ko-KR"
        elif isinstance(data, dict):
            user_text = str(data.get("text", ""))
            session_id = str(data.get("sessionId", "string"))
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
            session_id,
            locale,
        )

        # 2) 기존 IntentAnalyzer로 정규화
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

    self._change_mode(ai_res.get("userType", "NORMAL"))

    service_id = ai_res.get("serviceId")
    if service_id is None:
        logger.info("AI 응답에 serviceId 없음 — 서비스 진입 생략")
        return

    await self._execute_service(service_id)
    

    
    # async def _handle_voice(self, data):
    #     try:
    #         ai_res = self.ai.parse_voice_intent(data)
    #     except Exception as e:
    #         logger.error("[AI 분석 실패] %s", e)
    #         return

    #     if not ai_res or ai_res.get("confidence", 0) < 0.6:
    #         logger.info("AI 분석 신뢰도 부족 — 요청 무시")
    #         return

    #     self._change_mode(ai_res.get("userType", "NORMAL"))

    #     service_id = ai_res.get("serviceId")
    #     if service_id is None:
    #         logger.info("AI 응답에 serviceId 없음 — 서비스 진입 생략")
    #         return

    #     await self._execute_service(service_id)

    async def _handle_touch(self, service_id):
        if service_id is None:
            logger.warning("service_id 비어 있음 — 요청 무시")
            return
        await self._execute_service(service_id)

    async def _execute_service(self, service_id: int):
        try:
            mcp_result = await self.mcp.call_service(
                "start_session",
                {"userType": self.current_user_type},
                required_fields=["sessionId"],
            )
        except ConnectionError as e:
            logger.error("[MCP 연결 실패] %s", e)
            return
        except MCPError as e:
            logger.error("[MCP 응답 검증 실패] %s", e)
            return
        except Exception as e:
            logger.error("[MCP 호출 오류] %s", e)
            return

        session_id = mcp_result["sessionId"]

        self.sessions.create(session_id, self.current_user_type)
        self.sessions.activate(session_id, service_id)

        settings = mcp_result.get("settings") or config.USER_CONFIGS[self.current_user_type]

        # 이전 delayed navigation 흐름 무효화
        self.ui.reset_navigation()

        def _move():
            success = self.ui.send_command(
                session_id,
                "MOVE_PAGE",
                {
                    "serviceId": service_id,
                    "userType": self.current_user_type,
                    "settings": settings,
                },
                wait_ack=True,
                ack_timeout_sec=3.0,
            )

            if success:
                logger.info(
                    "서비스 진입: %d (세션: %s, 모드: %s)",
                    service_id, session_id, self.current_user_type
                )
            else:
                logger.warning("페이지 이동 명령 전송 실패/ACK 실패 (세션: %s)", session_id)

        # 약간의 지연이 필요한 UI 전환도 stale-safe 하게 처리 가능
        self.ui.run_delayed(0.05, _move)

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
        self._return_to_home()

    def _return_to_home(self):
        """
        홈 화면 이동만 수행.
        - stale delayed navigation 무효화
        - GO_HOME은 ACK까지 대기
        - mode는 유지 (프론트가 mode/page 상태를 분리해서 관리할 수 있도록)
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
            self.current_user_type,
            success,
        )


async def main():
    controller = KioskMainController()
    await controller.start()

    try:
        await asyncio.Event().wait()
    finally:
        await controller.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
