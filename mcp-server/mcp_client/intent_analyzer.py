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
        # ── ELDERLY — 큰 글씨 / 확대 요청 ────────────────────────────
        "어르신":      "ELDERLY",
        "노인":        "ELDERLY",
        "큰글씨":      "ELDERLY",
        "큰 글씨":     "ELDERLY",
        "글씨 크게":   "ELDERLY",
        "글자 크게":   "ELDERLY",
        "글씨 키워":   "ELDERLY",
        "글씨를 키워": "ELDERLY",
        "글자 키워":   "ELDERLY",
        "글자를 키워": "ELDERLY",
        "글자크기":    "ELDERLY",
        "글씨크기":    "ELDERLY",
        "폰트 크게":   "ELDERLY",
        "폰트크게":    "ELDERLY",
        "텍스트 크게": "ELDERLY",
        "텍스트크게":  "ELDERLY",
        "확대해":      "ELDERLY",
        "확대":        "ELDERLY",
        "크게 해":     "ELDERLY",
        "글자를 크게": "ELDERLY",
        "글씨를 크게": "ELDERLY",
        "크게 보":     "ELDERLY",
        "화면 크게":   "ELDERLY",
        "화면크게":    "ELDERLY",
        "더 크게":     "ELDERLY",
        "잘 안 보":    "ELDERLY",
        "안 보여":     "ELDERLY",
        "안보여":      "ELDERLY",
        "눈이 침침":   "ELDERLY",
        "침침":        "ELDERLY",
        "화면이 작":   "ELDERLY",
        "글씨가 작":   "ELDERLY",
        "글자가 작":   "ELDERLY",
        "잘 안보":     "ELDERLY",

        # ── HIGH_CONTRAST — 고대비 전용 ───────────────────────────────
        "고대비":        "HIGH_CONTRAST",
        "고대비 모드":   "HIGH_CONTRAST",
        "고대비로":      "HIGH_CONTRAST",
        "대비 높여":     "HIGH_CONTRAST",
        "대비 크게":     "HIGH_CONTRAST",
        "대비높여":      "HIGH_CONTRAST",
        "색상 대비":     "HIGH_CONTRAST",
        "색 대비":       "HIGH_CONTRAST",
        "눈이 부":       "HIGH_CONTRAST",
        "눈부":          "HIGH_CONTRAST",
        "너무 밝":       "HIGH_CONTRAST",
        "화면 밝":       "HIGH_CONTRAST",
        "화면이 밝":     "HIGH_CONTRAST",
        "어둡게":        "HIGH_CONTRAST",
        "화면 어둡":     "HIGH_CONTRAST",

        # ── WHEELCHAIR — 낮은 화면 ────────────────────────────────────
        "휠체어":        "WHEELCHAIR",
        "낮은":          "WHEELCHAIR",
        "낮은 화면":     "WHEELCHAIR",
        "화면 낮게":     "WHEELCHAIR",
        "화면 내려":     "WHEELCHAIR",
        "화면내려":      "WHEELCHAIR",
        "아래로 내려":   "WHEELCHAIR",
        "내려줘":        "WHEELCHAIR",
        "손이 안 닿":    "WHEELCHAIR",
        "손이 닿":       "WHEELCHAIR",
        "낮춰":          "WHEELCHAIR",
        "화면 낮춰":     "WHEELCHAIR",

        # ── NORMAL — 일반 모드 복귀 ───────────────────────────────────
        "일반":          "NORMAL",
        "일반 모드":     "NORMAL",
        "원래대로":      "NORMAL",
        "원래 화면":     "NORMAL",
        "되돌려":        "NORMAL",
        "기본":          "NORMAL",
        "기본 모드":     "NORMAL",
        "초기화":        "NORMAL",
        "원래로":        "NORMAL",
        "처음대로":      "NORMAL",
        "취소해":        "NORMAL",
    }

    def parse_voice_intent(self, ai_raw_response: dict, original_text: str = "") -> dict | None:
        """
        /chat 또는 /classify/service 응답을 파싱한다.
        """
        if not isinstance(ai_raw_response, dict):
            logger.warning(
                "AI 응답 형식 오류: dict가 아닌 %s", type(ai_raw_response)
            )
            return None

        confidence = float(ai_raw_response.get("confidence", 0.0))

        service_code = str(ai_raw_response.get("serviceId", ""))
        service_id = self._resolve_service_id_from_code(service_code)

        ai_user_type = ai_raw_response.get("userType", "")
        non_normal_types = {"ELDERLY", "HIGH_CONTRAST", "WHEELCHAIR"}
        if ai_user_type in non_normal_types:
            user_type = ai_user_type
            explicit_normal = False
            logger.debug("userType AI 응답 우선 사용: %s", user_type)
        else:
            ai_str_values = " ".join(
                str(v) for v in ai_raw_response.values() if isinstance(v, str)
            )
            combined_text = f"{original_text} {ai_str_values}".strip()
            keyword_type, explicit_normal = self._resolve_user_type(combined_text)
            if keyword_type != "NORMAL":
                logger.debug(
                    "AI userType=%s 이나 키워드 스캔으로 %s 감지 → 교정",
                    ai_user_type, keyword_type,
                )
            user_type = keyword_type

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
            "explicit_normal":      explicit_normal,
            "confidence":           confidence,
            "answer":               answer,
            "conversation_history": conversation_history,
        }

    def _resolve_service_id_from_code(self, service_code: str) -> int | None:
        if not service_code:
            return None
        return self._SERVICE_CODE_TO_ID.get(service_code)

    def _resolve_user_type(self, text: str) -> tuple[str, bool]:
        """
        키워드 스캔으로 userType을 결정한다.
        STT의 오인식(불규칙한 띄어쓰기) 방어를 위해 공백을 제거한 문자열 매칭을 수행한다. [수정]
        """
        text_no_spaces = text.replace(" ", "")  # 사용자 발화 전체 공백 제거

        for keyword, utype in self._USER_TYPE_HINTS.items():
            kw_no_spaces = keyword.replace(" ", "")  # 매칭 힌트용 키워드 공백 제거
            
            # 원문 매칭 또는 공백을 전부 제거한 텍스트의 부분 일치 확인
            if keyword in text or kw_no_spaces in text_no_spaces:
                return utype, (utype == "NORMAL")
                
        return "NORMAL", False