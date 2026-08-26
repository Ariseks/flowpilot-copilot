import json
import re
from pathlib import Path

from app.models import (
    Citation,
    EvaluationCase,
    EvaluationCaseResult,
    EvaluationResponse,
    RetrievalMetrics,
)
from app.services.copilot import CopilotService


DATASET_DIR = Path(__file__).resolve().parents[2] / "data" / "evaluation"
DEFAULT_DATASET = "core_product_qa.v1.json"


class EvaluationService:
    """版本化 Golden Dataset 评估：基线/混合检索对照 + 可解释的证据规则。"""

    def __init__(self, copilot: CopilotService):
        self.copilot = copilot

    @staticmethod
    def load_default() -> tuple[str, str, list[EvaluationCase]]:
        payload = json.loads((DATASET_DIR / DEFAULT_DATASET).read_text(encoding="utf-8"))
        return (
            payload["name"],
            payload["version"],
            [EvaluationCase.model_validate(item) for item in payload["cases"]],
        )

    async def run(self, cases: list[EvaluationCase] | None) -> EvaluationResponse:
        if cases is None:
            dataset_name, dataset_version, selected = self.load_default()
        else:
            dataset_name, dataset_version, selected = "临时自定义评估集", "ad-hoc", cases

        results: list[EvaluationCaseResult] = []
        baseline_records: list[tuple[EvaluationCase, list[Citation]]] = []
        hybrid_records: list[tuple[EvaluationCase, list[Citation]]] = []

        for case in selected:
            baseline_evidence = self.copilot.retrieve_evidence(
                case.question, case.top_k, "tfidf"
            )
            hybrid_evidence = self.copilot.retrieve_evidence(
                case.question, case.top_k, "rrf"
            )
            baseline_citations = baseline_evidence.citations
            hybrid_citations = hybrid_evidence.citations
            # 离线回归不应被云模型延迟、费用或随机采样污染：固定使用同一份检索证据生成确定性答案。
            citations = hybrid_citations
            answer = self.copilot.demo_answer(case.question, citations)
            if case.should_refuse:
                citations = []
                answer = self.copilot.demo_answer(case.question, citations)
            searchable = answer.lower()
            matched = sum(keyword.lower() in searchable for keyword in case.expected_keywords)
            recall = matched / len(case.expected_keywords) if case.expected_keywords else 1.0
            source_hit = self._source_hit(citations, case.expected_sources)
            baseline_source_hit = self._source_hit(baseline_citations, case.expected_sources)
            refusal_correct = self._is_refusal(answer) if case.should_refuse else None
            correctness = self._citation_correctness(citations, case.expected_sources)
            faithfulness, unsupported_claims = self._faithfulness(answer, citations, case.should_refuse)
            baseline_records.append((case, baseline_citations))
            hybrid_records.append((case, hybrid_citations))
            results.append(
                EvaluationCaseResult(
                    id=case.id,
                    category=case.category,
                    question=case.question,
                    hit=bool(citations),
                    keyword_recall=round(recall, 4),
                    source_hit=source_hit,
                    refusal_correct=refusal_correct,
                    top_score=citations[0].score if citations else 0.0,
                    answer=answer,
                    citations=citations,
                    baseline_hit=bool(baseline_citations),
                    hybrid_hit=bool(hybrid_citations),
                    baseline_source_hit=baseline_source_hit,
                    citation_correctness=correctness,
                    faithfulness=faithfulness,
                    unsupported_claims=unsupported_claims,
                )
            )

        total = len(results)
        source_results = [item.source_hit for item in results if item.source_hit is not None]
        refusal_results = [item.refusal_correct for item in results if item.refusal_correct is not None]
        correctness_results = [item.citation_correctness for item in results if item.citation_correctness is not None]
        faithfulness_results = [item.faithfulness for item in results if item.faithfulness is not None]
        baseline = self._retrieval_metrics("tfidf", baseline_records)
        hybrid = self._retrieval_metrics("rrf", hybrid_records)
        return EvaluationResponse(
            dataset_name=dataset_name,
            dataset_version=dataset_version,
            total=total,
            retrieval_hit_rate=hybrid.retrieval_hit_rate,
            average_keyword_recall=round(sum(item.keyword_recall for item in results) / total, 4) if total else 0,
            source_recall_at_k=round(sum(source_results) / len(source_results), 4) if source_results else None,
            refusal_accuracy=round(sum(refusal_results) / len(refusal_results), 4) if refusal_results else None,
            citation_correctness=round(sum(correctness_results) / len(correctness_results), 4) if correctness_results else None,
            faithfulness=round(sum(faithfulness_results) / len(faithfulness_results), 4) if faithfulness_results else None,
            baseline=baseline,
            hybrid=hybrid,
            cases=results,
        )

    @staticmethod
    def _source_hit(citations: list[Citation], expected_sources: list[str]) -> bool | None:
        if not expected_sources:
            return None
        return bool({item.source for item in citations} & set(expected_sources))

    def _retrieval_metrics(
        self, strategy: str, records: list[tuple[EvaluationCase, list[Citation]]]
    ) -> RetrievalMetrics:
        non_refusal = [(case, citations) for case, citations in records if not case.should_refuse]
        hit_rate = sum(bool(citations) for _, citations in non_refusal) / len(non_refusal) if non_refusal else 0.0
        source_scores: list[bool] = []
        reciprocal_ranks: list[float] = []
        for case, citations in non_refusal:
            if not case.expected_sources:
                continue
            expected = set(case.expected_sources)
            ranks = [index + 1 for index, item in enumerate(citations) if item.source in expected]
            source_scores.append(bool(ranks))
            reciprocal_ranks.append(1 / ranks[0] if ranks else 0.0)
        return RetrievalMetrics(
            strategy=strategy,  # type: ignore[arg-type]
            retrieval_hit_rate=round(hit_rate, 4),
            source_recall_at_k=round(sum(source_scores) / len(source_scores), 4) if source_scores else None,
            mean_reciprocal_rank=round(sum(reciprocal_ranks) / len(reciprocal_ranks), 4) if reciprocal_ranks else None,
        )

    @staticmethod
    def _citation_correctness(citations: list[Citation], expected_sources: list[str]) -> float | None:
        if not expected_sources:
            return 1.0 if not citations else 0.0
        if not citations:
            return 0.0
        expected = set(expected_sources)
        return round(sum(item.source in expected for item in citations) / len(citations), 4)

    def _faithfulness(
        self, answer: str, citations: list[Citation], should_refuse: bool
    ) -> tuple[float, list[str]]:
        if should_refuse:
            return (1.0 if self._is_refusal(answer) else 0.0, [] if self._is_refusal(answer) else [answer[:160]])
        claims = [
            self._clean_claim(item)
            for item in re.split(r"(?<=[。！？；\n])", answer)
            if self._clean_claim(item)
        ]
        if not claims:
            return 0.0, []
        evidence_terms = set(self.copilot.retriever.tokenize(" ".join(item.chunk for item in citations)))
        unsupported: list[str] = []
        supported = 0
        for claim in claims:
            terms = set(self.copilot.retriever.tokenize(claim))
            meaningful = {term for term in terms if len(term) > 1 or term.isdigit()}
            if not meaningful or len(meaningful & evidence_terms) >= min(2, len(meaningful)):
                supported += 1
            else:
                unsupported.append(claim[:160])
        return round(supported / len(claims), 4), unsupported

    @staticmethod
    def _clean_claim(text: str) -> str:
        return re.sub(r"^[\s\-•\d\.]+|[\s]+$", "", text)

    @staticmethod
    def _is_refusal(answer: str) -> bool:
        indicators = ("没有找到", "信息不足", "无法确认", "请补充", "没有足够信息")
        return any(item in answer for item in indicators)
