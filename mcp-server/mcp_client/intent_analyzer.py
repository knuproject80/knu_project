# intent_analyzer.py
import logging

import config

logger = logging.getLogger(__name__)


class IntentAnalyzer:
    """
    AI의 원시 응답을 파싱하여 통일된 dict 형태로 반환

    변경 이력
    ─────────────────────────────────────────────────────────
    - parse_voice_intent() 반환값에 answer / conversation_history 추가
      · answer              : AI가 생성한 자연어 답변 (VOICE_GUIDE guideText로 사용)
      · conversation_history: 누적 대화 기록 (다음 /chat 호출 시 그대로 전달)
    - logger 미선언 버그 수정 (기존 코드에 logger 없음)
    - _resolve_user_type: combined_text에 answer도 포함하여 userType 감지 정확도 향상
    ─────────────────────────────────────────────────────────
    """

    _SERVICE_CODE_TO_ID = {
        "RESIDENT_REGISTRATION_COPY":     config.SERVICE_ID_CERTIFICATE,
        "RESIDENT_REGISTRATION_ABSTRACT": config.SERVICE_ID_CERTIFICATE,
        "MOVE_IN_REPORT":                 config.SERVICE_ID_REGISTRATION,
        "MOVE_OUT_REPORT":                config.SERVICE_ID_REGISTRATION,
    }

    _USER_TYPE_HINTS = {
        "어르신":  "ELDERLY",
        "노인":    "ELDERLY",
        "큰글씨":  "ELDERLY",
        "휠체어":  "WHEELCHAIR",
        "낮은":    "WHEELCHAIR",
    }

    def parse_voice_intent(self, ai_raw_response: dict) -> dict | None:
        """
        /chat 또는 /classify/service 응답을 파싱한다.

        반환 예시:
        {
            "serviceId":            102,
            "serviceCode":          "RESIDENT_REGISTRATION_COPY",
            "userType":             "NORMAL",
            "confidence":           0.92,
            "answer":               "주민등록등본 발급을 도와드릴게요. 신분증을 준비해 주세요.",
            "conversation_history": [ ... ]
        }
        """
        if not isinstance(ai_raw_response, dict):
            logger.warning(
                "AI 응답 형식 오류: dict가 아닌 %s", type(ai_raw_response)
            )
            return None

        confidence = float(ai_raw_response.get("confidence", 0.0))

        service_code = str(ai_raw_response.get("serviceId", ""))
        service_id = self._resolve_service_id_from_code(service_code)

        # answer도 combined_text에 포함 — userType 감지 정확도 향상
        # (예: answer에 "어르신" 포함 시 ELDERLY 감지)
        combined_text = " ".join(
            str(v) for v in ai_raw_response.values() if isinstance(v, str)
        )
        user_type = self._resolve_user_type(combined_text)

        # ── /chat 전용 필드 추출 ──────────────────────────────
        answer = str(ai_raw_response.get("answer", ""))
        conversation_history = ai_raw_response.get("conversation_history", [])
        if not isinstance(conversation_history, list):
            logger.warning("conversation_history가 list가 아님 — 빈 리스트로 대체")
            conversation_history = []

        return {
            "serviceId":            service_id,
            "serviceCode":          service_code,
            "userType":             user_type,
            "confidence":           confidence,
            "answer":               answer,               # AI 생성 자연어 답변
            "conversation_history": conversation_history, # 누적 대화 기록
        }

    def _resolve_service_id_from_code(self, service_code: str) -> int | None:
        """
        문자열 serviceCode를 정수 serviceId로 변환한다.
        매핑 없는 코드(빈 문자열 포함)는 None 반환 →
        main.py에서 None 체크 후 미지원 서비스 안내로 분기한다.
        """
        if not service_code:
            return None
        return self._SERVICE_CODE_TO_ID.get(service_code)  # 없으면 None

    def _resolve_user_type(self, text: str) -> str:
        for keyword, utype in self._USER_TYPE_HINTS.items():
            if keyword in text:
                return utype
        return "NORMAL"
