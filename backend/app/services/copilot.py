from dataclasses import dataclass

from app.models import Citation, RetrievalStrategy
from app.services.llm import LLMClient, LLMResult
from app.services.rag import LocalTfidfRetriever


@dataclass(frozen=True)
class EvidenceResult:
    raw_citations: list[Citation]
    citations: list[Citation]
    threshold: float

    @property
    def status(self) -> str:
        return "accepted" if self.citations else "refused"


class CopilotService:
    def __init__(
        self,
        retriever: LocalTfidfRetriever,
        llm: LLMClient,
        evidence_threshold: float = 0.1,
    ):
        self.retriever = retriever
        self.llm = llm
        self.evidence_threshold = evidence_threshold

    @staticmethod
    def effective_mode(result: LLMResult) -> str:
        """Return the mode that actually produced the visible answer."""
        return "cloud" if result.provider_used == "cloud" and not result.fallback_used else "demo"

    def retrieve_evidence(
        self,
        message: str,
        top_k: int,
        strategy: RetrievalStrategy | None = None,
    ) -> EvidenceResult:
        raw_citations = self.retriever.search(message, top_k, strategy)
        # 门槛固定看排序结果的 Top-1 TF-IDF 分数；通过后只发送仍达标的候选。
        # 这样 BM25/RRF 的排序策略不会改变分数的量纲，也不会把弱相关片段交给模型。
        citations = []
        if raw_citations and raw_citations[0].score >= self.evidence_threshold:
            citations = [
                item for item in raw_citations if item.score >= self.evidence_threshold
            ]
        return EvidenceResult(raw_citations, citations, self.evidence_threshold)

    @staticmethod
    def demo_answer(message: str, citations: list[Citation]) -> str:
        if not citations:
            return "当前知识库中没有找到足够相关的信息。请补充问题细节或导入相关文档。"
        evidence = "\n".join(
            f"- {item.chunk}（来源：{item.source}，片段：{item.chunk_id}）"
            for item in citations[:3]
        )
        return f"根据 FlowPilot 知识库，关于“{message}”可参考：\n{evidence}"

    async def answer_with_trace(
        self, message: str, top_k: int
    ) -> tuple[str, list[Citation], LLMResult]:
        evidence = self.retrieve_evidence(message, top_k)
        citations = evidence.citations
        if not citations:
            return (
                self.demo_answer(message, citations),
                citations,
                LLMResult(None, "demo", True, "evidence_threshold", 0),
            )
        result = await self.llm.complete(
            "你是 FlowPilot 产品运营 Copilot。仅依据资料用中文准确回答；信息不足时明确说明，并保留事实边界。",
            message,
            citations,
        )
        return result.content or self.demo_answer(message, citations), citations, result

    async def answer(self, message: str, top_k: int) -> tuple[str, list[Citation]]:
        answer, citations, _ = await self.answer_with_trace(message, top_k)
        return answer, citations
