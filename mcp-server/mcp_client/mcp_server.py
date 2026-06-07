# mcp_server.py
"""
배리어프리 키오스크 MCP Server

테스트 가이드 v6.2 기준 구현
  - start_session  : 세션 생성 + userType별 settings 반환
  - start_service  : 서비스 시작 + serviceName 반환
  - end_session    : 세션 종료 (모든 reason 처리)
  - voice_guide    : 인자 text를 guideText로 그대로 반환 (자체 문구 생성 금지)

실행 방식: MCP Client(main.py)가 stdio로 직접 기동
  StdioServerParameters(command="python", args=["mcp_server.py"])
"""

import asyncio
import logging
import uuid
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# ── 로거 ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("kiosk.mcp_server")


# ──────────────────────────────────────────────────────────
#  userType별 UI 설정 (config.USER_CONFIGS와 동일하게 맞춤)
# ──────────────────────────────────────────────────────────
USER_SETTINGS: dict[str, dict] = {
    "NORMAL": {
        "largeFont":     False,
        "highContrast":  False,
        "simpleMode":    False,
        "lowScreenMode": False,
        "fontSize":      "16px",
    },
    "ELDERLY": {
        "largeFont":     True,
        "highContrast":  False,     # 고대비는 HIGH_CONTRAST 타입으로 분리
        "simpleMode":    True,
        "lowScreenMode": False,
        "fontSize":      "24px",
    },
    "HIGH_CONTRAST": {
        "largeFont":     False,
        "highContrast":  True,      # 고대비 전용
        "simpleMode":    False,
        "lowScreenMode": False,
        "fontSize":      "16px",
    },
    "WHEELCHAIR": {
        "largeFont":     False,
        "highContrast":  False,
        "simpleMode":    False,
        "lowScreenMode": True,
        "fontSize":      "20px",
    },
}

# serviceId → serviceName 매핑
SERVICE_NAMES: dict[int, str] = {
    101: "전입신고",
    102: "주민등록등본/초본 발급",
}

# 허용 reason 목록
VALID_REASONS = {"COMPLETED", "CANCELLED", "TIMEOUT", "ERROR"}

# 인메모리 세션 저장소 {sessionId: {"userType": ..., "status": ...}}
_sessions: dict[str, dict] = {}


# ──────────────────────────────────────────────────────────
#  MCP Server 인스턴스
# ──────────────────────────────────────────────────────────
server = Server("kiosk-mcp-server")


# ──────────────────────────────────────────────────────────
#  도구 목록 선언
# ──────────────────────────────────────────────────────────
@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="start_session",
            description="키오스크 세션을 시작하고 sessionId와 UI 설정을 반환합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "userType": {
                        "type": "string",
                        "enum": ["NORMAL", "ELDERLY", "HIGH_CONTRAST", "WHEELCHAIR"],
                        "description": "사용자 유형",
                    },
                },
                "required": ["userType"],
            },
        ),
        Tool(
            name="start_service",
            description="서비스를 시작하고 serviceId와 serviceName을 반환합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sessionId": {
                        "type": "string",
                        "description": "start_session에서 발급된 sessionId",
                    },
                    "serviceId": {
                        "type": "integer",
                        "enum": [101, 102],
                        "description": "101: 전입신고, 102: 주민등록등본/초본 발급",
                    },
                    "userType": {
                        "type": "string",
                        "enum": ["NORMAL", "ELDERLY", "HIGH_CONTRAST", "WHEELCHAIR"],
                    },
                },
                "required": ["sessionId", "serviceId", "userType"],
            },
        ),
        Tool(
            name="end_session",
            description="세션을 종료합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sessionId": {
                        "type": "string",
                        "description": "종료할 sessionId",
                    },
                    "reason": {
                        "type": "string",
                        "enum": ["COMPLETED", "CANCELLED", "TIMEOUT", "ERROR"],
                        "description": "종료 사유",
                    },
                },
                "required": ["sessionId", "reason"],
            },
        ),
        Tool(
            name="voice_guide",
            description=(
                "음성 안내를 처리합니다. "
                "인자로 전달된 text를 guideText로 그대로 반환합니다. "
                "서버 자체 문구 생성 금지 — v5.0 계약."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "sessionId": {
                        "type": "string",
                        "description": "세션 ID (global 허용)",
                    },
                    "text": {
                        "type": "string",
                        "description": "AI 또는 폴백이 생성한 안내 문구",
                    },
                    "userType": {
                        "type": "string",
                        "enum": ["NORMAL", "ELDERLY", "HIGH_CONTRAST", "WHEELCHAIR"],
                    },
                    "context": {
                        "type": "string",
                        "description": (
                            "SESSION_START | SERVICE_ENTER | MODE_CHANGE | "
                            "HOME | SESSION_END | <STEP_KEY>"
                        ),
                    },
                },
                "required": ["sessionId", "text", "userType", "context"],
            },
        ),
    ]


# ──────────────────────────────────────────────────────────
#  도구 핸들러
# ──────────────────────────────────────────────────────────
@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        if name == "start_session":
            result = _start_session(arguments)
        elif name == "start_service":
            result = _start_service(arguments)
        elif name == "end_session":
            result = _end_session(arguments)
        elif name == "voice_guide":
            result = _voice_guide(arguments)
        else:
            raise ValueError(f"알 수 없는 도구: {name}")
    except (KeyError, ValueError) as e:
        # 필수 필드 누락 또는 유효성 오류 → MCPError로 처리되도록 error 응답
        logger.error("[%s] 오류: %s", name, e)
        import json
        return [TextContent(type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False))]

    import json
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


# ──────────────────────────────────────────────────────────
#  도구별 로직
# ──────────────────────────────────────────────────────────

def _start_session(args: dict) -> dict:
    """
    세션 생성.

    반환 계약 (테스트 가이드 3.1):
      { "sessionId": "uuid-string", "settings": { "largeFont": ..., ... } }

    sessionId 또는 settings가 누락되면 MCP Client가 MCPError를 발생시킨다.
    """
    user_type = args.get("userType", "NORMAL")
    if user_type not in USER_SETTINGS:
        logger.warning("start_session: 미지원 userType '%s' → NORMAL 대체", user_type)
        user_type = "NORMAL"

    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "userType": user_type,
        "status":   "OPEN",
    }

    result = {
        "sessionId": session_id,
        "settings":  USER_SETTINGS[user_type],
    }
    logger.info("[MCP] start_session 완료 — sessionId=%s userType=%s", session_id, user_type)
    return result


def _start_service(args: dict) -> dict:
    """
    서비스 시작.

    반환 계약 (테스트 가이드 3.1):
      { "sessionId": "...", "serviceId": 101|102, "serviceName": "전입신고" }
    """
    session_id = args["sessionId"]   # 없으면 KeyError → error 응답
    service_id = args["serviceId"]   # 없으면 KeyError → error 응답
    user_type  = args.get("userType", "NORMAL")

    if session_id not in _sessions:
        raise ValueError(f"존재하지 않는 sessionId: {session_id}")

    if service_id not in SERVICE_NAMES:
        raise ValueError(f"지원하지 않는 serviceId: {service_id}")

    _sessions[session_id]["serviceId"] = service_id
    service_name = SERVICE_NAMES[service_id]

    result = {
        "sessionId":   session_id,
        "serviceId":   service_id,
        "serviceName": service_name,
    }
    logger.info(
        "[MCP] start_service 완료 — sessionId=%s serviceId=%d serviceName=%s userType=%s",
        session_id, service_id, service_name, user_type,
    )
    return result


def _end_session(args: dict) -> dict:
    """
    세션 종료.

    반환 계약 (테스트 가이드 3.1):
      { "sessionId": "...", "status": "CLOSED" }

    모든 reason(COMPLETED / CANCELLED / TIMEOUT / ERROR) 처리 필수.
    """
    session_id = args["sessionId"]
    reason     = args.get("reason", "COMPLETED")

    if reason not in VALID_REASONS:
        logger.warning("end_session: 미지원 reason '%s' — COMPLETED로 처리", reason)
        reason = "COMPLETED"

    if session_id in _sessions:
        _sessions[session_id]["status"] = "CLOSED"
        _sessions[session_id]["reason"] = reason
        # 메모리 해제
        _sessions.pop(session_id, None)

    result = {
        "sessionId": session_id,
        "status":    "CLOSED",
    }
    logger.info("[MCP] end_session 완료 — sessionId=%s reason=%s", session_id, reason)
    return result


def _voice_guide(args: dict) -> dict:
    """
    음성 안내.

    반환 계약 (테스트 가이드 3.1 / v5.0 계약):
      - text를 guideText로 그대로 반환 — 서버 자체 문구 생성 금지
      - audioUrl: TTS 파일 URL 또는 null
      - lang: "ko-KR"

    audioUrl 생성 정책:
      현재 구현에서는 null을 반환한다.
      향후 TTS 서비스 연동 시 여기서 URL을 생성하여 반환한다.
    """
    session_id = args["sessionId"]
    text       = args["text"]        # 없으면 KeyError → error 응답
    user_type  = args.get("userType", "NORMAL")
    context    = args.get("context", "")

    # ── 핵심 계약: text를 그대로 guideText로 반환 ──────────────
    result = {
        "sessionId": session_id,
        "guideText": text,           # 서버가 임의로 변환하지 않음
        "audioUrl":  None,           # TTS 연동 전까지 null
        "lang":      "ko-KR",
    }
    logger.info(
        "[MCP] voice_guide 완료 — sessionId=%s context=%s userType=%s text=%.40s…",
        session_id, context, user_type, text,
    )
    return result


# ──────────────────────────────────────────────────────────
#  엔트리포인트
# ──────────────────────────────────────────────────────────
async def main():
    logger.info("키오스크 MCP Server 기동 — stdio 모드")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
