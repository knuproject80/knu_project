from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

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
ChatModeType = Literal["classify", "step_guide"]



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


class StepGuideExtraContext(BaseModel):
    retryCount: int = Field(default=0, ge=0, description="현재 단계 재진입 횟수. 0이면 첫 진입")
    prevStep: Optional[str] = Field(default=None, description="직전 단계 키")


class ChatRequest(BaseModel):
    """/chat 통합 요청.

    mode가 누락되면 하위 호환을 위해 classify로 처리한다.
    - classify: VOICE_INPUT용. text 필수.
    - step_guide: STEP_CHANGE용. step 필수, text는 빈 문자열 허용.
    """

    mode: ChatModeType = Field(default="classify", description="classify 또는 step_guide")
    text: str = Field(default="", max_length=500, description="사용자 발화. step_guide에서는 미사용 가능")
    session_id: Optional[str] = Field(default=None, description="세션 ID")
    locale: str = Field(default="ko-KR", description="언어 코드")
    conversation_history: list[ConversationMessage] = Field(
        default_factory=list,
        description="이전 대화 기록. [{role: 'user'|'assistant', content: '...'}] 형식",
    )

    # step_guide 전용 필드
    step: Optional[str] = Field(default=None, description="현재 STEP_CHANGE 단계 키")
    userType: UserType = Field(default="NORMAL", description="NORMAL / ELDERLY / WHEELCHAIR")
    serviceId: Optional[int | str] = Field(default=None, description="101 전입신고 / 102 등본·초본")
    extra_context: StepGuideExtraContext = Field(default_factory=StepGuideExtraContext)

    @field_validator("text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return (value or "").strip()

    @field_validator("step")
    @classmethod
    def strip_step(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def validate_by_mode(self) -> "ChatRequest":
        if self.mode == "classify" and not self.text:
            raise ValueError("text must not be empty when mode='classify'.")
        if self.mode == "step_guide" and not self.step:
            raise ValueError("step must not be empty when mode='step_guide'.")
        return self


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


class StepGuideResponse(BaseModel):
    """mode=step_guide 응답.

    MCP Client는 answer만 필수로 사용한다. 의도 분류 필드는 의도적으로 포함하지 않는다.
    """

    task: Literal["chat"] = "chat"
    success: bool = True
    mode: Literal["step_guide"] = "step_guide"
    answer: str
    conversation_history: list[ConversationMessage] = Field(default_factory=list)
    source: SourceType = "rule_based"
    raw_text: str = ""
    model_name: str = "rule_based"


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
