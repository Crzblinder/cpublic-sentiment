import { useCallback, useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts'
import { api } from '../api'
import { TrendCharts } from '../components'
import type { DashboardData } from '../types'

const PIE_COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#f97316', '#84cc16']
const BAR_COLOR = '#2563eb'

export default function SkillDashboard() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.getDashboard()
      setData(res)
      setUpdatedAt(new Date())
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const jobs = data?.jobs
  const skills = data?.skills
  const trends = data?.trends

  const avgSalary = jobs ? Math.round((jobs.avg_salary_min + jobs.avg_salary_max) / 2) : 0

  return (
    <div>
      <div className="page-header">
        <h2>技能图谱仪表盘</h2>
        <button className="btn btn-sm btn-outline" onClick={load} disabled={loading}>
          {loading ? '加载中...' : '刷新'}
        </button>
      </div>
      {error && <div className="error-banner">{error}</div>}
      {updatedAt && (
        <div className="muted-text" style={{ marginBottom: 12, fontSize: 12 }}>
          更新时间：{updatedAt.toLocaleString('zh-CN')}
        </div>
      )}

      {/* ---- 顶部指标卡片 ---- */}
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-label">岗位总数</div>
          <div className="stat-value">{jobs?.total_jobs ?? '-'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">技能总数</div>
          <div className="stat-value">{skills?.total_skills ?? '-'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">企业总数</div>
          <div className="stat-value">{jobs?.total_companies ?? '-'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">平均薪资</div>
          <div className="stat-value">{avgSalary ? `¥${avgSalary.toLocaleString()}` : '-'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">薪资区间</div>
          <div className="stat-value">
            {jobs ? `¥${jobs.avg_salary_min.toLocaleString()}-${jobs.avg_salary_max.toLocaleString()}` : '-'}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">技能关系数</div>
          <div className="stat-value">{skills?.total_relations ?? '-'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">热门岗位</div>
          <div className="stat-value">{trends?.hot_job_titles?.length ?? '-'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">热门技能</div>
          <div className="stat-value">{trends?.top_skills?.length ?? '-'}</div>
        </div>
      </div>

      {/* ---- 图表区域 ---- */}
      <TrendCharts
        topCities={jobs?.top_cities}
        experienceDistribution={jobs?.experience_distribution}
      />

      <div className="chart-row">
        {/* 热门技能饼图 */}
        <div className="card chart-card">
          <h3>热门技能分布</h3>
          {jobs?.hot_skills?.length ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={jobs.hot_skills.slice(0, 8)}
                  dataKey="count"
                  nameKey="skill"
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                  label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                >
                  {jobs.hot_skills.slice(0, 8).map((_, i) => (
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
          <h3>行业需求分布</h3>
          {jobs?.top_industries?.length ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={jobs.top_industries} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="industry" type="category" tick={{ fontSize: 12 }} width={80} />
                <Tooltip />
                <Bar dataKey="count" fill={BAR_COLOR} radius={[0, 4, 4, 0]} name="岗位数" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="chart-empty">暂无数据</div>
          )}
        </div>
      </div>

      {/* 趋势摘要 */}
      {trends?.summary && (
        <div className="card">
          <h3>市场趋势洞察</h3>
          <p className="muted-text" style={{ lineHeight: 1.7, margin: 0 }}>{trends.summary}</p>
          {trends.avg_salary_range && (
            <div style={{ marginTop: 12 }}>
              <span className="step-label">主流薪资范围</span>
              <span className="step-val">{trends.avg_salary_range}</span>
            </div>
          )}
        </div>
      )}

      {/* TOP10 热门岗位 */}
      {trends?.hot_job_titles?.length ? (
        <div className="card chart-card">
          <h3>热门岗位 TOP10</h3>
          <div className="rank-list">
            {trends.hot_job_titles.slice(0, 10).map((title, idx) => (
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
