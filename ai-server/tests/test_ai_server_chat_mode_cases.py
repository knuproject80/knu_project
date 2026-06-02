from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas import ChatRequest
from app.services.chat import chat_step_guide, chat_text


def assert_case(name: str, condition: bool, result: dict | object) -> None:
    print("=" * 80)
    print(name, "PASS" if condition else "FAIL")
    if isinstance(result, dict):
        print("result:", result)
    else:
        print("result:", result)
    if not condition:
        raise AssertionError(name)


def main() -> None:
    # 하위 호환: mode 누락 시 classify로 처리되어야 함.
    req = ChatRequest(text="주민등록등본 발급받고 싶어요")
    assert_case("TC-MODE-COMPAT-DEFAULT", req.mode == "classify", req)

    classify = chat_text("주민등록등본 발급받고 싶어요", session_id="test", conversation_history=[])
    assert_case(
        "TC-MODE-CLASSIFY",
        classify["serviceId"] == "RESIDENT_REGISTRATION_COPY"
        and classify["confidence"] >= 0.6
        and "answer" in classify,
        classify,
    )

    # step_guide: text 빈 문자열 허용, step 필수.
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
    assert_case("TC-MODE-STEP-REQUEST", step_req.mode == "step_guide" and step_req.text == "", step_req)

    basic = chat_step_guide(
        step="MOVEIN_INPUT_BASIC_INFO",
        session_id="test-session",
        user_type="NORMAL",
        service_id=101,
        extra_context={"retryCount": 0},
        conversation_history=[],
    )
    assert_case(
        "TC-STEP-GUIDE-BASIC-INFO",
        "본인확인" in basic["answer"]
        and "기본정보" in basic["answer"]
        and "intent" not in basic
        and "serviceId" not in basic
        and "confidence" not in basic,
        basic,
    )

    rrn_elderly = chat_step_guide(
        step="CERTIFICATE_SELECT_RRN",
        user_type="ELDERLY",
        service_id=102,
        extra_context={"retryCount": 0, "prevStep": "CERTIFICATE_SELECT_PURPOSE"},
        conversation_history=[],
    )
    assert_case(
        "TC-STEP-GUIDE-RRN-ELDERLY",
        "천천히" in rrn_elderly["answer"] and "주민등록번호" not in rrn_elderly["answer"],
        rrn_elderly,
    )

    rrn_retry = chat_step_guide(
        step="CERTIFICATE_SELECT_RRN",
        user_type="ELDERLY",
        service_id=102,
        extra_context={"retryCount": 2},
        conversation_history=[],
    )
    assert_case(
        "TC-STEP-GUIDE-RETRY-STAFF",
        "직원 호출" in rrn_retry["answer"],
        rrn_retry,
    )

    confirm_wheelchair = chat_step_guide(
        step="MOVEIN_CONFIRM",
        user_type="WHEELCHAIR",
        service_id=101,
        extra_context={"retryCount": 0},
        conversation_history=[],
    )
    assert_case(
        "TC-STEP-GUIDE-WHEELCHAIR-CONFIRM",
        "한 번" in confirm_wheelchair["answer"] and "제출 버튼" in confirm_wheelchair["answer"],
        confirm_wheelchair,
    )

    unknown = chat_step_guide(
        step="UNKNOWN_STEP",
        user_type="NORMAL",
        service_id=101,
        extra_context={"retryCount": 0},
        conversation_history=[],
    )
    banned = ["무엇을 도와", "필요한 민원 서비스", "다시 말씀해"]
    assert_case(
        "TC-STEP-GUIDE-NO-INTENT-REPROMPT",
        not any(fragment in unknown["answer"] for fragment in banned),
        unknown,
    )


if __name__ == "__main__":
    main()
