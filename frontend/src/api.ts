import { dashboardData, knowledgeSources } from './mockData'
import type { AgentStep, AgentTrace, Citation, CopilotAnswer, DashboardData, EvaluationCaseDetail, EvaluationSet, GapItem, KnowledgeSource, LowScoreItem, TaskHistoryItem, TaskReplay, RetrievalStrategy } from './types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || window.location.origin
const REQUEST_TIMEOUT = 60000

export type DataSource = 'api' | 'mock'
export type DataResult<T> = { data: T; source: DataSource; error?: string }
export type HealthStatus = { status: string; mode: 'demo' | 'cloud'; rag_framework: string; documents: number; chunks: number }

type BackendCitation = { source: string; chunk: string; score: number; chunk_id: string }
type BackendStep = { name: string; status: 'completed'; detail: string }
type BackendTrace = AgentTrace
type BackendTask = { id: string; input: string; intent: 'knowledge_qa' | 'customer_reply' | 'feedback_analysis' | 'campaign_plan'; steps: BackendStep[]; artifacts: Record<string, unknown>; citations: BackendCitation[]; trace: BackendTrace; created_at: string }
type BackendTaskList = { items: BackendTask[]; total: number; next_cursor?: string | null }
type BackendDocument = { id: string; title: string; source: string; category: string; created_at: string; chunk_count: number }
type BackendMetrics = { documents: number; chunks: number; feedback_count: number; average_rating: number; chat_count: number; agent_task_count: number; document_categories: Record<string, number>; mode: 'demo' | 'cloud' }
type BackendInsights = { gaps: Array<{ topic: string; query_count: number; average_top_score: number; low_feedback_count: number; priority: '高' | '中' | '低' }>; low_scores: Array<{ task_id?: string | null; question: string; score: number; reason: string; created_at: string; fallback_used: boolean }> }
type BackendEvaluationCase = { id?: string; category: string; question: string; hit: boolean; keyword_recall: number; source_hit?: boolean | null; refusal_correct?: boolean | null; citation_correctness?: number | null; faithfulness?: number | null; unsupported_claims: string[] }
type BackendEvaluation = {
  dataset_name: string; dataset_version: string; total: number; retrieval_hit_rate: number; average_keyword_recall: number
  source_recall_at_k?: number | null; refusal_accuracy?: number | null; citation_correctness?: number | null; faithfulness?: number | null
  baseline: { retrieval_hit_rate: number; source_recall_at_k?: number | null; mean_reciprocal_rank?: number | null }
  hybrid: { retrieval_hit_rate: number; source_recall_at_k?: number | null; mean_reciprocal_rank?: number | null }
  evaluation_method: string; cases: BackendEvaluationCase[]
}

export class ApiError extends Error {
  status?: number
  constructor(message: string, status?: number) { super(message); this.name = 'ApiError'; this.status = status }
}

function errorMessage(error: unknown): string {
  if (error instanceof DOMException && error.name === 'AbortError') return '请求超时，请确认后端服务是否运行'
  if (error instanceof Error) return error.message
  return '未知 API 错误'
}

function mapCitations(items: BackendCitation[]): Citation[] {
  return items.map((item) => ({ id: item.chunk_id, source: item.source, section: `知识片段 ${item.chunk_id}`, excerpt: item.chunk, score: item.score }))
}

function mapTask(task: BackendTask, question: string, taskType: string): CopilotAnswer {
  const artifact = task.artifacts
  const citations = mapCitations(task.citations)
  const answerText = String(artifact.answer || artifact.reply || artifact.summary || '')
  const findings = Array.isArray(artifact.top_findings) ? artifact.top_findings.map(String) : []
  const keyPoints = Array.isArray(artifact.key_points) ? artifact.key_points.map(String) : []
  const recommendations = Array.isArray(artifact.recommendations) ? artifact.recommendations.map(String) : []
  const campaignBullets = [artifact.audience, artifact.value_proposition, artifact.experiment].filter(Boolean).map(String)
  const bullets = task.intent === 'customer_reply' ? [] : findings.length ? findings.slice(0, 3) : keyPoints.length ? keyPoints.slice(0, 3) : task.intent === 'campaign_plan' ? campaignBullets : []
  const summary = answerText || (task.intent === 'campaign_plan' ? String(artifact.summary || `已生成「${String(artifact.name || 'FlowPilot 运营活动')}」方案，覆盖目标人群、价值主张、触达节奏和衡量指标。`) : '已基于企业知识库完成检索与分析。')
  const nextAction = recommendations[0] || (task.intent === 'customer_reply' ? '请人工复核客户身份、套餐状态和处理步骤后再发送。' : '') || (Array.isArray(artifact.metrics) ? `建议上线前确认指标：${artifact.metrics.map(String).join('、')}` : '') || '建议结合引用原文复核关键事实，再进入执行环节。'
  const steps: AgentStep[] = task.steps.map((step, index) => ({ id: `${task.id}-step-${index}`, title: step.name, detail: step.detail, status: 'done', duration: index === 1 ? `${task.trace.timing.retrieve_ms}ms` : index === 2 ? `${task.trace.timing.generate_ms}ms` : '规则节点' }))
  return { id: task.id, question, taskType, summary, bullets, nextAction, steps, citations, trace: task.trace }
}

function mapHistoryTask(task: BackendTask): TaskHistoryItem { return { id: task.id, input: task.input, intent: task.intent, createdAt: task.created_at, trace: task.trace } }
function mapReplay(task: BackendTask): TaskReplay { return { id: task.id, input: task.input, intent: task.intent, artifacts: task.artifacts, citations: mapCitations(task.citations), trace: task.trace, createdAt: task.created_at } }
function mapDocument(item: BackendDocument): KnowledgeSource { return { id: item.id, name: item.title, type: item.category, status: 'ready', chunks: item.chunk_count, updatedAt: new Date(item.created_at).toLocaleDateString('zh-CN'), owner: item.source.startsWith('用户') ? '运营管理员' : 'FlowPilot 团队' } }
function mapDocuments(items: BackendDocument[]): KnowledgeSource[] { return items.map(mapDocument) }

function mapDashboard(data: BackendMetrics): DashboardData {
  const categoryEntries = Object.entries(data.document_categories)
  const categoryTotal = categoryEntries.reduce((sum, [, value]) => sum + value, 0) || 1
  const colors = ['#f15a36', '#3157f6', '#c9f45b', '#8877c9', '#5c8d89']
  return { metrics: [
    { label: 'Copilot 会话', value: String(data.chat_count), change: '实时', trend: 'neutral', hint: '本地运行状态' },
    { label: 'Agent 任务', value: String(data.agent_task_count), change: '实时', trend: 'neutral', hint: '结构化工作流' },
    { label: '知识片段', value: String(data.chunks), change: `${data.documents} 个来源`, trend: 'up', hint: '本地检索索引' },
    { label: '平均反馈', value: data.average_rating ? `${data.average_rating}/5` : '待收集', change: `${data.feedback_count} 条`, trend: 'neutral', hint: '本地用户反馈' },
  ], categories: categoryEntries.map(([label, value], index) => ({ label, value: Math.round(value / categoryTotal * 100), color: colors[index % colors.length] })), gaps: [], lowScores: [] }
}

function mapInsights(result: BackendInsights): { gaps: GapItem[]; lowScores: LowScoreItem[] } {
  return { gaps: result.gaps.map((item) => ({ topic: item.topic, queries: item.query_count, coverage: Math.round(item.average_top_score * 100), priority: item.priority })), lowScores: result.low_scores.map((item) => ({ taskId: item.task_id || undefined, question: item.question, score: item.score, reason: item.reason, time: new Date(item.created_at).toLocaleString('zh-CN'), fallbackUsed: item.fallback_used })) }
}

const percent = (value: number | null | undefined) => value == null ? undefined : Math.round(value * 1000) / 10
function mapEvaluation(result: BackendEvaluation): EvaluationSet[] {
  const accuracy = percent(result.average_keyword_recall) || 0
  const groundedness = percent(result.hybrid.retrieval_hit_rate) || 0
  const measures = [accuracy, groundedness, percent(result.citation_correctness), percent(result.faithfulness)].filter((item): item is number => item !== undefined)
  const caseDetails: EvaluationCaseDetail[] = result.cases.map((item) => ({ id: item.id, category: item.category, question: item.question, hit: item.hit, keywordRecall: percent(item.keyword_recall) || 0, sourceHit: item.source_hit, refusalCorrect: item.refusal_correct, citationCorrectness: percent(item.citation_correctness), faithfulness: percent(item.faithfulness), unsupportedClaims: item.unsupported_claims }))
  return [{
    id: 'live-evaluation', name: result.dataset_name, cases: result.total, lastRun: '刚刚', status: 'passed', accuracy, groundedness,
    helpfulness: Math.round((measures.reduce((sum, item) => sum + item, 0) / measures.length) * 10) / 10,
    sourceRecall: percent(result.hybrid.source_recall_at_k), refusalAccuracy: percent(result.refusal_accuracy), citationCorrectness: percent(result.citation_correctness), faithfulness: percent(result.faithfulness),
    baselineHitRate: percent(result.baseline.retrieval_hit_rate), baselineSourceRecall: percent(result.baseline.source_recall_at_k), baselineMrr: percent(result.baseline.mean_reciprocal_rank), hybridMrr: percent(result.hybrid.mean_reciprocal_rank), datasetVersion: result.dataset_version, evaluationMethod: result.evaluation_method, caseDetails,
  }]
}

async function request<T>(path: string, options?: RequestInit, timeoutMs = REQUEST_TIMEOUT): Promise<T> {
  const controller = new AbortController(); const timeout = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, { ...options, signal: controller.signal, headers: { 'Content-Type': 'application/json', ...options?.headers } })
    if (!response.ok) { const payload = await response.json().catch(() => ({})) as { detail?: string }; throw new ApiError(payload.detail || `API 请求失败 (${response.status})`, response.status) }
    return (await response.json()) as T
  } finally { window.clearTimeout(timeout) }
}
async function readWithFallback<T>(apiCall: () => Promise<T>, fallback: T): Promise<DataResult<T>> { try { return { data: await apiCall(), source: 'api' } } catch (error) { return { data: fallback, source: 'mock', error: errorMessage(error) } } }

const intentMap: Record<string, BackendTask['intent'] | 'auto'> = { '运营诊断': 'feedback_analysis', '数据分析': 'feedback_analysis', '内容生成': 'campaign_plan', '运营策划': 'campaign_plan', '活动策划': 'campaign_plan', '用户研究': 'feedback_analysis', '客服回复': 'customer_reply', '知识问答': 'knowledge_qa' }

export const apiClient = {
  getHealth: () => request<HealthStatus>('/api/health'),
  getDashboard: () => readWithFallback(async () => mapDashboard(await request<BackendMetrics>('/api/dashboard/metrics')), dashboardData),
  getInsights: () => request<BackendInsights>('/api/insights').then(mapInsights),
  getKnowledgeSources: () => readWithFallback(async () => mapDocuments(await request<BackendDocument[]>('/api/documents')), knowledgeSources),
  getEvaluationSets: () => request<BackendEvaluation>('/api/evaluation', { method: 'POST', body: JSON.stringify({}) }, 30000).then(mapEvaluation),
  runEvaluation: () => request<BackendEvaluation>('/api/evaluation', { method: 'POST', body: JSON.stringify({}) }, 30000).then(mapEvaluation),
  getAgentTasks: async (filters?: { limit?: number; cursor?: number; intent?: string; fallbackUsed?: boolean }) => {
    const params = new URLSearchParams()
    if (filters?.limit) params.set('limit', String(filters.limit))
    if (filters?.cursor) params.set('cursor', String(filters.cursor))
    if (filters?.intent) params.set('intent', filters.intent)
    if (filters?.fallbackUsed !== undefined) params.set('fallback_used', String(filters.fallbackUsed))
    const data = await request<BackendTaskList>(`/api/agent/tasks${params.size ? `?${params.toString()}` : ''}`)
    return { items: data.items.map(mapHistoryTask), total: data.total, nextCursor: data.next_cursor || undefined }
  },
  getAgentTask: (taskId: string) => request<BackendTask>(`/api/agent/tasks/${taskId}`),
  replayAgentTask: async (taskId: string, options?: { retrievalStrategy?: RetrievalStrategy; topK?: number }) => mapReplay(await request<BackendTask>(`/api/agent/tasks/${taskId}/replay`, { method: 'POST', body: JSON.stringify({ retrieval_strategy: options?.retrievalStrategy, top_k: options?.topK }) })),
  askCopilot: async (question: string, taskType: string) => mapTask(await request<BackendTask>('/api/agent/tasks', { method: 'POST', body: JSON.stringify({ input: question, intent: intentMap[taskType] || 'auto', top_k: 4 }) }), question, taskType),
  submitFeedback: (taskId: string, message: string, helpful: boolean) => request<{ id: string }>('/api/feedback', { method: 'POST', body: JSON.stringify({ task_id: taskId, message, rating: helpful ? 5 : 2, category: 'copilot_answer', user: '演示用户' }) }),
  importText: async (name: string, content: string) => mapDocument(await request<BackendDocument>('/api/documents/import', { method: 'POST', body: JSON.stringify({ title: name, text: content, source: `用户导入/${name}`, category: '用户导入' }) })),
  importFile: async (file: File) => {
    const controller = new AbortController(); const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT)
    try { const body = new FormData(); body.append('file', file); const response = await fetch(`${API_BASE_URL}/api/documents/upload`, { method: 'POST', body, signal: controller.signal }); if (!response.ok) { const payload = await response.json().catch(() => ({})) as { detail?: string }; throw new ApiError(payload.detail || `文件导入失败 (${response.status})`, response.status) }; return mapDocument(await response.json() as BackendDocument) } finally { window.clearTimeout(timeout) }
  },
}
