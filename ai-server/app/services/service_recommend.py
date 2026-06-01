from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.catalog import (
    DEFAULT_ENTITIES,
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

MAX_CERTIFICATE_COUNT = 10

KOREAN_NUMBER_MAP = {
    "한": 1,
    "하나": 1,
    "일": 1,
    "두": 2,
    "둘": 2,
    "이": 2,
    "세": 3,
    "셋": 3,
    "삼": 3,
    "네": 4,
    "넷": 4,
    "사": 4,
    "다섯": 5,
    "오": 5,
    "여섯": 6,
    "육": 6,
    "일곱": 7,
    "칠": 7,
    "여덟": 8,
    "팔": 8,
    "아홉": 9,
    "구": 9,
    "열": 10,
    "십": 10,
}


def _clamp_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def _empty_entities() -> dict[str, Any]:
    return dict(DEFAULT_ENTITIES)


def _valid_count(value: int | None) -> int | None:
    if value is None:
        return None
    if 1 <= value <= MAX_CERTIFICATE_COUNT:
        return value
    return None


def _extract_count(text: str) -> int | None:
    normalized = normalize_text(text)

    # 숫자 표현: 1개, 1부, 2장, 3매 등
    match = re.search(r"(\d{1,3})(?:개|부|장|매)", normalized)
    if match:
        return _valid_count(int(match.group(1)))

    # 한글 수 표현: 한 장, 두장, 세 부 등
    for word, value in sorted(KOREAN_NUMBER_MAP.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(re.escape(word) + r"(?:개|부|장|매)", normalized):
            return _valid_count(value)

    return None


def _extract_payment_method(text: str) -> str | None:
    normalized = normalize_text(text)
    if any(keyword in normalized for keyword in ["현금", "돈으로", "지폐", "동전"]):
        return "CASH"
    if any(keyword in normalized for keyword in ["카드", "신용카드", "체크카드"]):
        return "CARD"
    return None


def _extract_purpose(text: str) -> str | None:
    # v6.1에서는 purpose 단계 매핑이 제거됐지만, AI 응답 entities 필드는 유지한다.
    # 사용자가 명시한 경우에만 추출한다.
    candidates = [
        "제출용",
        "은행용",
        "학교 제출용",
        "회사 제출용",
        "관공서 제출용",
        "취업용",
        "대출용",
        "확인용",
    ]
    normalized = normalize_text(text)
    for candidate in candidates:
        if normalize_text(candidate) in normalized:
            return candidate
    # "은행에 제출"처럼 조사와 함께 말한 경우
    if "은행" in normalized and "제출" in normalized:
        return "은행용"
    if "학교" in normalized and "제출" in normalized:
        return "학교 제출용"
    if "회사" in normalized and "제출" in normalized:
        return "회사 제출용"
    return None


def _extract_scope(text: str) -> str | None:
    normalized = normalize_text(text)
    if any(keyword in normalized for keyword in ["주민번호가리고", "주민등록번호가리고", "뒷자리가리고", "뒷자리비공개", "비공개"]):
        return "주민등록번호 뒷자리 비공개"
    if any(keyword in normalized for keyword in ["전체공개", "모두공개", "전부공개", "주민번호공개", "주민등록번호공개"]):
        return "주민등록번호 전체 공개"
    if "일부공개" in normalized:
        return "일부 공개"
    return None


def extract_entities(text: str) -> dict[str, Any]:
    """v6.0/v6.1 다중 발화 필드 추출.

    예: "주민등록등본 1개 현금으로 발급"
    → {count: 1, paymentMethod: "CASH", purpose: None, scope: None}
    """
    return {
        "count": _extract_count(text),
        "paymentMethod": _extract_payment_method(text),
        "purpose": _extract_purpose(text),
        "scope": _extract_scope(text),
    }


def sanitize_entities(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return _empty_entities()

    count = value.get("count")
    try:
        count = int(count) if count is not None else None
    except (TypeError, ValueError):
        count = None
    count = _valid_count(count)

    payment_method = value.get("paymentMethod")
    if payment_method not in {"CASH", "CARD", None}:
        payment_method = None

    purpose = value.get("purpose")
    if purpose is not None:
        purpose = str(purpose).strip() or None

    scope = value.get("scope")
    if scope is not None:
        scope = str(scope).strip() or None

    return {
        "count": count,
        "paymentMethod": payment_method,
        "purpose": purpose,
        "scope": scope,
    }


def has_prefilled_entities(entities: dict[str, Any]) -> bool:
    return any(entities.get(key) is not None for key in ["count", "paymentMethod", "purpose", "scope"])


def _make_response(
    *,
    intent: str,
    service_id: str,
    confidence: float,
    answer: str,
    source: str,
    entities: dict[str, Any] | None = None,
    raw: dict[str, Any] | None = None,
    success: bool = True,
    fallback_used: bool = False,
    model_name: str | None = None,
) -> dict[str, Any]:
    safe_entities = sanitize_entities(entities or _empty_entities())
    raw_obj = raw or {
        "intent": intent,
        "serviceId": service_id,
        "confidence": confidence,
        "entities": safe_entities,
        "answer": answer,
    }
    return {
        "task": "recommend_service",
        "success": success,
        "fallback_used": fallback_used,
        "intent": intent,
        "serviceId": service_id,
        "confidence": _clamp_confidence(confidence),
        "entities": safe_entities,
        "answer": answer.strip(),
        "source": source,
        "raw_text": json.dumps(raw_obj, ensure_ascii=False),
        "model_name": model_name or source,
    }


def _format_entity_summary(entities: dict[str, Any]) -> str:
    parts: list[str] = []
    if entities.get("count") is not None:
        parts.append(f"{entities['count']}부")
    if entities.get("paymentMethod") == "CASH":
        parts.append("현금")
    elif entities.get("paymentMethod") == "CARD":
        parts.append("카드")
    if entities.get("purpose"):
        parts.append(str(entities["purpose"]))
    if entities.get("scope"):
        parts.append(str(entities["scope"]))
    return " ".join(parts)


def _certificate_opening(noun: str, entities: dict[str, Any]) -> str:
    count = entities.get("count")
    payment = entities.get("paymentMethod")
    purpose = entities.get("purpose")
    scope = entities.get("scope")

    count_part = f" {count}부" if count is not None else ""
    payment_part = " 현금으로" if payment == "CASH" else " 카드로" if payment == "CARD" else ""
    extra_parts = []
    if purpose:
        extra_parts.append(str(purpose))
    if scope:
        extra_parts.append(str(scope))
    extra_part = (" " + " ".join(extra_parts)) if extra_parts else ""

    if count_part or payment_part or extra_part:
        object_marker = "을" if not count_part else ""
        return f"{noun}{object_marker}{count_part}{payment_part}{extra_part} 발급해 드릴게요."
    return f"{noun} 발급을 도와드릴게요."


def build_service_answer(service_id: str, entities: dict[str, Any] | None = None) -> str:
    safe_entities = sanitize_entities(entities or _empty_entities())

    if service_id == "RESIDENT_REGISTRATION_COPY":
        return f"{_certificate_opening('등본', safe_entities)} 주민등록번호를 입력해 주세요."
    if service_id == "RESIDENT_REGISTRATION_ABSTRACT":
        return f"{_certificate_opening('초본', safe_entities)} 주민등록번호를 입력해 주세요."
    if service_id == "MOVE_IN_REPORT":
        return "전입신고를 도와드릴게요. 본인확인 및 기본정보를 입력해 주세요."
    if service_id == "MOVE_OUT_REPORT":
        return "전출신고를 도와드릴게요. 이사 관련 정보를 준비해 주세요."
    return "도움이 필요하신가요? 주민등록등본이나 전입신고처럼 필요한 민원 서비스를 말씀해 주세요."


def _rule_based_response(text: str) -> dict[str, Any] | None:
    entities = extract_entities(text)

    step = find_step_prompt(text)
    if step is not None:
        step_key, step_answer = step
        return _make_response(
            intent="general_question",
            service_id="",
            confidence=0.9,
            answer=step_answer,
            source="rule_based",
            entities=entities,
            raw={
                "intent": "general_question",
                "serviceId": "",
                "confidence": 0.9,
                "entities": entities,
                "answer": step_answer,
                "step": step_key,
            },
            model_name="rule_based",
        )

    item = find_service_by_rule(text)
    if item is not None:
        return _make_response(
            intent=item.intent,
            service_id=item.service_id,
            confidence=0.99,
            answer=build_service_answer(item.service_id, entities),
            source="rule_based",
            entities=entities,
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
            entities=entities,
            model_name="rule_based",
        )

    if any(keyword in t for keyword in ["그럼", "아까", "방금", "몇장", "몇매", "준비물", "필요한거", "다음", "계속"]):
        return _make_response(
            intent="general_question",
            service_id="",
            confidence=0.5,
            answer="이전 대화에 이어서 안내드릴게요. 필요한 내용을 말씀해 주세요.",
            source="rule_based",
            entities=entities,
            model_name="rule_based",
        )

    if contains_any_keyword(text, OUT_OF_SCOPE_KEYWORDS):
        return _make_response(
            intent="general_question",
            service_id="",
            confidence=0.2,
            answer="도움이 필요하신가요? 주민등록등본이나 전입신고처럼 필요한 민원 서비스를 말씀해 주세요.",
            source="rule_based",
            entities=entities,
            model_name="rule_based",
        )

    if contains_any_keyword(text, UNSUPPORTED_SERVICE_KEYWORDS):
        return _make_response(
            intent="general_question",
            service_id="",
            confidence=0.55,
            answer="현재 이 키오스크에서는 해당 서비스를 바로 진행할 수 없습니다. 주민등록등본이나 전입신고 같은 지원 서비스를 말씀해 주세요.",
            source="rule_based",
            entities=entities,
            model_name="rule_based",
        )

    return None


def _ensure_model_loaded() -> None:
    # FastAPI 실행 시에는 startup에서 load()가 호출된다. 단독 테스트에서는 호출되지 않을 수 있어 보강한다.
    try:
        load = getattr(model_instance, "load", None)
        if callable(load):
            load()
    except Exception as exc:
        logger.debug("model load skipped in service_recommend: %s", exc)


def recommend_service(text: str) -> dict[str, Any]:
    rule_result = _rule_based_response(text)
    if rule_result is not None:
        if settings.DEBUG_LOGS:
            logger.debug("service rule matched: %s", rule_result["serviceId"])
        return rule_result

    try:
        _ensure_model_loaded()
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

        entities = sanitize_entities(parsed.get("entities"))

        answer = parsed.get("answer")
        if not isinstance(answer, str) or not answer.strip():
            answer = build_service_answer(service_id, entities)

        return {
            "task": "recommend_service",
            "success": True,
            "fallback_used": False,
            "intent": intent,
            "serviceId": service_id,
            "confidence": confidence,
            "entities": entities,
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
