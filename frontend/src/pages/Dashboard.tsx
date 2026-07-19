import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
  LineChart, Line,
} from 'recharts'
import { api } from '../api'
import type { DashboardStats, TrendPoint, EventItem } from '../types'

const PIE_COLORS = ['#16a34a', '#f59e0b', '#dc2626', '#991b1b']
const BAR_COLOR = '#2563eb'

function levelClass(level: string | null) {
  if (!level) return 'badge'
  const map: Record<string, string> = { '低': 'low', '中': 'medium', '高': 'high', '极高': 'critical' }
  return `badge ${map[level] || ''}`
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [trend, setTrend] = useState<TrendPoint[]>([])
  const [events, setEvents] = useState<EventItem[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    api.getDashboardStats().then(setStats).catch((e) => setError(e.message))
    api.getTrend(30).then(setTrend).catch((e) => setError(e.message))
    api.listEvents(0, 20).then(setEvents).catch((e) => setError(e.message))
  }, [])

  const s = stats?.summary

  return (
    <div>
      <h2>仪表盘</h2>
      {error && <div className="error-banner">{error}</div>}

      {/* ---- 顶部指标卡片 ---- */}
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-label">累计分析事件</div>
          <div className="stat-value">{s?.total_events ?? '-'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">高风险占比</div>
          <div className="stat-value">{s ? `${(s.high_risk_ratio * 100).toFixed(1)}%` : '-'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">平均响应时间</div>
          <div className="stat-value">{s ? `${s.avg_response_time_ms.toFixed(0)}ms` : '-'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">系统准确率</div>
          <div className="stat-value">{s ? `${(s.accuracy * 100).toFixed(1)}%` : '-'}</div>
        </div>
      </div>

      {/* ---- 图表区域 ---- */}
      <div className="chart-row">
        {/* 风险等级饼图 */}
        <div className="card chart-card">
          <h3>风险等级分布</h3>
          {stats?.risk_distribution?.length ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={stats.risk_distribution}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                  label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                >
                  {stats.risk_distribution.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="chart-empty">暂无数据</div>
          )}
        </div>

        {/* 行业分布柱状图 */}
        <div className="card chart-card">
          <h3>行业风险分布</h3>
          {stats?.industry_distribution?.length ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={stats.industry_distribution}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill={BAR_COLOR} radius={[4, 4, 0, 0]} name="事件数" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="chart-empty">暂无数据</div>
          )}
        </div>
      </div>

      <div className="chart-row">
        {/* 趋势折线图 */}
        <div className="card chart-card">
          <h3>近 30 天事件趋势</h3>
          {trend.length ? (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis yAxisId="left" />
                <YAxis yAxisId="right" orientation="right" />
                <Tooltip />
                <Legend />
                <Line yAxisId="left" type="monotone" dataKey="count" stroke="#2563eb" name="事件数" dot={false} />
                <Line yAxisId="right" type="monotone" dataKey="avg_score" stroke="#f59e0b" name="平均风险分" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="chart-empty">暂无数据</div>
          )}
        </div>

        {/* TOP10 高风险企业 */}
        <div className="card chart-card">
          <h3>TOP 10 高风险企业</h3>
          {stats?.top_enterprises?.length ? (
            <div className="rank-list">
              {stats.top_enterprises.map((ent, idx) => (
                <div key={ent.id} className="rank-item">
                  <span className={`rank-num ${idx < 3 ? 'rank-top' : ''}`}>{idx + 1}</span>
                  <span className="rank-name">{ent.name}</span>
                  <span className="rank-industry">{ent.industry}</span>
                  <span className="rank-score">{ent.avg_risk_score.toFixed(2)}</span>
                  <span className="rank-count">{ent.event_count} 事件</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="chart-empty">暂无数据</div>
          )}
        </div>
      </div>

      {/* ---- 最近舆情列表 ---- */}
      <div className="card">
        <h3>最近舆情事件</h3>
        <table className="table">
          <thead>
            <tr>
              <th>标题</th>
              <th>风险等级</th>
              <th>风险类型</th>
              <th>评分</th>
              <th>时间</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.id}>
                <td>{e.title}</td>
                <td><span className={levelClass(e.risk_level)}>{e.risk_level ?? '-'}</span></td>
                <td>{e.risk_type ?? '-'}</td>
                <td>{e.risk_score.toFixed(2)}</td>
                <td className="muted-text">{e.created_at ? new Date(e.created_at).toLocaleString('zh-CN') : '-'}</td>
              </tr>
            ))}
            {events.length === 0 && (
              <tr><td colSpan={5} style={{ textAlign: 'center' }}>暂无事件</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
