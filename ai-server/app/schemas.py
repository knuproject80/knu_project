from __future__ import annotations

from typing import Literal, Optional

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

ServiceIdType = Literal[
    "RESIDENT_REGISTRATION_COPY",
    "FAMILY_CERTIFICATE",
    "MOVE_IN_REPORT",
    "HEALTH_INSURANCE",
    "MARRIAGE_CERTIFICATE",
    "TAX_CERTIFICATE",
    "UNKNOWN",
]

SourceType = Literal["rule_based", "llm", "fallback", "mixed"]


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    model: str


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
    answer: str
    source: SourceType
    raw_text: str
    model_name: str


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
    answer: str

    needsConfirmation: bool
    source: SourceType
    model_name: str
