import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import type { AnalysisHistoryItem, AnalysisHistoryDetail } from '../types'

function levelClass(level: string | null) {
  if (!level) return 'badge'
  const map: Record<string, string> = { '低': 'low', '中': 'medium', '高': 'high', '极高': 'critical' }
  return `badge ${map[level] || ''}`
}

function levelColor(level: string) {
  const map: Record<string, string> = { '低': '#16a34a', '中': '#f59e0b', '高': '#dc2626', '极高': '#991b1b' }
  return map[level] || '#6b7280'
}

export default function History() {
  const [items, setItems] = useState<AnalysisHistoryItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<AnalysisHistoryDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [chainOpen, setChainOpen] = useState(false)

  const pageSize = 20

  const load = useCallback((p = 0) => {
    api.listAnalysisHistory(p * pageSize, pageSize)
      .then((res) => { setItems(res.items); setTotal(res.total) })
      .catch((e) => setError(e.message))
  }, [])

  useEffect(() => { load(0); setPage(0) }, [load])

  const openDetail = (id: number) => {
    setDetailLoading(true)
    setChainOpen(false)
    api.getAnalysisHistoryDetail(id)
      .then(setSelected)
      .catch((e) => setError(e.message))
      .finally(() => setDetailLoading(false))
  }

  const maxPage = Math.ceil(total / pageSize)
  const scan = selected?.scan_result as Record<string, unknown> | undefined
  const pred = selected?.prediction as Record<string, unknown> | undefined
  const gov = selected?.governance as Record<string, unknown> | undefined

  return (
    <div>
      <h2>分析历史</h2>

      {error && <div className="error-banner">{error}</div>}

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>时间</th>
              <th>文本摘要</th>
              <th>风险等级</th>
              <th>风险类型</th>
              <th>评分</th>
              <th>响应</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {items.map((h) => (
              <tr key={h.id}>
                <td className="muted-text" style={{ fontSize: 12, whiteSpace: 'nowrap' }}>
                  {h.created_at ? new Date(h.created_at).toLocaleString('zh-CN') : '-'}
                </td>
                <td style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {h.text}
                </td>
                <td><span className={levelClass(h.risk_level)}>{h.risk_level ?? '-'}</span></td>
                <td>{h.risk_type ?? '-'}</td>
                <td>{h.risk_score ?? '-'}</td>
                <td className="muted-text">{h.response_time_ms != null ? `${h.response_time_ms}ms` : '-'}</td>
                <td>
                  <button className="btn btn-sm btn-outline" onClick={() => openDetail(h.id)}>详情</button>
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr><td colSpan={7} style={{ textAlign: 'center' }}>
                暂无分析记录，请前往「舆情分析」页面进行分析
              </td></tr>
            )}
          </tbody>
        </table>
      </div>

      {maxPage > 1 && (
        <div className="pagination">
          <button className="btn btn-sm" disabled={page === 0} onClick={() => { const p = page - 1; setPage(p); load(p) }}>上一页</button>
          <span>{page + 1} / {maxPage}</span>
          <button className="btn btn-sm" disabled={page >= maxPage - 1} onClick={() => { const p = page + 1; setPage(p); load(p) }}>下一页</button>
        </div>
      )}

      {/* 详情抽屉 */}
      {detailLoading && <div className="drawer-overlay"><div className="spinner" /></div>}
      {selected && !detailLoading && (
        <div className="drawer-overlay" onClick={() => setSelected(null)}>
          <div className="drawer-panel" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-header">
              <h3>分析详情 #{selected.id}</h3>
              <button className="btn btn-sm" onClick={() => setSelected(null)}>关闭</button>
            </div>

            <div className="drawer-body">
              {/* 原始文本 */}
              <div className="detail-section">
                <h4>原始文本</h4>
                <p style={{ lineHeight: 1.8, color: 'var(--text-secondary)' }}>{selected.text}</p>
              </div>

              {/* 扫描结果 */}
              <div className="detail-section">
                <h4>扫描结果</h4>
                <div className="detail-grid">
                  <div><span className="step-label">风险类型</span><span>{String(scan?.risk_type ?? pred?.risk_type ?? '-')}</span></div>
                  <div><span className="step-label">情绪倾向</span><span>{String(scan?.sentiment ?? '-')}</span></div>
                  <div><span className="step-label">置信度</span><span>{((Number(scan?.confidence ?? 0)) * 100).toFixed(0)}%</span></div>
                </div>
                <div className="tag-list" style={{ marginTop: 8 }}>
                  {(scan?.entities as string[] || []).map((e: string, i: number) => (
                    <span key={i} className="tag-chip">{e}</span>
                  ))}
                </div>
              </div>

              {/* 匹配案例 */}
              <div className="detail-section">
                <h4>匹配案例</h4>
                {selected.matched_cases?.length ? (
                  <div className="case-list">
                    {selected.matched_cases.map((c: Record<string, unknown>, i: number) => (
                      <div key={i} className="case-item">
                        <div className="case-title">{String(c.title || '')}</div>
                        <div className="case-meta">
                          <span className={String(c.risk_level || '') === '高' || String(c.risk_level || '') === '极高' ? 'text-danger' : ''}>
                            {String(c.risk_level || '')}
                          </span>
                          <span className="muted-text">·</span>
                          <span className="muted-text">{String(c.risk_type || '')}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="muted-text">无匹配案例</div>
                )}
              </div>

              {/* 预测结果 */}
              <div className="detail-section">
                <h4>预测结果</h4>
                <div className="prediction-main">
                  <div className="risk-level-big" style={{ color: levelColor(String(pred?.risk_level ?? '')) }}>
                    {String(pred?.risk_level ?? '-')}
                  </div>
                  <div className="prediction-details">
                    <div><span className="step-label">风险评分</span><span className="step-val">{Number(pred?.risk_score ?? 0).toFixed(2)}</span></div>
                    <div><span className="step-label">时间窗口</span><span className="step-val">{String(pred?.time_horizon ?? pred?.time_window ?? '-')}</span></div>
                    <div><span className="step-label">响应时间</span><span className="step-val">{selected.response_time_ms}ms</span></div>
                  </div>
                </div>
              </div>

              {/* 治理方案 */}
              <div className="detail-section">
                <h4>治理方案</h4>
                {gov ? (
                  <div className="governance-grid">
                    <div className="gov-section">
                      <h4 className="gov-title gov-immediate">即时行动</h4>
                      <ul className="gov-list">
                        {(gov.immediate_actions as string[] || []).map((a: string, i: number) => (
                          <li key={i}>{a}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="gov-section">
                      <h4 className="gov-title gov-short">短期措施</h4>
                      <ul className="gov-list">
                        {(gov.short_term as string[] || []).map((a: string, i: number) => (
                          <li key={i}>{a}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="gov-section">
                      <h4 className="gov-title gov-long">长期策略</h4>
                      <ul className="gov-list">
                        {(gov.long_term as string[] || []).map((a: string, i: number) => (
                          <li key={i}>{a}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                ) : (
                  <div className="muted-text">无治理方案</div>
                )}
              </div>

              {/* 推理链 */}
              {selected.reasoning_chain?.length > 0 && (
                <div className="detail-section">
                  <div className="chain-toggle" onClick={() => setChainOpen(!chainOpen)}>
                    <span>{chainOpen ? '▼' : '▶'} 推理链详情（{selected.reasoning_chain.length} 步）</span>
                  </div>
                  {chainOpen && (
                    <div className="chain-body">
                      {selected.reasoning_chain.map((step: Record<string, unknown>, i: number) => (
                        <div key={i} className="chain-step">
                          <div className="chain-step-label">
                            {String(step.agent || step.step || `Step ${i + 1}`)}
                          </div>
                          <pre>{typeof step === 'string' ? step : JSON.stringify(step, null, 2)}</pre>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}