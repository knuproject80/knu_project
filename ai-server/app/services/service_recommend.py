from __future__ import annotations

import json
import logging
from typing import Any

from app.catalog import (
    OUT_OF_SCOPE_KEYWORDS,
    UNSUPPORTED_SERVICE_KEYWORDS,
    contains_any_keyword,
    find_service_by_rule,
    find_step_prompt,
    normalize_text,
)
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
    "RESIDENT_REGISTRATION_ABSTRACT",
    "MOVE_IN_REPORT",
    "MOVE_OUT_REPORT",
    "",
}


def _clamp_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def _make_response(
    *,
    intent: str,
    service_id: str,
    confidence: float,
    answer: str,
    source: str,
    raw: dict[str, Any] | None = None,
    success: bool = True,
    fallback_used: bool = False,
    model_name: str | None = None,
) -> dict[str, Any]:
    raw_obj = raw or {
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
        "answer": answer.strip(),
        "source": source,
        "raw_text": json.dumps(raw_obj, ensure_ascii=False),
        "model_name": model_name or source,
    }


def _rule_based_response(text: str) -> dict[str, Any] | None:
    step = find_step_prompt(text)
    if step is not None:
        step_key, step_answer = step
        return _make_response(
            intent="general_question",
            service_id="",
            confidence=0.9,
            answer=step_answer,
            source="rule_based",
            raw={"intent": "general_question", "serviceId": "", "confidence": 0.9, "answer": step_answer, "step": step_key},
            model_name="rule_based",
        )

    item = find_service_by_rule(text)
    if item is not None:
        return _make_response(
            intent=item.intent,
            service_id=item.service_id,
            confidence=0.99,
            answer=item.answer,
            source="rule_based",
            model_name="rule_based",
        )


    t = normalize_text(text)
    if any(keyword in t for keyword in ["어르신", "노인", "고령", "천천히", "큰글씨", "글씨크게", "휠체어", "낮은화면"]):
        return _make_response(
            intent="general_question",
            service_id="",
            confidence=0.7,
            answer="접근성 설정 요청으로 확인했습니다. 원하시는 민원 서비스도 함께 말씀해 주세요.",
            source="rule_based",
            model_name="rule_based",
        )

    if any(keyword in t for keyword in ["그럼", "아까", "방금", "몇장", "몇매", "준비물", "필요한거", "다음", "계속"]):
        return _make_response(
            intent="general_question",
            service_id="",
            confidence=0.5,
            answer="이전 대화에 이어서 안내드릴게요. 필요한 내용을 말씀해 주세요.",
            source="rule_based",
            model_name="rule_based",
        )

    if contains_any_keyword(text, OUT_OF_SCOPE_KEYWORDS):
        return _make_response(
            intent="general_question",
            service_id="",
            confidence=0.2,
            answer="도움이 필요하신가요? 주민등록등본이나 전입신고처럼 필요한 민원 서비스를 말씀해 주세요.",
            source="rule_based",
            model_name="rule_based",
        )

    if contains_any_keyword(text, UNSUPPORTED_SERVICE_KEYWORDS):
        return _make_response(
            intent="general_question",
            service_id="",
            confidence=0.55,
            answer="현재 이 키오스크에서는 해당 서비스를 바로 진행할 수 없습니다. 주민등록등본이나 전입신고 같은 지원 서비스를 말씀해 주세요.",
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

        service_id = parsed.get("serviceId", "")
        if service_id not in ALLOWED_SERVICE_IDS:
            service_id = ""

        confidence = _clamp_confidence(parsed.get("confidence", 0.0))
        if confidence < settings.SERVICE_CONFIDENCE_THRESHOLD:
            intent = "general_question"
            service_id = ""

        answer = parsed.get("answer")
        if not isinstance(answer, str) or not answer.strip():
            answer = "무엇을 도와드릴까요? 필요한 민원 서비스를 말씀해 주세요."

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
        return _make_response(
            intent="unknown",
            service_id="",
            confidence=0.0,
            answer="무엇을 도와드릴까요? 필요한 민원 서비스를 다시 말씀해 주세요.",
            source="fallback",
            model_name=model_instance.model_id,
            success=False,
            fallback_used=True,
        )
