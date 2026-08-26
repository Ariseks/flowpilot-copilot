from app.models import Citation
from app.services.llm import LLMClient, LLMResult
from app.services.rag import LocalTfidfRetriever


class CopilotService:
    def __init__(self, retriever: LocalTfidfRetriever, llm: LLMClient):
        self.retriever = retriever
        self.llm = llm

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
        citations = self.retriever.search(message, top_k)
        # RRF 排序沿用 TF-IDF 相似度作为 Citation.score；低分结果仍是无关片段，按原边界拒答。
        if not citations or citations[0].score < 0.1:
            citations = []
        result = await self.llm.complete(
            "你是 FlowPilot 产品运营 Copilot。仅依据资料用中文准确回答；信息不足时明确说明，并保留事实边界。",
            message,
            citations,
        )
        return result.content or self.demo_answer(message, citations), citations, result

    async def answer(self, message: str, top_k: int) -> tuple[str, list[Citation]]:
        answer, citations, _ = await self.answer_with_trace(message, top_k)
        return answer, citations
