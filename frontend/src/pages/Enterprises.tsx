import { useEffect, useState } from 'react'
import { api } from '../api'
import type { EnterpriseItem } from '../types'

export default function Enterprises() {
  const [enterprises, setEnterprises] = useState<EnterpriseItem[]>([])
  const [industry, setIndustry] = useState('')
  const [error, setError] = useState('')

  const load = () => {
    api.listEnterprises(industry || undefined).then(setEnterprises).catch((e) => setError(e.message))
  }

  useEffect(() => {
    load()
  }, [])

  return (
    <div>
      <h2>企业画像</h2>
      <div className="card" style={{ display: 'flex', gap: 12 }}>
        <input
          value={industry}
          onChange={(e) => setIndustry(e.target.value)}
          placeholder="行业筛选"
        />
        <button className="btn" onClick={load}>筛选</button>
      </div>
      {error && <div style={{ color: 'red' }}>{error}</div>}
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>企业名称</th>
              <th>行业</th>
              <th>规模</th>
              <th>地区</th>
            </tr>
          </thead>
          <tbody>
            {enterprises.map((e) => (
              <tr key={e.id}>
                <td>{e.name}</td>
                <td>{e.industry}</td>
                <td>{e.scale}</td>
                <td>{e.region}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
