from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.catalog import CONTEXT_PROMPTS, STEP_PROMPTS, find_step_prompt, normalize_text
from app.exceptions import ModelResponseError
from app.llm_schemas import CHAT_JSON_SCHEMA
from app.model import model_instance
from app.prompts import CHAT_ANSWER_SYSTEM_PROMPT
from app.schemas import ConversationMessage
from app.services.service_recommend import recommend_service
from app.services.user_type import classify_user_type

logger = logging.getLogger(__name__)

SERVICE_NAMES = {
    "RESIDENT_REGISTRATION_COPY": "주민등록등본",
    "RESIDENT_REGISTRATION_ABSTRACT": "주민등록초본",
    "MOVE_IN_REPORT": "전입신고",
    "MOVE_OUT_REPORT": "전출신고",
    "": "",
}


def _history_to_dicts(history: list[ConversationMessage] | list[dict[str, str]] | None) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for item in history or []:
        if isinstance(item, ConversationMessage):
            role = item.role
            content = item.content
        elif isinstance(item, dict):
            role = str(item.get("role", "user"))
            content = str(item.get("content", ""))
        else:
            continue
        if role not in {"user", "assistant", "system"}:
            role = "user"
        content = content.strip()
        if content:
            items.append({"role": role, "content": content[:2000]})
    return items


def _infer_prior_service(history: list[dict[str, str]]) -> str:
    joined = normalize_text(" ".join(item["content"] for item in history[-8:]))
    if any(key in joined for key in ["주민등록등본", "등본", "residentregistrationcopy"]):
        return "RESIDENT_REGISTRATION_COPY"
    if any(key in joined for key in ["주민등록초본", "초본", "residentregistrationabstract"]):
        return "RESIDENT_REGISTRATION_ABSTRACT"
    if any(key in joined for key in ["전입신고", "moveinreport"]):
        return "MOVE_IN_REPORT"
    if any(key in joined for key in ["전출신고", "moveoutreport"]):
        return "MOVE_OUT_REPORT"
    return ""


def _is_context_followup(text: str) -> bool:
    t = normalize_text(text)
    return any(key in t for key in ["그럼", "아까", "방금", "몇장", "몇매", "준비물", "필요한거", "다음", "계속"])


def _limit_sentences(answer: str, max_sentences: int = 3) -> str:
    answer = re.sub(r"\s+", " ", answer).strip()
    if not answer:
        return "무엇을 도와드릴까요? 필요한 민원 서비스를 말씀해 주세요."

    # 문장 구분자가 부족하면 그대로 반환한다.
    parts = re.split(r"(?<=[.!?。]|[요다니다세요])\s+", answer)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) <= max_sentences:
        return answer
    return " ".join(parts[:max_sentences]).strip()


def _apply_user_type_style(answer: str, user_type: str) -> str:
    if user_type == "ELDERLY":
        if "천천히" not in answer:
            answer = "천천히 도와드리겠습니다. " + answer
        if "크게" not in answer and "글씨" in normalize_text(answer):
            answer += " 글씨를 크게 보실 수 있게 안내하겠습니다."
    elif user_type == "WHEELCHAIR":
        if "동작" not in answer and "이동" not in answer:
            answer = "이동을 줄일 수 있게 안내하겠습니다. " + answer
    return _limit_sentences(answer)


def _service_answer(service_id: str, user_type: str, *, from_history: bool = False) -> str:
    if service_id == "RESIDENT_REGISTRATION_COPY":
        prefix = "아까 말씀하신 등본은" if from_history else "주민등록등본 발급을"
        answer = f"{prefix} 도와드릴게요. 신분증을 준비해 주세요."
    elif service_id == "RESIDENT_REGISTRATION_ABSTRACT":
        prefix = "아까 말씀하신 초본은" if from_history else "주민등록초본 발급을"
        answer = f"{prefix} 도와드릴게요. 신분증을 준비해 주세요."
    elif service_id == "MOVE_IN_REPORT":
        prefix = "아까 말씀하신 전입신고는" if from_history else "전입신고를"
        answer = f"{prefix} 도와드릴게요. 이사 오신 새 주소를 준비해 주세요."
    elif service_id == "MOVE_OUT_REPORT":
        prefix = "아까 말씀하신 전출신고는" if from_history else "전출신고를"
        answer = f"{prefix} 도와드릴게요. 이사 가실 주소를 준비해 주세요."
    else:
        answer = "도움이 필요하신가요? 주민등록등본이나 전입신고처럼 필요한 민원 서비스를 말씀해 주세요."
    return _apply_user_type_style(answer, user_type)


def _step_answer(step_key: str, guide_text: str, user_type: str) -> str:
    answer = guide_text
    if step_key.endswith("COMPLETE"):
        answer = guide_text
    elif "버튼" not in answer and step_key not in {"CERTIFICATE_PRINTING"}:
        answer = f"{guide_text} 선택이 끝나면 다음 버튼을 눌러 주세요."
    return _apply_user_type_style(answer, user_type)


def _context_answer(context_key: str, user_type: str) -> str:
    answer = CONTEXT_PROMPTS.get(context_key, "무엇을 도와드릴까요? 필요한 민원 서비스를 말씀해 주세요.")
    return _apply_user_type_style(answer, user_type)


def _accessibility_answer(user_type: str) -> str:
    if user_type == "ELDERLY":
        return "천천히 진행하실 수 있게 글씨를 크게 안내하겠습니다. 원하시는 민원 서비스를 말씀해 주세요."
    if user_type == "WHEELCHAIR":
        return "이동을 줄일 수 있게 화면을 편하게 안내하겠습니다. 원하시는 민원 서비스를 말씀해 주세요."
    return "편하게 이용하실 수 있도록 안내하겠습니다. 원하시는 민원 서비스를 말씀해 주세요."


def _fallback_llm_answer(prompt_payload: dict[str, Any], fallback: str) -> tuple[str, bool, str, str]:
    """LLM 답변 생성 시도. 실패하면 fallback을 그대로 사용한다.

    테스트 가이드 핵심 케이스는 deterministic fallback만으로도 통과하도록 구성했다.
    운영 환경에서 OPENAI_API_KEY가 설정되어 있으면 모호한 발화에 대해 LLM 답변을 보강한다.
    """
    try:
        result = model_instance.generate_json(
            CHAT_ANSWER_SYSTEM_PROMPT,
            json.dumps(prompt_payload, ensure_ascii=False),
            CHAT_JSON_SCHEMA,
        )
        answer = str(result.parsed.get("answer", "")).strip()
        if answer:
            return _limit_sentences(answer), False, result.raw_text, result.model_name
    except (ModelResponseError, Exception) as exc:
        logger.warning("chat answer LLM fallback: %s", exc)
    return fallback, True, json.dumps({"answer": fallback}, ensure_ascii=False), "rule_based_fallback"


def chat_text(
    text: str,
    *,
    session_id: str | None = None,
    locale: str = "ko-KR",
    conversation_history: list[ConversationMessage] | list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    history = _history_to_dicts(conversation_history)
    user_result = classify_user_type(text)
    service_result = recommend_service(text)

    user_type = str(user_result.get("userType") or "NORMAL")
    if user_type == "UNKNOWN":
        user_type = "NORMAL"

    intent = str(service_result.get("intent") or "unknown")
    service_id = str(service_result.get("serviceId") or "")
    confidence = float(service_result.get("confidence") or 0.0)
    entities: dict[str, Any] = {
        "session_id": session_id or "string",
        "locale": locale,
        "userType": user_type,
    }

    step_match = find_step_prompt(text)
    from_history = False

    if step_match is not None:
        step_key, step_guide = step_match
        answer = _step_answer(step_key, step_guide, user_type)
        entities["step"] = step_key
        # STEP_CHANGE 안내는 특정 서비스 분류가 아니므로 serviceId는 빈 문자열로 둔다.
        intent = "general_question"
        service_id = ""
        confidence = max(confidence, 0.9)
        source = "rule_based"
        raw_text = json.dumps({"answer": answer, "step": step_key}, ensure_ascii=False)
        model_name = "rule_based"
        fallback_used = False
    elif text.strip() in CONTEXT_PROMPTS or normalize_text(text) in {normalize_text(k) for k in CONTEXT_PROMPTS}:
        # MCP Client가 SESSION_START 같은 context를 /chat에 넘긴 경우도 처리한다.
        key = next((k for k in CONTEXT_PROMPTS if normalize_text(k) == normalize_text(text)), text.strip())
        answer = _context_answer(key, user_type)
        entities["context"] = key
        intent = "general_question"
        service_id = ""
        confidence = max(confidence, 0.9)
        source = "rule_based"
        raw_text = json.dumps({"answer": answer, "context": key}, ensure_ascii=False)
        model_name = "rule_based"
        fallback_used = False
    elif service_id:
        answer = _service_answer(service_id, user_type)
        source = service_result.get("source", "rule_based")
        raw_text = service_result.get("raw_text", "")
        model_name = service_result.get("model_name", "")
        fallback_used = bool(service_result.get("fallback_used"))
    else:
        prior_service_id = _infer_prior_service(history)
        if prior_service_id and _is_context_followup(text):
            service_id = prior_service_id
            service_name = SERVICE_NAMES.get(service_id, "")
            entities["resolved_from_history"] = True
            entities["serviceName"] = service_name
            confidence = max(confidence, 0.75)
            intent = "issue_document" if "REGISTRATION" in service_id else "submit_application"
            answer = _service_answer(service_id, user_type, from_history=True)
            from_history = True
            source = "rule_based"
            raw_text = json.dumps({"answer": answer, "resolved_from_history": service_id}, ensure_ascii=False)
            model_name = "rule_based"
            fallback_used = False
        elif user_type in {"ELDERLY", "WHEELCHAIR"}:
            answer = _accessibility_answer(user_type)
            source = "rule_based"
            raw_text = json.dumps({"answer": answer, "userType": user_type}, ensure_ascii=False)
            model_name = "rule_based"
            fallback_used = False
            confidence = max(confidence, 0.7)
            intent = "general_question"
        else:
            fallback = "도움이 필요하신가요? 주민등록등본이나 전입신고처럼 필요한 민원 서비스를 말씀해 주세요."
            payload = {
                "text": text,
                "conversation_history": history[-8:],
                "userType": user_type,
                "intent": intent,
                "serviceId": service_id,
                "confidence": confidence,
            }
            answer, fallback_used, raw_text, model_name = _fallback_llm_answer(payload, fallback)
            source = "fallback" if fallback_used else "llm"
            if confidence >= 0.6 and not service_id:
                confidence = 0.55

    answer = _limit_sentences(answer)
    updated_history = history + [
        {"role": "user", "content": text.strip()},
        {"role": "assistant", "content": answer},
    ]

    if from_history and "아까" not in answer:
        answer = "아까 말씀하신 내용에 이어서 안내드릴게요. " + answer
        updated_history[-1]["content"] = answer

    return {
        "task": "chat",
        "success": True,
        "fallback_used": fallback_used,
        "intent": intent,
        "serviceId": service_id,
        "confidence": confidence,
        "entities": entities,
        "answer": answer,
        "conversation_history": updated_history,
        "userType": user_type,
        "userTypeConfidence": float(user_result.get("confidence") or 0.0),
        "source": source,
        "raw_text": raw_text,
        "model_name": model_name,
    }
