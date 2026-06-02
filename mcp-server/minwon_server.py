import json
import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, dict

# 로깅 설정 (팀 가이드라인 준수)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="KNU Minwon AI Server")

# JSON 파일 경로 설정
DATA_FILE = os.path.join(os.path.dirname(__file__), 'minwon_data.json')

def load_minwon_data():
    """JSON 파일에서 민원 데이터를 읽어오는 함수 (예외 처리 추가)"""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"데이터 파일을 찾을 수 없습니다: {DATA_FILE}")
        return {"minwon_list": {}}
    except json.JSONDecodeError:
        logging.error("JSON 파일 형식이 올바르지 않습니다.")
        return {"minwon_list": {}}

# ============================================================
# [추가] Pydantic 데이터 모델 정의 (MCP Client 인터페이스 준수)
# ============================================================
class ExtraContext(BaseModel):
    retryCount: int = 0
    prevStep: Optional[str] = None

class ChatRequest(BaseModel):
    mode: str = "classify"  # "classify" (기본값) 또는 "step_guide"[cite: 3]
    text: Optional[str] = ""
    session_id: str
    locale: str = "ko-KR"
    conversation_history: Optional[List[dict]] = []
    
    # step_guide 모드용 추가 필드[cite: 3]
    step: Optional[str] = None
    userType: Optional[str] = "NORMAL"
    serviceId: Optional[int] = None
    extra_context: Optional[ExtraContext] = None

class ChatResponse(BaseModel):
    intent: Optional[str] = None
    serviceId: Optional[str] = None
    userType: Optional[str] = None
    confidence: Optional[float] = None
    answer: str
    conversation_history: List[dict] = []

# ============================================================
# [추가] /chat 엔드포인트 비즈니스 로직
# ============================================================
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    logging.info(f"[/chat] 요청 수신 - 모드: {request.mode}, 세션ID: {request.session_id}")[cite: 3]
    
    # --------------------------------------------------------
    # [CASE 1] mode = "classify" (기존 음성 발화 분석 및 최초 진입)[cite: 3]
    # --------------------------------------------------------
    if request.mode == "classify":
        # 기존 키워드 기반 매칭 로직 활용
        keyword = request.text or ""
        data = load_minwon_data()
        minwon_dict = data.get("minwon_list", {})
        
        matched_info = None
        matched_key = None
        
        for key, info in minwon_dict.items():
            if key in keyword or info.get("name") in keyword:
                matched_info = info
                matched_key = key
                break
        
        if matched_info:
            # 매칭된 민원 서비스가 있을 때의 응답 (하위 호환성 유지)
            service_id_str = str(matched_info.get("serviceId"))
            # 기본 안내 문구 결합
            answer_text = f"{matched_info['name']} 발급을 도와드릴게요. 신분증을 준비해 주세요."[cite: 3]
            
            return ChatResponse(
                intent="SERVICE_REQUEST",
                serviceId=service_id_str,
                userType="NORMAL",  # 기본값 설정 (mcp_server에서 힌트 정제 가능)
                confidence=0.95,
                answer=answer_text,
                conversation_history=request.conversation_history + [{"role": "assistant", "content": answer_text}]
            )
        else:
            # 매칭 실패 시 기본 응답
            fallback_answer = "무엇을 도와드릴까요? 필요한 민원 서비스를 말씀해 주세요."[cite: 3]
            return ChatResponse(
                intent="GENERAL_QUESTION",
                serviceId=None,
                userType="NORMAL",
                confidence=0.0,
                answer=fallback_answer,
                conversation_history=request.conversation_history + [{"role": "assistant", "content": fallback_answer}]
            )

    # --------------------------------------------------------
    # [CASE 2] mode = "step_guide" (신규 단계 전환 안내 문구 생성)[cite: 3]
    # --------------------------------------------------------
    elif request.mode == "step_guide":
        if not request.step:
            raise HTTPException(status_code=400, detail="step_guide 모드에서는 'step' 필드가 필수입니다.")[cite: 3]
            
        step_key = request.step
        user_type = request.userType or "NORMAL"
        retry_count = request.extra_context.retryCount if request.extra_context else 0[cite: 3]
        
        logging.info(f"단계 가이드 생성 중: 단계={step_key}, 유저유형={user_type}, 재시도={retry_count}")
        
        # 기본 안내 문구 (폴백용 기본 셋팅)
        guide_answer = "화면의 지시에 따라 단계를 진행해 주세요."
        
        # 3절 가이드라인을 준수한 단계별/속성별 분기 가이드 멘트 빌더[cite: 3]
        # (실제 LLM 연동 시 아래 프롬프트 지침을 시스템 프롬프트에 주입하여 처리하도록 구현하면 됩니다)[cite: 3]
        
        # 예시: 주민등록등본 관련 단계 처리 (serviceId = 102 또는 관련 스텝)[cite: 3]
        if "CERTIFICATE" in step_key or request.serviceId == 102:
            if step_key == "CERTIFICATE_SELECT_PURPOSE":
                guide_answer = "발급받으실 증명서의 종류를 선택해 주세요."
                if user_type == "ELDERLY":
                    guide_answer = "어르신, 원하시는 증명서 종류를 화면에서 천천히 골라주세요."[cite: 3]
                    
            elif step_key == "CERTIFICATE_SELECT_RRN":
                # 보안 지침 준수: 실제 수집이 아닌 키패드 입력 행동 지침만 전달[cite: 3]
                if user_type == "ELDERLY":
                    guide_answer = "앞자리와 뒷자리를 화면에 천천히 입력해 주세요."[cite: 3]
                    if retry_count >= 1:
                        guide_answer = "어려우시면 화면 우측의 직원 호출 버튼을 눌러 주세요."[cite: 3]
                else:
                    guide_answer = "주민등록번호 13자리를 입력해 주세요."[cite: 3]
                    if retry_count >= 1:
                        guide_answer = "다시 한번 천천히 입력해 주세요."[cite: 3]
                        
            elif step_key == "CERTIFICATE_SELECT_SCOPE":
                guide_answer = "발급 형태와 표시할 정보 범위를 선택해 주세요."
            elif step_key == "CERTIFICATE_SELECT_COUNT":
                guide_answer = "발급받으실 매수를 선택해 주세요."
            elif step_key == "CERTIFICATE_CONFIRM":
                guide_answer = "신청 내용을 확인하신 후 최종 확인 버튼을 눌러주세요."
            elif step_key == "CERTIFICATE_PRINTING":
                guide_answer = "증명서를 인쇄하고 있습니다. 잠시만 기다려 주세요."
            elif step_key == "CERTIFICATE_COMPLETE":
                guide_answer = "발급이 완료되었습니다. 출력구에서 증명서를 잊지 말고 챙겨 가세요."
                if user_type == "WHEELCHAIR":
                    guide_answer = "발급이 완료되었습니다. 기기 아래 출력구에서 한 번에 편하게 꺼내 가세요."[cite: 3]

        # 예시: 전입신고 관련 단계 처리 (serviceId = 101 또는 관련 스텝)[cite: 3]
        elif "MOVEIN" in step_key or request.serviceId == 101:
            if step_key == "MOVEIN_INPUT_BASIC_INFO":
                guide_answer = "본인 확인을 위해 인적 사항을 입력해 주세요."
                if user_type == "ELDERLY":
                    guide_answer = "인적 사항을 천천히 기입해 주세요. 괜찮으시니 서두르지 마세요."[cite: 3]
            elif step_key == "MOVEIN_CONFIRM":
                guide_answer = "신고 내용을 최종적으로 확인하고 제출 버튼을 눌러 주세요."[cite: 3]
                if user_type == "WHEELCHAIR":
                    guide_answer = "내용을 확인하고 화면 아래 제출 버튼을 한 번 눌러 주세요."[cite: 3]
            elif step_key == "MOVEIN_COMPLETE":
                guide_answer = "전입신고 신청이 정상적으로 완료되었습니다."

        return ChatResponse(
            answer=guide_answer,
            conversation_history=request.conversation_history
        )
        
    else:
        raise HTTPException(status_code=400, detail="올바르지 않은 mode 파라미터 값입니다.")[cite: 3]

# 기존 함수 유지 (호환성 및 테스트용)
def get_minwon_info_by_id(service_id):
    data = load_minwon_data()
    minwon_dict = data.get("minwon_list", {})
    for key, info in minwon_dict.items():
        if str(info.get("serviceId")) == str(service_id):
            return f"{info['name']} 발급 안내입니다. 절차는 {info['steps']} 이며, 수수료는 {info['fee']}입니다."
    return f"요청하신 서비스 ID {service_id}에 대한 정보를 찾을 수 없습니다."

def get_minwon_info(keyword):
    data = load_minwon_data()
    minwon_dict = data.get("minwon_list", {})
    for key, info in minwon_dict.items():
        if key in keyword:
            return f"{info['name']} 발급 안내입니다. 절차는 {info['steps']} 이며, 수수료는 {info['fee']}입니다."
    return "해당 민원에 대한 정보를 찾을 수 없습니다."

# 로컬 단독 테스트 실행용 구문
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("minwon_server:app", host="127.0.0.1", port=8000, reload=True)