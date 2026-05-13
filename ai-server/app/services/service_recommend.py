from __future__ import annotations

import json
import logging
from typing import Any

from app.catalog import find_service_by_rule
from app.config import settings
from app.exceptions import ModelResponseError
from app.llm_schemas import SERVICE_RECOMMEND_JSON_SCHEMA
from app.model import model_instance
from app.prompts import SERVICE_RECOMMEND_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

ALLOWED_INTENTS = {
    "issue_document",
    "submit_application",
    "pay_or_check",
    "welfare_service",
    "general_question",
    "unknown",
}

ALLOWED_SERVICE_IDS = {
    "RESIDENT_REGISTRATION_COPY",
    "FAMILY_CERTIFICATE",
    "MOVE_IN_REPORT",
    "HEALTH_INSURANCE",
    "MARRIAGE_CERTIFICATE",
    "TAX_CERTIFICATE",
    "UNKNOWN",
}


def _clamp_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def _rule_based_response(text: str) -> dict[str, Any] | None:
    item = find_service_by_rule(text)
    if item is None:
        return None

    raw = {
        "intent": item.intent,
        "serviceId": item.service_id,
        "confidence": 0.99,
        "answer": item.answer,
    }
    return {
        "task": "recommend_service",
        "success": True,
        "fallback_used": False,
        "intent": item.intent,
        "serviceId": item.service_id,
        "confidence": 0.99,
        "answer": item.answer,
        "source": "rule_based",
        "raw_text": json.dumps(raw, ensure_ascii=False),
        "model_name": "rule_based",
    }


def recommend_service(text: str) -> dict[str, Any]:
    rule_result = _rule_based_response(text)
    if rule_result is not None:
        if settings.DEBUG_LOGS:
            logger.debug("service rule matched: %s", rule_result["serviceId"])
        return rule_result

    try:
        result = model_instance.generate_json(
            SERVICE_RECOMMEND_SYSTEM_PROMPT,
            text,
            SERVICE_RECOMMEND_JSON_SCHEMA,
        )
        parsed = result.parsed

        intent = parsed.get("intent", "unknown")
        if intent not in ALLOWED_INTENTS:
            intent = "unknown"

        service_id = parsed.get("serviceId", "UNKNOWN")
        if service_id not in ALLOWED_SERVICE_IDS:
            service_id = "UNKNOWN"

        confidence = _clamp_confidence(parsed.get("confidence", 0.0))
        if confidence < settings.SERVICE_CONFIDENCE_THRESHOLD:
            intent = "unknown"
            service_id = "UNKNOWN"

        answer = parsed.get("answer")
        if not isinstance(answer, str) or not answer.strip():
            answer = "적절한 서비스를 찾지 못했습니다. 다시 말씀해 주세요."

        return {
            "task": "recommend_service",
            "success": True,
            "fallback_used": False,
            "intent": intent,
            "serviceId": service_id,
            "confidence": confidence,
            "answer": answer.strip(),
            "source": "llm",
            "raw_text": result.raw_text,
            "model_name": result.model_name,
        }

    except ModelResponseError as exc:
        logger.warning("service recommendation fallback: %s", exc)
        return {
            "task": "recommend_service",
            "success": False,
            "fallback_used": True,
            "intent": "unknown",
            "serviceId": "UNKNOWN",
            "confidence": 0.0,
            "answer": "서비스를 정확히 찾지 못했습니다. 다시 말씀해 주세요.",
            "source": "fallback",
            "raw_text": "",
            "model_name": model_instance.model_id,
        }
