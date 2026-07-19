import { useState } from 'react'
import { api } from '../api'
import type { AnalyzeResult } from '../types'

const STEP_LABELS: Record<string, string> = {
  scan: 'Step 1 扫描',
  retrieve: 'RAG 检索',
  match: 'Step 2 匹配',
  predict: 'Step 3 预测',
  govern: 'Step 4 治理',
  expert_review: '专家审核',
  fast_exit: '快速通道',
  finalize: '完成',
}

const EXAMPLE_INPUTS = [
  {
    label: '外卖骑手冲突',
    text: '某外卖平台骑手因配送超时与消费者发生争执，引发网友热议。',
  },
  {
    label: '食品过期',
    text: '某食品企业被曝使用过期原料，视频在社交平台广泛传播，多名消费者表示食用后出现腹泻。',
  },
  {
    label: 'App 宕机',
    text: '某科技公司App发生大规模宕机，用户无法登录，客服电话被打爆。',
  },
]

function levelColor(level: string) {
  const map: Record<string, string> = { '低': '#16a34a', '中': '#f59e0b', '高': '#dc2626', '极高': '#991b1b' }
  return map[level] || '#6b7280'
}

export default function Analyze() {
  const [text, setText] = useState('')
  const [hint, setHint] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AnalyzeResult | null>(null)
  const [error, setError] = useState('')
  const [chainOpen, setChainOpen] = useState(false)
  const [activeStep, setActiveStep] = useState<string>('')
  const [completedSteps, setCompletedSteps] = useState<string[]>([])

  const canAnalyze = text.length >= 5 && !loading

  const handleAnalyze = async () => {
    if (!canAnalyze) return
    setLoading(true)
    setError('')
    setResult(null)
    setActiveStep('')
    setCompletedSteps([])
    try {
      const res = await api.analyzeStream(text, hint || undefined, (event) => {
        const update = event.node_update as Record<string, unknown> | undefined
        if (update) {
          const stepName = Object.keys(update)[0]
          if (stepName) {
            setActiveStep(stepName)
            setCompletedSteps((prev) => [...prev, stepName])
          }
        }
      })
      setResult(res as unknown as AnalyzeResult)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
      setActiveStep('')
    }
  }

  const scan = result?.scan as Record<string, any> | undefined
  const pred = result?.prediction as Record<string, any> | undefined
  const gov = result?.governance as Record<string, any> | undefined

  return (
    <div>
      <h2>舆情分析</h2>

      {/* ---- 输入区 ---- */}
      <div className="card">
        <div style={{ marginBottom: 12 }}>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.ctrlKey && e.key === 'Enter' && canAnalyze) {
                e.preventDefault()
                handleAnalyze()
              }
            }}
            placeholder="输入舆情文本，例如：某外卖平台骑手因配送超时与消费者发生争执，引发网友热议。"
          />
          <div className="input-meta">
            <div className="example-btns">
              <span className="muted-text">快速示例：</span>
              {EXAMPLE_INPUTS.map((ex) => (
                <button
                  key={ex.label}
                  className="btn-sm btn-outline"
                  onClick={() => { setText(ex.text); setHint(''); setResult(null); setError('') }}
                  disabled={loading}
                >
                  {ex.label}
                </button>
              ))}
            </div>
            <span className={`char-count ${text.length < 5 ? 'char-count-warn' : ''}`}>
              {text.length} 字
            </span>
          </div>
        </div>
        <div style={{ marginBottom: 12 }}>
          <input
            value={hint}
            onChange={(e) => setHint(e.target.value)}
            placeholder="企业名称提示（可选）"
          />
        </div>
        <button className="btn" onClick={handleAnalyze} disabled={!canAnalyze}>
          {loading ? '分析中...' : '开始分析（Ctrl + Enter）'}
        </button>
        {error && <div className="error-banner">{error}</div>}
      </div>

      {/* ---- 流式进度指示器 ---- */}
      {loading && (
        <div className="card stream-progress-card">
          <h3>分析进度</h3>
          <div className="stream-steps">
            {completedSteps.map((s, i) => (
              <div key={i} className="stream-step-item stream-step-done">
                <span className="stream-step-icon">&#10003;</span>
                <span>{STEP_LABELS[s] || s}</span>
              </div>
            ))}
            {activeStep && !completedSteps.includes(activeStep) && (
              <div className="stream-step-item stream-step-active">
                <span className="stream-step-icon stream-step-spinner" />
                <span>{STEP_LABELS[activeStep] || activeStep}</span>
              </div>
            )}
            {completedSteps.length === 0 && !activeStep && (
              <div className="stream-step-item stream-step-active">
                <span className="stream-step-icon stream-step-spinner" />
                <span>初始化...</span>
              </div>
            )}
          </div>
        </div>
      )}

      {result && (
        <>
          {/* ---- Step 1: 扫描结果 ---- */}
          <div className="step-card">
            <div className="step-header">
              <span className="step-badge">Step 1</span>
              <span>扫描结果</span>
            </div>
            <div className="step-body">
              <div className="step-grid">
                <div>
                  <span className="step-label">风险类型</span>
                  <span className="step-val">{String(scan?.risk_type ?? pred?.risk_type ?? '-')}</span>
                </div>
                <div>
                  <span className="step-label">情绪倾向</span>
                  <span className="step-val">{String(scan?.sentiment ?? '-')}</span>
                </div>
                <div>
                  <span className="step-label">置信度</span>
                  <div className="confidence-bar">
                    <div
                      className="confidence-fill"
                      style={{ width: `${(Number(scan?.confidence ?? 0) * 100)}%` }}
                    />
                  </div>
                  <span className="step-val-sm">{((Number(scan?.confidence ?? 0)) * 100).toFixed(0)}%</span>
                </div>
                <div>
                  <span className="step-label">关键实体</span>
                  <div className="tag-list">
                    {(scan?.entities as string[] || []).map((e: string, i: number) => (
                      <span key={i} className="tag-chip">{e}</span>
                    ))}
                    {!(scan?.entities as string[] | undefined)?.length && <span className="step-val">-</span>}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* ---- Step 2: 匹配案例 ---- */}
          <div className="step-card">
            <div className="step-header">
              <span className="step-badge">Step 2</span>
              <span>匹配案例</span>
            </div>
            <div className="step-body">
              {result.matched_cases.length ? (
                <div className="case-list">
                  {result.matched_cases.map((c) => (
                    <div key={c.id} className="case-item">
                      <div className="case-title">{c.title}</div>
                      <div className="case-meta">
                        <span className={c.risk_level === '高' || c.risk_level === '极高' ? 'text-danger' : ''}>
                          {c.risk_level}
                        </span>
                        <span className="muted-text">·</span>
                        <span className="muted-text">{c.risk_type}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="muted-text">无匹配案例</div>
              )}
            </div>
          </div>

          {/* ---- Step 3: 预测结果 ---- */}
          <div className="step-card">
            <div className="step-header">
              <span className="step-badge">Step 3</span>
              <span>预测结果</span>
            </div>
            <div className="step-body">
              <div className="prediction-main">
                <div className="risk-level-big" style={{ color: levelColor(String(pred?.risk_level ?? '')) }}>
                  {String(pred?.risk_level ?? '-')}
                </div>
                <div className="prediction-details">
                  <div>
                    <span className="step-label">风险评分</span>
                    <span className="step-val">{Number(pred?.risk_score ?? 0).toFixed(2)}</span>
                  </div>
                  <div>
                    <span className="step-label">时间窗口</span>
                    <span className="step-val">{String(pred?.time_horizon ?? pred?.time_window ?? '-')}</span>
                  </div>
                  <div>
                    <span className="step-label">响应时间</span>
                    <span className="step-val">{result.response_time_ms}ms</span>
                  </div>
                  {result.enterprise && (
                    <div>
                      <span className="step-label">匹配企业</span>
                      <span className="step-val">{result.enterprise.name}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* ---- Step 4: 治理方案 ---- */}
          <div className="step-card">
            <div className="step-header">
              <span className="step-badge">Step 4</span>
              <span>治理方案</span>
            </div>
            <div className="step-body">
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
                  {gov.spokesperson_script && (
                    <div className="gov-section gov-full">
                      <h4 className="gov-title">发言人话术</h4>
                      <blockquote className="gov-quote">{String(gov.spokesperson_script)}</blockquote>
                    </div>
                  )}
                  {gov.monitoring_plan && (
                    <div className="gov-section gov-full">
                      <h4 className="gov-title">监测计划</h4>
                      <ul className="gov-list">
                        {(gov.monitoring_plan as string[] || []).map((a: string, i: number) => (
                          <li key={i}>{a}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <div className="muted-text">无治理方案</div>
              )}
            </div>
          </div>

          {/* ---- 事件持久化信息 ---- */}
          {result.event_id > 0 && (
            <div className="card event-id-card">
              <span className="muted-text">事件编号</span>
              <span className="event-id">#{result.event_id}</span>
              <span className="muted-text">可在仪表盘查看历史记录</span>
            </div>
          )}

          {/* ---- 推理链折叠面板 ---- */}
          <div className="card chain-panel">
            <div className="chain-toggle" onClick={() => setChainOpen(!chainOpen)}>
              <span>{chainOpen ? '▼' : '▶'} 推理链详情（{result.reasoning_chain.length} 步）</span>
            </div>
            {chainOpen && (
              <div className="chain-body">
                {result.reasoning_chain.map((step, i) => (
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
        </>
      )}
    </div>
  )
}
