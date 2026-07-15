import { NavLink, Route, Routes } from 'react-router-dom'
import Analyze from './pages/Analyze'
import Cases from './pages/Cases'
import Dashboard from './pages/Dashboard'
import Enterprises from './pages/Enterprises'
import Evaluation from './pages/Evaluation'

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="layout">
      <aside className="sidebar">
        <h1>CPublic Sentiment</h1>
        <nav>
          <NavLink to="/" end>仪表盘</NavLink>
          <NavLink to="/analyze">舆情分析</NavLink>
          <NavLink to="/cases">案例库</NavLink>
          <NavLink to="/enterprises">企业画像</NavLink>
          <NavLink to="/evaluation">效果评估</NavLink>
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
