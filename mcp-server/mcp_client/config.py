import os

# .env 파일 자동 로드 (로컬 개발용). 클라우드에서는 플랫폼 환경변수가 우선.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _env(key: str, default: str) -> str:
    return os.getenv(key, default)


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default


def _env_bool(key: str, default: bool) -> bool:
    raw = os.getenv(key)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


# ─────────────────────────────────────────────────────────
# WebSocket/STOMP 설정 (Spring 백엔드)
#   로컬:   ws://localhost:8080/ws
#   배포:   wss://<spring-도메인>/ws  (또는 Railway 내부망 ws://<service>.railway.internal:8080/ws)
# ─────────────────────────────────────────────────────────
WS_URL = _env("WS_URL", "ws://localhost:8080/ws")
WS_RECONNECT_DELAY = _env_int("WS_RECONNECT_DELAY", 2)
WS_MAX_RECONNECT_TRIES = _env_int("WS_MAX_RECONNECT_TRIES", 10)

# 구독 경로
STOMP_SUB_FRONT_EVENTS = _env("STOMP_SUB_FRONT_EVENTS", "/topic/front/events")
STOMP_SUB_FRONT_ACK = _env("STOMP_SUB_FRONT_ACK", "/topic/front/ack")

# 발행 경로
STOMP_PUB_UI_PREFIX = _env("STOMP_PUB_UI_PREFIX", "/topic/ui")

# MCP 서버 설정 (mcp_client와 같은 폴더에 mcp_server.py가 있어야 함)
MCP_SERVER_PATH = _env("MCP_SERVER_PATH", "./mcp_server.py")

# 서비스 ID 상수
SERVICE_ID_REGISTRATION = 101
SERVICE_ID_CERTIFICATE = 102

# 세션 설정
SESSION_TIMEOUT_SEC = _env_int("SESSION_TIMEOUT_SEC", 300)
SESSION_CLEANUP_INTERVAL = _env_int("SESSION_CLEANUP_INTERVAL", 30)

# 참고:
# 프론트에서 페이지 단위 idle timer를 관리하는 구조라면,
# MCP Client 쪽 app-global idle timer는 사용하지 않는 것을 권장.
IDLE_TIMEOUT_SEC = _env_int("IDLE_TIMEOUT_SEC", 60)
IDLE_WARNING_SEC = _env_int("IDLE_WARNING_SEC", 45)

# ─────────────────────────────────────────────────────────
# AI 서버 설정 (FastAPI)
#   로컬:   http://127.0.0.1:8000
#   배포:   http://<ai-service>.railway.internal:8000  (Railway 내부망 권장)
# ─────────────────────────────────────────────────────────
AI_SERVER_BASE_URL = _env("AI_SERVER_BASE_URL", "http://127.0.0.1:8000")
AI_SERVER_TIMEOUT_SEC = _env_int("AI_SERVER_TIMEOUT_SEC", 5)
AI_SERVER_CHAT_TIMEOUT_SEC = _env_int("AI_SERVER_CHAT_TIMEOUT_SEC", 10)  # /chat은 /classify보다 느림

# VOICE_GUIDE 관련
VOICE_GUIDE_ENABLED = _env_bool("VOICE_GUIDE_ENABLED", True)   # MCP 서버 미연결 시 False로 끄기 용도
VOICE_GUIDE_FALLBACK = _env_bool("VOICE_GUIDE_FALLBACK", True)  # MCP 실패 시 로컬 문구 사용 여부

# MCP 재시도 설정
MCP_MAX_RETRIES = _env_int("MCP_MAX_RETRIES", 2)
MCP_RETRY_DELAY_SEC = _env_int("MCP_RETRY_DELAY_SEC", 1)

# 사용자 유형별 자동 UI 설정 데이터 (변경 없음)
USER_CONFIGS = {
    "ELDERLY": {
        "largeFont": True,
        "highContrast": False,
        "simpleMode": True,
        "lowScreenMode": False,
        "fontSize": "24px",
    },
    "HIGH_CONTRAST": {
        "largeFont": False,
        "highContrast": True,
        "simpleMode": False,
        "lowScreenMode": False,
        "fontSize": "16px",
    },
    "WHEELCHAIR": {
        "largeFont": False,
        "highContrast": False,
        "simpleMode": False,
        "lowScreenMode": True,
        "fontSize": "20px",
    },
    "NORMAL": {
        "largeFont": False,
        "highContrast": False,
        "simpleMode": False,
        "lowScreenMode": False,
        "fontSize": "16px",
    },
}
