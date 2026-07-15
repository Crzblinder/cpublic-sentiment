import { useEffect, useState } from 'react'
import { api } from '../api'
import type { EventItem, Metrics } from '../types'

function levelClass(level: string | null) {
  if (!level) return 'badge'
  const map: Record<string, string> = { 低: 'low', 中: 'medium', 高: 'high', 极高: 'critical' }
  return `badge ${map[level] || ''}`
}

export default function Dashboard() {
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [events, setEvents] = useState<EventItem[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    api.getMetrics().then(setMetrics).catch((e) => setError(e.message))
    api.listEvents(0, 10).then(setEvents).catch((e) => setError(e.message))
  }, [])

  return (
    <div>
      <h2>仪表盘</h2>
      {error && <div style={{ color: 'red' }}>{error}</div>}
      <div className="grid">
        <div className="card">
          <div className="label">累计分析事件</div>
          <div className="metric">{metrics?.total ?? '-'}</div>
        </div>
        <div className="card">
          <div className="label">标注准确率</div>
          <div className="metric">{metrics ? `${(metrics.accuracy * 100).toFixed(1)}%` : '-'}</div>
        </div>
        <div className="card">
          <div className="label">平均响应时间</div>
          <div className="metric">{metrics ? `${metrics.avg_response_time_ms}ms` : '-'}</div>
        </div>
        <div className="card">
          <div className="label">已标注样本</div>
          <div className="metric">{metrics?.labeled ?? '-'}</div>
        </div>
      </div>

      <div className="card">
        <h3>最近舆情</h3>
        <table className="table">
          <thead>
            <tr>
              <th>标题</th>
              <th>风险等级</th>
              <th>风险类型</th>
              <th>评分</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.id}>
                <td>{e.title}</td>
                <td><span className={levelClass(e.risk_level)}>{e.risk_level ?? '-'}</span></td>
                <td>{e.risk_type ?? '-'}</td>
                <td>{e.risk_score.toFixed(2)}</td>
                <td>{e.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
