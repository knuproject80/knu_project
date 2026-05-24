from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceItem:
    service_id: str
    intent: str
    answer: str
    keywords: tuple[str, ...]


# 테스트 가이드 2.4 기준 지원 서비스만 매핑한다.
# 101: 전입/전출신고, 102: 주민등록등본/초본 발급
SERVICE_CATALOG: tuple[ServiceItem, ...] = (
    ServiceItem(
        service_id="RESIDENT_REGISTRATION_COPY",
        intent="issue_document",
        answer="주민등록등본 발급 메뉴로 안내할게요.",
        keywords=("주민등록등본", "등본", "등본발급", "주민등록표등본"),
    ),
    ServiceItem(
        service_id="RESIDENT_REGISTRATION_ABSTRACT",
        intent="issue_document",
        answer="주민등록초본 발급 메뉴로 안내할게요.",
        keywords=("주민등록초본", "초본", "초본발급", "주민등록표초본"),
    ),
    ServiceItem(
        service_id="MOVE_IN_REPORT",
        intent="submit_application",
        answer="전입신고 메뉴로 안내할게요.",
        keywords=("전입신고", "이사신고", "이사와서신고", "주소이전", "주소이전신고", "주소옮김"),
    ),
    ServiceItem(
        service_id="MOVE_OUT_REPORT",
        intent="submit_application",
        answer="전출신고 메뉴로 안내할게요.",
        keywords=("전출신고", "전출", "이사나가서신고", "주소나감"),
    ),
)


UNSUPPORTED_SERVICE_KEYWORDS: tuple[str, ...] = (
    "여권", "여권발급", "여권신청", "passport",
    "운전면허", "면허증", "가족관계증명서", "건강보험", "혼인관계증명서", "납세", "세금",
)

OUT_OF_SCOPE_KEYWORDS: tuple[str, ...] = (
    "날씨", "기온", "비와", "뉴스", "주가", "맛집", "길찾기", "시간 알려", "몇시",
)

USER_TYPE_HINT_KEYWORDS: tuple[str, ...] = (
    "어르신", "노인", "글씨크게", "큰글씨", "글자크게", "큰글자", "천천히", "휠체어", "낮은화면",
)


def normalize_text(text: str) -> str:
    """키워드 매칭용 정규화. 한글은 유지하고 공백/기호만 줄인다."""
    lowered = text.strip().lower()
    return re.sub(r"[\s\-_/.,!?~]+", "", lowered)


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    normalized = normalize_text(text)
    return any(normalize_text(keyword) in normalized for keyword in keywords)


def find_service_by_rule(text: str) -> ServiceItem | None:
    normalized = normalize_text(text)
    for item in SERVICE_CATALOG:
        for keyword in item.keywords:
            if normalize_text(keyword) in normalized:
                return item
    return None


def is_unsupported_service_request(text: str) -> bool:
    return _contains_any(text, UNSUPPORTED_SERVICE_KEYWORDS)


def is_out_of_scope_question(text: str) -> bool:
    return _contains_any(text, OUT_OF_SCOPE_KEYWORDS)


def is_user_type_hint_only(text: str) -> bool:
    return _contains_any(text, USER_TYPE_HINT_KEYWORDS)
