from __future__ import annotations

from typing import Any

from app.config import settings
from app.services.service_recommend import recommend_service
from app.services.user_type import classify_user_type


def analyze_text(text: str) -> dict[str, Any]:
    user_result = classify_user_type(text)
    service_result = recommend_service(text)

    service_confidence = float(service_result.get("confidence", 0.0))
    user_confidence = float(user_result.get("confidence", 0.0))

    needs_confirmation = (
        service_result.get("serviceId") == "UNKNOWN"
        or service_confidence < settings.AUTO_CONFIRM_CONFIDENCE_THRESHOLD
    )

    fallback_used = bool(user_result.get("fallback_used")) or bool(service_result.get("fallback_used"))
    success = bool(user_result.get("success")) and bool(service_result.get("success"))

    user_source = user_result.get("source", "fallback")
    service_source = service_result.get("source", "fallback")
    source = user_source if user_source == service_source else "mixed"

    model_names = sorted(
        {
            str(user_result.get("model_name", "unknown")),
            str(service_result.get("model_name", "unknown")),
        }
    )

    return {
        "task": "analyze",
        "success": success,
        "fallback_used": fallback_used,
        "userType": user_result.get("userType", "UNKNOWN"),
        "userTypeConfidence": user_confidence,
        "userTypeReason": user_result.get("reason", ""),
        "intent": service_result.get("intent", "unknown"),
        "serviceId": service_result.get("serviceId", "UNKNOWN"),
        "serviceConfidence": service_confidence,
        "answer": service_result.get("answer", "다시 말씀해 주세요."),
        "needsConfirmation": needs_confirmation,
        "source": source,
        "model_name": ",".join(model_names),
    }
