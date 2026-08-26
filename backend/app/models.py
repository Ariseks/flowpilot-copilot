from typing import Any, Literal

from pydantic import BaseModel, Field


AgentIntent = Literal[
    "knowledge_qa", "customer_reply", "feedback_analysis", "campaign_plan"
]
RetrievalStrategy = Literal["tfidf", "bm25", "rrf"]


class Citation(BaseModel):
    source: str
    chunk: str
    score: float
    chunk_id: str


class DocumentSummary(BaseModel):
    id: str
    title: str
    source: str
    category: str
    created_at: str
    chunk_count: int = 0


class TextImportRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1)
    source: str | None = None
    category: str = "用户导入"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=4, ge=1, le=10)


class ChatResponse(BaseModel):
    answer: str
    mode: Literal["demo", "cloud"]
    citations: list[Citation]


class AgentTaskRequest(BaseModel):
    input: str = Field(min_length=1, max_length=8000)
    intent: AgentIntent | Literal["auto"] = "auto"
    top_k: int = Field(default=4, ge=1, le=10)
    retrieval_strategy: RetrievalStrategy = "rrf"


class AgentReplayRequest(BaseModel):
    retrieval_strategy: RetrievalStrategy | None = None
    top_k: int | None = Field(default=None, ge=1, le=10)


class AgentStep(BaseModel):
    name: str
    status: Literal["completed"] = "completed"
    detail: str


class TimingTrace(BaseModel):
    total_ms: int = 0
    retrieve_ms: int = 0
    generate_ms: int = 0


class RetrievalTrace(BaseModel):
    citation_count: int = 0
    raw_citation_count: int = 0
    top_score: float = 0.0
    strategy: RetrievalStrategy = "rrf"
    evidence_threshold: float = 0.1
    evidence_status: Literal["accepted", "refused"] | None = None
    candidates: list[Citation] = Field(default_factory=list)


class RequestTrace(BaseModel):
    requested_intent: AgentIntent | Literal["auto"] | None = None
    top_k: int | None = None
    retrieval_strategy: RetrievalStrategy | None = None


class FeedbackContextRecord(BaseModel):
    id: str
    message: str
    rating: int
    category: str
    user: str = "演示用户"
    task_id: str | None = None
    created_at: str


class GenerationTrace(BaseModel):
    mode: Literal["demo", "cloud"] = "demo"
    provider_used: Literal["demo", "cloud"] = "demo"
    fallback_used: bool = True
    error_type: str | None = None
    model: str | None = None
    generator_version: str | None = None
    prompt_version: str | None = None
    system_prompt: str | None = None
    user_prompt: str | None = None
    context_chunk_ids: list[str] = Field(default_factory=list)


class AgentTrace(BaseModel):
    timing: TimingTrace = Field(default_factory=TimingTrace)
    retrieval: RetrievalTrace = Field(default_factory=RetrievalTrace)
    generation: GenerationTrace = Field(default_factory=GenerationTrace)
    request: RequestTrace = Field(default_factory=RequestTrace)
    feedback_context: list[FeedbackContextRecord] = Field(default_factory=list)
    replay_of: str | None = None


class AgentTaskResponse(BaseModel):
    id: str
    input: str = "历史任务未记录原始输入"
    intent: AgentIntent
    status: Literal["completed"] = "completed"
    mode: Literal["demo", "cloud"]
    steps: list[AgentStep]
    artifacts: dict[str, Any]
    citations: list[Citation]
    trace: AgentTrace = Field(default_factory=AgentTrace)
    created_at: str


class AgentTaskListResponse(BaseModel):
    items: list[AgentTaskResponse]
    total: int
    next_cursor: str | None = None


class FeedbackCreate(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    rating: int = Field(ge=1, le=5)
    category: str = "general"
    user: str = "演示用户"
    task_id: str | None = None


class FeedbackRecord(FeedbackCreate):
    id: str
    created_at: str


class EvaluationCase(BaseModel):
    id: str | None = None
    category: str = "general"
    question: str = Field(min_length=1)
    expected_keywords: list[str] = Field(default_factory=list)
    expected_sources: list[str] = Field(default_factory=list)
    should_refuse: bool = False
    top_k: int = Field(default=4, ge=1, le=10)


class EvaluationRequest(BaseModel):
    cases: list[EvaluationCase] | None = None


class RetrievalMetrics(BaseModel):
    strategy: RetrievalStrategy
    retrieval_hit_rate: float
    source_recall_at_k: float | None = None
    mean_reciprocal_rank: float | None = None


class EvaluationCaseResult(BaseModel):
    id: str | None = None
    category: str
    question: str
    hit: bool
    keyword_recall: float
    source_hit: bool | None = None
    refusal_correct: bool | None = None
    top_score: float
    answer: str
    citations: list[Citation]
    baseline_hit: bool = False
    hybrid_hit: bool = False
    baseline_source_hit: bool | None = None
    citation_correctness: float | None = None
    faithfulness: float | None = None
    unsupported_claims: list[str] = Field(default_factory=list)


class EvaluationResponse(BaseModel):
    dataset_name: str
    dataset_version: str
    total: int
    retrieval_hit_rate: float
    average_keyword_recall: float
    source_recall_at_k: float | None = None
    refusal_accuracy: float | None = None
    citation_correctness: float | None = None
    faithfulness: float | None = None
    baseline: RetrievalMetrics
    hybrid: RetrievalMetrics
    evaluation_method: str = "规则评估 v1"
    cases: list[EvaluationCaseResult]


class InsightGap(BaseModel):
    topic: str
    query_count: int
    average_top_score: float
    low_feedback_count: int
    priority: Literal["高", "中", "低"]


class LowScoreInsight(BaseModel):
    task_id: str | None = None
    question: str
    score: float
    reason: str
    created_at: str
    fallback_used: bool = False


class InsightsResponse(BaseModel):
    gaps: list[InsightGap]
    low_scores: list[LowScoreInsight]
