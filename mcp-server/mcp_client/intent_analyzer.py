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
            print(f"⚠️ AI 응답 형식 오류: dict가 아닌 {type(ai_raw_response)}")
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


# import config


# class IntentAnalyzer:
#     """AI의 원시 응답을 파싱하여 통일된 dict 형태로 반환"""

#     # 키워드 → 서비스 ID 매핑 테이블
#     _SERVICE_MAP = {
#         "등본":   config.SERVICE_ID_CERTIFICATE,    # 102
#         "초본":   config.SERVICE_ID_CERTIFICATE,
#         "전입":   config.SERVICE_ID_REGISTRATION,    # 101
#         "전출":   config.SERVICE_ID_REGISTRATION,
#     }

#     # 키워드 → 사용자 유형 힌트 매핑
#     _USER_TYPE_HINTS = {
#         "어르신": "ELDERLY",
#         "노인":   "ELDERLY",
#         "큰글씨": "ELDERLY",
#         "휠체어": "WHEELCHAIR",
#         "낮은":   "WHEELCHAIR",
#     }

#     def parse_voice_intent(self, ai_raw_response: dict) -> dict | None:
#         """
#         AI의 원시 응답에서 핵심 의도를 추출한다.

#         Parameters
#         ----------
#         ai_raw_response : dict
#             AI 서버가 돌려준 원본 JSON.
#             예: {"intent": "ISSUE", "target": "등본", "confidence": 0.92,
#                  "extra": "휠체어 이용자입니다"}

#         Returns
#         -------
#         dict | None
#             {
#                 "serviceId":  int,       # 실행할 서비스 ID
#                 "userType":   str,       # "NORMAL" | "ELDERLY" | "WHEELCHAIR"
#                 "confidence": float      # 0.0 ~ 1.0
#             }
#             파싱에 실패하면 None을 반환한다.
#         """
#         if not isinstance(ai_raw_response, dict):
#             print(f"⚠️ AI 응답 형식 오류: dict가 아닌 {type(ai_raw_response)}")
#             return None

#         # ── 1. 신뢰도 추출 ──────────────────────
#         confidence = ai_raw_response.get("confidence", 0.0)

#         # ── 2. 서비스 ID 결정 ────────────────────
#         target = str(ai_raw_response.get("target", ""))
#         service_id = self._resolve_service(target)

#         # ── 3. 사용자 유형 결정 ──────────────────
#         # AI 응답의 모든 텍스트 필드를 합쳐서 힌트 탐색
#         combined_text = " ".join(
#             str(v) for v in ai_raw_response.values() if isinstance(v, str)
#         )
#         user_type = self._resolve_user_type(combined_text)

#         return {
#             "serviceId":  service_id,
#             "userType":   user_type,
#             "confidence": confidence,
#         }

#     # ─────────────────────────────────────────────
#     # 내부 헬퍼
#     # ─────────────────────────────────────────────
#     def _resolve_service(self, target_text: str) -> int:
#         """target 문자열에서 서비스 ID를 결정한다."""
#         for keyword, sid in self._SERVICE_MAP.items():
#             if keyword in target_text:
#                 return sid
#         # 매칭 실패 시 기본값
#         return config.SERVICE_ID_REGISTRATION

#     def _resolve_user_type(self, text: str) -> str:
#         """텍스트 내 힌트 키워드로 사용자 유형을 판별한다."""
#         for keyword, utype in self._USER_TYPE_HINTS.items():
#             if keyword in text:
#                 return utype
#         return "NORMAL"