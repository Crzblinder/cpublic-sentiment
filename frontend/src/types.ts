export interface EventItem {
  id: number
  title: string
  risk_level: string | null
  risk_type: string | null
  risk_score: number
  source: string | null
  status: string
  created_at: string | null
}

export interface AnalyzeResult {
  event_id: number
  text: string
  scan: Record<string, unknown>
  matched_cases: Array<{
    id: number
    title: string
    risk_level: string
    risk_type: string
    match_score?: number
    reason?: string
  }>
  enterprise: { id: number; name: string; industry: string } | null
  prediction: Record<string, unknown>
  governance: Record<string, unknown>
  reasoning_chain: Array<Record<string, unknown>>
  response_time_ms: number
}

export interface CaseItem {
  id: number
  title: string
  industry: string
  risk_type: string
  risk_level: string
  summary: string
  governance_playbook?: Record<string, unknown>
}

export interface PaginatedResponse<T> {
  total: number
  items: T[]
}

export interface EnterpriseItem {
  id: number
  name: string
  industry: string
  scale: string
  region: string
  business_tags: string[]
  risk_profile: Record<string, unknown>
  risk_score_history: Array<{ month: string; score: number }>
}

export interface Metrics {
  total: number
  labeled: number
  accuracy: number
  recall: number
  avg_response_time_ms: number
}

/* ---- Dashboard stats ---- */

export interface DashboardStats {
  summary: {
    total_events: number
    today_events: number
    week_high_risk_events: number
    high_risk_ratio: number
    avg_risk_score: number
    avg_response_time_ms: number
    accuracy: number
    labeled_count: number
  }
  risk_distribution: Array<{ name: string; value: number }>
  risk_type_distribution: Array<{ name: string; value: number }>
  industry_distribution: Array<{ name: string; value: number }>
  top_enterprises: Array<{
    id: number
    name: string
    industry: string
    avg_risk_score: number
    event_count: number
  }>
}

export interface TrendPoint {
  date: string
  count: number
  avg_score: number
}

/* ---- Enterprise detail ---- */

export interface EnterpriseDetail {
  enterprise: {
    id: number
    name: string
    industry: string
    scale: string
    region: string
    business_tags: string[]
    risk_profile: Record<string, unknown>
    risk_score_history: Array<{ month: string; score: number }>
  }
  events: Array<{
    id: number
    title: string
    risk_level: string | null
    risk_type: string | null
    risk_score: number
    created_at: string | null
  }>
  rank_in_industry: number | null
  industry_peers: Array<{
    id: number
    name: string
    avg_risk_score: number
  }>
}

/* ---- Crawler ---- */

export interface CrawlerSourceDetail {
  name: string
  count: number
  ok: boolean
}

export interface CrawlerStatus {
  last_run: string | null
  total_fetched: number
  sources_ok: string[]
  sources_failed: string[]
  sources_detail?: CrawlerSourceDetail[]
}

export interface CrawlerRunResult {
  fetched: number
  cleaned: number
  persisted: number
  deduped: number
  analyzed: number
  status: CrawlerStatus
}

export interface LlmStatus {
  enabled: boolean
  mode: 'openai' | 'ollama' | 'fallback'
  model: string
  base_url: string
  is_fallback: boolean
}

/* ---- 分析历史 ---- */

export interface AnalysisHistoryItem {
  id: number
  text: string
  risk_level: string | null
  risk_type: string | null
  risk_score: string | null
  response_time_ms: number | null
  created_at: string | null
}

export interface AnalysisHistoryDetail {
  id: number
  text: string
  scan_result: Record<string, unknown>
  matched_cases: Array<Record<string, unknown>>
  enterprise: Record<string, unknown> | null
  prediction: Record<string, unknown>
  governance: Record<string, unknown>
  reasoning_chain: Array<Record<string, unknown>>
  risk_level: string | null
  risk_type: string | null
  risk_score: string | null
  response_time_ms: number | null
  created_at: string | null
}

/* ---- 高危事件 ---- */

export interface HighRiskEvent {
  id: number
  title: string
  risk_level: string | null
  risk_type: string | null
  risk_score: number
  source: string | null
  created_at: string | null
}

/* ---- 爬虫日志 ---- */

export interface CrawlerLogItem {
  id: number
  fetched: number
  cleaned: number
  persisted: number
  deduped: number
  sources_ok: string
  sources_failed: string
  error: string | null
  created_at: string | null
}

/* ---- 企业趋势 ---- */

export interface EnterpriseTrendPoint {
  date: string
  count: number
  avg_score: number
}
