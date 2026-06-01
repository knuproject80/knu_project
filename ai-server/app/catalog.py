from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


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
        answer="전입신고를 도와드릴게요. 이사 후 주소를 준비해 주세요.",
        keywords=("전입신고", "이사신고", "이사와서신고", "주소이전", "주소이전신고", "주소옮김"),
    ),
    ServiceItem(
        service_id="MOVE_OUT_REPORT",
        intent="submit_application",
        service_name="전출신고",
        answer="전출신고를 도와드릴게요. 이사 가실 주소를 준비해 주세요.",
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

# v6.1 공식 단계 + 프론트 실제 STEP_CHANGE key를 모두 수용한다.
# - v6.1 가이드: 등본 단계는 RRN → SCOPE → COUNT → CONFIRM → PRINTING → COMPLETE.
# - 프론트 협의 요청: CERTIFICATE_SELECT_PURPOSE 및 세분화된 MOVEIN_* key도 사용.
STEP_PROMPTS: dict[str, str] = {
    # 주민등록등본/초본 발급 단계
    "CERTIFICATE_SELECT_PURPOSE": "발급할 증명서 종류를 선택해 주세요.",
    "CERTIFICATE_SELECT_RRN": "주민등록번호를 입력해 주세요.",
    "CERTIFICATE_SELECT_SCOPE": "발급형태를 선택해 주세요.",
    "CERTIFICATE_SELECT_COUNT": "발급 매수를 선택해 주세요.",
    "CERTIFICATE_CONFIRM": "입력하신 내용을 확인해 주세요. 맞으면 제출 버튼을 눌러 주세요.",
    "CERTIFICATE_PRINTING": "출력 중입니다. 잠시 기다려 주세요.",
    "CERTIFICATE_COMPLETE": "등본 출력이 완료되었습니다. 서류를 가져가 주세요.",
    # 전입신고 단계: 프론트 실제 화면 흐름 기준 세분화 key
    "MOVEIN_INPUT_BASIC_INFO": "본인확인 및 기본정보를 입력해 주세요.",
    "MOVEIN_SELECT_REASON": "전입사유를 선택해 주세요.",
    "MOVEIN_INPUT_PREV_ADDRESS": "이사 전 주소를 확인하고, 이사 가는 사람을 선택해 주세요.",
    "MOVEIN_INPUT_NEW_ADDRESS": "이사 후 주소를 입력해 주세요.",
    "MOVEIN_SELECT_HOUSEHOLD": "이사 후 세대 구성을 선택해 주세요.",
    "MOVEIN_SELECT_EXTRA_SERVICE": "추가 신청 서비스를 선택해 주세요.",
    "MOVEIN_CONFIRM": "입력하신 전입신고 내용을 확인해 주세요. 맞으면 제출 버튼을 눌러 주세요.",
    # 전입신고 단계: v6.1 테스트 가이드에 남아있는 key도 하위 호환 지원
    "MOVEIN_SELECT_DATE": "전입일을 선택해 주세요.",
    "MOVEIN_INPUT_MEMBERS": "전입 세대원 정보를 입력해 주세요.",
    "MOVEIN_COMPLETE": "전입신고가 완료되었습니다.",
}


CONTEXT_PROMPTS: dict[str, str] = {
    "SESSION_START": "안녕하세요. 무엇을 도와드릴까요? 필요한 민원 서비스를 말씀해 주세요.",
    "SERVICE_ENTER": "서비스 화면으로 이동합니다. 화면의 안내에 따라 버튼을 눌러 주세요.",
    "MODE_CHANGE": "화면 설정을 바꿨습니다. 계속 진행해 주세요.",
    "HOME": "처음 화면으로 돌아왔습니다. 필요한 민원 서비스를 말씀해 주세요.",
    "SESSION_END": "이용해 주셔서 감사합니다. 서류와 소지품을 챙겨 주세요.",
    "ERROR_RETRY": "죄송합니다. 다시 한 번 말씀해 주세요.",
}

# v6.0/v6.1 prefilled 스킵 대상. AI Server는 entities를 반환하고,
# 실제 스킵 여부는 MCP Client(session_manager)가 판단한다.
STEP_TO_ENTITY: dict[str, str] = {
    "CERTIFICATE_SELECT_COUNT": "count",
    "CERTIFICATE_SELECT_SCOPE": "scope",
}

DEFAULT_ENTITIES: dict[str, Any] = {
    "count": None,
    "paymentMethod": None,
    "purpose": None,
    "scope": None,
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
