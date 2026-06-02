from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas import ChatRequest
from app.services.chat import chat_step_guide, chat_text


def sentence_count(answer: str) -> int:
    parts = [p.strip() for p in answer.replace("?", ".").replace("!", ".").split(".") if p.strip()]
    return len(parts) if parts else 1


def print_result(name: str, ok: bool, result: dict | object) -> None:
    print("=" * 80)
    print(name, "PASS" if ok else "FAIL")
    if isinstance(result, dict):
        for key in ["mode", "intent", "serviceId", "confidence", "userType", "entities", "answer", "source", "model_name"]:
            if key in result:
                print(f"{key}:", repr(result.get(key)) if key == "serviceId" else result.get(key))
        print("history_len:", len(result.get("conversation_history", [])))
    else:
        print(result)
    if not ok:
        raise AssertionError(name)


def main() -> None:
    # v6.3: mode 누락 시 classify로 처리해야 한다.
    req = ChatRequest(text="주민등록등본 발급받고 싶어요")
    print_result("TC-AI-MODE-DEFAULT", req.mode == "classify", req)

    # TC-AI-01
    r1 = chat_text("주민등록등본 발급받고 싶어요", session_id="test", conversation_history=[])
    print_result(
        "TC-AI-01",
        r1["serviceId"] == "RESIDENT_REGISTRATION_COPY"
        and r1["confidence"] >= 0.6
        and "등본" in r1["answer"]
        and set(r1["entities"].keys()) >= {"count", "paymentMethod", "purpose", "scope"},
        r1,
    )

    # TC-AI-02
    r2 = chat_text("전입신고 하려고요", session_id="test", conversation_history=[])
    print_result(
        "TC-AI-02",
        r2["serviceId"] == "MOVE_IN_REPORT"
        and r2["confidence"] >= 0.6
        and "전입신고" in r2["answer"],
        r2,
    )

    # TC-AI-03
    r3 = chat_text("어르신 글씨 크게 해주세요", session_id="test", conversation_history=[])
    print_result(
        "TC-AI-03",
        r3["userType"] == "ELDERLY"
        and ("천천히" in r3["answer"] or "크게" in r3["answer"]),
        r3,
    )

    # TC-AI-04
    r4 = chat_text("날씨 알려줘", session_id="test", conversation_history=[])
    print_result(
        "TC-AI-04",
        r4["confidence"] < 0.6
        and r4["serviceId"] == ""
        and ("도움" in r4["answer"] or "무엇" in r4["answer"]),
        r4,
    )

    # TC-AI-07
    r7 = chat_text("주민등록등본 발급받고 싶어요", session_id="test", conversation_history=[])
    print_result(
        "TC-AI-07",
        bool(r7["answer"])
        and sentence_count(r7["answer"]) <= 3
        and len(r7["conversation_history"]) == 2,
        r7,
    )

    # TC-AI-08
    r8 = chat_text(
        "그럼 준비물은 뭐가 필요해요?",
        session_id="test",
        conversation_history=r7["conversation_history"],
    )
    print_result(
        "TC-AI-08",
        "아까" in r8["answer"]
        and "등본" in r8["answer"]
        and len(r8["conversation_history"]) == 4,
        r8,
    )

    # TC-AI-09: 다중 발화 필드 추출
    r9 = chat_text("주민등록등본 1개 현금으로 발급", session_id="test", conversation_history=[])
    print_result(
        "TC-AI-09",
        r9["serviceId"] == "RESIDENT_REGISTRATION_COPY"
        and r9["entities"].get("count") == 1
        and r9["entities"].get("paymentMethod") == "CASH"
        and r9["entities"].get("purpose") is None
        and r9["entities"].get("scope") is None
        and ("1부" in r9["answer"] or "1개" in r9["answer"])
        and "현금" in r9["answer"],
        r9,
    )

    # TC-AI-10: v6.3 step_guide 정상 동작
    step = chat_step_guide(
        step="CERTIFICATE_SELECT_RRN",
        session_id="test-session",
        user_type="ELDERLY",
        service_id=102,
        extra_context={"retryCount": 0, "prevStep": "CERTIFICATE_SELECT_PURPOSE"},
        conversation_history=[],
    )
    print_result(
        "TC-AI-10-STEP_GUIDE-RRN-ELDERLY",
        "주민등록번호" in step["answer"]
        and "천천히" in step["answer"]
        and "intent" not in step
        and "serviceId" not in step
        and "confidence" not in step,
        step,
    )

    # step_guide text 빈 문자열 허용 및 mode 파싱
    step_req = ChatRequest(
        mode="step_guide",
        text="",
        session_id="test-session",
        step="MOVEIN_INPUT_BASIC_INFO",
        userType="NORMAL",
        serviceId=101,
        extra_context={"retryCount": 0, "prevStep": None},
        conversation_history=[],
    )
    print_result("TC-AI-10-REQUEST-SCHEMA", step_req.mode == "step_guide" and step_req.text == "", step_req)

    # 재진입 횟수 반영
    retry = chat_step_guide(
        step="CERTIFICATE_SELECT_RRN",
        session_id="test-session",
        user_type="ELDERLY",
        service_id=102,
        extra_context={"retryCount": 2, "prevStep": "CERTIFICATE_SELECT_PURPOSE"},
        conversation_history=[],
    )
    print_result(
        "TC-AI-10-STEP_GUIDE-RETRY",
        "직원 호출" in retry["answer"],
        retry,
    )

    # v6.2/v6.3 프론트 step key 동기화
    step_cases = [
        ("CERTIFICATE_SELECT_PURPOSE", "증명서 종류"),
        ("CERTIFICATE_SELECT_RRN", "주민등록번호"),
        ("CERTIFICATE_SELECT_SCOPE", "발급형태"),
        ("MOVEIN_INPUT_BASIC_INFO", "본인확인"),
        ("MOVEIN_SELECT_REASON", "전입사유"),
        ("MOVEIN_INPUT_PREV_ADDRESS", "이사 전 주소"),
        ("MOVEIN_INPUT_NEW_ADDRESS", "이사 후 주소"),
        ("MOVEIN_SELECT_HOUSEHOLD", "세대 구성"),
        ("MOVEIN_SELECT_EXTRA_SERVICE", "추가 신청 서비스"),
        ("MOVEIN_CONFIRM", "전입신고 내용"),
    ]
    for step_key, expected_text in step_cases:
        r = chat_step_guide(
            step=step_key,
            session_id="test-session",
            user_type="NORMAL",
            service_id=102 if step_key.startswith("CERTIFICATE") else 101,
            extra_context={"retryCount": 0},
            conversation_history=[],
        )
        print_result(f"TC-AI-STEP-{step_key}", expected_text in r["answer"], r)

    # 확인 단계에서 이전 다중 발화 맥락 반영
    confirm = chat_text(
        "CERTIFICATE_CONFIRM",
        session_id="test",
        conversation_history=r9["conversation_history"],
    )
    print_result(
        "TC-AI-E2E-CONFIRM-WITH-ENTITIES",
        "1부" in confirm["answer"] and "현금" in confirm["answer"],
        confirm,
    )

    # count 범위 초과는 prefilled 되면 안 됨
    invalid = chat_text("주민등록등본 100개 현금으로 발급", session_id="test", conversation_history=[])
    print_result(
        "TC-AI-EDGE-INVALID-COUNT",
        invalid["entities"].get("count") is None
        and invalid["entities"].get("paymentMethod") == "CASH",
        invalid,
    )

    print("=" * 80)
    print("TC-AI-11 is MCP Client fallback test: simulate AI Server 500/timeout in MCP Client integration.")


if __name__ == "__main__":
    main()
