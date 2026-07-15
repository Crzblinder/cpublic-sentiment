import { useEffect, useState } from 'react'
import { api } from '../api'
import type { Metrics } from '../types'

const SAMPLE_DATASET = [
  { text: '某外卖平台骑手因配送超时与消费者发生争执，引发网友热议。', true_risk_level: '中', true_risk_type: '劳资纠纷' },
  { text: '某新能源车企发布新一代固态电池，续航里程突破 1000 公里。', true_risk_level: '低', true_risk_type: '产品竞争力' },
  { text: '某食品企业被曝使用过期原料，视频在社交平台广泛传播。', true_risk_level: '高', true_risk_type: '食品安全' },
  { text: '某科技公司App发生大规模宕机，用户无法登录。', true_risk_level: '高', true_risk_type: '服务中断' },
]

export default function Evaluation() {
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [abResult, setAbResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getMetrics().then(setMetrics).catch((e) => setError(e.message))
  }, [])

  const runTest = async (agentType?: string) => {
    setLoading(true)
    setError('')
    try {
      const res = await api.runAbTest(SAMPLE_DATASET, agentType)
      setAbResult(res)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h2>效果评估</h2>
      <div className="grid">
        <div className="card">
          <div className="label">累计分析事件</div>
          <div className="metric">{metrics?.total ?? '-'}</div>
        </div>
        <div className="card">
          <div className="label">准确率</div>
          <div className="metric">{metrics ? `${(metrics.accuracy * 100).toFixed(1)}%` : '-'}</div>
        </div>
        <div className="card">
          <div className="label">召回率</div>
          <div className="metric">{metrics ? `${(metrics.recall * 100).toFixed(1)}%` : '-'}</div>
        </div>
        <div className="card">
          <div className="label">平均响应时间</div>
          <div className="metric">{metrics ? `${metrics.avg_response_time_ms}ms` : '-'}</div>
        </div>
      </div>

      <div className="card">
        <h3>A/B Prompt 测试</h3>
        <p className="label">使用 4 条示例数据快速对比不同 Prompt 技术的效果。</p>
        <div style={{ marginTop: 12, display: 'flex', gap: 12 }}>
          <button className="btn" onClick={() => runTest()} disabled={loading}>
            {loading ? '测试中...' : '全部 Agent 测试'}
          </button>
          <button className="btn" onClick={() => runTest('scanner')} disabled={loading}>
            仅 Scanner
          </button>
        </div>
        {error && <div style={{ color: 'red', marginTop: 12 }}>{error}</div>}
      </div>

      {abResult && (
        <div className="card">
          <h3>测试结果</h3>
          <pre>{JSON.stringify(abResult.summary, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}
