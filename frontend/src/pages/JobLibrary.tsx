import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { JobCard } from '../components'
import type { Job } from '../types'

const EXPERIENCE_LEVELS = ['不限', '应届生', '1-3年', '3-5年', '5-10年', '10年以上']
const SEARCH_SUGGESTIONS = ['Java', '前端', '算法', '产品', '运营', '数据分析', 'Go', 'Python']

interface Filters {
  search: string
  city: string
  industry: string
  experienceLevel: string
}

export default function JobLibrary() {
  const navigate = useNavigate()

  const [jobs, setJobs] = useState<Job[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const pageSize = 15

  const [filters, setFilters] = useState<Filters>({
    search: '',
    city: '',
    industry: '',
    experienceLevel: '',
  })
  const [showSuggestions, setShowSuggestions] = useState(false)

  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [selectedJob, setSelectedJob] = useState<Job | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  const load = useCallback(async (p: number) => {
    setLoading(true)
    setError('')
    try {
      const res = await api.listJobs({
        page: p,
        size: pageSize,
        q: filters.search || undefined,
        city: filters.city || undefined,
        industry: filters.industry || undefined,
        experience_level: filters.experienceLevel || undefined,
      })
      setJobs(res.items)
      setTotal(res.total)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [filters, pageSize])

  useEffect(() => {
    load(page)
  }, [load, page])

  const updateFilter = (key: keyof Filters, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
    setPage(1)
  }

  const openDetail = (job: Job) => {
    setDetailLoading(true)
    api.getJob(job.id)
      .then(setSelectedJob)
      .catch((e) => setError(e.message))
      .finally(() => setDetailLoading(false))
  }

  const handleSearch = () => { setPage(1); setShowSuggestions(false) }
  const clearFilters = () => {
    setFilters({ search: '', city: '', industry: '', experienceLevel: '' })
    setPage(1)
  }

  const maxPage = Math.max(1, Math.ceil(total / pageSize))
  const activeFilterCount = Object.values(filters).filter(Boolean).length

  return (
    <div>
      <h2>岗位库</h2>

      {/* 筛选栏 */}
      <div className="card filter-bar">
        <div className="search-with-suggestions">
          <input
            value={filters.search}
            onChange={(e) => updateFilter('search', e.target.value)}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
            placeholder="搜索岗位关键词"
            style={{ maxWidth: 220 }}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
          {showSuggestions && (
            <div className="search-suggestions">
              <div className="muted-text" style={{ padding: '6px 10px', fontSize: 12 }}>热门搜索</div>
              {SEARCH_SUGGESTIONS.map((kw) => (
                <button
                  key={kw}
                  className="suggestion-item"
                  onMouseDown={() => { updateFilter('search', kw); setShowSuggestions(false) }}
                >
                  {kw}
                </button>
              ))}
            </div>
          )}
        </div>
        <input
          value={filters.city}
          onChange={(e) => updateFilter('city', e.target.value)}
          placeholder="城市"
          style={{ maxWidth: 120 }}
        />
        <input
          value={filters.industry}
          onChange={(e) => updateFilter('industry', e.target.value)}
          placeholder="行业"
          style={{ maxWidth: 140 }}
        />
        <select
          value={filters.experienceLevel}
          onChange={(e) => updateFilter('experienceLevel', e.target.value)}
          className="filter-select"
        >
          <option value="">全部经验</option>
          {EXPERIENCE_LEVELS.map((level) => (
            <option key={level} value={level}>{level}</option>
          ))}
        </select>
        <button className="btn" onClick={handleSearch} disabled={loading}>筛选</button>
        {activeFilterCount > 0 && (
          <button className="btn btn-sm btn-outline" onClick={clearFilters}>清空</button>
        )}
        <span className="muted-text" style={{ marginLeft: 'auto' }}>共 {total} 条</span>
      </div>

      {activeFilterCount > 0 && (
        <div className="filter-summary">
          已启用 {activeFilterCount} 项筛选，找到 <strong>{total}</strong> 条结果
        </div>
      )}

      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>岗位</th>
              <th>公司</th>
              <th>城市</th>
              <th>薪资</th>
              <th>经验</th>
              <th>学历</th>
              <th>技能要求</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                onClick={openDetail}
                onMatchClick={(j) => navigate('/match', { state: { jobId: j.id } })}
              />
            ))}
            {jobs.length === 0 && (
              <tr><td colSpan={8} style={{ textAlign: 'center' }}>{loading ? '加载中...' : '暂无岗位'}</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* 分页 */}
      {maxPage > 1 && (
        <div className="pagination">
          <button
            className="btn btn-sm"
            disabled={page <= 1 || loading}
            onClick={() => setPage(page - 1)}
          >
            上一页
          </button>
          <span>{page} / {maxPage}</span>
          <button
            className="btn btn-sm"
            disabled={page >= maxPage || loading}
            onClick={() => setPage(page + 1)}
          >
            下一页
          </button>
        </div>
      )}

      {/* 详情抽屉面板 */}
      {detailLoading && <div className="drawer-overlay"><div className="spinner" /></div>}
      {selectedJob && !detailLoading && (
        <div className="drawer-overlay" onClick={() => setSelectedJob(null)}>
          <div className="drawer-panel" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-header">
              <h3>{selectedJob.title}</h3>
              <button className="btn btn-sm" onClick={() => setSelectedJob(null)}>关闭</button>
            </div>
            <div className="drawer-body">
              <div className="detail-section">
                <h4>基本信息</h4>
                <div className="detail-grid">
                  <div><span className="step-label">公司</span><span>{selectedJob.company.name}</span></div>
                  <div><span className="step-label">行业</span><span>{selectedJob.company.industry}</span></div>
                  <div><span className="step-label">规模</span><span>{selectedJob.company.size}</span></div>
                  <div><span className="step-label">城市</span><span>{selectedJob.city}</span></div>
                  <div><span className="step-label">薪资</span><span>¥{selectedJob.salary_min.toLocaleString()}-{selectedJob.salary_max.toLocaleString()}</span></div>
                  <div><span className="step-label">经验</span><span>{selectedJob.experience_level}</span></div>
                  <div><span className="step-label">学历</span><span>{selectedJob.education_level}</span></div>
                  <div><span className="step-label">发布时间</span><span>{selectedJob.posted_at ? new Date(selectedJob.posted_at).toLocaleDateString('zh-CN') : '-'}</span></div>
                </div>
              </div>

              <div className="detail-section">
                <h4>技能要求</h4>
                <div className="tag-list">
                  {selectedJob.required_skills.map((skill, i) => (
                    <span key={i} className="tag-chip">{skill}</span>
                  ))}
                </div>
              </div>

              <div className="detail-section">
                <h4>岗位描述</h4>
                <p style={{ margin: 0, lineHeight: 1.7, fontSize: 14, whiteSpace: 'pre-line' }}>{selectedJob.description}</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
