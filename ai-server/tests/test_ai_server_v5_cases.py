from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.chat import chat_text


def sentence_count(answer: str) -> int:
    # 마침표/물음표/느낌표 기준으로만 센다.
    # 한국어 종결어미 "요"는 단어 안에도 들어갈 수 있어 과대 계산하지 않는다.
    parts = [p.strip() for p in answer.replace("?", ".").replace("!", ".").split(".") if p.strip()]
    return len(parts) if parts else 1


def assert_case(name: str, condition: bool, result: dict) -> None:
    print("=" * 80)
    print(name, "PASS" if condition else "FAIL")
    print("intent:", result.get("intent"))
    print("serviceId:", repr(result.get("serviceId")))
    print("confidence:", result.get("confidence"))
    print("userType:", result.get("userType"))
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
        and "등본" in r1["answer"],
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

    # STEP_CHANGE 안내 답변 생성 샘플
    rs = chat_text("CERTIFICATE_SELECT_COUNT", session_id="test", conversation_history=[])
    assert_case(
        "TC-AI-STEP-SAMPLE",
        "발급 매수" in rs["answer"]
        and len(rs["conversation_history"]) == 2,
        rs,
    )


if __name__ == "__main__":
    main()
