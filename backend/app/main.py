from contextlib import asynccontextmanager
from dataclasses import dataclass
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import Settings, get_settings
from app.observability import FixedWindowLimiter, Metrics, ObservabilityMiddleware, configure_logging
from app.services.agent import AgentService
from app.services.copilot import CopilotService
from app.services.evaluation import EvaluationService
from app.services.insights import InsightsService
from app.services.langchain_adapter import LangChainRagService
from app.services.llm import LLMClient
from app.services.rag import LocalTfidfRetriever
from app.services.storage import JsonStore


@dataclass
class Services:
    settings: Settings
    store: JsonStore
    retriever: LocalTfidfRetriever
    llm: LLMClient
    copilot: CopilotService
    langchain_rag: LangChainRagService
    agent: AgentService
    evaluation: EvaluationService
    insights: InsightsService


def build_services(settings: Settings) -> Services:
    seed_path = Path(__file__).resolve().parents[1] / "data" / "seed.json"
    store = JsonStore(settings.data_path, seed_path)
    retriever = LocalTfidfRetriever()
    retriever.build(store.documents())
    llm = LLMClient(settings)
    copilot = CopilotService(retriever, llm, settings.evidence_threshold)
    return Services(
        settings=settings,
        store=store,
        retriever=retriever,
        llm=llm,
        copilot=copilot,
        langchain_rag=LangChainRagService(retriever, copilot),
        agent=AgentService(copilot),
        evaluation=EvaluationService(copilot),
        insights=InsightsService(),
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    configured = settings or get_settings()
    configure_logging()
    metrics = Metrics()
    limiter = FixedWindowLimiter(configured.rate_limit, configured.rate_window_seconds)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.services = build_services(configured)
        yield

    app = FastAPI(
        title=configured.app_name,
        version=configured.app_version,
        description="FlowPilot AI 产品运营 Copilot API",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        ObservabilityMiddleware,
        metrics=metrics,
        limiter=limiter,
        logger=logging.getLogger("flowpilot.http"),
    )
    app.state.metrics = metrics
    app.state.limiter = limiter
    app.include_router(router)

    frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "release-dist"
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
    return app


app = create_app()
