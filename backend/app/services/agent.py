import re
import time
from collections import Counter
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.models import AgentIntent, AgentStep, Citation, RetrievalStrategy
from app.services.copilot import CopilotService
from app.services.llm import LLMResult


class AgentService:
    PROMPT_VERSION = "agent-v1"
    TRACE_PROMPT_LIMIT = 4000
    TRACE_FEEDBACK_MESSAGE_LIMIT = 500

    ROUTES: dict[AgentIntent, tuple[str, ...]] = {
        "customer_reply": ("客服", "回复", "投诉", "工单", "客户", "道歉"),
        "feedback_analysis": ("反馈", "分析", "洞察", "聚类", "痛点", "满意度"),
        "campaign_plan": ("活动", "运营", "推广", "转化", "召回", "campaign"),
        "knowledge_qa": (),
    }

    SYSTEM_PROMPTS: dict[AgentIntent, str] = {
        "knowledge_qa": (
            "你是 FlowPilot 产品知识助手。仅根据可用资料，用中文直接回答问题。"
            "不要复制大段原文，不要重复列出关键事实，不要使用 Markdown 标题或表格，不要在正文中写来源编号；"
            "引用由界面单独展示。信息不足时明确说明。回答控制在180字以内。"
        ),
        "customer_reply": (
            "你是 FlowPilot 客服助手。根据资料直接生成一份可发送前需人工审核的中文客服回复草稿。"
            "回复应包含问题确认、简洁解释、明确处理步骤和必要的补充信息请求。不要复制知识库原文，"
            "不要在正文中展示检索过程、来源编号或内部分析，不承诺资料未说明的能力。"
            "禁止声称已经核查账户、订单或系统状态，因为当前工具没有执行核查；只能说根据现有资料判断。控制在220字以内。"
        ),
        "feedback_analysis": (
            "你是 FlowPilot 产品运营分析助手。结合用户任务、站内反馈摘要和可用资料，用中文输出一段总体判断。"
            "只总结最重要的现象和优先方向，不重复逐条反馈，不使用 Markdown 标题、列表或表格。"
            "区分事实与推断，不虚构样本规模或效果数据。控制在180字以内；详细发现和建议由系统结构化展示。"
        ),
        "campaign_plan": (
            "你是 FlowPilot SaaS 产品运营助手。根据任务和资料，用中文概括一个可执行运营活动的目标与核心策略。"
            "不要使用 Markdown 标题、列表或表格，不要重复系统将单独展示的人群、渠道、节奏和指标。"
            "不承诺未上线能力，不虚构时长、样本量、显著性阈值或历史效果。控制在180字以内。"
        ),
    }

    def __init__(self, copilot: CopilotService):
        self.copilot = copilot

    def route(self, text: str, requested: str) -> AgentIntent:
        if requested != "auto":
            return requested  # type: ignore[return-value]
        scores = {
            intent: sum(keyword in text.lower() for keyword in keywords)
            for intent, keywords in self.ROUTES.items()
            if intent != "knowledge_qa"
        }
        best_intent = max(scores, key=scores.get)  # type: ignore[arg-type]
        return best_intent if scores[best_intent] > 0 else "knowledge_qa"

    async def execute(
        self,
        text: str,
        requested_intent: str,
        top_k: int,
        feedback: list[dict[str, Any]],
        retrieval_strategy: RetrievalStrategy | None = None,
        replay_of: str | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        intent = self.route(text, requested_intent)
        selected_strategy = retrieval_strategy or self.copilot.retriever.default_strategy
        retrieval_started = time.perf_counter()
        evidence = self.copilot.retrieve_evidence(text, top_k, selected_strategy)
        raw_citations = evidence.raw_citations
        citations = evidence.citations
        retrieve_ms = round((time.perf_counter() - retrieval_started) * 1000)
        user_prompt = self._user_prompt(intent, text, feedback)
        generation = (
            LLMResult(None, "demo", True, "evidence_threshold", 0)
            if not citations
            else await self.copilot.llm.complete(
                self.SYSTEM_PROMPTS[intent], user_prompt, citations
            )
        )
        artifacts = self._artifacts(intent, text, generation.content, citations, feedback)
        steps = [
            AgentStep(name="意图路由", detail=f"识别为 {intent}"),
            AgentStep(
                name="知识检索",
                detail=(
                    f"证据门槛拒答：原始候选 {len(raw_citations)} 个，"
                    f"Top-1 {raw_citations[0].score:.2f} < {evidence.threshold:.2f}"
                    if not citations and raw_citations
                    else f"本地 {evidence.status} 命中 {len(citations)} 个片段"
                ),
            ),
            AgentStep(
                name="产物生成",
                detail=(
                    f"云模型已生成 {artifacts['type']} 产物"
                    if generation.content
                    else f"本地规则已生成 {artifacts['type']} {'拒答' if not citations else '降级'}产物"
                ),
            ),
        ]
        return {
            "id": f"task-{uuid4().hex[:12]}",
            "input": text,
            "intent": intent,
            "status": "completed",
            "mode": self.copilot.effective_mode(generation),
            "steps": [step.model_dump() for step in steps],
            "artifacts": artifacts,
            "citations": [item.model_dump() for item in citations],
            "trace": {
                "timing": {
                    "total_ms": round((time.perf_counter() - started) * 1000),
                    "retrieve_ms": retrieve_ms,
                    "generate_ms": generation.latency_ms,
                },
                "retrieval": {
                    "citation_count": len(citations),
                    "raw_citation_count": len(raw_citations),
                    "top_score": raw_citations[0].score if raw_citations else 0.0,
                    "strategy": selected_strategy,
                    "evidence_threshold": evidence.threshold,
                    "evidence_status": evidence.status,
                    "candidates": [item.model_dump() for item in raw_citations],
                },
                "generation": {
                    "mode": self.copilot.effective_mode(generation),
                    "provider_used": generation.provider_used,
                    "fallback_used": generation.fallback_used,
                    "error_type": generation.error_type,
                    "model": self.copilot.llm.settings.llm_model if generation.provider_used == "cloud" else None,
                    "generator_version": (
                        self.copilot.llm.settings.llm_model
                        if generation.provider_used == "cloud"
                        else "deterministic-demo-v1"
                    ),
                    "prompt_version": self.PROMPT_VERSION,
                    "system_prompt": self.SYSTEM_PROMPTS[intent],
                    "user_prompt": user_prompt[: self.TRACE_PROMPT_LIMIT],
                    "context_chunk_ids": [item.chunk_id for item in citations],
                },
                "request": {
                    "requested_intent": requested_intent,
                    "top_k": top_k,
                    "retrieval_strategy": selected_strategy,
                },
                "feedback_context": self._feedback_context(feedback),
                "replay_of": replay_of,
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _user_prompt(intent: AgentIntent, text: str, feedback: list[dict[str, Any]]) -> str:
        if intent != "feedback_analysis":
            return text
        feedback_summary = "\n".join(
            f"- 评分 {item['rating']}/5，类别 {item['category']}：{item['message']}"
            for item in feedback[-20:]
        )
        return f"分析任务：{text}\n\n站内反馈摘要：\n{feedback_summary or '暂无站内反馈'}"

    @staticmethod
    def _feedback_context(feedback: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "id": item["id"],
                "message": item["message"][: AgentService.TRACE_FEEDBACK_MESSAGE_LIMIT],
                "rating": item["rating"],
                "category": item["category"],
                "user": item.get("user", "演示用户"),
                "task_id": item.get("task_id"),
                "created_at": item["created_at"],
            }
            for item in feedback[-20:]
        ]

    def _artifacts(
        self,
        intent: AgentIntent,
        text: str,
        generated: str | None,
        citations: list[Citation],
        feedback: list[dict[str, Any]],
    ) -> dict[str, Any]:
        facts = self._relevant_facts(text, citations)
        if intent == "knowledge_qa":
            answer = generated or self._demo_knowledge_answer(facts)
            return {
                "type": "knowledge_answer",
                "answer": answer,
                "key_points": facts[:3],
            }
        if intent == "customer_reply":
            reply = generated or self._demo_customer_reply(facts)
            return {
                "type": "customer_reply",
                "subject": "FlowPilot 问题处理建议",
                "reply": reply,
                "handling_notes": facts[:2],
            }
        if intent == "feedback_analysis":
            categories = Counter(item["category"] for item in feedback)
            average = (
                round(sum(item["rating"] for item in feedback) / len(feedback), 2)
                if feedback
                else 0.0
            )
            return {
                "type": "feedback_report",
                "summary": self._clean_generated(generated)
                or f"结合 {len(feedback)} 条本地反馈完成分析，当前主要问题集中在错误定位、计费解释和模板需求。",
                "average_rating": average,
                "category_distribution": dict(sorted(categories.items())),
                "top_findings": self._feedback_findings(feedback, facts),
                "recommendations": [
                    "优先优化字段级错误提示与失败定位",
                    "在账单页解释任务运行计数并展示明细",
                    "按反馈频次评估模板和流程管理需求",
                ],
            }
        return {
            "type": "campaign_plan",
            "name": f"FlowPilot 运营活动：{text[:30]}",
            "summary": self._clean_generated(generated)
            or "面向尚未发布首个流程的试用用户，使用模板案例和产品内引导完成7天激活触达。",
            "audience": "未发布首个流程或试用期内的团队用户",
            "value_proposition": "用模板快速发布首个自动化流程，直观看到效率收益",
            "channels": ["站内信", "生命周期邮件", "产品内引导"],
            "schedule": ["第1天价值触达", "第3天模板案例", "第7天转化提醒"],
            "metrics": ["首个流程发布率", "7日留存率", "试用转付费率"],
            "experiment": "A/B测试价值导向与效率导向标题",
        }

    def _relevant_facts(self, text: str, citations: list[Citation]) -> list[str]:
        query_terms = set(self.copilot.retriever.tokenize(text))
        candidates: list[tuple[int, int, str]] = []
        seen: set[str] = set()
        for citation_index, citation in enumerate(citations):
            sentences = re.split(r"(?<=[。！？；])", citation.chunk)
            for sentence_index, sentence in enumerate(sentences):
                cleaned = sentence.strip(" -\n")
                if not cleaned or cleaned in seen:
                    continue
                seen.add(cleaned)
                overlap = len(query_terms & set(self.copilot.retriever.tokenize(cleaned)))
                candidates.append((overlap, -(citation_index * 100 + sentence_index), cleaned))
        candidates.sort(reverse=True)
        return [item[2][:160] for item in candidates[:4]]

    @staticmethod
    def _clean_generated(text: str | None) -> str | None:
        if not text:
            return None
        cleaned = re.sub(r"^#{1,6}\s*", "", text.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned[:700].strip()

    @staticmethod
    def _demo_knowledge_answer(facts: list[str]) -> str:
        if not facts:
            return "当前知识库没有足够信息回答这个问题，请补充问题细节或导入相关资料。"
        return "根据当前知识库：\n" + "\n".join(f"{index + 1}. {fact}" for index, fact in enumerate(facts[:3]))

    @staticmethod
    def _demo_customer_reply(facts: list[str]) -> str:
        if not facts:
            return (
                "您好，感谢您的反馈。目前资料不足以确认问题原因。"
                "请提供工作区名称、问题发生时间和相关截图，我们会进一步核查。"
            )
        steps = "；".join(fact.rstrip("。；") for fact in facts[:2])
        return (
            "您好，感谢您的反馈。我们已了解您遇到的问题。"
            f"根据当前产品规则，{steps}。"
            "建议您先按上述方式处理；如果问题仍未解决，请提供工作区名称、问题发生时间和相关截图，我们会继续核查。"
        )

    @staticmethod
    def _feedback_findings(feedback: list[dict[str, Any]], facts: list[str]) -> list[str]:
        low_rated = sorted(feedback, key=lambda item: item["rating"])
        findings = [
            f"{item['category']}：{item['message']}（评分 {item['rating']}/5）"
            for item in low_rated[:3]
        ]
        return findings or facts[:3]
