# WebSocket/STOMP 설정
WS_URL = "ws://localhost:8080/ws"
WS_RECONNECT_DELAY = 2
WS_MAX_RECONNECT_TRIES = 10

# 구독 경로
STOMP_SUB_FRONT_EVENTS = "/topic/front/events"
STOMP_SUB_FRONT_ACK = "/topic/front/ack"

# 발행 경로
STOMP_PUB_UI_PREFIX = "/topic/ui"

# MCP 서버 설정
MCP_SERVER_PATH = "./mcp_server.py"

# 서비스 ID 상수
SERVICE_ID_REGISTRATION = 101
SERVICE_ID_CERTIFICATE = 102

# 세션 설정
SESSION_TIMEOUT_SEC = 300
SESSION_CLEANUP_INTERVAL = 30

# 참고:
# 프론트에서 페이지 단위 idle timer를 관리하는 구조라면,
# MCP Client 쪽 app-global idle timer는 사용하지 않는 것을 권장.
IDLE_TIMEOUT_SEC = 60
IDLE_WARNING_SEC = 45

# AI 서버 설정
AI_SERVER_BASE_URL = "http://127.0.0.1:8000"
AI_SERVER_TIMEOUT_SEC = 5

# 사용자 유형별 자동 UI 설정 데이터
USER_CONFIGS = {
    "ELDERLY": {
        "largeFont": True,
        "highContrast": True,
        "simpleMode": True,
        "lowScreenMode": False,
        "fontSize": "24px"
    },
    "WHEELCHAIR": {
        "largeFont": False,
        "highContrast": False,
        "simpleMode": False,
        "lowScreenMode": True,
        "fontSize": "20px"
    },
    "NORMAL": {
        "largeFont": False,
        "highContrast": False,
        "simpleMode": False,
        "lowScreenMode": False,
        "fontSize": "16px"
    }
}
