import type { CopilotAnswer, DashboardData, EvaluationSet, KnowledgeSource } from './types'

export const mockAnswer: CopilotAnswer = {
  id: 'answer-1042',
  question: '分析最近两周新用户激活率下降的可能原因，并给出优先排查建议',
  taskType: '运营诊断',
  summary: '近两周新用户激活率从 42.6% 降至 36.8%，主要降幅集中在「首次创建工作流」环节。结合埋点变化与客服反馈，判断引导路径变长和模板匹配度下降是最可能的两个原因。',
  bullets: [
    '首次工作流创建完成率下降 9.4%，贡献了约 61% 的整体激活损失。',
    '移动端新用户占比提升 12%，但移动端模板预览加载失败率达到 7.8%。',
    '「不知道选哪个模板」相关咨询环比增加 34%，集中在电商与内容团队。',
  ],
  nextAction: '建议先修复移动端模板预览，并针对电商与内容团队上线按角色推荐模板的 A/B 测试。',
  steps: [
    { id: 's1', title: '理解任务与拆解目标', detail: '识别激活率口径、时间范围和关键转化节点', status: 'done', duration: '0.4s' },
    { id: 's2', title: '检索业务知识', detail: '命中 6 个数据字典、实验记录与用户反馈片段', status: 'done', duration: '1.2s' },
    { id: 's3', title: '交叉分析指标', detail: '对比渠道、设备和关键行为漏斗', status: 'done', duration: '2.8s' },
    { id: 's4', title: '生成诊断建议', detail: '按影响范围与修复成本排列优先级', status: 'done', duration: '1.1s' },
  ],
  citations: [
    { id: 'c1', source: '增长指标周报 · W31', section: '新用户激活漏斗', excerpt: '首次创建工作流完成率由 68.2% 下降至 58.8%，移动端降幅高于桌面端。', score: 0.94 },
    { id: 'c2', source: '客服问题聚类 · 7月', section: '模板选择问题', excerpt: '模板选择相关咨询共 126 条，主要反馈为行业模板不明确、预览等待时间长。', score: 0.89 },
    { id: 'c3', source: '实验记录 EXP-087', section: '角色化模板推荐', excerpt: '角色化推荐在小流量实验中使首次模板使用率提升 11.7%。', score: 0.86 },
  ],
}

export const knowledgeSources: KnowledgeSource[] = [
  { id: 'k1', name: '产品使用手册 2026', type: '在线文档', status: 'ready', chunks: 386, updatedAt: '今天 09:42', owner: '产品运营' },
  { id: 'k2', name: '用户反馈与工单', type: '数据同步', status: 'syncing', chunks: 1248, updatedAt: '同步中 · 72%', owner: '客户成功' },
  { id: 'k3', name: '增长实验记录', type: '表格', status: 'ready', chunks: 214, updatedAt: '昨天 18:20', owner: '增长团队' },
  { id: 'k4', name: '业务指标口径字典', type: 'API', status: 'ready', chunks: 97, updatedAt: '8月4日', owner: '数据平台' },
  { id: 'k5', name: '竞品研究资料库', type: '文件夹', status: 'warning', chunks: 156, updatedAt: '7月28日', owner: '战略分析' },
]

export const dashboardData: DashboardData = {
  metrics: [
    { label: 'Copilot 会话', value: '2,846', change: '+18.4%', trend: 'up', hint: '较上个周期' },
    { label: '问题解决率', value: '84.7%', change: '+3.2%', trend: 'up', hint: '用户确认解决' },
    { label: '平均响应耗时', value: '5.8s', change: '-0.9s', trend: 'up', hint: 'P50 响应时间' },
    { label: '知识引用率', value: '91.2%', change: '+1.6%', trend: 'up', hint: '回答包含有效引用' },
  ],
  categories: [
    { label: '数据分析', value: 34, color: '#2ec5ce' },
    { label: '运营策划', value: 26, color: '#4f8cff' },
    { label: '运营诊断', value: 18, color: '#f5b74f' },
    { label: '知识问答', value: 14, color: '#7c91b5' },
    { label: '其他', value: 8, color: '#44516a' },
  ],
  gaps: [
    { topic: '企业版权限配置', queries: 86, coverage: 42, priority: '高' },
    { topic: '移动端能力边界', queries: 64, coverage: 55, priority: '高' },
    { topic: '海外数据合规', queries: 41, coverage: 63, priority: '中' },
    { topic: '自动化计费规则', queries: 37, coverage: 71, priority: '中' },
  ],
  lowScores: [
    { question: '如何批量迁移旧版自动化流程？', score: 2.1, reason: '步骤已过期', time: '12 分钟前' },
    { question: '专业版的 API 调用额度是多少？', score: 2.4, reason: '引用内容冲突', time: '38 分钟前' },
    { question: '如何计算渠道带来的增量用户？', score: 2.7, reason: '回答不够具体', time: '1 小时前' },
  ],
}

export const evaluationSets: EvaluationSet[] = [
  { id: 'e1', name: '核心产品问答回归集', cases: 120, lastRun: '今天 10:24', status: 'passed', accuracy: 92.4, groundedness: 95.1, helpfulness: 89.8 },
  { id: 'e2', name: '运营分析复杂任务集', cases: 68, lastRun: '昨天 16:40', status: 'passed', accuracy: 87.6, groundedness: 91.3, helpfulness: 90.2 },
  { id: 'e3', name: '安全与拒答边界集', cases: 42, lastRun: '运行中', status: 'running', accuracy: 96.8, groundedness: 98.2, helpfulness: 86.4 },
  { id: 'e4', name: '新版功能增量用例', cases: 24, lastRun: '尚未运行', status: 'draft', accuracy: 0, groundedness: 0, helpfulness: 0 },
]
