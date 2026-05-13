from __future__ import annotations

import json
import logging
from typing import Any

from app.catalog import normalize_text
from app.config import settings
from app.exceptions import ModelResponseError
from app.llm_schemas import USER_TYPE_JSON_SCHEMA
from app.model import model_instance
from app.prompts import USER_TYPE_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

ALLOWED_USER_TYPES = {
    "ELDERLY",
    "WHEELCHAIR",
    "VISUAL_IMPAIRMENT",
    "HEARING_IMPAIRMENT",
    "NORMAL",
    "UNKNOWN",
}


def _clamp_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def _make_rule_response(user_type: str, confidence: float, reason: str) -> dict[str, Any]:
    raw = {"userType": user_type, "confidence": confidence, "reason": reason}
    return {
        "task": "classify_user_type",
        "success": True,
        "fallback_used": False,
        "userType": user_type,
        "confidence": confidence,
        "reason": reason,
        "source": "rule_based",
        "raw_text": json.dumps(raw, ensure_ascii=False),
        "model_name": "rule_based",
    }


def _rule_based_user_type(text: str) -> dict[str, Any] | None:
    t = normalize_text(text)

    if any(keyword in t for keyword in ["휠체어", "화면낮", "낮은화면", "높이가높", "높아요"]):
        return _make_rule_response("WHEELCHAIR", 0.98, "휠체어 또는 화면 높이 관련 표현이 포함되었습니다.")

    if any(keyword in t for keyword in ["글씨가잘안보", "잘안보", "눈이안좋", "시각", "저시력", "글씨크", "화면확대"]):
        return _make_rule_response("VISUAL_IMPAIRMENT", 0.95, "시각 불편 또는 글씨 확대 요청이 포함되었습니다.")

    if any(keyword in t for keyword in ["잘안들", "소리가안들", "귀가안", "청각", "음성안내안들"]):
        return _make_rule_response("HEARING_IMPAIRMENT", 0.95, "청각 불편 또는 소리 관련 표현이 포함되었습니다.")

    if any(keyword in t for keyword in ["어르신", "노인", "고령", "천천히", "큰버튼"]):
        return _make_rule_response("ELDERLY", 0.90, "고령 사용자 또는 천천히 진행 요청이 포함되었습니다.")

    return None


def classify_user_type(text: str) -> dict[str, Any]:
    rule_result = _rule_based_user_type(text)
    if rule_result is not None:
        if settings.DEBUG_LOGS:
            logger.debug("user type rule matched: %s", rule_result["userType"])
        return rule_result

    try:
        result = model_instance.generate_json(
            USER_TYPE_SYSTEM_PROMPT,
            text,
            USER_TYPE_JSON_SCHEMA,
        )
        parsed = result.parsed

        user_type = parsed.get("userType", "UNKNOWN")
        if user_type not in ALLOWED_USER_TYPES:
            user_type = "UNKNOWN"

        confidence = _clamp_confidence(parsed.get("confidence", 0.0))
        if confidence < settings.USER_TYPE_CONFIDENCE_THRESHOLD:
            user_type = "UNKNOWN"

        reason = parsed.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            reason = "분류 근거를 찾지 못했습니다."

        return {
            "task": "classify_user_type",
            "success": True,
            "fallback_used": False,
            "userType": user_type,
            "confidence": confidence,
            "reason": reason.strip(),
            "source": "llm",
            "raw_text": result.raw_text,
            "model_name": result.model_name,
        }

    except ModelResponseError as exc:
        logger.warning("user type fallback: %s", exc)
        return {
            "task": "classify_user_type",
            "success": False,
            "fallback_used": True,
            "userType": "UNKNOWN",
            "confidence": 0.0,
            "reason": "사용자 유형을 분류하지 못했습니다.",
            "source": "fallback",
            "raw_text": "",
            "model_name": model_instance.model_id,
        }
