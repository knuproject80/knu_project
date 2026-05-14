# # intent_analyzer.py
import config


class IntentAnalyzer:
    """AI의 원시 응답을 파싱하여 통일된 dict 형태로 반환"""

    _SERVICE_CODE_TO_ID = {
        "RESIDENT_REGISTRATION_COPY": config.SERVICE_ID_CERTIFICATE,
        "RESIDENT_REGISTRATION_ABSTRACT": config.SERVICE_ID_CERTIFICATE,
        "MOVE_IN_REPORT": config.SERVICE_ID_REGISTRATION,
        "MOVE_OUT_REPORT": config.SERVICE_ID_REGISTRATION,
    }

    _USER_TYPE_HINTS = {
        "어르신": "ELDERLY",
        "노인": "ELDERLY",
        "큰글씨": "ELDERLY",
        "휠체어": "WHEELCHAIR",
        "낮은": "WHEELCHAIR",
    }

    def parse_voice_intent(self, ai_raw_response: dict) -> dict | None:
        if not isinstance(ai_raw_response, dict):
            logger.warning("AI 응답 형식 오류: dict가 아닌 %s", type(ai_raw_response))
            return None

        confidence = float(ai_raw_response.get("confidence", 0.0))

        # AI 서버가 직접 serviceId를 준다고 가정
        service_code = str(ai_raw_response.get("serviceId", ""))
        service_id = self._resolve_service_id_from_code(service_code)

        combined_text = " ".join(
            str(v) for v in ai_raw_response.values() if isinstance(v, str)
        )
        user_type = self._resolve_user_type(combined_text)

        return {
            "serviceId": service_id,
            "serviceCode": service_code,
            "userType": user_type,
            "confidence": confidence,
        }

    def _resolve_service_id_from_code(self, service_code: str) -> int:
        return self._SERVICE_CODE_TO_ID.get(
            service_code,
            config.SERVICE_ID_REGISTRATION,
        )

    def _resolve_user_type(self, text: str) -> str:
        for keyword, utype in self._USER_TYPE_HINTS.items():
            if keyword in text:
                return utype
        return "NORMAL"


