# FlowPilot Copilot｜简历项目描述

## 项目名称

**FlowPilot Copilot｜SaaS 产品运营 RAG Agent**

技术栈：React、TypeScript、FastAPI、Pydantic、LangChain Core、OpenAI-compatible API、TF-IDF、pytest

## 精简版（适合一页简历）

- 独立设计并实现 SaaS 产品运营 Copilot，围绕产品文档、FAQ、客服工单构建可追溯 RAG 问答，支持来源片段与相关度展示。
- 设计受控 Agent 路由，覆盖知识问答、客服回复、反馈分析、活动策划 4 类业务任务，以结构化输出和人工确认边界提升可控性。
- 建立“知识导入—检索生成—引用核验—用户反馈—离线评估—知识优化”闭环，完成 5 个产品模块及 11 个后端自动化测试。
- 实现 OpenAI-compatible 云模型与无密钥 Demo 双模式；前端 API 异常时可显式降级，降低现场演示对网络与外部服务的依赖。

## 详细版（适合项目经历展开）

- 针对 SaaS 团队知识分散、回答不可追溯和低质量结果难运营的问题，完成需求拆解、信息架构、技术方案和全栈 MVP，实现 Copilot、Agent 工作流、知识库、评估中心、运营洞察 5 个模块。
- 自主实现中文段落/句子切分、重叠窗口、中文字符/bigram 与英文词项处理、TF-IDF 余弦 top-k 检索，返回 `source/chunk_id/score` 证据链；使用 LangChain Core `Document` 与 Runnable 适配为 `retrieve → generate` 标准链路，并为 Embedding、混合检索和 Reranker 预留边界。
- 基于“规则/显式选择优先”的受控路由编排 4 类 Agent 任务，避免完全自主工具调用带来的随机性和副作用；客服、反馈和活动任务返回可校验的结构化产物。
- 使用 FastAPI + Pydantic 构建知识导入、对话、Agent、反馈、评估和运营指标 API；文本导入后自动重建索引，前端点赞/点踩真实写入反馈数据。
- 通过 OpenAI-compatible Adapter 解耦模型供应商，无 Key 时使用确定性回答保证离线可演示；完成 11 个 pytest 用例并通过 TypeScript/Vite 生产构建。

## 面试实测后可补的量化项

只在你亲自跑过并保存结果后填写：

- 在 `[测试集数量]` 条 Golden Questions 上实现 Retrieval Hit Rate `[实测后填写]%`、关键词召回 `[实测后填写]%`。
- P50/P95 端到端响应耗时分别为 `[实测后填写]s / [实测后填写]s`。
- 接入 Embedding + Reranker 后，Recall@k 相比 TF-IDF 基线提升 `[实测后填写]%`。
- 通过缓存和上下文裁剪将单次请求 token 成本降低 `[实测后填写]%`。

## 30 秒项目介绍

“我做的是一个面向 SaaS 产品运营团队的 RAG Agent，不是普通 PDF Chat。系统把产品文档、FAQ、工单和运营规范做成可追溯知识库，再通过受控路由完成知识问答、客服回复、反馈分析和活动策划。每次回答都展示引用，用户反馈会进入评估和知识缺口闭环。MVP 用 React + FastAPI，自实现可解释检索并用 LangChain Core 适配标准 RAG 链路，通过模型适配层支持云 API；下一步会用 LangGraph、混合检索、Reranker 和可观测链路做生产化。”

## 表述红线

- 可以写“使用 LangChain Core 适配 RAG Runnable 链路”；不写“已使用 LangGraph”，当前代码没有该依赖。
- 不写“向量数据库”，当前 MVP 是本地 TF-IDF 索引。
- 不写未经实测的准确率、效率提升和用户数量。
- 可以强调你理解框架应放在哪里、为什么当前先做可解释基线、如何演进到生产架构。
