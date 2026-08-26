import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.models import InsightGap, InsightsResponse, LowScoreInsight


class InsightsService:
    """将本地任务、检索 Trace 和反馈聚合为可解释的知识治理信号。"""

    def build(self, tasks: list[dict[str, Any]], feedback: list[dict[str, Any]]) -> InsightsResponse:
        task_by_id = {task["id"]: task for task in tasks}
        feedback_by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
        feedback_by_question: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in feedback:
            if item.get("task_id"):
                feedback_by_task[item["task_id"]].append(item)
            feedback_by_question[self._normalize(item.get("message", ""))].append(item)

        gaps: dict[str, dict[str, float | int]] = {}
        low_scores: list[LowScoreInsight] = []
        for task in tasks:
            task_feedback = feedback_by_task.get(task["id"], [])
            if not task_feedback:
                task_feedback = feedback_by_question.get(self._normalize(task.get("input", "")), [])
            trace = task.get("trace", {})
            retrieval = trace.get("retrieval", {})
            generation = trace.get("generation", {})
            top_score = float(retrieval.get("top_score", 0.0))
            fallback_used = bool(generation.get("fallback_used", task.get("mode") == "demo"))
            ratings = [float(item["rating"]) for item in task_feedback]
            low_feedback = [rating for rating in ratings if rating <= 2]
            average_rating = sum(ratings) / len(ratings) if ratings else None
            reason = self._reason(average_rating, top_score, fallback_used, len(task.get("citations", [])))
            if average_rating is not None and average_rating < 3:
                low_scores.append(
                    LowScoreInsight(
                        task_id=task["id"],
                        question=task.get("input", "未记录问题"),
                        score=round(average_rating, 1),
                        reason=reason,
                        created_at=task.get("created_at", ""),
                        fallback_used=fallback_used,
                    )
                )

            topic = self._topic(task.get("input", ""))
            signal = gaps.setdefault(topic, {"queries": 0, "scores": 0.0, "low": 0, "fallback": 0, "empty": 0})
            signal["queries"] = int(signal["queries"]) + 1
            signal["scores"] = float(signal["scores"]) + top_score
            signal["low"] = int(signal["low"]) + len(low_feedback)
            signal["fallback"] = int(signal["fallback"]) + int(fallback_used)
            signal["empty"] = int(signal["empty"]) + int(not task.get("citations"))

        ranked_gaps: list[tuple[float, InsightGap]] = []
        for topic, signal in gaps.items():
            query_count = int(signal["queries"])
            average_top_score = round(float(signal["scores"]) / query_count, 4) if query_count else 0.0
            low_feedback_count = int(signal["low"])
            score = low_feedback_count * 3 + int(signal["empty"]) * 2 + int(signal["fallback"]) + max(0, 1 - average_top_score)
            priority = "高" if score >= 4 else "中" if score >= 2 else "低"
            ranked_gaps.append(
                (
                    score,
                    InsightGap(
                        topic=topic,
                        query_count=query_count,
                        average_top_score=average_top_score,
                        low_feedback_count=low_feedback_count,
                        priority=priority,
                    ),
                )
            )
        low_scores.sort(key=lambda item: (item.score, item.created_at))
        ranked_gaps.sort(key=lambda item: (-item[0], -item[1].query_count, item[1].topic))
        return InsightsResponse(gaps=[item[1] for item in ranked_gaps[:5]], low_scores=low_scores[:8])

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", "", text).lower()

    @staticmethod
    def _topic(text: str) -> str:
        cleaned = re.sub(r"[？?！!。；;，,、]", " ", text).strip()
        return cleaned[:28] or "未命名问题"

    @staticmethod
    def _reason(
        average_rating: float | None, top_score: float, fallback_used: bool, citation_count: int
    ) -> str:
        if citation_count == 0:
            return "未检索到可引用证据"
        if top_score < 0.18:
            return "检索相关性偏低，建议补充或修订知识"
        if fallback_used:
            return "云模型未返回可用结果，已使用本地规则降级"
        if average_rating is not None and average_rating < 3:
            return "用户评分偏低，建议复核引用与表达"
        return "待结合更多反馈复核"
