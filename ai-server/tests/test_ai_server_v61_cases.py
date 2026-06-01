from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.chat import chat_text


def sentence_count(answer: str) -> int:
    parts = [p.strip() for p in answer.replace("?", ".").replace("!", ".").split(".") if p.strip()]
    return len(parts) if parts else 1


def assert_case(name: str, condition: bool, result: dict) -> None:
    print("=" * 80)
    print(name, "PASS" if condition else "FAIL")
    print("intent:", result.get("intent"))
    print("serviceId:", repr(result.get("serviceId")))
    print("confidence:", result.get("confidence"))
    print("userType:", result.get("userType"))
    print("entities:", result.get("entities"))
    print("answer:", result.get("answer"))
    print("history_len:", len(result.get("conversation_history", [])))
    if not condition:
        raise AssertionError(name)


def main() -> None:
    # TC-AI-01
    r1 = chat_text("주민등록등본 발급받고 싶어요", session_id="test", conversation_history=[])
    assert_case(
        "TC-AI-01",
        r1["serviceId"] == "RESIDENT_REGISTRATION_COPY"
        and r1["confidence"] >= 0.6
        and "등본" in r1["answer"]
        and set(r1["entities"].keys()) >= {"count", "paymentMethod", "purpose", "scope"},
        r1,
    )

    # TC-AI-02
    r2 = chat_text("전입신고 하려고요", session_id="test", conversation_history=[])
    assert_case(
        "TC-AI-02",
        r2["serviceId"] == "MOVE_IN_REPORT"
        and r2["confidence"] >= 0.6
        and "전입신고" in r2["answer"],
        r2,
    )

    # TC-AI-03
    r3 = chat_text("어르신 글씨 크게 해주세요", session_id="test", conversation_history=[])
    assert_case(
        "TC-AI-03",
        r3["userType"] == "ELDERLY"
        and ("천천히" in r3["answer"] or "크게" in r3["answer"]),
        r3,
    )

    # TC-AI-04
    r4 = chat_text("날씨 알려줘", session_id="test", conversation_history=[])
    assert_case(
        "TC-AI-04",
        r4["confidence"] < 0.6
        and r4["serviceId"] == ""
        and ("도움" in r4["answer"] or "무엇" in r4["answer"]),
        r4,
    )

    # TC-AI-07
    r7 = chat_text("주민등록등본 발급받고 싶어요", session_id="test", conversation_history=[])
    assert_case(
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
    assert_case(
        "TC-AI-08",
        "아까" in r8["answer"]
        and "등본" in r8["answer"]
        and len(r8["conversation_history"]) == 4,
        r8,
    )

    # TC-AI-09: 다중 발화 필드 추출
    r9 = chat_text("주민등록등본 1개 현금으로 발급", session_id="test", conversation_history=[])
    assert_case(
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

    # v6.1: RRN 단계 추가
    rrn = chat_text("CERTIFICATE_SELECT_RRN", session_id="test", conversation_history=[])
    assert_case(
        "TC-AI-STEP-RRN",
        rrn["serviceId"] == ""
        and "주민등록번호" in rrn["answer"],
        rrn,
    )

    # v6.1/KakaoTalk 협의: 프론트 실제 step key와 문구 일치
    cert_purpose = chat_text("CERTIFICATE_SELECT_PURPOSE", session_id="test", conversation_history=[])
    assert_case(
        "TC-AI-FE-STEP-CERTIFICATE_SELECT_PURPOSE",
        "증명서 종류" in cert_purpose["answer"],
        cert_purpose,
    )

    movein_basic = chat_text("MOVEIN_INPUT_BASIC_INFO", session_id="test", conversation_history=[])
    assert_case(
        "TC-AI-FE-STEP-MOVEIN_INPUT_BASIC_INFO",
        "본인확인" in movein_basic["answer"] and "기본정보" in movein_basic["answer"],
        movein_basic,
    )

    movein_reason = chat_text("MOVEIN_SELECT_REASON", session_id="test", conversation_history=[])
    assert_case(
        "TC-AI-FE-STEP-MOVEIN_SELECT_REASON",
        "전입사유" in movein_reason["answer"],
        movein_reason,
    )

    movein_household = chat_text("MOVEIN_SELECT_HOUSEHOLD", session_id="test", conversation_history=[])
    assert_case(
        "TC-AI-FE-STEP-MOVEIN_SELECT_HOUSEHOLD",
        "세대 구성" in movein_household["answer"],
        movein_household,
    )

    movein_extra = chat_text("MOVEIN_SELECT_EXTRA_SERVICE", session_id="test", conversation_history=[])
    assert_case(
        "TC-AI-FE-STEP-MOVEIN_SELECT_EXTRA_SERVICE",
        "추가 신청 서비스" in movein_extra["answer"],
        movein_extra,
    )

    # 확인 단계에서 이전 다중 발화 맥락 반영
    confirm = chat_text(
        "CERTIFICATE_CONFIRM",
        session_id="test",
        conversation_history=r9["conversation_history"],
    )
    assert_case(
        "TC-AI-E2E-CONFIRM-WITH-ENTITIES",
        "1부" in confirm["answer"] and "현금" in confirm["answer"],
        confirm,
    )

    # count 범위 초과는 prefilled 되면 안 됨
    invalid = chat_text("주민등록등본 100개 현금으로 발급", session_id="test", conversation_history=[])
    assert_case(
        "TC-AI-EDGE-INVALID-COUNT",
        invalid["entities"].get("count") is None
        and invalid["entities"].get("paymentMethod") == "CASH",
        invalid,
    )


if __name__ == "__main__":
    main()
