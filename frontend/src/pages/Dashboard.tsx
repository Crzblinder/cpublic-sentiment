import { useCallback, useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
  LineChart, Line,
} from 'recharts'
import { api } from '../api'
import type { CrawlerStatus, DashboardStats, TrendPoint, EventItem } from '../types'

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
  const [crawlerStatus, setCrawlerStatus] = useState<CrawlerStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState<string[]>([])
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setErrors([])
    const nextErrors: string[] = []
    try {
      const [statsRes, trendRes, eventsRes, crawlerRes] = await Promise.all([
        api.getDashboardStats().catch((e) => { nextErrors.push(`统计: ${e.message}`); return null }),
        api.getTrend(30).catch((e) => { nextErrors.push(`趋势: ${e.message}`); return [] }),
        api.listEvents(0, 20).catch((e) => { nextErrors.push(`事件: ${e.message}`); return [] }),
        api.getCrawlerStatus().catch((e) => { nextErrors.push(`爬虫状态: ${e.message}`); return null }),
      ])
      if (statsRes) setStats(statsRes)
      if (trendRes) setTrend(trendRes as TrendPoint[])
      if (eventsRes) setEvents(eventsRes as EventItem[])
      if (crawlerRes) setCrawlerStatus(crawlerRes)
      setUpdatedAt(new Date())
      if (nextErrors.length) setErrors(nextErrors)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const s = stats?.summary

  return (
    <div>
      <div className="page-header">
        <h2>仪表盘</h2>
        <button className="btn btn-sm btn-outline" onClick={load} disabled={loading}>
          {loading ? '加载中...' : '刷新'}
        </button>
      </div>
      {errors.map((err, i) => (
        <div key={i} className="error-banner">{err}</div>
      ))}
      {updatedAt && (
        <div className="muted-text" style={{ marginBottom: 12, fontSize: 12 }}>
          更新时间：{updatedAt.toLocaleString('zh-CN')}
        </div>
      )}

      {/* ---- 顶部指标卡片 ---- */}
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-label">累计分析事件</div>
          <div className="stat-value">{s?.total_events ?? '-'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">今日新增</div>
          <div className="stat-value">{s?.today_events ?? '-'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">近 7 天高风险</div>
          <div className="stat-value">{s?.week_high_risk_events ?? '-'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">高风险占比</div>
          <div className="stat-value">{s ? `${(s.high_risk_ratio * 100).toFixed(1)}%` : '-'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">平均风险分</div>
          <div className="stat-value">{s ? s.avg_risk_score.toFixed(2) : '-'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">平均响应时间</div>
          <div className="stat-value">{s ? `${s.avg_response_time_ms.toFixed(0)}ms` : '-'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">系统准确率</div>
          <div className="stat-value">{s ? `${(s.accuracy * 100).toFixed(1)}%` : '-'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">已标注样本</div>
          <div className="stat-value">{s?.labeled_count ?? '-'}</div>
        </div>
      </div>

      {/* ---- 数据源状态卡片 ---- */}
      <div className="card" style={{ marginBottom: 16 }}>
        <h3>数据源状态</h3>
        {crawlerStatus?.last_run ? (
          <div>
            <div className="muted-text" style={{ marginBottom: 8, fontSize: 12 }}>
              最近运行：{new Date(crawlerStatus.last_run).toLocaleString('zh-CN')}
              {' | '}
              总采集量：{crawlerStatus.total_fetched} 条
              {' | '}
              成功源：{crawlerStatus.sources_ok.length}
              {' | '}
              失败源：{crawlerStatus.sources_failed.length}
            </div>
            {crawlerStatus.sources_detail && crawlerStatus.sources_detail.length > 0 && (
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                {crawlerStatus.sources_detail.map((src) => (
                  <div
                    key={src.name}
                    style={{
                      padding: '6px 12px',
                      borderRadius: 6,
                      border: `1px solid ${src.ok ? '#16a34a40' : '#dc262640'}`,
                      background: src.ok ? '#16a34a0a' : '#dc26260a',
                      fontSize: 13,
                    }}
                  >
                    <span style={{ fontWeight: 600 }}>{src.name}</span>
                    {' '}
                    <span className={src.ok ? 'muted-text' : ''} style={{ color: src.ok ? '#16a34a' : '#dc2626' }}>
                      {src.ok ? `✓ ${src.count} 条` : '✗ 失败'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="chart-empty">
            爬虫尚未运行，请前往「舆情分析」页面触发采集
          </div>
        )}
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
            <div className="chart-empty">暂无数据，请先运行爬虫采集</div>
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
            <div className="chart-empty">暂无数据，请先运行爬虫采集</div>
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
            <div className="chart-empty">暂无数据，请先运行爬虫采集</div>
          )}
        </div>

        {/* 风险类型分布 */}
        <div className="card chart-card">
          <h3>风险类型 TOP10</h3>
          {stats?.risk_type_distribution?.length ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={stats.risk_type_distribution} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 12 }} width={80} />
                <Tooltip />
                <Bar dataKey="value" fill={BAR_COLOR} radius={[0, 4, 4, 0]} name="事件数" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="chart-empty">暂无数据，请先运行爬虫采集</div>
          )}
        </div>
      </div>

      {/* TOP10 高风险企业：整行展示，避免右侧留白 */}
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
            <div className="chart-empty">暂无数据，请先运行爬虫采集</div>
          )}
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
              <th>来源</th>
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
                <td className="muted-text" style={{ fontSize: 12 }}>{e.source ?? '-'}</td>
                <td>{e.risk_score.toFixed(2)}</td>
                <td className="muted-text">{e.created_at ? new Date(e.created_at).toLocaleString('zh-CN') : '-'}</td>
              </tr>
            ))}
            {events.length === 0 && (
              <tr><td colSpan={6} style={{ textAlign: 'center' }}>
                暂无事件，请先运行爬虫采集数据
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
