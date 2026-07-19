import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { api } from '../api'
import type { Metrics } from '../types'

const SAMPLE_DATASET = [
  { text: '某外卖平台骑手因配送超时与消费者发生争执，引发网友热议。', true_risk_level: '中', true_risk_type: '劳资纠纷' },
  { text: '某新能源车企发布新一代固态电池，续航里程突破 1000 公里。', true_risk_level: '低', true_risk_type: '产品竞争力' },
  { text: '某食品企业被曝使用过期原料，视频在社交平台广泛传播。', true_risk_level: '高', true_risk_type: '食品安全' },
  { text: '某科技公司App发生大规模宕机，用户无法登录。', true_risk_level: '高', true_risk_type: '服务中断' },
]

interface AbVariant {
  variant: string
  accuracy: number
  recall: number
  avg_response_time_ms: number
}

export default function Evaluation() {
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [abResult, setAbResult] = useState<{ variants: AbVariant[]; summary: Record<string, any> } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [history, setHistory] = useState<Array<{ time: string; dataset_size: number; best_variant: string; accuracy: number }>>([])

  useEffect(() => {
    api.getMetrics().then(setMetrics).catch((e) => setError(e.message))
  }, [])

  const runTest = async (agentType?: string) => {
    setLoading(true)
    setError('')
    try {
      const res = await api.runAbTest(SAMPLE_DATASET, agentType) as any
      setAbResult(res)
      // 记录到历史
      const variants: AbVariant[] = res.variants || []
      const best = variants.reduce((a: AbVariant, b: AbVariant) => (a.accuracy >= b.accuracy ? a : b), variants[0])
      setHistory((prev) => [
        {
          time: new Date().toLocaleString('zh-CN'),
          dataset_size: SAMPLE_DATASET.length,
          best_variant: best?.variant || '-',
          accuracy: best?.accuracy ?? 0,
        },
        ...prev,
      ].slice(0, 10))
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // 为图表准备数据
  const chartData = abResult?.variants?.map((v: AbVariant) => ({
    name: v.variant,
    '准确率': +(v.accuracy * 100).toFixed(1),
    '召回率': +(v.recall * 100).toFixed(1),
    '延迟(ms)': v.avg_response_time_ms,
  })) || []

  return (
    <div>
      <h2>效果评估</h2>
      {error && <div className="error-banner">{error}</div>}

      {/* ---- 效能指标卡片 ---- */}
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-label">准确率</div>
          <div className="stat-value">{metrics ? `${(metrics.accuracy * 100).toFixed(1)}%` : '-'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">召回率</div>
          <div className="stat-value">{metrics ? `${(metrics.recall * 100).toFixed(1)}%` : '-'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">平均延迟</div>
          <div className="stat-value">{metrics ? `${metrics.avg_response_time_ms}ms` : '-'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">标注样本数</div>
          <div className="stat-value">{metrics?.labeled ?? '-'}</div>
        </div>
      </div>

      {/* ---- A/B 测试区 ---- */}
      <div className="card">
        <h3>A/B Prompt 测试</h3>
        <p className="label">使用 {SAMPLE_DATASET.length} 条示例数据快速对比不同 Prompt 变体的效果。</p>
        <div style={{ marginTop: 12, display: 'flex', gap: 12 }}>
          <button className="btn" onClick={() => runTest()} disabled={loading}>
            {loading ? '测试中...' : '全部 Agent 测试'}
          </button>
          <button className="btn btn-outline" onClick={() => runTest('scanner')} disabled={loading}>
            仅 Scanner
          </button>
        </div>
      </div>

      {/* ---- A/B 测试结果图表 ---- */}
      {chartData.length > 0 && (
        <div className="card chart-card">
          <h3>变体对比</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="准确率" fill="#2563eb" radius={[4, 4, 0, 0]} />
              <Bar dataKey="召回率" fill="#16a34a" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ---- 历史评测记录 ---- */}
      {history.length > 0 && (
        <div className="card">
          <h3>评测历史</h3>
          <table className="table">
            <thead>
              <tr>
                <th>时间</th>
                <th>数据集</th>
                <th>最佳变体</th>
                <th>准确率</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h, i) => (
                <tr key={i}>
                  <td className="muted-text">{h.time}</td>
                  <td>{h.dataset_size} 条</td>
                  <td>{h.best_variant}</td>
                  <td>{(h.accuracy * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
