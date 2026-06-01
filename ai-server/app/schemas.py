from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

UserType = Literal[
    "ELDERLY",
    "WHEELCHAIR",
    "VISUAL_IMPAIRMENT",
    "HEARING_IMPAIRMENT",
    "NORMAL",
    "UNKNOWN",
]

IntentType = Literal[
    "issue_document",
    "submit_application",
    "pay_or_check",
    "welfare_service",
    "general_question",
    "unknown",
]

# v6.1 기준 허용 serviceId.
# low confidence / 서비스 외 발화는 빈 문자열("")로 내려보낸다.
ServiceIdType = Literal[
    "RESIDENT_REGISTRATION_COPY",
    "RESIDENT_REGISTRATION_ABSTRACT",
    "MOVE_IN_REPORT",
    "MOVE_OUT_REPORT",
    "",
]

SourceType = Literal["rule_based", "llm", "fallback", "mixed"]
ConversationRole = Literal["user", "assistant", "system"]
PaymentMethodType = Literal["CASH", "CARD"]


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    model: str


class ConversationMessage(BaseModel):
    role: ConversationRole
    content: str = Field(default="", max_length=2000)


class CertificateEntities(BaseModel):
    """v6.0/v6.1 다중 발화 필드 추출 결과.

    MCP Client는 이 값을 session_manager.set_prefilled(session_id, entities)에 저장한 뒤
    STEP_CHANGE 단계에서 prefilled 여부를 판단한다.
    """

    count: Optional[int] = Field(default=None, description="발급 매수. 예: 1개, 두 장")
    paymentMethod: Optional[PaymentMethodType] = Field(default=None, description="CASH 또는 CARD")
    purpose: Optional[str] = Field(default=None, description="제출용, 은행용 등")
    scope: Optional[str] = Field(default=None, description="발급형태/공개범위")


class BaseTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500, description="사용자 입력 문장")
    session_id: Optional[str] = Field(default=None, description="세션 ID")
    locale: str = Field(default="ko-KR", description="언어 코드")

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("text must not be empty.")
        return value


class ChatRequest(BaseTextRequest):
    conversation_history: list[ConversationMessage] = Field(
        default_factory=list,
        description="이전 대화 기록. [{role: 'user'|'assistant', content: '...'}] 형식",
    )


class UserTypeResponse(BaseModel):
    task: Literal["classify_user_type"]
    success: bool
    fallback_used: bool
    userType: UserType
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str
    source: SourceType
    raw_text: str
    model_name: str


class ServiceRecommendResponse(BaseModel):
    task: Literal["recommend_service"]
    success: bool
    fallback_used: bool
    intent: IntentType
    serviceId: ServiceIdType
    confidence: float = Field(..., ge=0.0, le=1.0)
    entities: CertificateEntities = Field(default_factory=CertificateEntities)
    answer: str
    source: SourceType
    raw_text: str
    model_name: str


class ChatResponse(BaseModel):
    task: Literal["chat"] = "chat"
    success: bool
    fallback_used: bool
    intent: IntentType
    serviceId: ServiceIdType
    confidence: float = Field(..., ge=0.0, le=1.0)
    # v6.0부터 필수. count/paymentMethod/purpose/scope 키가 항상 포함되어야 한다.
    entities: CertificateEntities = Field(default_factory=CertificateEntities)
    answer: str
    conversation_history: list[ConversationMessage]
    userType: UserType = "NORMAL"
    userTypeConfidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source: SourceType
    raw_text: str = ""
    model_name: str = ""


class AnalyzeResponse(BaseModel):
    task: Literal["analyze"]
    success: bool
    fallback_used: bool

    userType: UserType
    userTypeConfidence: float = Field(..., ge=0.0, le=1.0)
    userTypeReason: str

    intent: IntentType
    serviceId: ServiceIdType
    serviceConfidence: float = Field(..., ge=0.0, le=1.0)
    entities: CertificateEntities = Field(default_factory=CertificateEntities)
    answer: str

    needsConfirmation: bool
    source: SourceType
    model_name: str
