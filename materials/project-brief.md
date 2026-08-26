# FlowPilot Copilot｜AI 产品运营智能体

## 1. 项目定位

FlowPilot Copilot 是一个面向 SaaS 产品运营、客服与知识管理员的本地可运行 RAG + 受控 Agent MVP。它把产品文档、FAQ、客服工单和运营规范转成可检索知识，在同一工作台内完成知识问答、客服回复草稿、用户反馈分析和运营活动策划；每次生成都返回执行步骤与引用证据，反馈和评估结果可继续沉淀到质量闭环。

**它不是“上传文件后聊天”的页面 Demo，而是把知识导入、检索、任务路由、结构化生成、反馈和离线回归串成一条可解释链路。**

---

## 2. 解决的问题与范围

### 2.1 面向的真实问题

1. **资料分散、口径不一致**：客服、产品和运营分别查 FAQ、工单和规则文档，回复质量依赖个人经验。
2. **生成结果不可追溯**：只展示 LLM 正文时，用户无法判断结论是否有资料依据。
3. **任务形态不止问答**：客服回复、反馈归纳、运营策划需要不同格式的交付物，不能只靠一套泛化 Prompt。
4. **质量无法闭环**：没有用户反馈和最小回归集，就无法持续发现知识缺口与检索退化。

### 2.2 MVP 的边界

- 面向单机演示与面试展示，不接入真实企业生产数据。
- Agent 只生成建议、草稿和结构化方案，**不调用外部系统执行发消息、改数据或发布活动等副作用操作**。
- 使用本地 TF-IDF + BM25 检索和 JSON 持久化，重点展示链路可解释性与工程取舍，不宣称已具备生产级多租户能力。

---

## 3. 总体技术架构

```text
┌─────────────────────────────────────────────────────────────────┐
│ React 18 + TypeScript + Vite                                    │
│ 工作台 / 知识资产 / 质量评估 / 运营洞察                         │
└───────────────────────┬─────────────────────────────────────────┘
                        │ HTTP + JSON
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ FastAPI + Pydantic API Layer                                    │
│ 文档导入 | 对话 | Agent 任务 | 反馈 | 评估 | 看板 | 运行检查   │
└───────┬──────────────────┬───────────────────────┬──────────────┘
        │                  │                       │
        ▼                  ▼                       ▼
┌──────────────┐  ┌──────────────────────┐  ┌─────────────────────┐
│ JsonStore    │  │ LocalTfidfRetriever  │  │ AgentService        │
│ RLock +      │  │ 切分 / 分词 /        │  │ 显式路由 / 专用      │
│ 临时文件原子 │  │ TF-IDF + BM25 / RRF  │  │ Prompt / 结构化产物 │
│ 替换         │  │ Top-K Citation       │  └──────────┬──────────┘
└──────────────┘  └──────────┬───────────┘             │
                              │                         ▼
                              │              ┌─────────────────────┐
                              └─────────────►│ LLMClient           │
                                             │ OpenAI-compatible   │
                                             │ 云模型 / 本地规则    │
                                             │ 降级                │
                                             └─────────────────────┘

LangChain Core 适配层：Document + RunnableLambda，封装 retrieve → generate 链路
```

**核心技术栈**：React 18、TypeScript、Vite、FastAPI、Pydantic、httpx、LangChain Core、pytest。前端生产构建输出到 `frontend/release-dist`，由 FastAPI 静态托管。

---

## 4. 功能与技术路线对应

| 业务功能 | 前端交互与页面 | 后端接口 | 核心实现 | 返回结果与数据沉淀 | 当前边界 |
|---|---|---|---|---|---|
| 智能工作台 | 输入问题、选择任务类型、查看产物/步骤/引用/Trace | `POST /api/agent/tasks` | `AgentService.execute()`：路由 → 共享证据门槛 → 检索 → 生成 → 专用 Artifact | `intent`、`steps`、`artifacts`、`citations`、原始候选/门槛判定/请求配置/版本与反馈快照写入任务 Trace | 不执行外部动作，仅生成建议或草稿；低相关候选不会交给模型 |
| 知识问答 | Copilot 对话、引用展开 | `POST /api/chat` | `CopilotService.answer()` 调用共享 `retrieve_evidence()`，只把通过门槛的 Top-K 证据传入模型 | `answer`、`mode`、`citations`；会话计数 +1 | 不是语义向量检索；低于证据门槛时明确拒答 |
| LangChain 链路验证 | 可调用框架化 RAG 接口 | `POST /api/langchain/chat` | `Document` 承载检索结果；`RunnableLambda` 组成 `retrieve → generate` | 框架链路结果；会话计数 +1 | 真实使用 LangChain Core，未使用 LangGraph |
| 客服回复草稿 | 工作台选择“客服回复” | `POST /api/agent/tasks` | `customer_reply` Prompt + 引用事实提取 + 规则降级模板 | 主题、回复正文、处理要点、引用 | 文案须人工审核；不会声称已核查账户或订单 |
| 用户反馈分析 | 工作台选择“用户研究” | `POST /api/agent/tasks` | 读取最近最多 20 条本地反馈；`Counter` 聚合分类与均分；模型输出总体判断 | 总结、分类分布、低分发现、建议 | 样本是本地 Demo/运行数据，非生产用户样本 |
| 运营活动策划 | 工作台选择“运营策划” | `POST /api/agent/tasks` | `campaign_plan` Prompt + 固定结构化字段 | 目标人群、价值主张、渠道、节奏、指标、A/B 实验建议 | 不会自动建活动、发消息或归因 |
| 文本知识导入 | 知识资产页输入文本 | `POST /api/documents/import` | 校验非空 → `JsonStore.add_document()` → 全量重建检索索引 | 文档摘要、片段数，文档写入本地状态 | 索引全量重建，适合小规模单机资料 |
| 文件知识导入 | 上传文件 | `POST /api/documents/upload` | 支持 UTF-8 `.txt` / `.md` / `.csv`，以及可提取文本的 `.pdf` / `.docx`；统一复用导入和索引重建链路 | 文档摘要、片段数 | 2MB 上限；扫描件 PDF 不含 OCR，不做病毒扫描或异步解析 |
| 知识资产查看 | 文档清单与分类 | `GET /api/documents` | 根据检索器 `chunk_counts()` 关联文档与切片数 | 文档 ID、来源、分类、创建时间、片段数 | 无文档权限、版本管理和删除流程 |
| 回答质量反馈 | 点赞/点踩、输入反馈内容 | `GET /api/feedback`、`POST /api/feedback` | Pydantic 校验后生成反馈 ID 和时间戳，并关联 `task_id` 写入 JSON 状态 | 反馈可关联具体任务，供洞察、看板和反馈分析复用 | 无登录身份、用户归因或人工工单流转 |
| 离线评估中心 | 运行评估、查看每条 Case 结果 | `POST /api/evaluation` | 同一 20 条 Golden Dataset 分别运行 TF-IDF、BM25 融合 RRF；离线评估固定用检索证据生成确定性答案 | Baseline/Hybrid 命中、Source Recall@K、MRR、关键词召回、拒答正确率、引用正确性、规则忠实度、待复核主张 | 规则式 Citation/Faithfulness 为可解释 MVP，不等同人工标注或 LLM Judge |
| Agent 任务历史与回放 | 按意图/降级状态筛选、查看完整 Trace、切换策略重跑 | `GET /api/agent/tasks`、`GET /api/agent/tasks/{task_id}`、`POST /api/agent/tasks/{task_id}/replay` | JSON MVP 中倒序、筛选、limit/cursor 分页；回放读取原任务输入并可覆盖检索策略/Top-K，生成新任务并记录 `replay_of` | 输入、意图、耗时、检索策略、Top-1、原始候选、门槛、模型/Prompt 版本、实际 Prompt、反馈快照、重跑关联 | 历史数据量大时应迁移数据库；老任务缺少上下文时使用兼容默认值，无法还原原始配置 |
| 运营洞察与复盘 | 查看待补知识信号、低分任务 | `GET /api/insights`、`GET /api/agent/tasks/{task_id}` | `InsightsService` 聚合任务、检索分数、模型降级和关联反馈 | 高频/低分/低置信信号、低分复盘队列、任务 Trace | 规则式单机聚合，不是线上主题模型或全量 BI |
| 数据看板 | 文档、片段、反馈、会话、任务数等指标 | `GET /api/dashboard/metrics` | 从 `JsonStore.snapshot()` 与检索器实时聚合 | 文档数、片段数、反馈数、均分、会话数、任务数、分类分布 | 当前不含用户身份、分群和时间窗口分析 |
| 运行可观测与健康检查 | 监控容器/进程是否可服务 | `GET /api/health/live`、`GET /api/health/ready`、`GET /api/metrics` | 标准库 JSON 日志、进程内请求计数/延迟直方图、存活与就绪检查；前端真实写请求 60 秒超时覆盖后端 45 秒模型调用超时 | 请求量、状态码、路径、P50/P95 延迟、错误数与服务就绪状态 | 指标和日志均为单进程 MVP，不是集中式可观测平台 |
| 轻量 API 保护 | 高频调用时返回明确等待提示 | API 中间件 | 客户端 IP 的线程安全固定窗口内存计数；响应附带 `Retry-After` 与 `X-Request-Latency-Ms` | 超限 `429`、等待秒数、请求耗时 | 默认每 IP 60 秒 120 次；多副本下必须迁移 Redis 等共享限流 |
| Docker 单机交付 | 用一个命令构建并启动完整产品 | `docker compose up --build -d` | 前端 Node 多阶段构建 + Python slim 运行镜像；非 root 用户；命名卷持久化运行状态；Compose 健康检查；显式 `name: flowpilot` 兼容中文目录 | 已在本机 Docker Desktop 构建镜像并启动；`flowpilot-data` 命名卷创建，`/api/health/ready` 返回 200 | 当前配置适合单机/演示，不代表多实例生产部署 |

---

## 5. 关键技术实现

### 5.1 本地可解释 RAG：从导入文档到引用证据

文档导入后执行以下路径：

```text
文本 / UTF-8 文件
  → 格式、编码、大小校验
  → JSON Store 持久化
  → 段落与中文句子边界切分（chunk_size=260, overlap=40）
  → 中英文词项 Tokenize
  → TF-IDF 余弦基线召回 + BM25 词频召回
  → Reciprocal Rank Fusion（RRF）融合排序
  → Citation(source / chunk_id / score / chunk)
  → 对外保留 TF-IDF 相关度；由 `EVIDENCE_THRESHOLD`（默认 0.1）统一判断 Top-1 是否达到证据门槛
  → LLM Prompt 与前端引用展示
```

检索器 `LocalTfidfRetriever` 的实现取舍：

- **切分**：先按段落和句子边界拆分，再使用重叠窗口避免上下文在边界被截断。
- **中文分词基线**：保留中文单字与连续 bigram，同时保留英文、数字和下划线词项，适配套餐名、错误码、功能字段等知识库内容。
- **双路召回**：对 Query 与每个 Chunk 分别计算 TF-IDF 余弦分和 BM25 分；两路都不依赖外部服务。
- **融合排序**：使用 Reciprocal Rank Fusion 将两路排名合并，避免直接相加不同量纲的相似度分数；默认取 RRF Top-K。
- **分数语义**：RRF 与 BM25 的内部得分只用于排序，对外的 `Citation.score` 统一保留 TF-IDF 余弦分，因此 Trace 与 UI 百分比始终表示同一相关度，而不是融合权重。
- **统一门槛**：`CopilotService.retrieve_evidence()` 是 Agent 与普通问答共用的证据边界；Agent 任务 Trace 会保存原始候选和判定，门槛未通过时不将弱相关片段发送给 LLM。
- **任务边界**：该门槛约束知识库事实注入；`feedback_analysis` 仍可基于本地反馈快照生成分析，`campaign_plan` 仍可返回待人工审核的通用模板，两者不代表知识库事实已被证实。
- **可解释性**：每条引用保留来源、片段 ID、分数和文本；前端将引用与答案分开展示，避免把“模型结论”和“原始证据”混在一起。

选择 TF-IDF + BM25 的原因是无需外部向量服务、结果稳定、适合关键词密集的 SaaS 产品资料，也能确保断网时可演示。它仍无法解决全部语义召回问题，因此生产升级方向是 Embedding + 向量库、Reranker、元数据过滤与查询改写。

### 5.2 受控 Agent：显式路由，而非自由工具调用

Agent 支持四种意图：

- `knowledge_qa`：基于知识库直接问答；
- `customer_reply`：生成需人工审核的客服回复草稿；
- `feedback_analysis`：汇总站内反馈、低分问题和分类分布；
- `campaign_plan`：生成结构化运营活动方案。

一次 Agent 请求的执行路径：

```text
前端提交 input + intent + top_k
  → intent 非 auto 时直接采用显式类型
  → auto 时用关键词评分路由
  → LocalTfidfRetriever.search()
  → 按任务类型拼装 System Prompt 与用户上下文
  → LLMClient.complete()
  → 根据 intent 输出专用 artifacts
  → 生成可展示的 steps 与 citations
  → JsonStore.add_agent_task()
```

这样设计的目的不是追求“完全自主”，而是在企业知识场景优先保证稳定、可审计和可演示。路由、检索、生成、交付物格式都可被观察；外部写操作留给后续审批节点处理。

### 5.3 模型适配与失败降级

`LLMClient` 使用 OpenAI-compatible Chat Completions 协议，通过 `.env` 配置模型地址、密钥和模型名；当前本地云模式接入小米 MiMo 普通 API 的 `mimo-v2.5-pro`，使用 `sk-` Key 与 `https://api.xiaomimimo.com/v1`，最小请求实测返回 HTTP 200。若使用 Token Plan，则应改为对应的 `tp-` Key 与 `https://token-plan-cn.xiaomimimo.com/v1`。小米的 Anthropic 兼容地址暂未接入，因为当前适配器只实现了 OpenAI Chat Completions 请求格式。

- **云模式**：用 `httpx.AsyncClient(timeout=45)` 请求 `/chat/completions`，将检索引用注入 Prompt 后生成任务结果。
- **Demo 模式**：未配置 API Key 时，返回基于检索事实组织的确定性回答/客服草稿/方案。
- **云端异常降级**：网络、HTTP、JSON 解析或响应结构异常均被捕获并记录 warning；`complete()` 返回包含 `fallback_used`、`error_type` 和 `latency_ms` 的结构化结果，上层根据同一批检索证据构造确定性 Artifact，避免上游模型异常直接造成 Agent 接口 HTTP 500。

这不是前端伪造请求成功：写接口仍是真实后端处理；降级状态会在 Agent 执行步骤中显示“本地规则已生成降级产物”。

### 5.4 LangChain Core 的实际使用范围

项目没有用框架替代底层检索实现，而是保留可讲解的自研检索器，再在 `langchain_adapter.py` 中完成适配：

- 将检索结果转换为 `langchain_core.documents.Document`；
- 用两个 `RunnableLambda` 组成 `flowpilot_retrieve | flowpilot_generate`；
- 通过 `/api/langchain/chat` 暴露可调用的 `retrieve → generate` 链路。

**事实边界**：当前真实使用的是 LangChain Core 的 `Document` 与 Runnable；没有实现 LangGraph 状态图、向量数据库、Reranker 或框架 Agent 工具调用。

### 5.5 本地持久化与并发写入保护

`JsonStore` 用于 MVP 的文档、反馈、Agent 任务和会话计数持久化：

1. 进程内通过 `threading.RLock` 保护状态读写；
2. 保存时先写临时 `.tmp` 文件；
3. 再通过 `replace()` 原子替换状态文件，降低写入中断导致文件损坏的概率。

该方案降低了演示环境部署复杂度，但不适合多实例并发、复杂查询、权限隔离和大规模文档管理。生产版应迁移到 PostgreSQL、Redis、对象存储和异步解析队列。

### 5.6 运行可交付性：容器、日志、健康检查与轻量保护

第 2 批把应用从“本机可启动”推进到“可复现交付的单机服务”：

```text
Docker Compose
  → 前端 Node 22 多阶段构建（npm ci → Vite release-dist）
  → Python 3.13 slim 运行镜像（非 root flowpilot 用户）
  → FastAPI / Uvicorn :8011
  → /api/health/live、/api/health/ready
  → 标准输出 JSON 请求日志 + /api/metrics 进程内快照
  → flowpilot-data 命名卷保存 state.json
```

- **状态卷隔离**：Compose 把 `DATA_FILE` 指向 `/app/runtime-data/state.json` 并只挂载该目录，而不是覆盖 `backend/data`。这样首启仍能读取镜像内 `seed.json` 与版本化评估集，后续导入文档、反馈和任务记录则写入命名卷，容器重建不丢失。
- **健康检查**：`/api/health/live` 只判断进程是否响应；`/api/health/ready` 在服务初始化后确认依赖的本地服务对象可用。Compose 使用就绪端点作为容器健康检查。
- **结构化日志和指标**：请求日志以单行 JSON 输出，记录方法、路径、状态码与耗时。`/api/metrics` 返回单进程的请求总量、错误数、限流数、路径/状态分布、P50/P95/最大延迟和运行时长，且每个响应带 `X-Request-Latency-Ms`。
- **轻量限流**：仅覆盖 `/api/`，按客户端 IP 在内存中固定窗口计数。默认每 IP 每 60 秒 120 次；超限返回 `429`、`Retry-After` 和中文原因。设 `RATE_LIMIT=0` 可以关闭以便本地压测。

这些能力用于单机 Demo 的交付稳定性，而不是生产级运维平台：日志没有集中采集，指标没有持久化，限流也不跨实例共享。未来多副本部署时应接入 OpenTelemetry/集中日志、Prometheus 或云监控，并用 Redis 等共享限流状态。

---

## 6. 质量闭环与数据真实性

### 6.1 当前可运行的版本化评估

默认加载 `backend/data/evaluation/core_product_qa.v1.json` 中的 **20 条**回归用例，覆盖价格、计费、上手流程、集成故障、安全权限、客服工单、运营规范与资料外问题。每个 Case 可标注期望关键词、正确来源和是否应拒答。一次离线评估会在同一份 Case 上对照 TF-IDF 基线与 Hybrid RRF；为排除云模型耗时、费用和随机性干扰，评估回答固定由当轮检索证据生成确定性文本。

- **Retrieval Hit Rate**：是否检索到 Top-1 TF-IDF 分数不低于 `EVIDENCE_THRESHOLD`（默认 0.1）的证据；
- **Source Recall@K / MRR**：正确来源是否进入 Top-K，以及首次命中的排名质量；
- **Average Keyword Recall**：确定性回答中命中期望关键词的比例；
- **Refusal Accuracy**：资料外问题是否返回明确的信息不足提示；
- **Citation Correctness**：引用来源中符合该 Case 标注来源的比例；
- **Faithfulness**：回答主张与引用片段存在词项证据覆盖的比例，并返回待人工复核的无支持主张。

其中 Citation Correctness 与 Faithfulness 是可解释的规则 MVP，不使用不稳定的 LLM Judge，也不等同人工标注结论。即使某次结果较高，也只能说明该版本化回归集通过，**不能外推为生产环境准确率或业务效果提升**。

### 6.2 数据分层与前端降级边界

1. **内置 Seed 数据**：产品文档、FAQ、客服工单、运营规范和反馈均是为 Demo 场景构造的合成资料。
2. **本地运行状态**：本机导入文档、Agent 任务、反馈、会话数会写入 `backend/data/state.json`，反映当前实例的真实操作记录。
3. **后端实时指标**：文档数、Chunk 数、反馈数、平均评分、会话数、任务数和文档分类分布由 `/api/dashboard/metrics` 实时聚合。
4. **真实质量信号**：`/api/insights` 按 `task_id` 关联反馈与任务，综合低分反馈、引用数量、Top-1 检索分数和模型降级状态生成待补知识信号与低分复盘队列；这是规则式单机聚合，不伪装为线上 BI 或主题模型。
5. **只读接口降级**：前端读取接口不可用时可用 `mockData.ts` 保持页面可浏览；Agent、导入、反馈、评估等写操作不静默 Mock，失败会显式提示。

---

## 7. 已实现能力与未实现边界

| 已实现 | 明确未实现 / 后续方向 |
|---|---|
| React 工作台与深浅主题、任务选择、引用和结构化结果展示 | 用户登录、RBAC、租户隔离（出现多角色/多客户业务需求后实施） |
| FastAPI REST API、Pydantic 请求/响应校验、单进程固定窗口限流 | Redis 共享限流、鉴权、生产审计日志 |
| 自研中文 TF-IDF + BM25 双路召回、RRF 融合和可解释引用分数 | Embedding、向量数据库、Reranker |
| 4 类受控 Agent、专用 Artifact、可筛选任务历史、Trace 上下文与可切换策略重跑 | LangGraph 检查点、状态机、人工审批节点（出现跨步骤审批需求后实施） |
| OpenAI-compatible 模型适配、后端规则降级与延迟/错误 Trace | 多模型路由、成本预算、模型 A/B 实验 |
| JSON 原子写入、文档/反馈/任务/会话沉淀、Compose 命名卷持久化 | PostgreSQL、Redis、对象存储、异步解析 |
| JSON 标准输出日志、live/ready 健康检查、进程内 `/api/metrics` | 集中日志、分布式 Trace、跨实例监控告警 |
| 20 条版本化 Golden Dataset、TF-IDF/RRF 对照、关键词召回、Source Recall@K、MRR、拒答正确率、规则 Citation Correctness/Faithfulness | 人工标注评估、LLM Judge、线上 P95/成本指标 |
| 文本、UTF-8 txt/md/csv、可提取文本 PDF/DOCX 导入 | OCR、病毒扫描、异步文件处理（出现扫描件和批量导入需求后实施） |
| 关联反馈的规则式 Insights、低分任务队列与任务详情回放 | 线上主题聚类、用户分群、全量 BI |
| Docker Compose 单机部署：多阶段构建、非 root 运行、状态卷与容器健康检查 | Kubernetes、多实例滚动发布、集中密钥管理 |

---

## 8. 本地运行与验证

### 8.1 启动服务

在项目根目录执行：

```bash
backend/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8011
```

打开：

- 应用：`http://127.0.0.1:8011`
- 健康检查：`http://127.0.0.1:8011/api/health`
- 存活检查：`http://127.0.0.1:8011/api/health/live`
- 就绪检查：`http://127.0.0.1:8011/api/health/ready`
- 运行指标：`http://127.0.0.1:8011/api/metrics`
- API 文档：`http://127.0.0.1:8011/docs`

前端由 FastAPI 从 `frontend/release-dist` 托管。云模式是否启用取决于 `.env` 中是否存在有效的 OpenAI-compatible 模型配置；无密钥时仍可进入 Demo 模式完成完整链路演示。

### 8.2 Docker Compose 交付

```bash
copy backend/.env.example backend/.env
docker compose up --build -d
docker compose ps
docker compose logs -f flowpilot
```

Compose 仅暴露 `127.0.0.1:8011`，并用 `flowpilot-data` 命名卷保存运行状态。停止应用使用 `docker compose down`；该命令不会删除命名卷。Docker Compose 已于本机 Docker Desktop（Linux 容器模式）完成镜像构建与启动验证：单服务容器通过 `127.0.0.1:8011` 提供服务，`/api/health/ready` 就绪检查返回 200，`flowpilot-data` 命名卷已创建，容器重建不会丢失运行状态。

### 8.3 回归验证口径

```bash
backend/.venv/Scripts/python.exe -m pytest backend/tests -q
```

当前已验证：**26 项 pytest 用例通过**。覆盖云模型不可达时的结构化降级、Hybrid RRF 检索排序、共享证据门槛与拒答、Agent Trace 上下文、任务筛选分页与可配置重跑、反馈关联后的真实 Insights、20 条版本化评估集、规则 Citation/Faithfulness、DOCX 文本导入，以及 live/ready 健康检查、进程内指标和轻量限流。

---

## 9. 生产化迭代顺序

1. **已完成数据真实性基线**：真实 Insights、关联反馈、版本化 Golden Dataset、共享证据门槛和可配置任务重跑。
2. **继续升级检索与评估**：已完成 BM25 / RRF 与规则 Citation/Faithfulness；下一步先用现有评估集验证 Embedding 或 Reranker 的真实增益，再补人工标注评估与线上 P95/成本指标。
3. **按业务需求升级 Agent 与平台能力**：跨步骤审批出现后再引入 LangGraph 工作流和人工审批；扫描件/批量导入出现后再补 OCR 与异步队列；多角色或多客户需求出现后再做认证、RBAC 与租户隔离。
4. **工程交付持续收口**：已补根 `.gitignore`、README、GitHub Actions CI、Docker Compose、健康检查、结构化日志、单进程指标与轻量限流；后续按实际发布环境补镜像仓库、密钥轮换、集中监控和多实例部署。
