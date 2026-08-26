from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from app.models import (
    AgentTaskListResponse,
    AgentTaskRequest,
    AgentTaskResponse,
    ChatRequest,
    ChatResponse,
    DocumentSummary,
    EvaluationRequest,
    EvaluationResponse,
    FeedbackCreate,
    FeedbackRecord,
    InsightsResponse,
    TextImportRequest,
)
from app.services.document_parser import extract_text


router = APIRouter(prefix="/api")


def _services(request: Request):
    return request.app.state.services


def _document_summary(document: dict, chunk_count: int) -> DocumentSummary:
    return DocumentSummary(
        id=document["id"],
        title=document["title"],
        source=document["source"],
        category=document["category"],
        created_at=document["created_at"],
        chunk_count=chunk_count,
    )


@router.get("/health/live")
def health_live() -> dict:
    return {"status": "ok", "check": "liveness"}


@router.get("/health/ready")
def health_ready(request: Request) -> dict:
    services = _services(request)
    return {
        "status": "ok",
        "check": "readiness",
        "documents": len(services.store.documents()),
        "chunks": len(services.retriever.chunks),
    }


@router.get("/health")
def health(request: Request) -> dict:
    services = _services(request)
    return {
        "status": "ok",
        "app": request.app.title,
        "version": request.app.version,
        "mode": services.settings.demo_mode and "demo" or "cloud",
        "rag_framework": "langchain-core",
        "documents": len(services.store.documents()),
        "chunks": len(services.retriever.chunks),
    }


@router.get("/metrics")
def metrics(request: Request) -> dict:
    return request.app.state.metrics.snapshot()


@router.get("/dashboard/metrics")
def dashboard_metrics(request: Request) -> dict:
    services = _services(request)
    state = services.store.snapshot()
    ratings = [item["rating"] for item in state["feedback"]]
    categories: dict[str, int] = {}
    for document in state["documents"]:
        category = document["category"]
        categories[category] = categories.get(category, 0) + 1
    return {
        "documents": len(state["documents"]),
        "chunks": len(services.retriever.chunks),
        "feedback_count": len(state["feedback"]),
        "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0,
        "chat_count": state["chat_count"],
        "agent_task_count": len(state["agent_tasks"]),
        "document_categories": dict(sorted(categories.items())),
        "mode": services.llm.mode,
    }


@router.get("/insights", response_model=InsightsResponse)
def insights(request: Request) -> InsightsResponse:
    services = _services(request)
    return services.insights.build(services.store.agent_tasks(), services.store.feedback())


@router.get("/documents", response_model=list[DocumentSummary])
def list_documents(request: Request) -> list[DocumentSummary]:
    services = _services(request)
    counts = services.retriever.chunk_counts()
    return [
        _document_summary(document, counts[document["id"]])
        for document in services.store.documents()
    ]


def _import_document(request: Request, title: str, text: str, source: str, category: str):
    services = _services(request)
    document = {
        "id": f"doc-{uuid4().hex[:12]}",
        "title": title,
        "text": text.strip(),
        "source": source,
        "category": category,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if not document["text"]:
        raise HTTPException(status_code=422, detail="文档内容不能为空")
    services.store.add_document(document)
    services.retriever.build(services.store.documents())
    return _document_summary(
        document, services.retriever.chunk_counts()[document["id"]]
    )


@router.post(
    "/documents/import", response_model=DocumentSummary, status_code=status.HTTP_201_CREATED
)
def import_text(payload: TextImportRequest, request: Request) -> DocumentSummary:
    return _import_document(
        request,
        payload.title,
        payload.text,
        payload.source or f"用户导入/{payload.title}",
        payload.category,
    )


@router.post(
    "/documents/upload", response_model=DocumentSummary, status_code=status.HTTP_201_CREATED
)
async def upload_document(request: Request, file: UploadFile = File(...)) -> DocumentSummary:
    filename = file.filename or "document.txt"
    suffix = Path(filename).suffix.lower()
    if suffix not in {".txt", ".md", ".csv", ".pdf", ".docx"}:
        raise HTTPException(status_code=415, detail="仅支持 UTF-8 的 txt、md、csv，以及可提取文本的 pdf、docx 文件")
    content = await file.read()
    if len(content) > 2_000_000:
        raise HTTPException(status_code=413, detail="文件不能超过 2MB")
    try:
        text = extract_text(content, suffix)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _import_document(request, Path(filename).stem, text, f"用户上传/{filename}", "用户上传")


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    services = _services(request)
    answer, citations = await services.copilot.answer(payload.message, payload.top_k)
    services.store.increment_chat_count()
    return ChatResponse(answer=answer, mode=services.llm.mode, citations=citations)


@router.post("/langchain/chat")
async def langchain_chat(payload: ChatRequest, request: Request) -> dict:
    services = _services(request)
    result = await services.langchain_rag.invoke(payload.message, payload.top_k)
    services.store.increment_chat_count()
    return result


@router.get("/agent/tasks", response_model=AgentTaskListResponse)
def list_agent_tasks(
    request: Request,
    limit: int = 20,
    cursor: int = 0,
    intent: str | None = None,
    fallback_used: bool | None = None,
) -> AgentTaskListResponse:
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=422, detail="limit 必须介于 1 到 100")
    tasks = list(reversed(_services(request).store.agent_tasks()))
    if intent:
        tasks = [item for item in tasks if item.get("intent") == intent]
    if fallback_used is not None:
        tasks = [
            item for item in tasks
            if bool(item.get("trace", {}).get("generation", {}).get("fallback_used", True)) == fallback_used
        ]
    page = tasks[cursor : cursor + limit]
    next_cursor = str(cursor + limit) if cursor + limit < len(tasks) else None
    return AgentTaskListResponse(items=page, total=len(tasks), next_cursor=next_cursor)


@router.get("/agent/tasks/{task_id}", response_model=AgentTaskResponse)
def get_agent_task(task_id: str, request: Request) -> dict:
    for task in _services(request).store.agent_tasks():
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail="未找到该 Agent 任务")


@router.post(
    "/agent/tasks", response_model=AgentTaskResponse, status_code=status.HTTP_201_CREATED
)
async def create_agent_task(payload: AgentTaskRequest, request: Request) -> dict:
    services = _services(request)
    task = await services.agent.execute(
        payload.input, payload.intent, payload.top_k, services.store.feedback()
    )
    services.store.add_agent_task(task)
    return task


@router.get("/feedback", response_model=list[FeedbackRecord])
def list_feedback(request: Request) -> list[dict]:
    return list(reversed(_services(request).store.feedback()))


@router.post(
    "/feedback", response_model=FeedbackRecord, status_code=status.HTTP_201_CREATED
)
def create_feedback(payload: FeedbackCreate, request: Request) -> dict:
    record = {
        **payload.model_dump(),
        "id": f"fb-{uuid4().hex[:12]}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _services(request).store.add_feedback(record)
    return record


@router.post("/evaluation", response_model=EvaluationResponse)
async def evaluate(payload: EvaluationRequest, request: Request) -> EvaluationResponse:
    return await _services(request).evaluation.run(payload.cases)
