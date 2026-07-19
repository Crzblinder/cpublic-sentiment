import { NavLink, Route, Routes } from 'react-router-dom'
import Analyze from './pages/Analyze'
import Cases from './pages/Cases'
import Dashboard from './pages/Dashboard'
import Enterprises from './pages/Enterprises'
import Evaluation from './pages/Evaluation'

const NAV_ITEMS = [
  { to: '/', icon: '📊', label: '仪表盘' },
  { to: '/analyze', icon: '🔍', label: '舆情分析' },
  { to: '/cases', icon: '📁', label: '案例库' },
  { to: '/enterprises', icon: '🏢', label: '企业画像' },
  { to: '/evaluation', icon: '📈', label: '效果评估' },
]

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="layout">
      <aside className="sidebar">
        <h1>CPublic Sentiment</h1>
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
        <Route path="/" element={<Dashboard />} />
        <Route path="/analyze" element={<Analyze />} />
        <Route path="/cases" element={<Cases />} />
        <Route path="/enterprises" element={<Enterprises />} />
        <Route path="/evaluation" element={<Evaluation />} />
      </Routes>
    </Layout>
  )
}
