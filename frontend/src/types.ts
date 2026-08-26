export type PageId = 'copilot' | 'workflow' | 'knowledge' | 'evaluation' | 'insights'

export type StepStatus = 'done' | 'running' | 'pending'

export interface AgentStep {
  id: string
  title: string
  detail: string
  status: StepStatus
  duration?: string
}

export interface Citation {
  id: string
  source: string
  section: string
  excerpt: string
  score: number
}

export interface AgentTrace {
  timing: { total_ms: number; retrieve_ms: number; generate_ms: number }
  retrieval: { citation_count: number; top_score: number; strategy?: 'tfidf' | 'bm25' | 'rrf' }
  generation: { mode: 'demo' | 'cloud'; provider_used: 'demo' | 'cloud'; fallback_used: boolean; error_type?: string | null; model?: string | null }
}

export interface CopilotAnswer {
  id: string
  question: string
  taskType: string
  summary: string
  bullets: string[]
  nextAction: string
  steps: AgentStep[]
  citations: Citation[]
  trace?: AgentTrace
}

export interface TaskHistoryItem {
  id: string
  input: string
  intent: 'knowledge_qa' | 'customer_reply' | 'feedback_analysis' | 'campaign_plan'
  createdAt: string
  trace: AgentTrace
}

export interface KnowledgeSource {
  id: string
  name: string
  type: string
  status: 'ready' | 'syncing' | 'warning'
  chunks: number
  updatedAt: string
  owner: string
}

export interface DashboardMetric {
  label: string
  value: string
  change: string
  trend: 'up' | 'down' | 'neutral'
  hint: string
}

export interface GapItem {
  topic: string
  queries: number
  coverage: number
  priority: '高' | '中' | '低'
}

export interface LowScoreItem {
  taskId?: string
  question: string
  score: number
  reason: string
  time: string
  fallbackUsed?: boolean
}

export interface DashboardData {
  metrics: DashboardMetric[]
  categories: Array<{ label: string; value: number; color: string }>
  gaps: GapItem[]
  lowScores: LowScoreItem[]
}

export interface EvaluationCaseDetail {
  id?: string
  category: string
  question: string
  hit: boolean
  keywordRecall: number
  sourceHit?: boolean | null
  refusalCorrect?: boolean | null
  citationCorrectness?: number | null
  faithfulness?: number | null
  unsupportedClaims: string[]
}

export interface EvaluationSet {
  id: string
  name: string
  cases: number
  lastRun: string
  status: 'passed' | 'running' | 'draft'
  accuracy: number
  groundedness: number
  helpfulness: number
  sourceRecall?: number
  refusalAccuracy?: number
  citationCorrectness?: number
  faithfulness?: number
  baselineHitRate?: number
  baselineSourceRecall?: number
  baselineMrr?: number
  hybridMrr?: number
  datasetVersion?: string
  evaluationMethod?: string
  caseDetails?: EvaluationCaseDetail[]
}
