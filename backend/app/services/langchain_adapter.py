from typing import Any

from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda, RunnableSerializable

from app.services.copilot import CopilotService
from app.services.rag import LocalTfidfRetriever


class LangChainRagService:
    """Expose the explainable local retriever through LangChain Runnable primitives."""

    def __init__(self, retriever: LocalTfidfRetriever, copilot: CopilotService):
        self.retriever = retriever
        self.copilot = copilot
        self.chain: RunnableSerializable[Any, Any] = (
            RunnableLambda(self._retrieve).with_config(run_name="flowpilot_retrieve")
            | RunnableLambda(self._generate).with_config(run_name="flowpilot_generate")
        )

    def _retrieve(self, payload: dict[str, Any]) -> dict[str, Any]:
        message = str(payload["message"])
        top_k = int(payload.get("top_k", 4))
        citations = self.retriever.search(message, top_k)
        documents = [
            Document(
                page_content=item.chunk,
                metadata={
                    "source": item.source,
                    "chunk_id": item.chunk_id,
                    "score": item.score,
                },
            )
            for item in citations
        ]
        return {"message": message, "top_k": top_k, "citations": citations, "documents": documents}

    async def _generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        citations = payload["citations"]
        result = await self.copilot.llm.complete(
            "你是 FlowPilot 产品运营 Copilot。仅依据检索文档回答，证据不足时明确说明，并保留引用事实边界。",
            payload["message"],
            citations,
        )
        answer = result.content or self.copilot.demo_answer(payload["message"], citations)
        return {
            "answer": answer,
            "mode": self.copilot.llm.mode,
            "framework": "langchain-core",
            "fallback_used": result.fallback_used,
            "documents": [
                {"page_content": doc.page_content, "metadata": doc.metadata}
                for doc in payload["documents"]
            ],
            "citations": [item.model_dump() for item in citations],
        }

    async def invoke(self, message: str, top_k: int = 4) -> dict[str, Any]:
        return await self.chain.ainvoke({"message": message, "top_k": top_k})
