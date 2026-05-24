from __future__ import annotations

import json
import logging
from typing import Any

from app.catalog import (
    find_service_by_rule,
    is_out_of_scope_question,
    is_unsupported_service_request,
    is_user_type_hint_only,
)
from app.config import settings
from app.exceptions import ModelResponseError
from app.llm_schemas import SERVICE_RECOMMEND_JSON_SCHEMA
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

# 테스트 가이드 기준 지원 서비스만 허용한다.
# 미지원/서비스 외 발화는 serviceId=None 으로 반환한다.
ALLOWED_SERVICE_IDS = {
    "RESIDENT_REGISTRATION_COPY",
    "RESIDENT_REGISTRATION_ABSTRACT",
    "MOVE_IN_REPORT",
    "MOVE_OUT_REPORT",
}

UNSUPPORTED_SERVICE_ANSWER = "죄송합니다. 현재 제공되지 않는 서비스입니다. 다른 서비스를 이용해 주세요."
OUT_OF_SCOPE_ANSWER = "민원 서비스 요청으로 확인되지 않았습니다. 필요한 민원 서비스를 말씀해 주세요."
USER_TYPE_HINT_ANSWER = "어르신 또는 접근성 설정 요청으로 확인했습니다. 원하시는 민원 서비스도 함께 말씀해 주세요."



def _fallback_model_name() -> str:
    try:
        from app.model import model_instance
        return model_instance.model_id
    except Exception:
        return "unknown"

def _clamp_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def _build_response(
    *,
    intent: str,
    service_id: str | None,
    confidence: float,
    answer: str,
    source: str,
    fallback_used: bool = False,
    success: bool = True,
    raw: dict[str, Any] | None = None,
    model_name: str | None = None,
) -> dict[str, Any]:
    raw_payload = raw or {
        "intent": intent,
        "serviceId": service_id,
        "confidence": confidence,
        "answer": answer,
    }
    return {
        "task": "recommend_service",
        "success": success,
        "fallback_used": fallback_used,
        "intent": intent,
        "serviceId": service_id,
        "confidence": _clamp_confidence(confidence),
        "answer": answer,
        "source": source,
        "raw_text": json.dumps(raw_payload, ensure_ascii=False),
        "model_name": model_name or source,
    }


def _rule_based_response(text: str) -> dict[str, Any] | None:
    item = find_service_by_rule(text)
    if item is None:
        return None

    return _build_response(
        intent=item.intent,
        service_id=item.service_id,
        confidence=0.99,
        answer=item.answer,
        source="rule_based",
        model_name="rule_based",
    )


def _guardrail_response(text: str) -> dict[str, Any] | None:
    """테스트 가이드 핵심 케이스를 LLM 호출 없이 안정적으로 처리한다."""
    if is_unsupported_service_request(text):
        return _build_response(
            intent="issue_document",
            service_id=None,
            confidence=0.90,
            answer=UNSUPPORTED_SERVICE_ANSWER,
            source="rule_based",
            model_name="rule_based",
        )

    if is_out_of_scope_question(text):
        return _build_response(
            intent="general_question",
            service_id=None,
            confidence=0.20,
            answer=OUT_OF_SCOPE_ANSWER,
            source="rule_based",
            model_name="rule_based",
        )

    if is_user_type_hint_only(text):
        return _build_response(
            intent="general_question",
            service_id=None,
            confidence=0.70,
            answer=USER_TYPE_HINT_ANSWER,
            source="rule_based",
            model_name="rule_based",
        )

    return None


def recommend_service(text: str) -> dict[str, Any]:
    rule_result = _rule_based_response(text)
    if rule_result is not None:
        if settings.DEBUG_LOGS:
            logger.debug("service rule matched: %s", rule_result["serviceId"])
        return rule_result

    guardrail_result = _guardrail_response(text)
    if guardrail_result is not None:
        if settings.DEBUG_LOGS:
            logger.debug("service guardrail matched: serviceId=%s", guardrail_result["serviceId"])
        return guardrail_result

    try:
        from app.model import model_instance

        result = model_instance.generate_json(
            SERVICE_RECOMMEND_SYSTEM_PROMPT,
            text,
            SERVICE_RECOMMEND_JSON_SCHEMA,
        )
        parsed = result.parsed

        intent = parsed.get("intent", "unknown")
        if intent not in ALLOWED_INTENTS:
            intent = "unknown"

        service_id = parsed.get("serviceId")
        if service_id not in ALLOWED_SERVICE_IDS:
            service_id = None

        confidence = _clamp_confidence(parsed.get("confidence", 0.0))
        if confidence < settings.SERVICE_CONFIDENCE_THRESHOLD:
            intent = "unknown" if intent != "general_question" else intent
            service_id = None

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
        return _build_response(
            intent="unknown",
            service_id=None,
            confidence=0.0,
            answer="서비스를 정확히 찾지 못했습니다. 다시 말씀해 주세요.",
            source="fallback",
            fallback_used=True,
            success=False,
            model_name=_fallback_model_name(),
        )
