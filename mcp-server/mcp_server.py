import os
import json
import logging
from mcp.server.fastmcp import FastMCP

# 로깅 설정 (팀의 main.py 포맷과 통일)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s  %(message)s",
)
logger = logging.getLogger("kiosk.mcp_server")

# 1. FastMCP 서버 초기화 (팀의 공식 서버 명칭 반영)
mcp = FastMCP("barrier-free-kiosk-mcp-server")

# 데이터 파일 경로 설정
DATA_FILE_PATH = os.path.join(os.path.dirname(__file__), "minwon_data.json")

def load_minwon_data() -> dict:
    """JSON 창고 파일로부터 민원 데이터를 안전하게 로드합니다."""
    try:
        if os.path.exists(DATA_FILE_PATH):
            with open(DATA_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"민원 데이터 로드 실패: {e}")
    return {"minwon_list": {}}

# ──────────────────────────────────────────────────────────
# 🛠️ MCP 공식 3대 Tool 구현부
# ──────────────────────────────────────────────────────────

@mcp.tool()
async def start_session(user_type: str = "NORMAL") -> dict:
    """
    [Tool 1] 키오스크 세션을 시작하고 사용자 유형별 고유 세션 ID를 생성합니다.
    팀의 README v0.2.0 규격에 맞춰 'sessionId' 키를 무조건 보장합니다.
    """
    logger.info(f"start_session 호출됨 - 사용자 유형: {user_type}")
    
    # 세션 ID 생성 (예: sess-ELDERLY-12345)
    import random
    rand_id = random.randint(10000, 99999)
    session_id = f"sess-{user_type}-{rand_id}"
    
    # 규칙: 반드시 dict 타입 리턴 및 'sessionId' 필드 포함 필수
    return {
        "sessionId": session_id,
        "status": "created",
        "userType": user_type
    }

@mcp.tool()
async def start_service(session_id: str, service_id: int, user_type: str = "NORMAL") -> dict:
    """
    [Tool 2] 선택된 서비스 ID에 맞는 민원 정보를 창고(JSON)에서 조회하여 메타데이터를 반환합니다.
    config.py의 ID 매핑(101: 전입신고, 102: 증명서류)과 완벽히 연동됩니다.
    """
    logger.info(f"start_service 호출됨 - 세션: {session_id}, 서비스ID: {service_id}")
    
    data = load_minwon_data()
    minwon_list = data.get("minwon_list", {})
    
    resolved_name = "알 수 없는 서비스"
    
    # 정합성이 교정된 데이터베이스 구조를 기반으로 ID 매칭 수행
    for key, info in minwon_list.items():
        if info.get("serviceId") == service_id:
            # 등본/초본 구분을 위해 정확한 name 추출
            resolved_name = info.get("name", key)
            break

    return {
        "serviceId": service_id,
        "serviceName": resolved_name,
        "status": "initialized"
    }

@mcp.tool()
async def voice_guide(session_id: str, text: str, user_type: str, context: str) -> dict:
    """
    [Tool 3] main.py의 _on_step_change 핸들러가 던져주는 상세 단계(context)를 분석하여
    수수료 정보나 가이드 문구를 하드웨어 및 로직 레벨에서 동적으로 조합해 반환합니다.
    """
    logger.info(f"voice_guide 호출됨 - 맥락(Context): {context}, 유저타입: {user_type}")
    
    final_text = text  # 기본값은 클라이언트가 준 fallback 텍스트 사용
    data = load_minwon_data()
    minwon_list = data.get("minwon_list", {})
    
    # 1. 주민등록등본/초본 관련 스텝 (serviceId: 102) 싱크 정렬
    if context.startswith("CERTIFICATE_"):
        cert_data = minwon_list.get("등본", {})
        fee = cert_data.get("fee", "400원")
        
        if context == "CERTIFICATE_CONFIRM":
            if user_type == "ELDERLY":
                final_text = f"내용을 천천히 확인해 보세요. 발급 수수료는 {fee}원입니다. 맞으시면 발급 버튼을 눌러 주세요."
            else:
                final_text = f"입력하신 내용을 확인해 주세요. 수수료는 {fee}원입니다. 맞으면 발급 버튼을 눌러 주세요."
                
        elif context == "CERTIFICATE_PRINTING":
            if user_type == "WHEELCHAIR":
                final_text = f"출력 중입니다. 수수료 {fee}원이 결제되며, 서류는 아래 출력구에서 나옵니다. 잠시 기다려 주세요."
            else:
                final_text = f"출력 중입니다. 수수료 {fee}원이 결제됩니다. 잠시 기다려 주세요."

    # 2. 전입신고 관련 스텝 (serviceId: 101) 싱크 정렬
    elif context.startswith("MOVEIN_"):
        movein_data = minwon_list.get("전입", {})
        steps_info = movein_data.get("steps", "인적사항 입력")
        
        if context == "MOVEIN_INPUT_PREV_ADDRESS":
            if user_type == "ELDERLY":
                final_text = f"{steps_info} 단계입니다. 이사 오시기 전 살던 주소를 천천히 입력해 주세요."
            else:
                final_text = f"{steps_info} 단계입니다. 이전 주소를 입력해 주세요."

    # 클라이언트가 크래시 없이 읽을 수 있는 표준 응답 포맷 보장
    return {
        "guideText": final_text,
        "audioUrl": None,  # 향후 릴리즈에서 실제 음성 파일 파일 주소 연동 공간
        "lang": "ko-KR"
    }

if __name__ == "__main__":
    # stdio 기반으로 서버 구동
    mcp.run(transport="stdio")