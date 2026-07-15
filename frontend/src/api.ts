import type { CaseItem, EnterpriseItem, EventItem, Metrics } from './types'

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
  analyze: (text: string, enterpriseHint?: string) =>
    request('/sentiment/analyze', {
      method: 'POST',
      body: JSON.stringify({ text, enterprise_hint: enterpriseHint }),
    }),

  listEvents: (skip = 0, limit = 20): Promise<EventItem[]> =>
    request(`/sentiment/events?skip=${skip}&limit=${limit}`),

  getEvent: (id: number) => request(`/sentiment/events/${id}`),

  listCases: (params?: { industry?: string; risk_type?: string }): Promise<CaseItem[]> => {
    const qs = new URLSearchParams()
    if (params?.industry) qs.set('industry', params.industry)
    if (params?.risk_type) qs.set('risk_type', params.risk_type)
    return request(`/cases?${qs.toString()}`)
  },

  listEnterprises: (industry?: string): Promise<EnterpriseItem[]> =>
    request(`/enterprises${industry ? `?industry=${industry}` : ''}`),

  getMetrics: (): Promise<Metrics> => request('/evaluation/metrics'),

  runAbTest: (dataset: Array<{ text: string; true_risk_level: string; true_risk_type: string }>, agentType?: string) =>
    request('/evaluation/ab-test', {
      method: 'POST',
      body: JSON.stringify({ dataset, agent_type: agentType }),
    }),
}
