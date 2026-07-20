import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../api'
import { SkillNetworkGraph } from '../components'
import type { RelatedSkill, Skill } from '../types'

const RELATION_TYPES = [
  { value: '', label: '全部关系' },
  { value: 'prerequisite', label: '依赖' },
  { value: 'similar', label: '相似' },
  { value: 'cooccurrence', label: '共现' },
]

const RELATION_COLORS: Record<string, string> = {
  prerequisite: '#ef4444',
  similar: '#3b82f6',
  cooccurrence: '#22c55e',
}

interface GraphNode {
  id: string
  name: string
  x: number
  y: number
  r: number
  isCenter: boolean
}

interface GraphEdge {
  source: string
  target: string
  relation_type: string
  weight: number
}

export default function SkillGraph() {
  const [skills, setSkills] = useState<Skill[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null)
  const [related, setRelated] = useState<RelatedSkill[]>([])
  const [relationFilter, setRelationFilter] = useState('')
  const [graphLoading, setGraphLoading] = useState(false)

  const containerRef = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ width: 600, height: 480 })

  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        setSize({ width: Math.max(320, rect.width - 40), height: 480 })
      }
    }
    updateSize()
    window.addEventListener('resize', updateSize)
    return () => window.removeEventListener('resize', updateSize)
  }, [])

  useEffect(() => {
    setLoading(true)
    api.listSkills()
      .then((res) => setSkills(res.items))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const loadRelated = useCallback(async (skill: Skill, filter = relationFilter) => {
    setGraphLoading(true)
    try {
      const res = await api.getRelatedSkills(skill.id, filter || undefined)
      setRelated(res)
      setSelectedSkill(skill)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setGraphLoading(false)
    }
  }, [relationFilter])

  const filteredRelated = useMemo(() => {
    return relationFilter ? related.filter((r) => r.relation_type === relationFilter) : related
  }, [related, relationFilter])

  const graphData = useMemo(() => {
    if (!selectedSkill) return { nodes: [] as GraphNode[], edges: [] as GraphEdge[] }
    const center: GraphNode = {
      id: selectedSkill.name,
      name: selectedSkill.name,
      x: size.width / 2,
      y: size.height / 2,
      r: 36,
      isCenter: true,
    }

    const targets = Array.from(new Set(filteredRelated.map((r) => r.target_skill)))
    const radius = Math.min(size.width, size.height) / 2 - 80
    const nodes: GraphNode[] = [center]
    targets.forEach((target, i) => {
      const angle = (2 * Math.PI * i) / Math.max(targets.length, 1) - Math.PI / 2
      nodes.push({
        id: target,
        name: target,
        x: center.x + radius * Math.cos(angle),
        y: center.y + radius * Math.sin(angle),
        r: 24,
        isCenter: false,
      })
    })

    const edges: GraphEdge[] = filteredRelated
      .filter((r) => targets.includes(r.target_skill))
      .map((r) => ({
        source: r.skill,
        target: r.target_skill,
        relation_type: r.relation_type,
        weight: r.weight,
      }))

    return { nodes, edges }
  }, [selectedSkill, filteredRelated, size])

  const handleSearch = () => {
    const keyword = search.trim().toLowerCase()
    const found = skills.find((s) => s.name.toLowerCase().includes(keyword) || s.aliases.some((a) => a.toLowerCase().includes(keyword)))
    if (found) {
      loadRelated(found)
    } else {
      setError('未找到相关技能')
    }
  }

  const stats = useMemo(() => {
    const counts: Record<string, number> = {}
    related.forEach((r) => {
      counts[r.relation_type] = (counts[r.relation_type] || 0) + 1
    })
    return counts
  }, [related])

  return (
    <div>
      <h2>技能知识图谱</h2>

      {/* 搜索与筛选 */}
      <div className="card filter-bar">
        <div className="search-with-suggestions">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索技能名称"
            style={{ maxWidth: 240 }}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          />
        </div>
        <button className="btn" onClick={handleSearch} disabled={loading || !search.trim()}>
          搜索
        </button>
        <select
          value={relationFilter}
          onChange={(e) => {
            setRelationFilter(e.target.value)
            if (selectedSkill) loadRelated(selectedSkill, e.target.value)
          }}
          className="filter-select"
        >
          {RELATION_TYPES.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
        <span className="muted-text" style={{ marginLeft: 'auto' }}>技能库共 {skills.length} 项</span>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="chart-row">
        {/* 图谱可视化 */}
        <div className="card chart-card" ref={containerRef}>
          <h3>技能关联图</h3>
          {graphLoading ? (
            <div className="chart-empty"><div className="spinner" /></div>
          ) : selectedSkill ? (
            <SkillNetworkGraph
              nodes={graphData.nodes}
              links={graphData.edges}
              width={size.width}
              height={size.height}
              relationColors={RELATION_COLORS}
            />
          ) : (
            <div className="chart-empty">搜索并选择一个技能查看关联图谱</div>
          )}

          {/* 图例 */}
          <div className="tag-list" style={{ marginTop: 12, justifyContent: 'center' }}>
            {RELATION_TYPES.slice(1).map((t) => (
              <span key={t.value} className="tag-chip" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 10, height: 10, borderRadius: '50%', background: RELATION_COLORS[t.value] }} />
                {t.label}
              </span>
            ))}
          </div>
        </div>

        {/* 关联技能列表 */}
        <div className="card chart-card">
          <h3>关联技能列表</h3>
          {selectedSkill ? (
            <>
              <div style={{ marginBottom: 14 }}>
                <span className="step-label">中心技能</span>
                <span className="step-val">{selectedSkill.name}</span>
                <p className="muted-text" style={{ marginTop: 6 }}>{selectedSkill.definition}</p>
              </div>
              {filteredRelated.length ? (
                <div className="rank-list">
                  {filteredRelated.map((r, idx) => (
                    <div key={idx} className="rank-item">
                      <span
                        className="rank-num"
                        style={{ background: RELATION_COLORS[r.relation_type] || '#e2e8f0', color: '#fff' }}
                      >
                        {idx + 1}
                      </span>
                      <span className="rank-name">{r.target_skill}</span>
                      <span className="rank-industry">{r.relation_type}</span>
                      <span className="rank-score">{(r.weight * 100).toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="chart-empty">该关系类型下暂无关联</div>
              )}
            </>
          ) : (
            <div className="chart-empty">请选择一个技能</div>
          )}
        </div>
      </div>

      {/* 统计 */}
      {selectedSkill && (
        <div className="stat-grid">
          {Object.entries(stats).map(([type, count]) => (
            <div key={type} className="stat-card">
              <div className="stat-label">{RELATION_TYPES.find((t) => t.value === type)?.label || type}</div>
              <div className="stat-value">{count}</div>
            </div>
          ))}
        </div>
      )}

      {/* 技能分类 */}
      <div className="card">
        <h3>技能分类</h3>
        <div className="tag-list">
          {Array.from(new Set(skills.map((s) => s.category))).map((category) => (
            <span key={category} className="tag-chip">{category}</span>
          ))}
        </div>
      </div>
    </div>
  )
}
