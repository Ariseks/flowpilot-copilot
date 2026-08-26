import { FormEvent, ReactNode, useEffect, useLayoutEffect, useRef, useState } from 'react'
import gsap from 'gsap'
import { apiClient } from './api'
import { dashboardData as initialDashboard, knowledgeSources as initialSources } from './mockData'
import { Icon } from './icons'
import type { CopilotAnswer, DashboardData, EvaluationSet, KnowledgeSource, PageId, RetrievalStrategy, TaskHistoryItem, TaskReplay } from './types'

const navigation: Array<{ id: PageId; label: string; index: string }> = [
  { id: 'copilot', label: '智能工作台', index: '01' },
  { id: 'workflow', label: 'Agent 流程', index: '02' },
  { id: 'knowledge', label: '知识资产', index: '03' },
  { id: 'evaluation', label: '质量评估', index: '04' },
  { id: 'insights', label: '运营洞察', index: '05' },
]

const pageMeta: Record<PageId, { eyebrow: string; title: string; description: string }> = {
  copilot: { eyebrow: 'AI OPERATIONS STUDIO', title: '把业务问题，推进成下一步行动。', description: '检索团队知识，调度受控 Agent，并把每次回答沉淀成可优化的产品信号。' },
  workflow: { eyebrow: 'CONTROLLED AGENTS', title: '让 Agent 自主，但不失控。', description: '用明确意图、固定节点和结构化产物，把复杂任务变成可审计流程。' },
  knowledge: { eyebrow: 'KNOWLEDGE ASSET', title: '知识不是文件夹，是产品能力。', description: '让每条产品规则、客服经验和运营规范都可检索、可引用、可治理。' },
  evaluation: { eyebrow: 'EVALUATE, THEN SHIP', title: '没有评估集，就没有可靠的 RAG。', description: '分开测量检索、引用和回答，定位问题到底发生在哪一层。' },
  insights: { eyebrow: 'FEEDBACK TO SIGNAL', title: '把用户反馈变成迭代优先级。', description: '观察使用、知识缺口和低分问题，让 Copilot 越用越准确。' },
}

const prompts = [
  { tag: 'RAG 问答', text: '专业版的任务运行次数怎么计算？额度用完后会怎样？', color: 'lime' },
  { tag: '用户研究', text: '分析近期用户反馈，给出最优先解决的三个问题。', color: 'blue' },
  { tag: '运营策划', text: '为未发布首个流程的试用用户，设计一个 7 天激活活动。', color: 'orange' },
]

const workflowPresets = [
  { id: '01', title: 'Knowledge QA', cn: '知识问答', desc: '基于检索证据生成可追溯回答', color: 'lime', question: prompts[0].text },
  { id: '02', title: 'Customer Reply', cn: '客服回复', desc: '生成可复核的客户沟通草稿', color: 'orange', question: '请根据知识库，为“升级专业版后仍显示 500 次额度”的客户生成一份客服回复草稿。' },
  { id: '03', title: 'Feedback Analysis', cn: '用户研究', desc: '归纳问题分布与产品优先级', color: 'blue', question: prompts[1].text },
  { id: '04', title: 'Campaign Plan', cn: '运营策划', desc: '构建人群、渠道、节奏与指标', color: 'black', question: prompts[2].text },
]

type Theme = 'light' | 'dark'
type ConnectionState = 'connected' | 'partial' | 'demo'
type CopilotPreset = { question: string; taskType: string; nonce: number }
type ImportSeed = { name: string; content: string }

function getInitialTheme(): Theme {
  const savedTheme = window.localStorage.getItem('flowpilot-theme')
  if (savedTheme === 'light' || savedTheme === 'dark') return savedTheme
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function App() {
  const root = useRef<HTMLDivElement>(null)
  const [page, setPage] = useState<PageId>('copilot')
  const [connection, setConnection] = useState<ConnectionState>('demo')
  const [modelMode, setModelMode] = useState<'demo' | 'cloud'>('demo')
  const [sources, setSources] = useState<KnowledgeSource[]>(initialSources)
  const [dashboard, setDashboard] = useState<DashboardData>(initialDashboard)
  const [evaluations, setEvaluations] = useState<EvaluationSet[]>([])
  const [importOpen, setImportOpen] = useState(false)
  const [importSeed, setImportSeed] = useState<ImportSeed | undefined>()
  const [searchOpen, setSearchOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [theme, setTheme] = useState<Theme>(getInitialTheme)
  const [copilotPreset, setCopilotPreset] = useState<CopilotPreset | undefined>()

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    document.documentElement.style.colorScheme = theme
    window.localStorage.setItem('flowpilot-theme', theme)
  }, [theme])

  useEffect(() => {
    let cancelled = false
    const loadInitialData = async () => {
      const [sourceResult, dashboardResult, health, insights] = await Promise.all([
        apiClient.getKnowledgeSources(),
        apiClient.getDashboard(),
        apiClient.getHealth().catch(() => null),
        apiClient.getInsights().catch(() => null),
      ])
      if (cancelled) return
      setSources(sourceResult.data)
      setDashboard(insights ? { ...dashboardResult.data, ...insights } : dashboardResult.data)
      if (!health) setConnection('demo')
      else {
        setModelMode(health.mode)
        const coreApiConnected = [sourceResult, dashboardResult].every((result) => result.source === 'api')
        setConnection(coreApiConnected ? 'connected' : 'partial')
      }

      try {
        const evaluationResult = await apiClient.getEvaluationSets()
        if (!cancelled) setEvaluations(evaluationResult)
      } catch (evaluationError) {
        if (!cancelled) setEvaluations([])
      }
    }
    void loadInitialData()
    return () => { cancelled = true }
  }, [])

  useLayoutEffect(() => {
    if (!root.current || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const ctx = gsap.context(() => {
      gsap.fromTo('.animate-in', { y: 28, opacity: 0 }, { y: 0, opacity: 1, duration: .72, stagger: .075, ease: 'power3.out' })
      gsap.fromTo('.hero-rule i', { scaleX: 0 }, { scaleX: 1, duration: 1.05, ease: 'expo.out', transformOrigin: 'left' })
    }, root)
    return () => ctx.revert()
  }, [page])

  const navigate = (next: PageId) => {
    if (next === page) return
    setPage(next)
    setMenuOpen(false)
  }

  const openWorkflow = (question: string, taskType: string) => {
    setCopilotPreset({ question, taskType, nonce: Date.now() })
    navigate('copilot')
  }

  const openGapFix = (topic: string) => {
    setImportSeed({ name: `${topic}知识补充`, content: `请在此补充“${topic}”的准确业务规则、适用范围、例外情况和更新时间。` })
    setImportOpen(true)
  }

  const connectionLabel = connection === 'connected'
    ? `API 已连接 · ${modelMode === 'cloud' ? '云模型' : '本地 Demo 模型'}`
    : connection === 'partial' ? 'API 部分降级' : '纯前端演示数据'

  return (
    <div className="studio-shell" ref={root}>
      <header className="studio-header">
        <button className="wordmark" onClick={() => navigate('copilot')} aria-label="FlowPilot 首页">
          <span className="wordmark-glyph" aria-hidden="true"><span>F</span><span>P</span></span>
          <span><strong>FlowPilot</strong><small>AI Operations Studio</small></span>
        </button>
        <nav className={`capsule-nav ${menuOpen ? 'open' : ''}`} aria-label="主导航">
          {navigation.map((item) => <button key={item.id} className={page === item.id ? 'active' : ''} onClick={() => navigate(item.id)}><small>{item.index}</small>{item.label}</button>)}
        </nav>
        <div className="header-tools">
          <span className={`live-status ${connection}`} title="状态按健康检查、知识列表和 Dashboard 接口综合判断"><i />{connectionLabel}</span>
          <button className="theme-toggle" onClick={() => setTheme((current) => current === 'light' ? 'dark' : 'light')} aria-label={`切换为${theme === 'light' ? '深色' : '浅色'}模式`} aria-pressed={theme === 'dark'} title={`当前为${theme === 'light' ? '浅色' : '深色'}模式`}>
            <span className="theme-toggle-icon"><Icon name={theme === 'light' ? 'sun' : 'moon'} size={15} /></span>
            <span className="theme-toggle-label">{theme === 'light' ? 'LIGHT' : 'DARK'}</span>
            <i aria-hidden="true"><b /></i>
          </button>
          <button className="round-button search-button" onClick={() => setSearchOpen(true)} aria-label="搜索知识来源"><Icon name="search" size={17} /></button>
          <button className="round-button menu-toggle" onClick={() => setMenuOpen(!menuOpen)} aria-label={menuOpen ? '关闭导航菜单' : '打开导航菜单'}><Icon name={menuOpen ? 'close' : 'menu'} size={18} /></button>
        </div>
      </header>

      <main className="page-stage" key={page}>
        <PageLead meta={pageMeta[page]} number={navigation.find((item) => item.id === page)?.index || '01'} />
        <DataProvenance page={page} connection={connection} modelMode={modelMode} />
        {page === 'copilot' && <CopilotPage onNavigate={navigate} preset={copilotPreset} sourceCount={sources.length} chunkCount={sources.reduce((sum, item) => sum + item.chunks, 0)} />}
        {page === 'workflow' && <WorkflowPage onOpen={openWorkflow} />}
        {page === 'knowledge' && <KnowledgePage sources={sources} onImport={() => { setImportSeed(undefined); setImportOpen(true) }} />}
        {page === 'evaluation' && <EvaluationPage sets={evaluations} onSetsChange={setEvaluations} />}
        {page === 'insights' && <InsightsPage data={dashboard} onFix={openGapFix} />}
      </main>

      <footer className="studio-footer"><span>FLOWPILOT / 2026</span><p>Grounded answers. Controlled agents. Measurable improvement.</p><span>LANGCHAIN + MODEL ADAPTER</span></footer>
      {importOpen && <ImportModal seed={importSeed} onClose={() => setImportOpen(false)} onImported={(source) => {
        setSources((items) => [source, ...items])
        void apiClient.getDashboard().then((result) => setDashboard(result.data))
      }} />}
      {searchOpen && <GlobalSearch sources={sources} onClose={() => setSearchOpen(false)} onSelect={() => { setSearchOpen(false); navigate('knowledge') }} />}
    </div>
  )
}

function PageLead({ meta, number }: { meta: typeof pageMeta[PageId]; number: string }) {
  return <section className="page-lead">
    <div className="lead-copy animate-in"><span className="kicker"><b>{number}</b>{meta.eyebrow}</span><h1>{meta.title}</h1><p>{meta.description}</p></div>
    <div className="lead-stamp animate-in"><span>FLOW</span><strong>{number}</strong><small>PRODUCT<br />INTELLIGENCE</small></div>
    <div className="hero-rule"><i /></div>
  </section>
}

function DataProvenance({ page, connection, modelMode }: { page: PageId; connection: ConnectionState; modelMode: 'demo' | 'cloud' }) {
  const content: Record<PageId, { primary: string; secondary: string }> = {
    copilot: { primary: connection === 'demo' ? '当前后端不可用，Agent 提交将明确报错，不会伪造成功。' : `回答由后端 RAG 生成；模型模式：${modelMode === 'cloud' ? 'OpenAI-compatible 云模型' : '基于检索证据的 deterministic Demo 模型'}。`, secondary: '知识正文来自内置合成 Seed 与本机用户导入，不是真实企业生产资料。' },
    workflow: { primary: '流程节点、四类意图与任务历史都来自当前后端受控 Agent。', secondary: '可按意图、模型降级状态筛选，并回放单任务 Trace；外部写操作仍停留在人工审核前。' },
    knowledge: { primary: connection === 'demo' ? '当前列表为前端 Mock 后备数据。' : '列表来自本地 state.json：内置合成 Seed + 本机导入内容。', secondary: '导入会写入本地 JSON 并即时重建 Hybrid RRF 检索索引。' },
    evaluation: { primary: connection === 'demo' ? '后端不可用，未展示合成评估分数。' : '分数由后端版本化 Golden Dataset 即时运行得到。', secondary: '当前指标包含 TF-IDF 与 Hybrid RRF 对照、引用正确性和规则忠实度，不代表生产准确率。' },
    insights: { primary: connection === 'demo' ? '当前全部指标为前端合成演示数据。' : '顶部指标、知识缺口和低分问题来自本地后端实时状态。', secondary: '当前用于单机质量治理，不代表线上全量业务统计。' },
  }
  return <aside className="provenance-bar animate-in"><span>DATA SOURCE</span><p><strong>{content[page].primary}</strong>{content[page].secondary}</p></aside>
}

function CopilotPage({ onNavigate, preset, sourceCount, chunkCount }: { onNavigate: (page: PageId) => void; preset?: CopilotPreset; sourceCount: number; chunkCount: number }) {
  const [question, setQuestion] = useState('')
  const [taskType, setTaskType] = useState('知识问答')
  const [answer, setAnswer] = useState<CopilotAnswer | null>(null)
  const [loading, setLoading] = useState(false)
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null)
  const [error, setError] = useState('')
  const [feedbackStatus, setFeedbackStatus] = useState('')

  useEffect(() => {
    if (!preset) return
    setQuestion(preset.question)
    setTaskType(preset.taskType)
  }, [preset])

  const submit = async (event?: FormEvent) => {
    event?.preventDefault()
    if (!question.trim() || loading) return
    setLoading(true); setAnswer(null); setFeedback(null); setError(''); setFeedbackStatus('')
    try {
      setAnswer(await apiClient.askCopilot(question.trim(), taskType))
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Agent 请求失败')
    } finally {
      setLoading(false)
    }
  }

  const recordFeedback = async (value: 'up' | 'down') => {
    if (!answer) return
    setFeedbackStatus('提交中…')
    try {
      await apiClient.submitFeedback(answer.id, answer.question, value === 'up')
      setFeedback(value)
      setFeedbackStatus('已写入后端反馈记录')
    } catch (submitError) {
      setFeedbackStatus(submitError instanceof Error ? `提交失败：${submitError.message}` : '提交失败')
    }
  }

  return <div className="copilot-studio">
    <section className="prompt-board animate-in">
      <div className="board-top"><span>START WITH A BRIEF</span><button onClick={() => onNavigate('knowledge')}>{sourceCount} SOURCES <Icon name="arrowUp" size={13} /></button></div>
      <form className="prompt-form" onSubmit={submit}>
        <textarea value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void submit() } }} placeholder="描述一个业务问题，或交给 Agent 一项任务…" rows={4} />
        <div className="prompt-controls">
          <div className="task-pills" role="group" aria-label="选择 Agent 任务类型">{['知识问答', '客服回复', '用户研究', '运营策划'].map((item) => <button type="button" key={item} className={taskType === item ? 'active' : ''} aria-pressed={taskType === item} onClick={() => setTaskType(item)}>{item}</button>)}</div>
          <button className="dispatch-button" disabled={!question.trim() || loading}>{loading ? '执行中' : '调度 Agent'}<Icon name="send" size={17} /></button>
        </div>
      </form>
      {error && <InlineNotice tone="error" title="Agent 未执行">{error}。为避免误导，本次没有返回前端 Mock 答案。</InlineNotice>}
      {!answer && !loading && !error && <div className="prompt-gallery">{prompts.map((item, index) => <button key={item.tag} className={`prompt-card ${item.color}`} onClick={() => { setQuestion(item.text); setTaskType(index === 0 ? '知识问答' : index === 1 ? '用户研究' : '运营策划') }}><span>0{index + 1}</span><small>{item.tag}</small><p>{item.text}</p><b>USE PROMPT ↗</b></button>)}</div>}
      {loading && <AgentLoading />}
      {answer && <AnswerPanel answer={answer} feedback={feedback} feedbackStatus={feedbackStatus} onFeedback={recordFeedback} />}
    </section>
    <aside className="signal-rail animate-in">
      <div className="rail-head"><span>LIVE SIGNAL</span><i /></div>
      <div className="signal-score"><strong>{String(chunkCount).padStart(2, '0')}</strong><span>可检索片段</span></div>
      <div className="signal-item"><small>RAG FRAMEWORK</small><strong>LangChain Core</strong></div>
      <div className="signal-item"><small>RETRIEVAL</small><strong>TF-IDF + BM25 / RRF</strong></div>
      <div className="signal-item"><small>AGENT MODE</small><strong>Controlled</strong></div>
      <div className="rail-note">每次回答保留 source、chunk ID 与检索分数。</div>
    </aside>
  </div>
}

function AgentLoading() {
  return <div className="agent-loading">
    <div className="loading-title"><span className="orbit-loader"><i /><i /><i /></span><div><small>AGENT IS WORKING</small><strong>正在理解任务并检索证据</strong></div></div>
    {['识别业务意图', '检索相关知识', '组织结构化产物'].map((step, index) => <div className="loading-step" key={step} style={{ animationDelay: `${index * .18}s` }}><span>0{index + 1}</span><p>{step}</p><i /></div>)}
  </div>
}

function AnswerPanel({ answer, feedback, feedbackStatus, onFeedback }: { answer: CopilotAnswer; feedback: 'up' | 'down' | null; feedbackStatus: string; onFeedback: (value: 'up' | 'down') => void }) {
  const [openCitation, setOpenCitation] = useState(answer.citations[0]?.id || '')
  return <div className="answer-panel">
    <div className="answer-meta"><span>COMPLETED / {answer.taskType.toUpperCase()}</span><small>{answer.steps.length} STEPS · {answer.citations.length} SOURCES</small></div>
    <div className="answer-grid">
      <article className="answer-main"><h2>{answer.summary}</h2>{answer.bullets.length > 0 && <><h3>{answer.taskType === '客服回复' ? '处理依据' : answer.taskType === '运营策划' ? '方案要点' : '关键发现'}</h3><ol>{answer.bullets.map((item, index) => <li key={`${item}-${index}`}><span>0{index + 1}</span><p>{item}</p></li>)}</ol></>}<div className="next-action"><span>NEXT</span><p>{answer.nextAction}</p></div></article>
      <aside className="trace-panel"><div className="trace-title">AGENT TRACE</div>{answer.steps.map((step, index) => <div className="trace-step" key={step.id}><span>{index + 1}</span><div><strong>{step.title}</strong><p>{step.detail}</p></div><small>{step.duration}</small></div>)}</aside>
    </div>
    <div className="citation-stack"><div className="citation-title"><span>EVIDENCE / 引用证据</span><small>{answer.citations.length ? '点击展开原文' : '证据门槛未通过'}</small></div>{answer.citations.length ? answer.citations.map((citation, index) => <button className={openCitation === citation.id ? 'open' : ''} key={citation.id} onClick={() => setOpenCitation(openCitation === citation.id ? '' : citation.id)}><span className="citation-index">[{index + 1}]</span><div><strong>{citation.source}</strong><small>{citation.section}</small>{openCitation === citation.id && <p>{citation.excerpt}</p>}</div><b>{Math.round(citation.score * 100)}%</b></button>) : <div className="evidence-refused">未找到达到相关度门槛（{Math.round((answer.trace?.retrieval.evidence_threshold ?? .1) * 100)}%）的可引用资料。系统没有把弱相关片段交给模型。</div>}</div>
    {answer.trace && <div className="trace-summary"><span>TRACE</span><p>总耗时 {answer.trace.timing.total_ms}ms · 检索 {answer.trace.timing.retrieve_ms}ms · {answer.trace.retrieval.strategy || 'rrf'} · Top-1 {Math.round(answer.trace.retrieval.top_score * 100)}% · {answer.trace.retrieval.evidence_status === 'refused' ? '证据门槛拒答' : answer.trace.generation.fallback_used ? '本地规则降级' : '云模型生成'}</p></div>}<div className="answer-footer"><span>这次回答有帮助吗？ {feedbackStatus && <small>{feedbackStatus}</small>}</span><button className={feedback === 'up' ? 'active' : ''} onClick={() => onFeedback('up')}><Icon name="thumbUp" size={15} />有帮助</button><button className={feedback === 'down' ? 'active negative' : ''} onClick={() => onFeedback('down')}><Icon name="thumbDown" size={15} />需改进</button></div>
  </div>
}

function WorkflowPage({ onOpen }: { onOpen: (question: string, taskType: string) => void }) {
  const [tasks, setTasks] = useState<TaskHistoryItem[]>([])
  const [total, setTotal] = useState(0)
  const [intent, setIntent] = useState('')
  const [fallbackOnly, setFallbackOnly] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [selectedJson, setSelectedJson] = useState('')
  const [selectedTask, setSelectedTask] = useState<TaskReplay | null>(null)
  const [replayStrategy, setReplayStrategy] = useState<RetrievalStrategy>('rrf')
  const [replayTopK, setReplayTopK] = useState(4)
  const [replayLoading, setReplayLoading] = useState(false)
  const [replayMessage, setReplayMessage] = useState('')

  const loadTasks = async () => {
    setLoading(true); setError('')
    try {
      const result = await apiClient.getAgentTasks({ limit: 12, intent: intent || undefined, fallbackUsed: fallbackOnly || undefined })
      setTasks(result.items); setTotal(result.total)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : '读取任务历史失败')
    } finally { setLoading(false) }
  }

  useEffect(() => { void loadTasks() }, [intent, fallbackOnly])

  const openReplay = async (taskId: string) => {
    setSelectedId(taskId); setSelectedJson(''); setSelectedTask(null); setReplayMessage('')
    try {
      const task = await apiClient.getAgentTask(taskId)
      setSelectedTask({ id: task.id, input: task.input, intent: task.intent, artifacts: task.artifacts, citations: task.citations.map((item) => ({ id: item.chunk_id, source: item.source, section: `知识片段 ${item.chunk_id}`, excerpt: item.chunk, score: item.score })), trace: task.trace, createdAt: task.created_at })
      setReplayStrategy(task.trace.request?.retrieval_strategy || task.trace.retrieval.strategy || 'rrf')
      setReplayTopK(task.trace.request?.top_k ?? task.trace.retrieval.citation_count ?? 4)
      setSelectedJson(JSON.stringify(task, null, 2))
    } catch (loadError) {
      setSelectedJson(JSON.stringify({ error: loadError instanceof Error ? loadError.message : '读取回放失败' }, null, 2))
    }
  }

  const replay = async () => {
    if (!selectedTask || replayLoading) return
    setReplayLoading(true); setReplayMessage('')
    try {
      const task = await apiClient.replayAgentTask(selectedTask.id, { retrievalStrategy: replayStrategy, topK: replayTopK })
      setSelectedTask(task)
      setSelectedId(task.id)
      setSelectedJson(JSON.stringify(task, null, 2))
      setReplayMessage(`已用 ${replayStrategy.toUpperCase()} 重跑，生成新任务 ${task.id}`)
      await loadTasks()
    } catch (replayError) {
      setReplayMessage(replayError instanceof Error ? `重跑失败：${replayError.message}` : '重跑失败')
    } finally { setReplayLoading(false) }
  }

  const closeReplay = () => { setSelectedId(null); setSelectedTask(null); setSelectedJson(''); setReplayMessage('') }

  return <div className="workflow-page">
    <section className="agent-map animate-in"><div className="map-head"><span>LIVE WORKFLOW / 当前工作流</span><button onClick={() => void loadTasks()}>刷新任务历史 ↗</button></div><div className="node-flow"><FlowBlock index="01" title="Intent Router" note="规则 + 显式选择" /><i /><FlowBlock index="02" title="Hybrid Retrieval" note="TF-IDF + BM25 / RRF" active /><i /><FlowBlock index="03" title="Structured Output" note="Schema validation" /><i /><FlowBlock index="04" title="Human Review" note="Side-effect gate" /></div><div className="map-foot"><span><i />当前策略</span><p>自主性被限制在可审计的业务边界内。</p></div></section>
    <section className="intent-grid">{workflowPresets.map((item) => <article className={`intent-card ${item.color} animate-in`} key={item.id}><span>{item.id}</span><small>{item.title}</small><h2>{item.cn === '用户研究' ? '反馈分析' : item.cn}</h2><p>{item.desc}</p><button onClick={() => onOpen(item.question, item.cn)}>OPEN IN COPILOT <Icon name="chevron" size={14} /></button></article>)}</section>
    <section className="task-history animate-in"><div className="task-history-head"><div><span>TASK HISTORY / 真实后端记录</span><p>按意图或模型降级状态筛选，点击任一任务查看完整 Trace 回放。</p></div><strong>{total}</strong></div><div className="task-history-tools"><select value={intent} onChange={(event) => setIntent(event.target.value)}><option value="">全部任务类型</option><option value="knowledge_qa">知识问答</option><option value="customer_reply">客服回复</option><option value="feedback_analysis">反馈分析</option><option value="campaign_plan">运营策划</option></select><label><input type="checkbox" checked={fallbackOnly} onChange={(event) => setFallbackOnly(event.target.checked)} /> 仅看本地规则降级</label><button onClick={() => void loadTasks()} disabled={loading}>{loading ? '加载中…' : '刷新'}</button></div>{error ? <InlineNotice tone="error" title="任务历史读取失败">{error}</InlineNotice> : <div className="task-history-list">{tasks.length ? tasks.map((task) => <article key={task.id} className="task-history-row"><div><strong>{task.input}</strong><small>{task.intent} · {new Date(task.createdAt).toLocaleString('zh-CN')}</small></div><span>{task.trace.retrieval.strategy || 'tfidf'} · Top-1 {Math.round(task.trace.retrieval.top_score * 100)}%</span><span>{task.trace.timing.total_ms}ms · {task.trace.generation.fallback_used ? 'FALLBACK' : 'CLOUD'}</span><button onClick={() => void openReplay(task.id)}>回放 <Icon name="chevron" size={13} /></button></article>) : <div className="empty-state">暂无任务记录。执行一次 Agent 后会在这里显示真实历史。</div>}</div>}</section>
    {selectedId && <DetailModal eyebrow="TASK REPLAY / REAL API DATA" title={`任务回放 ${selectedId}`} onClose={closeReplay}>{selectedTask && <div className="replay-tools"><label>重新检索策略<select value={replayStrategy} onChange={(event) => setReplayStrategy(event.target.value as RetrievalStrategy)}><option value="rrf">Hybrid RRF</option><option value="tfidf">TF-IDF</option><option value="bm25">BM25</option></select></label><label>Top-K<select value={replayTopK} onChange={(event) => setReplayTopK(Number(event.target.value))}>{[1, 2, 3, 4, 5, 6, 8, 10].map((value) => <option key={value} value={value}>{value} 条</option>)}</select></label><button onClick={() => void replay()} disabled={replayLoading}>{replayLoading ? '重跑中…' : '用此配置重跑'}</button></div>}{replayMessage && <p className="action-message">{replayMessage}</p>}{selectedJson ? <pre className="json-view">{selectedJson}</pre> : <p>正在读取 GET /api/agent/tasks/{selectedId}…</p>}</DetailModal>}
  </div>
}

function FlowBlock({ index, title, note, active }: { index: string; title: string; note: string; active?: boolean }) { return <div className={`flow-block ${active ? 'active' : ''}`}><span>{index}</span><strong>{title}</strong><small>{note}</small>{active && <b>RUNNING</b>}</div> }

function KnowledgePage({ sources, onImport }: { sources: KnowledgeSource[]; onImport: () => void }) {
  const [query, setQuery] = useState('')
  const filtered = sources.filter((source) => source.name.toLowerCase().includes(query.toLowerCase()))
  const chunks = sources.reduce((sum, item) => sum + item.chunks, 0)
  return <div className="knowledge-page">
    <div className="knowledge-stats animate-in"><div><small>SOURCES</small><strong>{String(sources.length).padStart(2, '0')}</strong><span>个知识来源</span></div><div className="lime"><small>CHUNKS</small><strong>{chunks}</strong><span>可检索片段</span></div><div className="blue"><small>INDEX</small><strong>LIVE</strong><span>导入后即时重建</span></div></div>
    <section className="asset-table animate-in"><div className="asset-tools"><div><span>KNOWLEDGE INVENTORY</span><p>将事实来源变成可管理的产品资产。</p></div><label><Icon name="search" size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索知识来源" /></label><button onClick={onImport}>导入新知识 <Icon name="plus" size={15} /></button></div><div className="asset-head"><span># / 来源</span><span>类型</span><span>片段</span><span>负责人</span><span>状态</span></div>{filtered.map((source, index) => <div className="asset-row" key={source.id}><span><b>{String(index + 1).padStart(2, '0')}</b><strong>{source.name}</strong><small>{source.updatedAt}</small></span><span>{source.type}</span><span>{source.chunks}</span><span>{source.owner}</span><span className="asset-ready"><i />READY</span></div>)}{filtered.length === 0 && <div className="empty-state">没有匹配的知识来源</div>}</section>
  </div>
}

function EvaluationPage({ sets, onSetsChange }: { sets: EvaluationSet[]; onSetsChange: (sets: EvaluationSet[]) => void }) {
  const [running, setRunning] = useState(false)
  const [message, setMessage] = useState('')
  const [selected, setSelected] = useState<EvaluationSet | null>(null)
  const safeSets = Array.isArray(sets) ? sets : []
  const valid = safeSets.filter((item) => item.status !== 'draft')
  const avg = (key: 'accuracy' | 'groundedness' | 'helpfulness') => valid.length ? valid.reduce((sum, item) => sum + item[key], 0) / valid.length : 0

  const runEvaluation = async () => {
    setRunning(true); setMessage('')
    try {
      const next = await apiClient.runEvaluation()
      onSetsChange(next)
      setMessage(`已运行 ${next[0].cases} 条内置回归用例，结果来自后端即时计算。`)
    } catch (error) {
      setMessage(`运行失败：${error instanceof Error ? error.message : '未知错误'}。未使用 Mock 分数覆盖。`)
    } finally {
      setRunning(false)
    }
  }

  return <div className="evaluation-page">
    <section className="score-marquee animate-in"><div className="score-copy"><span>QUALITY SNAPSHOT / BACKEND DATA</span><h2>回答可靠，不等于“听起来合理”。</h2><p>同一份 Golden Dataset 对比 TF-IDF 基线与 Hybrid RRF，并分开检查检索、引用与证据覆盖。</p><button onClick={() => void runEvaluation()} disabled={running}>{running ? '评估运行中…' : '运行完整评估'} <Icon name="play" size={14} /></button>{message && <small className="action-message">{message}</small>}</div><div className="giant-score"><small>OVERALL</small><strong>{((avg('accuracy') + avg('groundedness') + avg('helpfulness')) / 3).toFixed(1)}</strong><span>/ 100</span></div></section>
    <div className="metric-strips"><MetricStrip index="01" label="关键词召回" value={avg('accuracy')} color="orange" /><MetricStrip index="02" label="Hybrid 检索命中" value={avg('groundedness')} color="blue" /><MetricStrip index="03" label="综合质量" value={avg('helpfulness')} color="lime" /></div>
    <section className="test-sets animate-in"><div className="test-title"><span>VERSIONED GOLDEN DATASET</span><button className="disabled-action" disabled title="评估集 CRUD 尚未实现">NEW SET · 暂未开放</button></div>{safeSets.length ? safeSets.map((set, index) => <div className="test-row" key={set.id}><b>0{index + 1}</b><div><strong>{set.name}</strong><small>{set.cases} CASES · {set.datasetVersion || '未标记版本'} · {set.lastRun}</small></div><span className={`test-state ${set.status}`}>{set.status === 'passed' ? 'PASSED' : set.status === 'running' ? 'RUNNING' : 'DRAFT'}</span><strong>{set.status === 'draft' ? '—' : `${set.helpfulness}%`}</strong><button onClick={() => setSelected(set)} aria-label={`查看${set.name}详情`}><Icon name="chevron" size={15} /></button></div>) : <div className="empty-state">后端尚未返回评估结果；不会以旧样例分数替代。</div>}</section>
    {selected && <DetailModal eyebrow="EVALUATION RESULT / REAL API" title={selected.name} onClose={() => setSelected(null)}><dl className="detail-grid"><div><dt>用例数</dt><dd>{selected.cases}</dd></div><div><dt>TF-IDF 命中</dt><dd>{selected.baselineHitRate ?? '—'}%</dd></div><div><dt>Hybrid 命中</dt><dd>{selected.groundedness}%</dd></div><div><dt>引用正确性</dt><dd>{selected.citationCorrectness ?? '—'}%</dd></div><div><dt>回答忠实度</dt><dd>{selected.faithfulness ?? '—'}%</dd></div><div><dt>Hybrid MRR</dt><dd>{selected.hybridMrr ?? '—'}%</dd></div></dl><p className="detail-note">方法：{selected.evaluationMethod || '规则评估'}。引用正确性检查返回来源是否符合标注；忠实度按回答主张与引用片段的词项覆盖计算，属于可解释 MVP，不等同人工标注或 LLM Judge。</p>{selected.caseDetails?.length ? <div className="evaluation-case-list">{selected.caseDetails.map((item) => <article key={item.id || item.question}><strong>{item.question}</strong><small>{item.category} · 关键词 {item.keywordRecall}% · 引用 {item.citationCorrectness == null ? '—' : `${item.citationCorrectness}%`} · 忠实度 {item.faithfulness == null ? '—' : `${item.faithfulness}%`}</small>{item.unsupportedClaims.length > 0 && <p>待复核主张：{item.unsupportedClaims.join('；')}</p>}</article>)}</div> : null}</DetailModal>}
  </div>
}

function MetricStrip({ index, label, value, color }: { index: string; label: string; value: number; color: string }) { return <div className={`metric-strip ${color} animate-in`}><span>{index}</span><p>{label}</p><strong>{value.toFixed(1)}%</strong><div><i style={{ width: `${value}%` }} /></div></div> }

function InsightsPage({ data, onFix }: { data: DashboardData; onFix: (topic: string) => void }) {
  const total = data.categories.reduce((sum, item) => sum + item.value, 0) || 1
  return <div className="insights-page">
    <section className="insight-numbers">{data.metrics.map((item, index) => <article className={`insight-number n${index} animate-in`} key={item.label}><span>0{index + 1}</span><small>{item.label}</small><strong>{item.value}</strong><p>{item.change} / {item.hint}</p></article>)}</section>
    <div className="insight-columns">
      <section className="category-list animate-in"><div className="section-label"><span>QUESTION MIX</span><small>本地文档类型分布</small></div>{data.categories.map((item, index) => <div key={item.label}><b>{String(index + 1).padStart(2, '0')}</b><span>{item.label}</span><div><i style={{ width: `${item.value / total * 100}%`, background: item.color }} /></div><strong>{item.value}%</strong></div>)}</section>
      <section className="gap-list animate-in"><div className="section-label"><span>KNOWLEDGE SIGNALS</span><small>基于本地任务、检索 Trace 与反馈聚合</small></div>{data.gaps.length ? data.gaps.map((gap) => <div key={gap.topic}><span className={`gap-priority p${gap.priority}`}>{gap.priority}</span><div><strong>{gap.topic}</strong><small>{gap.queries} 次任务 / 平均检索相关度 {gap.coverage}%</small></div><button onClick={() => onFix(gap.topic)}>补充知识 ↗</button></div>) : <div className="empty-state">暂未收集到任务信号；执行 Agent 并提交反馈后会在这里形成待补知识建议。</div>}</section>
    </div>
    <section className="low-score-review animate-in">
      <div className="review-head">
        <div>
          <span className="review-kicker">QUALITY LOOP / 质量闭环</span>
          <h2>低分回答待复盘</h2>
          <p>展示已关联任务的低分反馈，并结合检索分数和模型降级状态定位问题。</p>
        </div>
        <div className="review-count"><strong>{data.lowScores.length}</strong><span>条待复盘</span></div>
      </div>
      <div className="review-list">
        {data.lowScores.length ? data.lowScores.map((item, index) => <article className="review-row" key={item.taskId || item.question}>
          <span className="review-index">{String(index + 1).padStart(2, '0')}</span>
          <div className="review-score"><strong>{item.score.toFixed(1)}</strong><small>/ 5</small></div>
          <div className="review-question"><strong>{item.question}</strong><small>主要原因：{item.reason}</small></div>
          <time>{item.time}</time>
          <span className="review-source">{item.fallbackUsed ? 'FALLBACK' : 'LIVE DATA'}</span>
          <button onClick={() => onFix(item.question)}>补充相关知识 <Icon name="chevron" size={13} /></button>
        </article>) : <div className="empty-state">暂无低分任务。对 Agent 回答提交“需改进”反馈后，会自动进入这里复盘。</div>}
      </div>
      <div className="review-foot"><span>REVIEW QUEUE</span><p>记录来自本地 Agent 任务和已关联的反馈；当前用于单机质量治理，不代表线上全量业务统计。</p></div>
    </section>
  </div>
}

function ImportModal({ seed, onClose, onImported }: { seed?: ImportSeed; onClose: () => void; onImported: (source: KnowledgeSource) => void }) {
  const [name, setName] = useState(seed?.name || '')
  const [content, setContent] = useState(seed?.content || '')
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (loading || (!file && (!name.trim() || !content.trim()))) return
    setLoading(true); setError('')
    try {
      const source = file ? await apiClient.importFile(file) : await apiClient.importText(name.trim(), content.trim())
      onImported(source)
      onClose()
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : '导入失败')
      setLoading(false)
    }
  }
  return <div className="modal-layer" onMouseDown={onClose}><form className="import-sheet" onSubmit={submit} onMouseDown={(event) => event.stopPropagation()}><div className="sheet-index">NEW<br />SOURCE</div><div className="sheet-main"><div className="sheet-head"><div><span>KNOWLEDGE INGESTION</span><h2>导入一份新知识</h2></div><button type="button" onClick={onClose}>×</button></div><label>来源名称<input value={name} disabled={Boolean(file)} onChange={(event) => setName(event.target.value)} placeholder="例如：8 月产品更新说明" autoFocus /></label><label>上传文件（可选）<input type="file" accept=".txt,.md,.csv,.pdf,.docx" onChange={(event) => { const next = event.target.files?.[0] || null; setFile(next); if (next) setName(next.name.replace(/\.[^.]+$/, '')) }} /><small>支持 TXT、MD、CSV、PDF、DOCX；仅提取文本，单文件不超过 2MB。</small></label>{!file && <label>知识正文<textarea value={content} onChange={(event) => setContent(event.target.value)} placeholder="粘贴产品规则、FAQ 或运营规范…" rows={7} /><small>{content.length} 字符 / 预计 {Math.max(0, Math.ceil(content.length / 280))} 个片段</small></label>}{file && <div className="inline-notice info"><strong>已选择文件</strong><p>{file.name}，将提取文本后写入本地索引。</p></div>}{error && <InlineNotice tone="error" title="导入未完成">{error}。内容没有写入，本界面不会伪造成功记录。</InlineNotice>}<div className="sheet-actions"><p>成功后将写入本地 state.json 并重建索引。</p><button disabled={loading || (!file && (!name.trim() || !content.trim()))}>{loading ? '正在建立索引…' : file ? '上传并建立索引' : '导入并建立索引'} <Icon name="arrowUp" size={14} /></button></div></div></form></div>
}

function GlobalSearch({ sources, onClose, onSelect }: { sources: KnowledgeSource[]; onClose: () => void; onSelect: () => void }) {
  const [query, setQuery] = useState('')
  const results = sources.filter((source) => source.name.toLowerCase().includes(query.toLowerCase())).slice(0, 8)
  return <DetailModal eyebrow="LOCAL KNOWLEDGE SEARCH" title="搜索知识来源" onClose={onClose}><label className="global-search-input"><Icon name="search" size={18} /><input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder="输入来源名称，例如：计费、权限、工单" /></label><div className="search-results">{results.map((source) => <button key={source.id} onClick={onSelect}><span><strong>{source.name}</strong><small>{source.type} · {source.chunks} 个片段</small></span><Icon name="chevron" size={15} /></button>)}{results.length === 0 && <div className="empty-state">没有匹配的知识来源</div>}</div><p className="detail-note">当前只支持本地知识来源名称搜索；全文检索 API 尚未开放，因此不伪装成全局内容搜索。</p></DetailModal>
}

function DetailModal({ eyebrow, title, onClose, children }: { eyebrow: string; title: string; onClose: () => void; children: ReactNode }) {
  return <div className="modal-layer" onMouseDown={onClose}><section className="detail-sheet" onMouseDown={(event) => event.stopPropagation()}><div className="sheet-head"><div><span>{eyebrow}</span><h2>{title}</h2></div><button type="button" onClick={onClose}>×</button></div><div className="detail-content">{children}</div></section></div>
}

function InlineNotice({ tone, title, children }: { tone: 'error' | 'info'; title: string; children: ReactNode }) {
  return <div className={`inline-notice ${tone}`}><strong>{title}</strong><p>{children}</p></div>
}

export default App
