export interface EventItem {
  id: number
  title: string
  risk_level: string | null
  risk_type: string | null
  risk_score: number
  status: string
  created_at: string | null
}

export interface AnalyzeResult {
  event_id: number
  text: string
  scan: Record<string, unknown>
  matched_cases: Array<{ id: number; title: string; risk_level: string; risk_type: string }>
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
}

export interface EnterpriseItem {
  id: number
  name: string
  industry: string
  scale: string
  region: string
}

export interface Metrics {
  total: number
  labeled: number
  accuracy: number
  recall: number
  avg_response_time_ms: number
}
