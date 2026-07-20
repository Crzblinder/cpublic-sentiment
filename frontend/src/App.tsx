import { NavLink, Route, Routes } from 'react-router-dom'
import SkillDashboard from './pages/SkillDashboard'
import JobMatch from './pages/JobMatch'
import JobLibrary from './pages/JobLibrary'
import SkillGraph from './pages/SkillGraph'
import TrendAnalysis from './pages/TrendAnalysis'

const NAV_ITEMS = [
  { to: '/', icon: '📊', label: '仪表盘' },
  { to: '/match', icon: '🎯', label: '岗位匹配' },
  { to: '/jobs', icon: '💼', label: '岗位库' },
  { to: '/skills', icon: '🧠', label: '技能图谱' },
  { to: '/trends', icon: '📈', label: '趋势分析' },
]

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="layout">
      <aside className="sidebar">
        <h1>TalentMatch Engine</h1>
        <nav>
          {NAV_ITEMS.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to === '/'}>
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="main">{children}</main>
    </div>
  )
}

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<SkillDashboard />} />
        <Route path="/match" element={<JobMatch />} />
        <Route path="/jobs" element={<JobLibrary />} />
        <Route path="/skills" element={<SkillGraph />} />
        <Route path="/trends" element={<TrendAnalysis />} />
      </Routes>
    </Layout>
  )
}
