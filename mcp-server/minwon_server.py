import json
import os
import logging

# 로깅 설정 (팀 가이드라인 준수)
logging.basicConfig(level=logging.INFO)

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

def get_minwon_info_by_id(service_id):
    """[추가] 팀 명세서의 serviceId(정수형)를 기반으로 정보를 조회하는 함수"""
    data = load_minwon_data()
    minwon_dict = data.get("minwon_list", {})

    # serviceId가 매칭되는 항목 찾기
    for key, info in minwon_dict.items():
        # json의 serviceId가 문자열일 수도 있고 정수일 수도 있으므로 안전하게 비교
        if str(info.get("serviceId")) == str(service_id):
            response = (
                f"{info['name']} 발급 안내입니다. "
                f"절차는 {info['steps']} 이며, "
                f"수수료는 {info['fee']}입니다."
            )
            return response
            
    return f"요청하신 서비스 ID {service_id}에 대한 정보를 찾을 수 없습니다."

def get_minwon_info(keyword):
    """기존 키워드 기반 검색 함수 (텍스트 매칭용)"""
    data = load_minwon_data()
    minwon_dict = data.get("minwon_list", {})

    # 사용자가 말한 문장에 키워드가 있는지 확인
    for key, info in minwon_dict.items():
        if key in keyword:
            response = (
                f"{info['name']} 발급 안내입니다. "
                f"절차는 {info['steps']} 이며, "
                f"수수료는 {info['fee']}입니다."
            )
            return response
            
    return "해당 민원에 대한 정보를 찾을 수 없습니다."