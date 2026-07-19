import { useEffect, useMemo, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
} from 'recharts'
import { api } from '../api'
import type { LlmStatus, Metrics } from '../types'

interface DatasetItem {
  text: string
  true_risk_level: string
  true_risk_type: string
}

const DATASET_OPTIONS: { label: string; value: string; items: DatasetItem[] }[] = [
  {
    label: '示例集（4 条）',
    value: 'tiny',
    items: [
      { text: '某外卖平台骑手因配送超时与消费者发生争执，引发网友热议。', true_risk_level: '中', true_risk_type: '劳资纠纷' },
      { text: '某新能源车企发布新一代固态电池，续航里程突破 1000 公里。', true_risk_level: '低', true_risk_type: '产品竞争力' },
      { text: '某食品企业被曝使用过期原料，视频在社交平台广泛传播。', true_risk_level: '高', true_risk_type: '食品安全' },
      { text: '某科技公司App发生大规模宕机，用户无法登录。', true_risk_level: '高', true_risk_type: '服务中断' },
    ],
  },
  {
    label: '扩展集（8 条）',
    value: 'small',
    items: [
      { text: '某外卖平台骑手因配送超时与消费者发生争执，引发网友热议。', true_risk_level: '中', true_risk_type: '劳资纠纷' },
      { text: '某新能源车企发布新一代固态电池，续航里程突破 1000 公里。', true_risk_level: '低', true_risk_type: '产品竞争力' },
      { text: '某食品企业被曝使用过期原料，视频在社交平台广泛传播。', true_risk_level: '高', true_risk_type: '食品安全' },
      { text: '某科技公司App发生大规模宕机，用户无法登录。', true_risk_level: '高', true_risk_type: '服务中断' },
      { text: '某银行被曝客户数据泄露，近百万条个人信息在暗网出售。', true_risk_level: '极高', true_risk_type: '数据泄露' },
      { text: '某直播平台主播销售假冒伪劣商品，遭消费者集体投诉。', true_risk_level: '高', true_risk_type: '产品质量' },
      { text: '某房企因资金链断裂导致多个楼盘停工，业主聚集维权。', true_risk_level: '极高', true_risk_type: '财务风险' },
      { text: '某教育机构突然关闭线下门店，家长退费困难。', true_risk_level: '中', true_risk_type: '服务质量' },
    ],
  },
  {
    label: '标准集（12 条）',
    value: 'medium',
    items: [
      { text: '某外卖平台骑手因配送超时与消费者发生争执，引发网友热议。', true_risk_level: '中', true_risk_type: '劳资纠纷' },
      { text: '某新能源车企发布新一代固态电池，续航里程突破 1000 公里。', true_risk_level: '低', true_risk_type: '产品竞争力' },
      { text: '某食品企业被曝使用过期原料，视频在社交平台广泛传播。', true_risk_level: '高', true_risk_type: '食品安全' },
      { text: '某科技公司App发生大规模宕机，用户无法登录。', true_risk_level: '高', true_risk_type: '服务中断' },
      { text: '某银行被曝客户数据泄露，近百万条个人信息在暗网出售。', true_risk_level: '极高', true_risk_type: '数据泄露' },
      { text: '某直播平台主播销售假冒伪劣商品，遭消费者集体投诉。', true_risk_level: '高', true_risk_type: '产品质量' },
      { text: '某房企因资金链断裂导致多个楼盘停工，业主聚集维权。', true_risk_level: '极高', true_risk_type: '财务风险' },
      { text: '某教育机构突然关闭线下门店，家长退费困难。', true_risk_level: '中', true_risk_type: '服务质量' },
      { text: '某网约车平台被曝算法压榨司机，连续工作时长超过 12 小时。', true_risk_level: '中', true_risk_type: '劳资纠纷' },
      { text: '某汽车品牌召回 10 万辆缺陷车辆，存在刹车失灵隐患。', true_risk_level: '高', true_risk_type: '产品质量' },
      { text: '某电商平台被曝光纵容商家刷单炒信，扰乱市场秩序。', true_risk_level: '中', true_risk_type: '合规风险' },
      { text: '某游戏公司未成年人充值退款流程复杂，被家长多次举报。', true_risk_level: '低', true_risk_type: '合规风险' },
    ],
  },
]

const AGENT_OPTIONS = [
  { label: '全部 Agent', value: '' },
  { label: 'Scanner', value: 'scanner' },
  { label: 'Matcher', value: 'matcher' },
  { label: 'Predictor', value: 'predictor' },
  { label: 'Governance', value: 'governance' },
  { label: 'Expert', value: 'expert' },
]

interface VariantMetric {
  agent_type: string
  technique: string
  accuracy_level: number
  accuracy_type: number
  recall_relevant: number
  avg_latency_ms: number
  samples: number
}

interface AbResult {
  run_id: number
  dataset_size: number
  summary: Record<string, VariantMetric>
}

interface HistoryItem {
  time: string
  dataset_size: number
  agent_type: string
  best_variant: string
  best_technique: string
  accuracy_level: number
  avg_latency_ms: number
}

const TECHNIQUE_ORDER = ['zero_shot', 'cot', 'few_shot', 'role_play']

function techniqueLabel(tech: string) {
  const map: Record<string, string> = {
    zero_shot: 'Zero-Shot',
    cot: 'CoT',
    few_shot: 'Few-Shot',
    role_play: 'RolePlay',
  }
  return map[tech] || tech
}

function agentLabel(agentType: string) {
  const found = AGENT_OPTIONS.find((a) => a.value === agentType)
  return found?.label || agentType || '全部 Agent'
}

export default function Evaluation() {
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [llmStatus, setLlmStatus] = useState<LlmStatus | null>(null)
  const [abResult, setAbResult] = useState<AbResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [agentType, setAgentType] = useState('')
  const [datasetKey, setDatasetKey] = useState('small')
  const [history, setHistory] = useState<HistoryItem[]>([])

  const dataset = useMemo(
    () => DATASET_OPTIONS.find((d) => d.value === datasetKey)?.items || DATASET_OPTIONS[1].items,
    [datasetKey],
  )

  useEffect(() => {
    api.getMetrics().then(setMetrics).catch((e) => setError(e.message))
    api.getLlmStatus().then(setLlmStatus).catch(() => { /* ignore */ })
  }, [])

  const runTest = async () => {
    setLoading(true)
    setError('')
    try {
      const res = (await api.runAbTest(dataset, agentType || undefined)) as AbResult
      setAbResult(res)
      const variants = Object.entries(res.summary || {}).map(([variant, m]) => ({ variant, ...m })) as Array<VariantMetric & { variant: string }>
      const best = variants.reduce((a, b) => (a.accuracy_level >= b.accuracy_level ? a : b), variants[0])
      setHistory((prev) =>
        [
          {
            time: new Date().toLocaleString('zh-CN'),
            dataset_size: res.dataset_size,
            agent_type: agentType,
            best_variant: best?.variant || '-',
            best_technique: techniqueLabel(best?.technique || '-'),
            accuracy_level: best?.accuracy_level ?? 0,
            avg_latency_ms: best?.avg_latency_ms ?? 0,
          },
          ...prev,
        ].slice(0, 10))
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const variants = useMemo(
    () => Object.entries(abResult?.summary || {}).map(([variant, m]) => ({ variant, ...m })) as Array<VariantMetric & { variant: string }>,
    [abResult],
  )

  const chartData = useMemo(
    () =>
      variants.map((v) => ({
        name: v.variant,
        '等级准确率': +(v.accuracy_level * 100).toFixed(1),
        '类型准确率': +(v.accuracy_type * 100).toFixed(1),
        '相关召回率': +(v.recall_relevant * 100).toFixed(1),
        '延迟(ms)': v.avg_latency_ms,
      })),
    [variants],
  )

  const radarData = useMemo(() => {
    if (variants.length < 2) return []
    return TECHNIQUE_ORDER.map((tech) => {
      const rows = variants.filter((v) => v.technique === tech)
      if (!rows.length) return null
      return {
        technique: techniqueLabel(tech),
        等级准确率: +(rows.reduce((s, v) => s + v.accuracy_level, 0) / rows.length * 100).toFixed(1),
        类型准确率: +(rows.reduce((s, v) => s + v.accuracy_type, 0) / rows.length * 100).toFixed(1),
        相关召回率: +(rows.reduce((s, v) => s + v.recall_relevant, 0) / rows.length * 100).toFixed(1),
      }
    }).filter(Boolean) as Array<Record<string, string | number>>
  }, [variants])

  const suggestions = useMemo(() => {
    if (!variants.length) return []
    const byTechnique = TECHNIQUE_ORDER.map((tech) => {
      const rows = variants.filter((v) => v.technique === tech)
      if (!rows.length) return null
      return {
        technique: tech,
        label: techniqueLabel(tech),
        avgAcc: rows.reduce((s, v) => s + v.accuracy_level, 0) / rows.length,
        avgLat: rows.reduce((s, v) => s + v.avg_latency_ms, 0) / rows.length,
      }
    }).filter(Boolean) as Array<{ technique: string; label: string; avgAcc: number; avgLat: number }>

    const bestTech = byTechnique.reduce((a, b) => (a.avgAcc >= b.avgAcc ? a : b), byTechnique[0])
    const fastestTech = byTechnique.reduce((a, b) => (a.avgLat <= b.avgLat ? a : b), byTechnique[0])
    const bestVariant = variants.reduce((a, b) => (a.accuracy_level >= b.accuracy_level ? a : b), variants[0])
    const fastestVariant = variants.reduce((a, b) => (a.avg_latency_ms <= b.avg_latency_ms ? a : b), variants[0])

    const tips: string[] = []
    tips.push(`综合风险等级准确率最高的是「${bestVariant.variant}」(${techniqueLabel(bestVariant.technique)})，准确率达到 ${(bestVariant.accuracy_level * 100).toFixed(1)}%。`)
    tips.push(`从 Prompt 技法维度看，${bestTech?.label} 平均等级准确率最高（${(bestTech?.avgAcc * 100).toFixed(1)}%），适合作为该 Agent 的主选模板。`)
    if (fastestTech && fastestTech.technique !== bestTech?.technique) {
      tips.push(`若对延迟敏感，可选用 ${fastestTech.label}，平均延迟 ${fastestTech.avgLat.toFixed(0)}ms，较 ${bestTech?.label} 更快。`)
    }
    if (fastestVariant.variant !== bestVariant.variant) {
      tips.push(`延迟最低的变体是「${fastestVariant.variant}」，平均响应 ${fastestVariant.avg_latency_ms.toFixed(0)}ms。`)
    }
    if (variants.some((v) => v.accuracy_level < 0.5)) {
      tips.push('部分变体准确率低于 50%，建议补充更多 Few-Shot 示例或调整 CoT 推理链。')
    }
    if (variants.every((v) => v.accuracy_level >= 0.8)) {
      tips.push('当前变体整体表现优异，可考虑加入更大规模的 badcase 数据集做回归测试。')
    }
    return tips
  }, [variants])

  const techniqueCompare = useMemo(() => {
    if (!variants.length) return []
    return TECHNIQUE_ORDER.map((tech) => {
      const rows = variants.filter((v) => v.technique === tech)
      if (!rows.length) return null
      return {
        technique: techniqueLabel(tech),
        样本数: rows.reduce((s, v) => s + v.samples, 0),
        平均等级准确率: (rows.reduce((s, v) => s + v.accuracy_level, 0) / rows.length * 100).toFixed(1) + '%',
        平均类型准确率: (rows.reduce((s, v) => s + v.accuracy_type, 0) / rows.length * 100).toFixed(1) + '%',
        平均延迟: Math.round(rows.reduce((s, v) => s + v.avg_latency_ms, 0) / rows.length) + 'ms',
      }
    }).filter((r): r is NonNullable<typeof r> => r !== null)
  }, [variants])

  return (
    <div>
      <h2>效果评估</h2>
      {error && <div className="error-banner">{error}</div>}

      {/* ---- LLM 运行状态提示 ---- */}
      {llmStatus?.is_fallback && (
        <div className="info-banner">
          <strong>当前为规则引擎降级模式</strong>
          <p>
            未配置 OpenAI API Key 或 Ollama，所有 Agent 走内置关键词规则，Prompt 变体不会被真正执行。
            因此 A/B 测试结果仅用于验证评估框架，不同变体的数据会高度一致。
            如需看到 Prompt 技法的真实差异，请配置 LLM 后重新评测。
          </p>
        </div>
      )}
      {llmStatus && !llmStatus.is_fallback && (
        <div className="info-banner info-success">
          <strong>LLM 已启用</strong>
          <span> 当前模式：{llmStatus.mode === 'openai' ? 'OpenAI 兼容 API' : '本地 Ollama'}，模型：{llmStatus.model}</span>
        </div>
      )}

      {/* ---- 效能指标卡片 ---- */}
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-label">风险等级准确率</div>
          <div className="stat-value">{metrics ? `${(metrics.accuracy * 100).toFixed(1)}%` : '-'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">相关召回率</div>
          <div className="stat-value">{metrics ? `${(metrics.recall * 100).toFixed(1)}%` : '-'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">平均响应延迟</div>
          <div className="stat-value">{metrics ? `${metrics.avg_response_time_ms}ms` : '-'}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">已标注样本数</div>
          <div className="stat-value">{metrics?.labeled ?? '-'}</div>
        </div>
      </div>

      {/* ---- A/B 测试控制台 ---- */}
      <div className="card">
        <h3>A/B Prompt 测试控制台</h3>
        <p className="muted-text" style={{ marginBottom: 16 }}>
          选择 Agent 类型与评测数据集，快速对比 Zero-Shot / CoT / Few-Shot / RolePlay 等 Prompt 技法的效果。
        </p>

        <div className="eval-control-row">
          <div className="eval-control-group">
            <label className="eval-label">Agent 类型</label>
            <div className="eval-options">
              {AGENT_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  className={agentType === opt.value ? 'btn btn-sm' : 'btn btn-sm btn-outline'}
                  onClick={() => setAgentType(opt.value)}
                  disabled={loading}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div className="eval-control-group">
            <label className="eval-label">数据集</label>
            <div className="eval-options">
              {DATASET_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  className={datasetKey === opt.value ? 'btn btn-sm' : 'btn btn-sm btn-outline'}
                  onClick={() => setDatasetKey(opt.value)}
                  disabled={loading}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="eval-dataset-preview">
          <span className="muted-text">当前数据集：</span>
          <span>{dataset.length} 条样本，覆盖 {new Set(dataset.map((d) => d.true_risk_type)).size} 种风险类型、{new Set(dataset.map((d) => d.true_risk_level)).size} 个风险等级</span>
        </div>

        <div style={{ marginTop: 16 }}>
          <button className="btn" onClick={runTest} disabled={loading}>
            {loading ? '评测中...' : `开始 ${agentLabel(agentType)} 评测`}
          </button>
        </div>
      </div>

      {/* ---- 结果建议 ---- */}
      {suggestions.length > 0 && (
        <div className="card suggestion-card">
          <h3>结果建议</h3>
          <ul className="suggestion-list">
            {suggestions.map((tip, i) => (
              <li key={i}>{tip}</li>
            ))}
          </ul>
        </div>
      )}

      {/* ---- A/B 测试结果摘要卡片 ---- */}
      {variants.length > 0 && (
        <div className="stat-grid">
          <div className="stat-card">
            <div className="stat-label">评测样本数</div>
            <div className="stat-value">{abResult?.dataset_size ?? '-'}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">对比变体数</div>
            <div className="stat-value">{variants.length}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">最佳等级准确率</div>
            <div className="stat-value">
              {`${(Math.max(...variants.map((v) => v.accuracy_level)) * 100).toFixed(1)}%`}
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-label">最低平均延迟</div>
            <div className="stat-value">{`${Math.min(...variants.map((v) => v.avg_latency_ms)).toFixed(0)}ms`}</div>
          </div>
        </div>
      )}

      {/* ---- 多维度对比图表 ---- */}
      {chartData.length > 0 && (
        <div className="card chart-card">
          <h3>变体多维度对比</h3>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="等级准确率" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              <Bar dataKey="类型准确率" fill="#22c55e" radius={[4, 4, 0, 0]} />
              <Bar dataKey="相关召回率" fill="#f59e0b" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ---- 技法雷达图 ---- */}
      {radarData.length > 0 && (
        <div className="card chart-card">
          <h3>Prompt 技法综合雷达</h3>
          <ResponsiveContainer width="100%" height={320}>
            <RadarChart data={radarData}>
              <PolarGrid />
              <PolarAngleAxis dataKey="technique" tick={{ fontSize: 12 }} />
              <PolarRadiusAxis angle={30} domain={[0, 100]} />
              <Radar name="等级准确率" dataKey="等级准确率" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.25} />
              <Radar name="类型准确率" dataKey="类型准确率" stroke="#22c55e" fill="#22c55e" fillOpacity={0.25} />
              <Radar name="相关召回率" dataKey="相关召回率" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.25} />
              <Legend />
              <Tooltip />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ---- 详细评测表 ---- */}
      {variants.length > 0 && (
        <div className="card">
          <h3>变体明细</h3>
          <table className="table">
            <thead>
              <tr>
                <th>变体</th>
                <th>Agent</th>
                <th>技法</th>
                <th>等级准确率</th>
                <th>类型准确率</th>
                <th>相关召回率</th>
                <th>平均延迟</th>
                <th>样本数</th>
              </tr>
            </thead>
            <tbody>
              {variants.map((v) => (
                <tr key={v.variant}>
                  <td>{v.variant}</td>
                  <td>{v.agent_type}</td>
                  <td>{techniqueLabel(v.technique)}</td>
                  <td>{(v.accuracy_level * 100).toFixed(1)}%</td>
                  <td>{(v.accuracy_type * 100).toFixed(1)}%</td>
                  <td>{(v.recall_relevant * 100).toFixed(1)}%</td>
                  <td>{v.avg_latency_ms.toFixed(0)}ms</td>
                  <td>{v.samples}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ---- 技法横向对比 ---- */}
      {techniqueCompare.length > 0 && (
        <div className="card">
          <h3>Prompt 技法横向对比</h3>
          <table className="table">
            <thead>
              <tr>
                <th>技法</th>
                <th>样本数</th>
                <th>平均等级准确率</th>
                <th>平均类型准确率</th>
                <th>平均延迟</th>
              </tr>
            </thead>
            <tbody>
              {techniqueCompare.map((row) => (
                <tr key={row.technique}>
                  <td>{row.technique}</td>
                  <td>{row.样本数}</td>
                  <td>{row.平均等级准确率}</td>
                  <td>{row.平均类型准确率}</td>
                  <td>{row.平均延迟}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ---- 历史评测记录 ---- */}
      {history.length > 0 && (
        <div className="card">
          <h3>评测历史（最近 10 次）</h3>
          <table className="table">
            <thead>
              <tr>
                <th>时间</th>
                <th>Agent</th>
                <th>数据集</th>
                <th>最佳变体</th>
                <th>最佳技法</th>
                <th>等级准确率</th>
                <th>平均延迟</th>
              </tr>
            </thead>
            <tbody>
              {history.map((h, i) => (
                <tr key={i}>
                  <td className="muted-text">{h.time}</td>
                  <td>{agentLabel(h.agent_type)}</td>
                  <td>{h.dataset_size} 条</td>
                  <td>{h.best_variant}</td>
                  <td>{h.best_technique}</td>
                  <td>{(h.accuracy_level * 100).toFixed(1)}%</td>
                  <td>{h.avg_latency_ms.toFixed(0)}ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
