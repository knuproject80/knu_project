import os
import json
import logging
import random
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

# ──────────────────────────────────────────────────────────
# 🚨 [신규 추가] TC-FE-15 해결을 위한 접근성 확장 키워드 사전
# ──────────────────────────────────────────────────────────
_USER_TYPE_HINTS = {
    "어르신": "ELDERLY",
    "노인": "ELDERLY",
    "큰글씨": "ELDERLY",
    "큰 글씨": "ELDERLY",
    "글씨 크게": "ELDERLY",
    "글자 크게": "ELDERLY",
    "글씨 키워": "ELDERLY",
    "글자 키워": "ELDERLY",
    "확대": "ELDERLY",
    "확대해": "ELDERLY",
    "크게 해": "ELDERLY",
    
    "휠체어": "WHEELCHAIR",
    "낮은": "WHEELCHAIR",
    "낮은 화면": "WHEELCHAIR",
    "화면 낮게": "WHEELCHAIR",
}

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
async def start_session(user_type: str = "NORMAL", raw_text: str = "") -> dict:
    """
    [Tool 1] 키오스크 세션을 시작하고 사용자 유형별 고유 세션 ID를 생성합니다.
    - 프론트엔드 동적 구독 대응을 위한 SESSION_ASSIGNED 시그널 메타데이터 포함.
    - AI 판단 결과(user_type)를 최우선으로 존중하며, 차선책으로 텍스트 힌트를 분석합니다.
    """
    logger.info(f"start_session 호출됨 - 입력 유저타입: {user_type}, 입력 텍스트: '{raw_text}'")
    
    # 1. 유저 타입 판별 보완 (AI 판단이 NORMAL이더라도 발화 텍스트에 힌트가 있다면 교정)
    final_user_type = user_type
    if final_user_type == "NORMAL" and raw_text:
        for keyword, hint_type in _USER_TYPE_HINTS.items():
            if keyword in raw_text:
                logger.info(f"🚨 [정정] 발화 키워드 '{keyword}' 감지로 인해 유저 타입을 {hint_type}로 전환합니다.")
                final_user_type = hint_type
                break
                
    # 2. 세션 ID 생성 (예: sess-ELDERLY-12345)
    rand_id = random.randint(10000, 99999)
    session_id = f"sess-{final_user_type}-{rand_id}"
    
    # 3. 프론트엔드가 /topic/ui/global 에서 캐치하여 동적 구독을 개시할 수 있도록 규격 설계
    # (mcp_client가 이 반환 데이터를 받아 STOMP global 토픽으로 SESSION_ASSIGNED 액션을 선행 전송합니다)
    return {
        "sessionId": session_id,
        "status": "created",
        "userType": final_user_type,
        "action": "SESSION_ASSIGNED",
        "targetTopic": f"/topic/ui/{session_id}"
    }

@mcp.tool()
async def start_service(session_id: str, service_id: int, user_type: str = "NORMAL") -> dict:
    """
    [Tool 2] 선택된 서비스 ID에 맞는 민원 정보를 창고(JSON)에서 조회하여 메타데이터를 반환합니다.
    """
    logger.info(f"start_service 호출됨 - 세션: {session_id}, 서비스ID: {service_id}")
    
    data = load_minwon_data()
    minwon_list = data.get("minwon_list", {})
    
    resolved_name = "알 수 없는 서비스"
    
    for key, info in minwon_list.items():
        if info.get("serviceId") == service_id:
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
    [Tool 3] 상세 단계(context) 및 유저 타입 정보를 분석하여 맞춤형 안내 멘트를 반환합니다.
    """
    logger.info(f"voice_guide 호출됨 - 맥락(Context): {context}, 유저타입: {user_type}")
    
    final_text = text  # 기본값은 클라이언트가 준 fallback 텍스트 사용
    data = load_minwon_data()
    minwon_list = data.get("minwon_list", {})
    
    # 1. 주민등록등본/초본 관련 스텝 (serviceId: 102) 싱크 정렬
    if context.startswith("CERTIFICATE_"):
        cert_data = minwon_list.get("등본", {})
        fee = cert_data.get("fee", "400원")
        
        # v6.1 추가 스텝 (주민등록번호 입력 단계 대응)
        if context == "CERTIFICATE_SELECT_RRN":
            if user_type == "ELDERLY":
                final_text = "앞자리와 뒷자리를 화면에 천천히 입력해 주세요. 어려우시면 우측의 직원 호출 버튼을 누르셔도 됩니다."
            else:
                final_text = "주민등록번호 13자리를 화면 키패드에 입력해 주세요."
                
        elif context == "CERTIFICATE_CONFIRM":
            if user_type == "ELDERLY":
                final_text = f"내용을 천천히 확인해 보세요. 발급 수수료는 {fee}원입니다. 맞으시면 발급 버튼을 눌러 주세요."
            else:
                final_text = f"입력하신 내용을 확인해 주세요. 수수료는 {fee}원입니다. 맞으면 발급 버튼을 눌러 주세요."
                
        elif context == "CERTIFICATE_PRINTING":
            if user_type == "WHEELCHAIR":
                final_text = f"출력 중입니다. 수수료 {fee}원이 결제되며, 서류는 아래 출력구에서 나옵니다. 잠시 기다려 주세요."
            else:
                final_text = f"출력 중입니다. 수수료 {fee}원이 결제됩니다. 잠시 기다려 주세요."
                
        elif context == "CERTIFICATE_COMPLETE":
            if user_type == "WHEELCHAIR":
                final_text = "발급이 완료되었습니다. 기기 아래 출력구에서 서류를 편하게 꺼내 가세요."

    # 2. 전입신고 관련 스텝 (serviceId: 101) 싱크 정렬
    elif context.startswith("MOVEIN_"):
        movein_data = minwon_list.get("전입", {})
        steps_info = movein_data.get("steps", "인적사항 입력")
        
        if context == "MOVEIN_INPUT_PREV_ADDRESS":
            if user_type == "ELDERLY":
                final_text = f"{steps_info} 단계입니다. 이사 오시기 전 살던 주소를 천천히 입력해 주세요."
            else:
                final_text = f"{steps_info} 단계입니다. 이전 주소를 입력해 주세요."
                
        elif context == "MOVEIN_CONFIRM":
            if user_type == "WHEELCHAIR":
                final_text = "신고 내용을 최종 확인하신 후 화면 아래쪽의 제출 버튼을 한 번 눌러 주세요."
            elif user_type == "ELDERLY":
                final_text = "작성하신 내용을 화면에서 천천히 확인해 보시고, 다 맞으시면 제출을 눌러 주세요."

    # 클라이언트가 크래시 없이 읽을 수 있는 표준 응답 포맷 보장
    return {
        "guideText": final_text,
        "audioUrl": None,  # 향후 릴리즈에서 실제 음성 파일 파일 주소 연동 공간
        "lang": "ko-KR"
    }

if __name__ == "__main__":
    # stdio 기반으로 서버 구동
    mcp.run(transport="stdio")