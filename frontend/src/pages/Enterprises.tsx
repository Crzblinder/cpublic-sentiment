import { useEffect, useState } from 'react'
import { LineChart, Line, ResponsiveContainer } from 'recharts'
import { api } from '../api'
import type { EnterpriseItem, EnterpriseDetail } from '../types'

function riskDot(score: number) {
  if (score >= 70) return '#dc2626'
  if (score >= 40) return '#f59e0b'
  return '#16a34a'
}

export default function Enterprises() {
  const [enterprises, setEnterprises] = useState<EnterpriseItem[]>([])
  const [total, setTotal] = useState(0)
  const [industry, setIndustry] = useState('')
  const [page, setPage] = useState(0)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<EnterpriseDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  const pageSize = 12

  const load = (p = 0) => {
    api.listEnterprises({ industry: industry || undefined, skip: p * pageSize, limit: pageSize })
      .then((res) => { setEnterprises(res.items); setTotal(res.total) })
      .catch((e) => setError(e.message))
  }

  useEffect(() => { load(0); setPage(0) }, [])

  const openDetail = (id: number) => {
    setDetailLoading(true)
    api.getEnterpriseDetail(id)
      .then(setSelected)
      .catch((e) => setError(e.message))
      .finally(() => setDetailLoading(false))
  }

  const maxPage = Math.ceil(total / pageSize)

  return (
    <div>
      <h2>企业画像</h2>

      {/* 筛选栏 */}
      <div className="card filter-bar">
        <input
          value={industry}
          onChange={(e) => setIndustry(e.target.value)}
          placeholder="行业筛选"
          style={{ maxWidth: 220 }}
        />
        <button className="btn" onClick={() => { load(0); setPage(0) }}>筛选</button>
        <span className="muted-text" style={{ marginLeft: 'auto' }}>共 {total} 家企业</span>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="enterprise-layout">
        {/* 卡片网格 */}
        <div className="ent-card-grid">
          {enterprises.map((ent) => {
            const lastScore = ent.risk_score_history?.length
              ? ent.risk_score_history[ent.risk_score_history.length - 1].score
              : 0
            return (
              <div key={ent.id} className="ent-card" onClick={() => openDetail(ent.id)}>
                <div className="ent-card-header">
                  <span className="ent-name">{ent.name}</span>
                  <span className="risk-dot" style={{ background: riskDot(lastScore) }} />
                </div>
                <div className="ent-meta">
                  <span>{ent.industry}</span>
                  <span>{ent.scale}</span>
                  <span>{ent.region}</span>
                </div>
                <div className="ent-tags">
                  {(ent.business_tags || []).slice(0, 4).map((tag, i) => (
                    <span key={i} className="tag-chip">{tag}</span>
                  ))}
                </div>
                {ent.risk_score_history?.length > 1 && (
                  <div className="sparkline">
                    <ResponsiveContainer width="100%" height={40}>
                      <LineChart data={ent.risk_score_history}>
                        <Line type="monotone" dataKey="score" stroke={riskDot(lastScore)} dot={false} strokeWidth={2} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
                <div className="ent-score">
                  风险评分 <strong>{lastScore.toFixed(1)}</strong>
                </div>
              </div>
            )
          })}
          {enterprises.length === 0 && <div className="muted-text">暂无企业数据</div>}
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

      {/* 详情抽屉面板 */}
      {detailLoading && <div className="drawer-overlay"><div className="spinner" /></div>}
      {selected && !detailLoading && (
        <div className="drawer-overlay" onClick={() => setSelected(null)}>
          <div className="drawer-panel" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-header">
              <h3>{selected.enterprise.name}</h3>
              <button className="btn btn-sm" onClick={() => setSelected(null)}>关闭</button>
            </div>

            <div className="drawer-body">
              {/* 基本信息 */}
              <div className="detail-section">
                <h4>企业画像</h4>
                <div className="detail-grid">
                  <div><span className="step-label">行业</span><span>{selected.enterprise.industry}</span></div>
                  <div><span className="step-label">规模</span><span>{selected.enterprise.scale}</span></div>
                  <div><span className="step-label">地区</span><span>{selected.enterprise.region}</span></div>
                  <div><span className="step-label">行业排名</span><span>#{selected.rank_in_industry ?? '-'}</span></div>
                </div>
                <div className="ent-tags" style={{ marginTop: 8 }}>
                  {(selected.enterprise.business_tags || []).map((tag, i) => (
                    <span key={i} className="tag-chip">{tag}</span>
                  ))}
                </div>
              </div>

              {/* 风险趋势 */}
              {selected.enterprise.risk_score_history?.length > 1 && (
                <div className="detail-section">
                  <h4>风险趋势（6个月）</h4>
                  <ResponsiveContainer width="100%" height={120}>
                    <LineChart data={selected.enterprise.risk_score_history}>
                      <Line type="monotone" dataKey="score" stroke="#2563eb" dot strokeWidth={3} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* 同行业对比 */}
              {selected.industry_peers?.length > 0 && (
                <div className="detail-section">
                  <h4>同行业风险对比</h4>
                  <table className="table">
                    <thead><tr><th>企业</th><th>平均风险分</th></tr></thead>
                    <tbody>
                      {selected.industry_peers.map((p) => (
                        <tr key={p.id} style={p.id === selected.enterprise.id ? { fontWeight: 700 } : {}}>
                          <td>{p.name}{p.id === selected.enterprise.id ? ' ★' : ''}</td>
                          <td>{p.avg_risk_score.toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* 关联事件 */}
              <div className="detail-section">
                <h4>关联舆情事件（最近 20 条）</h4>
                {selected.events.length ? (
                  <table className="table">
                    <thead><tr><th>标题</th><th>等级</th><th>评分</th><th>时间</th></tr></thead>
                    <tbody>
                      {selected.events.map((ev) => (
                        <tr key={ev.id}>
                          <td>{ev.title}</td>
                          <td><span className={`badge ${ev.risk_level === '高' || ev.risk_level === '极高' ? 'high' : ev.risk_level === '中' ? 'medium' : 'low'}`}>{ev.risk_level ?? '-'}</span></td>
                          <td>{ev.risk_score.toFixed(2)}</td>
                          <td className="muted-text">{ev.created_at ? new Date(ev.created_at).toLocaleDateString('zh-CN') : '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="muted-text">暂无关联事件</div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
