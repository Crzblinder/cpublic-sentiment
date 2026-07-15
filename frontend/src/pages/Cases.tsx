import { useEffect, useState } from 'react'
import { api } from '../api'
import type { CaseItem } from '../types'

export default function Cases() {
  const [cases, setCases] = useState<CaseItem[]>([])
  const [industry, setIndustry] = useState('')
  const [riskType, setRiskType] = useState('')
  const [error, setError] = useState('')

  const load = () => {
    api.listCases({ industry, risk_type: riskType }).then(setCases).catch((e) => setError(e.message))
  }

  useEffect(() => {
    load()
  }, [])

  return (
    <div>
      <h2>风险案例库</h2>
      <div className="card" style={{ display: 'flex', gap: 12 }}>
        <input
          value={industry}
          onChange={(e) => setIndustry(e.target.value)}
          placeholder="行业筛选"
        />
        <input
          value={riskType}
          onChange={(e) => setRiskType(e.target.value)}
          placeholder="风险类型筛选"
        />
        <button className="btn" onClick={load}>筛选</button>
      </div>
      {error && <div style={{ color: 'red' }}>{error}</div>}
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>标题</th>
              <th>行业</th>
              <th>风险类型</th>
              <th>风险等级</th>
              <th>摘要</th>
            </tr>
          </thead>
          <tbody>
            {cases.map((c) => (
              <tr key={c.id}>
                <td>{c.title}</td>
                <td>{c.industry}</td>
                <td>{c.risk_type}</td>
                <td>{c.risk_level}</td>
                <td>{c.summary}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
