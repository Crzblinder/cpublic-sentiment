import type {
  CaseItem,
  CrawlerStatus,
  DashboardStats,
  EnterpriseDetail,
  EnterpriseItem,
  EventItem,
  Metrics,
  PaginatedResponse,
  TrendPoint,
} from './types'

const API_BASE = '/api/v1'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
    },
    ...options,
  })
  if (!res.ok) {
    const err = await res.text()
    throw new Error(err || `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  /* ---- 舆情分析 ---- */
  analyze: (text: string, enterpriseHint?: string) =>
    request('/sentiment/analyze', {
      method: 'POST',
      body: JSON.stringify({ text, enterprise_hint: enterpriseHint }),
    }),

  /** SSE 流式分析：通过回调接收每个节点的中间结果 */
  analyzeStream: async (
    text: string,
    enterpriseHint?: string,
    onEvent?: (data: Record<string, unknown>) => void,
  ): Promise<Record<string, unknown>> => {
    const res = await fetch(`${API_BASE}/sentiment/analyze/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, enterprise_hint: enterpriseHint }),
    })
    if (!res.ok || !res.body) {
      throw new Error(`HTTP ${res.status}`)
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let finalResult: Record<string, unknown> = {}

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const payload = line.slice(6).trim()
          if (payload === '[DONE]') continue
          try {
            const parsed = JSON.parse(payload) as Record<string, unknown>
            if (parsed.final_result) {
              finalResult = parsed.final_result as Record<string, unknown>
            }
            onEvent?.(parsed)
          } catch {
            // skip malformed JSON
          }
        }
      }
    }
    return finalResult
  },

  listEvents: (skip = 0, limit = 20, riskLevel?: string): Promise<EventItem[]> => {
    const qs = new URLSearchParams()
    qs.set('skip', String(skip))
    qs.set('limit', String(limit))
    if (riskLevel) qs.set('risk_level', riskLevel)
    return request(`/sentiment/events?${qs.toString()}`)
  },

  getEvent: (id: number) => request(`/sentiment/events/${id}`),

  /* ---- 仪表盘 ---- */
  getDashboardStats: (): Promise<DashboardStats> => request('/dashboard/stats'),

  getTrend: (days = 30): Promise<TrendPoint[]> => request(`/dashboard/trend?days=${days}`),

  /* ---- 案例库 (分页) ---- */
  listCases: (params?: {
    industry?: string
    risk_type?: string
    search?: string
    skip?: number
    limit?: number
  }): Promise<PaginatedResponse<CaseItem>> => {
    const qs = new URLSearchParams()
    if (params?.industry) qs.set('industry', params.industry)
    if (params?.risk_type) qs.set('risk_type', params.risk_type)
    if (params?.search) qs.set('search', params.search)
    qs.set('skip', String(params?.skip ?? 0))
    qs.set('limit', String(params?.limit ?? 20))
    return request(`/cases?${qs.toString()}`)
  },

  /* ---- 企业画像 (分页) ---- */
  listEnterprises: (params?: {
    industry?: string
    skip?: number
    limit?: number
  }): Promise<PaginatedResponse<EnterpriseItem>> => {
    const qs = new URLSearchParams()
    if (params?.industry) qs.set('industry', params.industry)
    qs.set('skip', String(params?.skip ?? 0))
    qs.set('limit', String(params?.limit ?? 20))
    return request(`/enterprises?${qs.toString()}`)
  },

  getEnterpriseDetail: (id: number): Promise<EnterpriseDetail> =>
    request(`/enterprises/${id}`),

  getEnterpriseEvents: (id: number, skip = 0, limit = 20): Promise<EventItem[]> =>
    request(`/enterprises/${id}/events?skip=${skip}&limit=${limit}`),

  /* ---- 爬虫 ---- */
  runCrawler: (): Promise<{ fetched: number; analyzed: number; status: CrawlerStatus }> =>
    request('/crawler/run', { method: 'POST' }),

  getCrawlerStatus: (): Promise<CrawlerStatus> => request('/crawler/status'),

  /* ---- 效果评估 ---- */
  getMetrics: (): Promise<Metrics> => request('/evaluation/metrics'),

  runAbTest: (
    dataset: Array<{ text: string; true_risk_level: string; true_risk_type: string }>,
    agentType?: string,
  ) =>
    request('/evaluation/ab-test', {
      method: 'POST',
      body: JSON.stringify({ dataset, agent_type: agentType }),
    }),
}
