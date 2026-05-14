# mcp_client.py
import asyncio
import logging
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
import config

logger = logging.getLogger(__name__)


class MCPError(Exception):
    """MCP 서비스 호출 관련 커스텀 예외"""
    pass


class MCPToolManager:
    """
    MCP 서버 커넥터

    저수준 call_service()를 기반으로,
    키오스크 도메인 도구 4종을 래핑한 고수준 메서드를 제공한다.

    도구 목록
    ─────────────────────────────────────────────────────────
    start_session(userType)
        세션을 생성하고 사용자 유형에 맞는 UI 설정을 반환한다.
        필수 응답 필드: sessionId, settings

    start_service(sessionId, serviceId, userType)
        서비스 화면 진입을 서버에 알리고 서비스 메타데이터를 반환한다.
        필수 응답 필드: sessionId, serviceId

    end_session(sessionId, reason)
        세션 종료를 서버에 알린다.
        reason: "COMPLETED" | "CANCELLED" | "TIMEOUT" | "ERROR"
        필수 응답 필드: sessionId, status

    voice_guide(sessionId, text, userType, context)
        안내 텍스트에 대한 TTS 가이드 정보를 서버에 요청한다.
        context: "SESSION_START" | "SERVICE_ENTER" | "HOME" | "MODE_CHANGE" | "SESSION_END"
        필수 응답 필드: sessionId, guideText
        선택 응답 필드: audioUrl (서버가 음성 파일을 제공하는 경우)
    ─────────────────────────────────────────────────────────
    """

    def __init__(self):
        self.server_params = StdioServerParameters(
            command="python",
            args=[config.MCP_SERVER_PATH]
        )
        self._session: ClientSession | None = None
        self._read = None
        self._write = None
        self._lock = asyncio.Lock()
        self._context_manager = None

    # ══════════════════════════════════════════════
    #  연결 / 정리 / 종료
    # ══════════════════════════════════════════════

    async def connect(self):
        """MCP 서버와 세션을 열고 멤버로 유지"""
        if self._session is not None:
            return

        try:
            self._context_manager = stdio_client(self.server_params)
            self._read, self._write = await self._context_manager.__aenter__()

            self._session = ClientSession(self._read, self._write)
            await self._session.__aenter__()
            await self._session.initialize()
            logger.info("MCP 서버 연결 성공")
        except Exception as e:
            await self._cleanup()
            raise ConnectionError(f"MCP 서버 연결 실패: {e}")

    async def _cleanup(self):
        """내부 리소스 안전하게 정리"""
        try:
            if self._session:
                await self._session.__aexit__(None, None, None)
        except Exception:
            pass
        try:
            if self._context_manager:
                await self._context_manager.__aexit__(None, None, None)
        except Exception:
            pass
        self._session = None
        self._read = None
        self._write = None
        self._context_manager = None

    async def disconnect(self):
        """앱 종료 시 명시적으로 호출"""
        async with self._lock:
            await self._cleanup()
            logger.info("MCP 서버 연결 종료")

    # ══════════════════════════════════════════════
    #  저수준: 범용 도구 호출
    # ══════════════════════════════════════════════

    async def call_service(
        self,
        tool_name: str,
        arguments: dict,
        max_retries: int = 2,
        required_fields: list[str] | None = None,
    ) -> dict:
        """
        MCP 서버의 특정 도구를 호출하고 응답을 검증한 뒤 반환한다.

        Parameters
        ----------
        tool_name : str
            호출할 MCP 도구 이름
        arguments : dict
            도구에 전달할 인자
        max_retries : int
            최대 재시도 횟수 (기본 2)
        required_fields : list[str] | None
            응답 dict에 반드시 존재해야 하는 키 목록.
            None이면 검증을 건너뛴다.

        Raises
        ------
        ConnectionError  : max_retries 내 연결·호출 모두 실패
        MCPError         : 응답 형식 오류 또는 필수 필드 누락
        """
        async with self._lock:
            last_error = None

            for attempt in range(1, max_retries + 1):
                try:
                    if self._session is None:
                        await self.connect()

                    raw_result = await self._session.call_tool(tool_name, arguments)
                    return self._validate_result(tool_name, raw_result, required_fields)

                except MCPError:
                    raise

                except Exception as e:
                    last_error = e
                    logger.warning(
                        "MCP 호출 실패 (시도 %d/%d) [%s]: %s",
                        attempt, max_retries, tool_name, e,
                    )
                    await self._cleanup()

                    if attempt < max_retries:
                        await asyncio.sleep(1)

            raise ConnectionError(
                f"MCP 서비스 '{tool_name}' 호출 {max_retries}회 실패: {last_error}"
            )

    # ══════════════════════════════════════════════
    #  응답 검증
    # ══════════════════════════════════════════════

    @staticmethod
    def _validate_result(
        tool_name: str,
        raw_result,
        required_fields: list[str] | None,
    ) -> dict:
        if raw_result is None:
            raise MCPError(f"MCP '{tool_name}' 응답이 None입니다.")

        if not isinstance(raw_result, dict):
            raise MCPError(
                f"MCP '{tool_name}' 응답이 dict가 아닙니다: "
                f"type={type(raw_result).__name__}, value={str(raw_result)[:200]}"
            )

        if required_fields:
            missing = [f for f in required_fields if f not in raw_result]
            if missing:
                raise MCPError(
                    f"MCP '{tool_name}' 응답에 필수 필드 누락: {missing}  "
                    f"(수신 키: {list(raw_result.keys())})"
                )

        logger.debug("MCP '%s' 응답 검증 통과: %s", tool_name, list(raw_result.keys()))
        return raw_result

    # ══════════════════════════════════════════════
    #  고수준: 도메인 도구 래퍼
    # ══════════════════════════════════════════════

    async def start_session(self, user_type: str) -> dict:
        """
        세션을 생성하고 사용자 유형에 맞는 UI 설정을 받아온다.

        Parameters
        ----------
        user_type : str
            "NORMAL" | "ELDERLY" | "WHEELCHAIR"

        Returns
        -------
        dict
            {
                "sessionId": str,
                "settings": dict,   # UI 설정 (fontSize, largeFont 등)
                ...                 # 서버가 추가로 반환하는 필드
            }
        """
        logger.info("[MCP] start_session 호출 — userType=%s", user_type)
        result = await self.call_service(
            tool_name="start_session",
            arguments={"userType": user_type},
            required_fields=["sessionId", "settings"],
        )
        logger.info(
            "[MCP] start_session 완료 — sessionId=%s", result.get("sessionId")
        )
        return result

    async def start_service(
        self,
        session_id: str,
        service_id: int,
        user_type: str,
    ) -> dict:
        """
        서비스 화면 진입을 MCP 서버에 알리고 서비스 메타데이터를 받아온다.

        Parameters
        ----------
        session_id : str
        service_id : int
            예: 101(전입신고), 102(등본 발급)
        user_type : str
            "NORMAL" | "ELDERLY" | "WHEELCHAIR"

        Returns
        -------
        dict
            {
                "sessionId": str,
                "serviceId": int,
                "serviceName": str,   # 선택
                "steps": list,        # 선택 — 서비스 단계 목록
                ...
            }
        """
        logger.info(
            "[MCP] start_service 호출 — sessionId=%s serviceId=%d userType=%s",
            session_id, service_id, user_type,
        )
        result = await self.call_service(
            tool_name="start_service",
            arguments={
                "sessionId": session_id,
                "serviceId": service_id,
                "userType": user_type,
            },
            required_fields=["sessionId", "serviceId"],
        )
        logger.info(
            "[MCP] start_service 완료 — serviceId=%s serviceName=%s",
            result.get("serviceId"), result.get("serviceName", "-"),
        )
        return result

    async def end_session(
        self,
        session_id: str,
        reason: str = "COMPLETED",
    ) -> dict:
        """
        세션 종료를 MCP 서버에 알린다.

        Parameters
        ----------
        session_id : str
        reason : str
            "COMPLETED" | "CANCELLED" | "TIMEOUT" | "ERROR"

        Returns
        -------
        dict
            {
                "sessionId": str,
                "status": str,   # 예: "CLOSED"
                ...
            }
        """
        valid_reasons = {"COMPLETED", "CANCELLED", "TIMEOUT", "ERROR"}
        if reason not in valid_reasons:
            logger.warning(
                "[MCP] end_session — 알 수 없는 reason '%s' → 'ERROR' 대체", reason
            )
            reason = "ERROR"

        logger.info(
            "[MCP] end_session 호출 — sessionId=%s reason=%s", session_id, reason
        )
        result = await self.call_service(
            tool_name="end_session",
            arguments={
                "sessionId": session_id,
                "reason": reason,
            },
            required_fields=["sessionId", "status"],
        )
        logger.info(
            "[MCP] end_session 완료 — sessionId=%s status=%s",
            result.get("sessionId"), result.get("status"),
        )
        return result

    async def voice_guide(
        self,
        session_id: str,
        text: str,
        user_type: str,
        context: str = "SERVICE_ENTER",
    ) -> dict:
        """
        안내 텍스트에 대한 음성 가이드 정보를 MCP 서버에 요청한다.

        Parameters
        ----------
        session_id : str
        text : str
            TTS로 읽어줄 안내 문장
        user_type : str
            "NORMAL" | "ELDERLY" | "WHEELCHAIR"
        context : str
            호출 맥락.
            "SESSION_START" | "SERVICE_ENTER" | "HOME" | "MODE_CHANGE" | "SESSION_END"

        Returns
        -------
        dict
            {
                "sessionId": str,
                "guideText": str,       # 최종 안내 텍스트 (서버가 가공할 수 있음)
                "audioUrl": str | None, # 음성 파일 URL (서버가 제공하는 경우)
                "lang": str,            # 선택 — 예: "ko-KR"
                ...
            }

        Note
        ----
        audioUrl이 존재하면 STOMP를 통해 프론트에 VOICE_GUIDE 커맨드를 전송해
        프론트가 직접 오디오를 재생하도록 한다.
        audioUrl이 없으면 guideText를 VOICE_GUIDE 커맨드에 담아 전송하고,
        프론트(또는 OS TTS)가 읽어준다.
        """
        valid_contexts = {
            "SESSION_START", "SERVICE_ENTER", "HOME", "MODE_CHANGE", "SESSION_END"
        }
        if context not in valid_contexts:
            logger.warning(
                "[MCP] voice_guide — 알 수 없는 context '%s' → 'SERVICE_ENTER' 대체",
                context,
            )
            context = "SERVICE_ENTER"

        logger.info(
            "[MCP] voice_guide 호출 — sessionId=%s context=%s userType=%s text=%.40s…",
            session_id, context, user_type, text,
        )
        result = await self.call_service(
            tool_name="voice_guide",
            arguments={
                "sessionId": session_id,
                "text": text,
                "userType": user_type,
                "context": context,
            },
            required_fields=["sessionId", "guideText"],
        )
        logger.info(
            "[MCP] voice_guide 완료 — guideText=%.40s… audioUrl=%s",
            result.get("guideText", ""), result.get("audioUrl"),
        )
        return result
