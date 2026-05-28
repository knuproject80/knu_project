from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceItem:
    service_id: str
    intent: str
    service_name: str
    answer: str
    keywords: tuple[str, ...]


SERVICE_CATALOG: tuple[ServiceItem, ...] = (
    ServiceItem(
        service_id="RESIDENT_REGISTRATION_COPY",
        intent="issue_document",
        service_name="주민등록등본 발급",
        answer="주민등록등본 발급을 도와드릴게요. 신분증을 준비해 주세요.",
        keywords=("주민등록등본", "등본", "등본발급", "주민등록표등본"),
    ),
    ServiceItem(
        service_id="RESIDENT_REGISTRATION_ABSTRACT",
        intent="issue_document",
        service_name="주민등록초본 발급",
        answer="주민등록초본 발급을 도와드릴게요. 신분증을 준비해 주세요.",
        keywords=("주민등록초본", "초본", "초본발급", "주민등록표초본"),
    ),
    ServiceItem(
        service_id="MOVE_IN_REPORT",
        intent="submit_application",
        service_name="전입신고",
        answer="전입신고를 도와드릴게요. 이사 온 주소를 준비해 주세요.",
        keywords=("전입신고", "이사신고", "이사와서신고", "주소이전", "주소이전신고", "주소옮김"),
    ),
    ServiceItem(
        service_id="MOVE_OUT_REPORT",
        intent="submit_application",
        service_name="전출신고",
        answer="전출신고를 도와드릴게요. 이동할 주소 정보를 준비해 주세요.",
        keywords=("전출신고", "나가는신고", "이사나감", "전출"),
    ),
)

# 현재 키오스크에서 직접 진입할 화면은 없지만, 민원 요청임은 알 수 있는 케이스.
UNSUPPORTED_SERVICE_KEYWORDS: tuple[str, ...] = (
    "여권", "여권발급", "운전면허", "면허증", "자동차등록", "출생신고", "사망신고",
)

OUT_OF_SCOPE_KEYWORDS: tuple[str, ...] = (
    "날씨", "맛집", "주식", "뉴스", "노래", "게임", "농담", "시간알려", "몇시",
)


STEP_PROMPTS: dict[str, str] = {
    # 주민등록등본 발급 단계
    "CERTIFICATE_SELECT_PURPOSE": "등본 용도를 선택해 주세요.",
    "CERTIFICATE_SELECT_COUNT": "발급 매수를 선택해 주세요.",
    "CERTIFICATE_SELECT_SCOPE": "주민등록번호 공개 범위를 선택해 주세요.",
    "CERTIFICATE_CONFIRM": "입력하신 내용을 확인해 주세요. 맞으면 발급 버튼을 눌러 주세요.",
    "CERTIFICATE_PRINTING": "출력 중입니다. 잠시 기다려 주세요.",
    "CERTIFICATE_COMPLETE": "등본 출력이 완료되었습니다. 서류를 가져가 주세요.",
    # 전입신고 단계
    "MOVEIN_INPUT_PREV_ADDRESS": "이사 오시기 전 살던 주소를 입력해 주세요.",
    "MOVEIN_INPUT_NEW_ADDRESS": "이사 오신 새 주소를 입력해 주세요.",
    "MOVEIN_SELECT_DATE": "이사 오신 날짜를 선택해 주세요.",
    "MOVEIN_INPUT_MEMBERS": "함께 이사 오신 가족이 있으면 입력해 주세요.",
    "MOVEIN_CONFIRM": "내용을 확인해 주세요. 맞으시면 신고 버튼을 눌러 주세요.",
    "MOVEIN_COMPLETE": "전입신고가 완료되었습니다. 고생하셨습니다.",
}


CONTEXT_PROMPTS: dict[str, str] = {
    "SESSION_START": "안녕하세요. 무엇을 도와드릴까요? 필요한 민원 서비스를 말씀해 주세요.",
    "SERVICE_ENTER": "서비스 화면으로 이동합니다. 화면의 안내에 따라 버튼을 눌러 주세요.",
    "MODE_CHANGE": "화면 설정을 바꿨습니다. 계속 진행해 주세요.",
    "HOME": "처음 화면으로 돌아왔습니다. 필요한 민원 서비스를 말씀해 주세요.",
    "SESSION_END": "이용해 주셔서 감사합니다. 서류와 소지품을 챙겨 주세요.",
    "ERROR_RETRY": "죄송합니다. 다시 한 번 말씀해 주세요.",
}


def normalize_text(text: str) -> str:
    """키워드 매칭용 정규화. 한글은 유지하고 공백/기호만 줄인다."""
    lowered = text.strip().lower()
    return re.sub(r"[\s\-_/.,!?~:;()\[\]{}]+", "", lowered)


def find_service_by_rule(text: str) -> ServiceItem | None:
    normalized = normalize_text(text)
    for item in SERVICE_CATALOG:
        for keyword in item.keywords:
            if normalize_text(keyword) in normalized:
                return item
    return None


def contains_any_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    normalized = normalize_text(text)
    return any(normalize_text(keyword) in normalized for keyword in keywords)


def find_step_prompt(text: str) -> tuple[str, str] | None:
    normalized = normalize_text(text)
    for step_key, guide in STEP_PROMPTS.items():
        if normalize_text(step_key) in normalized:
            return step_key, guide
    return None
