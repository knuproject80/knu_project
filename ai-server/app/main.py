from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.model import model_instance
from typing import Union

from app.schemas import (
    AnalyzeResponse,
    BaseTextRequest,
    ChatRequest,
    ChatResponse,
    StepGuideResponse,
    HealthResponse,
    ServiceRecommendResponse,
    UserTypeResponse,
)
from app.services.analyze import analyze_text
from app.services.chat import chat_step_guide, chat_text
from app.services.service_recommend import recommend_service
from app.services.user_type import classify_user_type

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG_LOGS else logging.INFO,
    format="[%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="관공서 키오스크용 AI/LLM 서버",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=False if settings.allowed_origins_list == ["*"] else True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    model_instance.load()
    logger.info("%s started. model=%s", settings.APP_NAME, model_instance.model_id)


@app.get("/", response_model=HealthResponse)
def root() -> HealthResponse:
    return health()


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        model=model_instance.model_id,
    )


@app.post("/chat", response_model=Union[ChatResponse, StepGuideResponse])
def chat_endpoint(req: ChatRequest) -> ChatResponse | StepGuideResponse:
    """MCP Client 연동용 /chat 엔드포인트.

    - mode="classify" 또는 mode 누락: VOICE_INPUT용 의도 분류 + 진입 안내.
    - mode="step_guide": STEP_CHANGE용 단계 안내 문구만 생성. 의도 분류를 수행하지 않는다.
    """
    if req.mode == "step_guide":
        result = chat_step_guide(
            step=req.step or "",
            session_id=req.session_id,
            locale=req.locale,
            user_type=req.userType,
            service_id=req.serviceId,
            extra_context=req.extra_context,
            conversation_history=req.conversation_history,
        )
        return StepGuideResponse(**result)

    result = chat_text(
        req.text,
        session_id=req.session_id,
        locale=req.locale,
        conversation_history=req.conversation_history,
    )
    return ChatResponse(**result)


@app.post("/classify/user-type", response_model=UserTypeResponse)
def classify_user_type_endpoint(req: BaseTextRequest) -> UserTypeResponse:
    return UserTypeResponse(**classify_user_type(req.text))


@app.post("/classify/service", response_model=ServiceRecommendResponse)
def classify_service_endpoint(req: BaseTextRequest) -> ServiceRecommendResponse:
    """하위 호환용 엔드포인트.

    v6.1 기준 MCP Client는 /chat을 사용하지만, 기존 테스트/디버깅을 위해 유지한다.
    """
    return ServiceRecommendResponse(**recommend_service(req.text))


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_endpoint(req: BaseTextRequest) -> AnalyzeResponse:
    return AnalyzeResponse(**analyze_text(req.text))
