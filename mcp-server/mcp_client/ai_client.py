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

    역할:
    - 사용자 자연어 입력을 AI 서버에 전달
    - AI 서버 응답(JSON)을 받아 반환
    - 네트워크/응답 오류를 일관되게 처리
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout_sec: float | None = None,
    ):
        self.base_url = base_url or config.AI_SERVER_BASE_URL
        self.timeout_sec = timeout_sec or config.AI_SERVER_TIMEOUT_SEC

    def classify_service(
        self,
        text: str,
        session_id: str = "string",
        locale: str = "ko-KR",
    ) -> dict[str, Any]:
        """
        AI 서버 /classify/service 호출

        요청 예시:
        {
            "text": "주민등록등본 발급받고 싶어요",
            "session_id": "string",
            "locale": "ko-KR"
        }
        """
        url = f"{self.base_url}/classify/service"
        payload = {
            "text": text,
            "session_id": session_id,
            "locale": locale,
        }

        logger.info("AI 서버 호출: %s", url)

        try:
            response = requests.post(
                url,
                json=payload,
                headers={"accept": "application/json"},
                timeout=self.timeout_sec,
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

        logger.info(
            "AI 응답 수신: intent=%s serviceId=%s confidence=%s",
            result.get("intent"),
            result.get("serviceId"),
            result.get("confidence"),
        )
        return result