from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from openai import APIError, APITimeoutError, OpenAI, RateLimitError

from app.config import settings
from app.exceptions import ModelNotReadyError, ModelResponseError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelJsonResult:
    parsed: dict[str, Any]
    raw_text: str
    model_name: str


class OpenAIJsonModel:
    def __init__(self) -> None:
        self.model_id = settings.OPENAI_MODEL
        self.client: OpenAI | None = None

    def load(self) -> None:
        if self.client is not None:
            return
        self.client = OpenAI(
            timeout=settings.OPENAI_TIMEOUT,
            max_retries=settings.OPENAI_MAX_RETRIES,
        )
        logger.info("OpenAI client ready: %s", self.model_id)

    def _ensure_loaded(self) -> OpenAI:
        if self.client is None:
            raise ModelNotReadyError("OpenAI client is not initialized.")
        return self.client

    def _extract_text(self, response: Any) -> str:
        output_text = getattr(response, "output_text", None)
        if output_text:
            return str(output_text).strip()

        chunks: list[str] = []
        for output_item in getattr(response, "output", []) or []:
            for content_item in getattr(output_item, "content", []) or []:
                text = getattr(content_item, "text", None)
                if text:
                    chunks.append(str(text))
        return "".join(chunks).strip()

    def _extract_json(self, text: str) -> dict[str, Any]:
        text = text.strip()
        if not text:
            raise ModelResponseError("Empty model response.")

        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
            raise ModelResponseError("Model response JSON is not an object.")
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ModelResponseError("No JSON object found in model response.")

        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise ModelResponseError(f"Invalid JSON format: {exc}") from exc

        if not isinstance(parsed, dict):
            raise ModelResponseError("Model response JSON is not an object.")
        return parsed

    def generate_json(
        self,
        system_prompt: str,
        user_text: str,
        json_schema: dict[str, Any] | None = None,
    ) -> ModelJsonResult:
        client = self._ensure_loaded()

        payload: dict[str, Any] = {
            "model": self.model_id,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text.strip()},
            ],
            "max_output_tokens": settings.OPENAI_MAX_OUTPUT_TOKENS,
        }

        if settings.OPENAI_USE_STRUCTURED_OUTPUT and json_schema is not None:
            payload["text"] = {"format": json_schema}

        if self.model_id.startswith(("gpt-5", "o")):
            payload["reasoning"] = {"effort": settings.OPENAI_REASONING_EFFORT}

        try:
            response = client.responses.create(**payload)
        except (APIError, APITimeoutError, RateLimitError) as exc:
            raise ModelResponseError(f"OpenAI API call failed: {exc}") from exc
        except Exception as exc:
            raise ModelResponseError(f"Unexpected model error: {exc}") from exc

        if settings.DEBUG_LOGS:
            logger.debug("response.status=%s", getattr(response, "status", None))
            logger.debug("response.output_text=%r", getattr(response, "output_text", ""))

        if getattr(response, "error", None):
            raise ModelResponseError(f"OpenAI response error: {response.error}")

        incomplete_details = getattr(response, "incomplete_details", None)
        if incomplete_details is not None:
            raise ModelResponseError(f"OpenAI response incomplete: {incomplete_details}")

        raw_text = self._extract_text(response)
        parsed = self._extract_json(raw_text)
        return ModelJsonResult(parsed=parsed, raw_text=raw_text, model_name=self.model_id)


model_instance = OpenAIJsonModel()
