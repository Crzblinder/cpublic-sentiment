import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import type { CaseItem } from '../types'

function levelClass(level: string) {
  const map: Record<string, string> = { '低': 'low', '中': 'medium', '高': 'high', '极高': 'critical' }
  return `badge ${map[level] || ''}`
}

const RISK_LEVELS = ['低', '中', '高', '极高']
const SEARCH_SUGGESTIONS = ['食品', '外卖', '数据', 'App', '召回', '直播', '房产', '教育']

export default function Cases() {
  const [cases, setCases] = useState<CaseItem[]>([])
  const [total, setTotal] = useState(0)
  const [industry, setIndustry] = useState('')
  const [riskType, setRiskType] = useState('')
  const [riskLevel, setRiskLevel] = useState('')
  const [search, setSearch] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [page, setPage] = useState(0)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [error, setError] = useState('')

  const pageSize = 15

  const load = useCallback((p = 0) => {
    api.listCases({
      industry: industry || undefined,
      risk_type: riskType || undefined,
      risk_level: riskLevel || undefined,
      search: search || undefined,
      skip: p * pageSize,
      limit: pageSize,
    })
      .then((res) => { setCases(res.items); setTotal(res.total) })
      .catch((e) => setError(e.message))
  }, [industry, riskType, riskLevel, search])

  useEffect(() => { load(0); setPage(0) }, [load])

  const handleSearch = () => { load(0); setPage(0); setShowSuggestions(false) }
  const clearFilters = () => {
    setIndustry('')
    setRiskType('')
    setRiskLevel('')
    setSearch('')
    setPage(0)
  }
  const maxPage = Math.ceil(total / pageSize)

  const activeFilterCount = [industry, riskType, riskLevel, search].filter(Boolean).length

  return (
    <div>
      <h2>风险案例库</h2>

      {/* 筛选栏 */}
      <div className="card filter-bar">
        <div className="search-with-suggestions">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
            placeholder="搜索标题关键词"
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
                  onMouseDown={() => { setSearch(kw); handleSearch() }}
                >
                  {kw}
                </button>
              ))}
            </div>
          )}
        </div>
        <input
          value={industry}
          onChange={(e) => setIndustry(e.target.value)}
          placeholder="行业筛选"
          style={{ maxWidth: 150 }}
        />
        <input
          value={riskType}
          onChange={(e) => setRiskType(e.target.value)}
          placeholder="风险类型"
          style={{ maxWidth: 150 }}
        />
        <select
          value={riskLevel}
          onChange={(e) => { setRiskLevel(e.target.value); setPage(0) }}
          className="filter-select"
        >
          <option value="">全部等级</option>
          {RISK_LEVELS.map((level) => (
            <option key={level} value={level}>{level}</option>
          ))}
        </select>
        <button className="btn" onClick={handleSearch}>筛选</button>
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
              <th style={{ width: 30 }}></th>
              <th>标题</th>
              <th>行业</th>
              <th>风险类型</th>
              <th>风险等级</th>
              <th>摘要</th>
            </tr>
          </thead>
          <tbody>
            {cases.map((c) => (
              <>
                <tr key={c.id} className="clickable-row" onClick={() => setExpandedId(expandedId === c.id ? null : c.id)}>
                  <td className="expand-icon">{expandedId === c.id ? '▼' : '▶'}</td>
                  <td>{c.title}</td>
                  <td>{c.industry}</td>
                  <td>{c.risk_type}</td>
                  <td><span className={levelClass(c.risk_level)}>{c.risk_level}</span></td>
                  <td className="summary-cell">{c.summary}</td>
                </tr>
                {expandedId === c.id && c.governance_playbook && (
                  <tr className="expanded-row">
                    <td colSpan={6}>
                      <div className="playbook-panel">
                        <h4>治理方案 (Playbook)</h4>
                        {typeof c.governance_playbook === 'object' ? (
                          <div className="playbook-grid">
                            {!!c.governance_playbook.immediate_actions && (
                              <div>
                                <strong>即时行动</strong>
                                <ul>{(c.governance_playbook.immediate_actions as string[]).map((a: string, i: number) => <li key={i}>{String(a)}</li>)}</ul>
                              </div>
                            )}
                            {!!c.governance_playbook.short_term && (
                              <div>
                                <strong>短期措施</strong>
                                <ul>{(c.governance_playbook.short_term as string[]).map((a: string, i: number) => <li key={i}>{String(a)}</li>)}</ul>
                              </div>
                            )}
                            {!!c.governance_playbook.long_term && (
                              <div>
                                <strong>长期策略</strong>
                                <ul>{(c.governance_playbook.long_term as string[]).map((a: string, i: number) => <li key={i}>{String(a)}</li>)}</ul>
                              </div>
                            )}
                            {!c.governance_playbook.immediate_actions && !c.governance_playbook.short_term && (
                              <pre>{JSON.stringify(c.governance_playbook, null, 2)}</pre>
                            )}
                          </div>
                        ) : (
                          <pre>{String(c.governance_playbook)}</pre>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
            {cases.length === 0 && (
              <tr><td colSpan={6} style={{ textAlign: 'center' }}>暂无案例</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* 分页 */}
      {maxPage > 1 && (
        <div className="pagination">
          <button className="btn btn-sm" disabled={page === 0} onClick={() => { const p = page - 1; setPage(p); load(p) }}>上一页</button>
          <span>{page + 1} / {maxPage}</span>
          <button className="btn btn-sm" disabled={page >= maxPage - 1} onClick={() => { const p = page + 1; setPage(p); load(p) }}>下一页</button>
        </div>
      )}
    </div>
  )
}
