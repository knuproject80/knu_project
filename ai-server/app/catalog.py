from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceItem:
    service_id: str
    intent: str
    answer: str
    keywords: tuple[str, ...]


SERVICE_CATALOG: tuple[ServiceItem, ...] = (
    ServiceItem(
        service_id="RESIDENT_REGISTRATION_COPY",
        intent="issue_document",
        answer="주민등록등본 발급 메뉴로 안내할게요.",
        keywords=("주민등록등본", "등본", "등본발급", "주민등록표등본", "초본", "주민등록초본"),
    ),
    ServiceItem(
        service_id="FAMILY_CERTIFICATE",
        intent="issue_document",
        answer="가족관계증명서 발급 메뉴로 안내할게요.",
        keywords=("가족관계증명서", "가족관계", "가족증명서"),
    ),
    ServiceItem(
        service_id="MOVE_IN_REPORT",
        intent="submit_application",
        answer="전입신고 메뉴로 안내할게요.",
        keywords=("전입신고", "이사신고", "이사와서신고", "주소이전", "주소이전신고", "주소옮김"),
    ),
    ServiceItem(
        service_id="HEALTH_INSURANCE",
        intent="pay_or_check",
        answer="건강보험 관련 메뉴로 안내할게요.",
        keywords=("건강보험", "건강보험료", "보험료확인", "건강보험확인서"),
    ),
    ServiceItem(
        service_id="MARRIAGE_CERTIFICATE",
        intent="issue_document",
        answer="혼인관계증명서 발급 메뉴로 안내할게요.",
        keywords=("혼인관계증명서", "혼인관계", "결혼증명서"),
    ),
    ServiceItem(
        service_id="TAX_CERTIFICATE",
        intent="pay_or_check",
        answer="세금 납부 확인 메뉴로 안내할게요.",
        keywords=("세금", "납세", "납부확인", "세금납부확인서", "납세확인서", "지방세"),
    ),
)


def normalize_text(text: str) -> str:
    """키워드 매칭용 정규화. 한글은 유지하고 공백/기호만 줄인다."""
    lowered = text.strip().lower()
    return re.sub(r"[\s\-_/.,!?~]+", "", lowered)


def find_service_by_rule(text: str) -> ServiceItem | None:
    normalized = normalize_text(text)
    for item in SERVICE_CATALOG:
        for keyword in item.keywords:
            if normalize_text(keyword) in normalized:
                return item
    return None
