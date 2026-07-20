import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { TrendCharts } from '../components'
import type { DashboardData, TrendAnalysis as TrendData } from '../types'

function normalizeTopSkills(skills: string[] | null | undefined, hotSkills: { skill: string; count: number }[]) {
  if (!skills?.length) return hotSkills.slice(0, 10)
  return skills.map((name) => {
    const found = hotSkills.find((h) => h.skill === name)
    return { skill: name, count: found?.count ?? 1 }
  })
}

export default function TrendAnalysis() {
  const [trend, setTrend] = useState<TrendData | null>(null)
  const [dashboard, setDashboard] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [trendRes, dashboardRes] = await Promise.all([
        api.getTrends().catch((e) => { setError((prev) => prev || e.message); return null }),
        api.getDashboard().catch((e) => { setError((prev) => prev || e.message); return null }),
      ])
      if (trendRes) setTrend(trendRes)
      if (dashboardRes) setDashboard(dashboardRes)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const topSkills = useMemo(
    () => normalizeTopSkills(trend?.top_skills, dashboard?.jobs.hot_skills || []),
    [trend, dashboard],
  )

  const salaryDistribution = useMemo(() => {
    const jobs = dashboard?.jobs
    if (!jobs) return []
    return [
      { range: '最低平均', value: jobs.avg_salary_min },
      { range: '最高平均', value: jobs.avg_salary_max },
    ]
  }, [dashboard])

  return (
    <div>
      <div className="page-header">
        <h2>岗位趋势分析</h2>
        <button className="btn btn-sm btn-outline" onClick={load} disabled={loading}>
          {loading ? '加载中...' : '刷新'}
        </button>
      </div>
      {error && <div className="error-banner">{error}</div>}

      {/* 摘要 */}
      {trend?.summary && (
        <div className="card">
          <h3>趋势摘要</h3>
          <p className="muted-text" style={{ lineHeight: 1.7, margin: 0 }}>{trend.summary}</p>
        </div>
      )}

      {/* 关键指标 */}
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-label">岗位总数</div>
          <div className="stat-value">{dashboard?.jobs.total_jobs ?? '-'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">平均薪资下限</div>
          <div className="stat-value">
            {dashboard ? `¥${dashboard.jobs.avg_salary_min.toLocaleString()}` : '-'}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">平均薪资上限</div>
          <div className="stat-value">
            {dashboard ? `¥${dashboard.jobs.avg_salary_max.toLocaleString()}` : '-'}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">主流薪资范围</div>
          <div className="stat-value">{trend?.avg_salary_range ?? '-'}</div>
        </div>
      </div>

      <TrendCharts
        topSkills={topSkills}
        topCities={dashboard?.jobs.top_cities}
        salaryDistribution={salaryDistribution}
        experienceDistribution={dashboard?.jobs.experience_distribution}
      />

      {/* 关键指标表格 */}
      {trend?.key_metrics && Object.keys(trend.key_metrics).length > 0 && (
        <div className="card">
          <h3>关键指标</h3>
          <table className="table">
            <thead>
              <tr><th>指标</th><th>数值</th></tr>
            </thead>
            <tbody>
              {Object.entries(trend.key_metrics).map(([key, value]) => (
                <tr key={key}>
                  <td>{key}</td>
                  <td>{typeof value === 'number' ? value.toLocaleString() : String(value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 热门岗位 */}
      {trend?.hot_job_titles?.length ? (
        <div className="card chart-card">
          <h3>热门岗位</h3>
          <div className="rank-list">
            {trend.hot_job_titles.map((title, idx) => (
              <div key={idx} className="rank-item">
                <span className={`rank-num ${idx < 3 ? 'rank-top' : ''}`}>{idx + 1}</span>
                <span className="rank-name">{title}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}
