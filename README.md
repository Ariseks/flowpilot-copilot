# FlowPilot Copilot

面向 SaaS 产品运营、客服与知识管理员的本地可运行 RAG + 受控 Agent MVP。

## 已实现能力

- 双路混合检索：中文 TF-IDF 与 BM25 独立召回，使用 RRF 融合排序；对外保留可解释的 TF-IDF 相关度分数与引用证据；
- 四类受控 Agent：知识问答、客服回复、用户反馈分析、运营活动策划；
- OpenAI-compatible 模型适配：无 Key 的本地确定性 Demo 与云模型失败降级；
- 真实质量闭环：任务 Trace、可筛选任务历史与单任务回放、评分关联 `task_id`、低分任务复盘、待补知识信号；
- 版本化 Golden Dataset：20 条核心产品/支持/拒答回归题，对照 TF-IDF 基线与 Hybrid RRF，并提供关键词召回、来源命中、MRR、拒答正确率、引用正确性与规则忠实度；
- 文档导入：文本、TXT、MD、CSV、可提取文本的 PDF 与 DOCX；
- React + TypeScript 前端、FastAPI API、JSON MVP 持久化、LangChain Core Runnable 适配；
- Docker Compose 单机交付：多阶段前端构建、非 root 运行镜像、运行状态命名卷、存活/就绪检查、结构化日志、进程内指标和轻量限流。

## 项目结构

```text
backend/       FastAPI、RAG、Agent、评估、Trace、数据文件和测试
frontend/      React + TypeScript + Vite 产品界面
materials/     项目介绍与技术说明（project-brief.md）
```

## 快速启动

### 1. 后端环境

```bash
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
copy backend/.env.example backend/.env
```

留空 `LLM_API_KEY` 即使用 deterministic Demo 模式；当前默认示例配置为小米 MiMo 的 OpenAI-compatible API（`mimo-v2.5-pro`），配置匹配的 Key 后将尝试使用云模型，异常时会保留检索证据并使用后端规则降级。注意：Token Plan 地址需要对应的 `tp-` Key；普通 `sk-` Key 应使用小米普通 API 地址。Anthropic 兼容地址暂未接入当前 OpenAI Chat Completions 适配器。

### 2. 构建前端

```bash
cd frontend
npm install
npm run build
```

前端构建产物位于 `frontend/release-dist`，由 FastAPI 静态托管。

### 3. 启动服务

```bash
backend/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8011
```

- 应用：<http://127.0.0.1:8011>
- API 文档：<http://127.0.0.1:8011/docs>
- 健康检查：<http://127.0.0.1:8011/api/health>
- 存活检查：<http://127.0.0.1:8011/api/health/live>
- 就绪检查：<http://127.0.0.1:8011/api/health/ready>
- 运行指标：<http://127.0.0.1:8011/api/metrics>

### 4. Docker Compose 启动

项目根目录已提供 `Dockerfile`、`docker-compose.yml` 和 `.dockerignore`。Dockerfile 使用多阶段构建：第一阶段执行前端 `npm ci` 和生产构建，第二阶段安装后端依赖并由非 root 用户运行 Uvicorn。

```bash
copy backend/.env.example backend/.env
docker compose up --build -d
```

容器启动后访问：

- 应用：<http://127.0.0.1:8011>
- 就绪检查：<http://127.0.0.1:8011/api/health/ready>
- 运行指标：<http://127.0.0.1:8011/api/metrics>

运行状态写入 Compose 命名卷 `flowpilot-data`，容器重建不会丢失导入文档、反馈和 Agent 任务；镜像内的 `backend/data/seed.json` 与评估集保持为只读初始资料。查看状态和日志：

```bash
docker compose ps
docker compose logs -f flowpilot
docker compose down
```

Compose 默认将宿主机端口绑定到 `127.0.0.1:8011`。容器模式下 `DATA_FILE` 固定为 `/app/runtime-data/state.json`；`RATE_LIMIT` 默认每个客户端每 60 秒 120 次 API 请求，设为 `0` 可关闭。该限流器是单进程内存固定窗口，多实例部署应迁移到 Redis 等共享存储。

## 回归测试

```bash
backend/.venv/Scripts/python.exe -m pytest backend/tests -q
```

前端构建：

```bash
cd frontend
npm run build
```

## 重要边界

- JSON 状态适用于单机 MVP，不支持多实例并发、复杂查询、权限隔离；
- PDF 仅处理可提取文本的文件，扫描件/图片型 PDF 未接 OCR；
- Agent 只生成草稿和结构化建议，不执行外部写操作；
- 当前使用 LangChain Core 的 `Document` 与 Runnable，未使用 LangGraph；
- 当前检索为 TF-IDF + BM25 的 RRF 融合；仍未实现 Embedding 向量数据库、Reranker 与生产级权限过滤；
- 内置评估集用于回归验证，不代表真实线上业务准确率；
- 当前运行日志为标准输出 JSON，`/api/metrics` 为单进程内存快照；两者适合单机演示，不替代集中式日志、链路追踪和生产级监控；
- Docker Compose 已于本机 Docker Desktop（Linux 容器模式）完成首次镜像构建与启动验证；当前单服务容器通过 `127.0.0.1:8011` 提供访问，健康检查通过。Compose 顶层显式设置 `name: flowpilot`，避免中文项目目录在当前 Compose 版本中被解析为空项目名。

完整的技术路线与功能对应关系见 [materials/project-brief.md](materials/project-brief.md)。
