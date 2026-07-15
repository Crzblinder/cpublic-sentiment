import { useState } from 'react'
import { api } from '../api'
import type { AnalyzeResult } from '../types'

export default function Analyze() {
  const [text, setText] = useState('')
  const [hint, setHint] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AnalyzeResult | null>(null)
  const [error, setError] = useState('')

  const handleAnalyze = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.analyze(text, hint || undefined)
      setResult(res as AnalyzeResult)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h2>舆情分析</h2>
      <div className="card">
        <div style={{ marginBottom: 12 }}>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="输入舆情文本，例如：某外卖平台骑手因配送超时与消费者发生争执，引发网友热议。"
          />
        </div>
        <div style={{ marginBottom: 12 }}>
          <input
            value={hint}
            onChange={(e) => setHint(e.target.value)}
            placeholder="企业名称提示（可选）"
          />
        </div>
        <button className="btn" onClick={handleAnalyze} disabled={loading || text.length < 5}>
          {loading ? '分析中...' : '开始分析'}
        </button>
        {error && <div style={{ color: 'red', marginTop: 12 }}>{error}</div>}
      </div>

      {result && (
        <div className="card">
          <h3>分析结果</h3>
          <p><strong>风险等级：</strong>{String(result.prediction.risk_level)}</p>
          <p><strong>风险评分：</strong>{Number(result.prediction.risk_score).toFixed(2)}</p>
          <p><strong>风险类型：</strong>{String(result.prediction.risk_type)}</p>
          <p><strong>响应时间：</strong>{result.response_time_ms}ms</p>
          {result.enterprise && (
            <p><strong>匹配企业：</strong>{result.enterprise.name}（{result.enterprise.industry}）</p>
          )}
          <h4>匹配案例</h4>
          <ul>
            {result.matched_cases.map((c) => (
              <li key={c.id}>{c.title} [{c.risk_level}]</li>
            ))}
          </ul>
          <h4>治理方案</h4>
          <pre>{JSON.stringify(result.governance, null, 2)}</pre>
          <h4>推理链</h4>
          <pre>{JSON.stringify(result.reasoning_chain, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}
