from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.model import model_instance
from app.schemas import (
    AnalyzeResponse,
    BaseTextRequest,
    HealthResponse,
    ServiceRecommendResponse,
    UserTypeResponse,
)
from app.services.analyze import analyze_text
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


@app.post("/classify/user-type", response_model=UserTypeResponse)
def classify_user_type_endpoint(req: BaseTextRequest) -> UserTypeResponse:
    return UserTypeResponse(**classify_user_type(req.text))


@app.post("/classify/service", response_model=ServiceRecommendResponse)
def classify_service_endpoint(req: BaseTextRequest) -> ServiceRecommendResponse:
    return ServiceRecommendResponse(**recommend_service(req.text))


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_endpoint(req: BaseTextRequest) -> AnalyzeResponse:
    return AnalyzeResponse(**analyze_text(req.text))
