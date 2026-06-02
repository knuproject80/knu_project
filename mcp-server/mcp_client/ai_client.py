# ai_client.py
import logging
from typing import Any

import requests

import config

logger = logging.getLogger(__name__)


class AIClientError(Exception):
    """AI 서버 호출 관련 예외"""
    pass


class AIClient:
    """
    AI/LLM 서버 HTTP adapter

    변경 이력
    ─────────────────────────────────────────────────────────
    - chat() 메서드 추가: /chat 엔드포인트 호출
      · conversation_history 파라미터 지원 (대화 맥락 누적)
      · 응답에서 answer / conversation_history 수신
    - classify_service() 유지: 하위 호환 및 디버깅 용도
    ─────────────────────────────────────────────────────────

    역할:
    - 사용자 자연어 입력을 AI 서버에 전달
    - AI 서버 응답(JSON)을 받아 반환
    - 네트워크/응답 오류를 일관되게 처리
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout_sec: float | None = None,
        chat_timeout_sec: float | None = None,
    ):
        self.base_url = base_url or config.AI_SERVER_BASE_URL
        self.timeout_sec = timeout_sec or config.AI_SERVER_TIMEOUT_SEC
        # /chat은 AI 생성 포함으로 /classify보다 응답이 느림 — 별도 타임아웃 적용
        self.chat_timeout_sec = chat_timeout_sec or config.AI_SERVER_CHAT_TIMEOUT_SEC

    # ──────────────────────────────────────────────────────
    #  공통 HTTP 헬퍼
    # ──────────────────────────────────────────────────────

    def _post(self, endpoint: str, payload: dict, timeout: float | None = None) -> dict[str, Any]:
        """
        POST 요청 공통 처리.
        네트워크 오류 / JSON 파싱 실패 / 응답 형식 오류를 AIClientError로 변환한다.
        timeout이 None이면 self.timeout_sec을 사용한다.
        """
        url = f"{self.base_url}{endpoint}"
        logger.info("AI 서버 호출: %s", url)

        try:
            response = requests.post(
                url,
                json=payload,
                headers={"accept": "application/json"},
                timeout=timeout if timeout is not None else self.timeout_sec,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            raise AIClientError(f"AI 서버 호출 실패: {e}") from e

        try:
            result = response.json()
        except ValueError as e:
            raise AIClientError("AI 서버 응답이 JSON 형식이 아닙니다.") from e

        if not isinstance(result, dict):
            raise AIClientError(
                f"AI 서버 응답 형식 오류: dict가 아님 ({type(result).__name__})"
            )

        return result

    # ──────────────────────────────────────────────────────
    #  /chat  — 의도 분류 + 자연어 답변 생성 (주 호출)
    # ──────────────────────────────────────────────────────

    def chat(
        self,
        text: str,
        session_id: str = "string",
        locale: str = "ko-KR",
        conversation_history: list | None = None,
        mode: str = "classify",
        step: str | None = None,
        user_type: str | None = None,
        service_id: int | None = None,
        extra_context: dict | None = None,
    ) -> dict[str, Any]:
        """
        AI 서버 /chat 호출.

        mode 파라미터로 두 가지 호출 목적을 구분한다:

        ─────────────────────────────────────────────────────────
        mode="classify" (기본값) — 사용자 발화 의도 분류
        ─────────────────────────────────────────────────────────
        VOICE_INPUT 수신 시 호출. 사용자의 자연어 발화를 분석해
        의도(intent), 서비스 ID(serviceId), 사용자 유형(userType),
        신뢰도(confidence), 자연어 답변(answer)을 동시에 반환한다.

        Request:
        {
            "mode":                 "classify",
            "text":                 "주민등록등본 발급받고 싶어요",
            "session_id":           "uuid",
            "locale":               "ko-KR",
            "conversation_history": []
        }

        Response:
        {
            "intent":               "SERVICE_REQUEST",
            "serviceId":            "RESIDENT_REGISTRATION_COPY",
            "userType":             "NORMAL",
            "confidence":           0.92,
            "answer":               "주민등록등본 발급을 도와드릴게요...",
            "conversation_history": [ ... ],
            "entities":             { ... }     // 선택
        }

        ─────────────────────────────────────────────────────────
        mode="step_guide" — 단계별 안내 문구 생성 (의도 분류 없음)
        ─────────────────────────────────────────────────────────
        STEP_CHANGE 수신 시 호출. 현재 단계(step), 사용자 유형(userType),
        서비스 ID(service_id), 부가 맥락(extra_context: retryCount 등)을
        기반으로 해당 단계에 맞는 안내 문구만 생성한다.
        의도 분류는 수행하지 않으므로 intent/serviceId/confidence는 무시한다.

        Request:
        {
            "mode":          "step_guide",
            "session_id":    "uuid",
            "locale":        "ko-KR",
            "step":          "CERTIFICATE_SELECT_RRN",
            "userType":      "ELDERLY",
            "serviceId":     102,
            "extra_context": { "retryCount": 0, "prevStep": "..." },
            "conversation_history": []
        }

        Response:
        {
            "answer":               "주민등록번호 13자리를 천천히 입력해 주세요.",
            "conversation_history": [ ... ]
        }
        ─────────────────────────────────────────────────────────
        """
        payload: dict[str, Any] = {
            "mode":                 mode,
            "text":                 text,
            "session_id":           session_id,
            "locale":               locale,
            "conversation_history": conversation_history or [],
        }

        # step_guide 모드 전용 필드 — None은 전송하지 않음
        if mode == "step_guide":
            if step is not None:
                payload["step"] = step
            if user_type is not None:
                payload["userType"] = user_type
            if service_id is not None:
                payload["serviceId"] = service_id
            if extra_context is not None:
                payload["extra_context"] = extra_context

        result = self._post("/chat", payload, timeout=self.chat_timeout_sec)

        if mode == "step_guide":
            logger.info(
                "AI 응답 수신 (step_guide): step=%s userType=%s answer=%.40s…",
                step, user_type, result.get("answer", ""),
            )
        else:
            logger.info(
                "AI 응답 수신 (classify): intent=%s serviceId=%s confidence=%s answer=%.40s…",
                result.get("intent"),
                result.get("serviceId"),
                result.get("confidence"),
                result.get("answer", ""),
            )
        return result

    # ──────────────────────────────────────────────────────
    #  /classify/service  — 하위 호환 / 디버깅 전용
    # ──────────────────────────────────────────────────────

    def classify_service(
        self,
        text: str,
        session_id: str = "string",
        locale: str = "ko-KR",
    ) -> dict[str, Any]:
        """
        AI 서버 /classify/service 호출 (레거시).

        주 호출은 chat()으로 이전되었으며,
        이 메서드는 하위 호환 및 단독 분류 테스트 용도로 유지한다.

        Request:
        {
            "text":       "주민등록등본 발급받고 싶어요",
            "session_id": "string",
            "locale":     "ko-KR"
        }
        """
        payload = {
            "text":       text,
            "session_id": session_id,
            "locale":     locale,
        }

        result = self._post("/classify/service", payload)

        logger.info(
            "AI 응답 수신 (classify): intent=%s serviceId=%s confidence=%s",
            result.get("intent"),
            result.get("serviceId"),
            result.get("confidence"),
        )
        return result
