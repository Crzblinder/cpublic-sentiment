import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { MatchResultCard, SkillRadarChart } from '../components'
import type { Job, MatchResult } from '../types'

const STEP_LABELS: Record<string, string> = {
  parse_profile: '解析画像',
  retrieve_jobs: '检索岗位',
  match_skills: '技能匹配',
  analyze_gap: '差距分析',
  finalize: '完成',
}

const EXPERIENCE_LEVELS = ['不限', '应届生', '1-3年', '3-5年', '5-10年', '10年以上']

const EXAMPLE_PROFILES = [
  {
    label: 'Java 后端',
    name: 'Java 后端工程师',
    skills: 'Java, Spring Boot, MySQL, Redis, Kafka, Docker',
    target: 'Java 后端工程师, 后端开发工程师',
    experience: '3-5年',
  },
  {
    label: '前端工程师',
    name: '前端开发工程师',
    skills: 'JavaScript, TypeScript, React, Vue, CSS, Webpack',
    target: '前端工程师, Web 前端开发',
    experience: '1-3年',
  },
  {
    label: '算法工程师',
    name: '算法工程师',
    skills: 'Python, PyTorch, TensorFlow, 机器学习, 深度学习, SQL',
    target: '算法工程师, 机器学习工程师',
    experience: '3-5年',
  },
]

export default function JobMatch() {
  const [name, setName] = useState('')
  const [skillsText, setSkillsText] = useState('')
  const [experienceLevel, setExperienceLevel] = useState('不限')
  const [targetText, setTargetText] = useState('')

  const [jobs, setJobs] = useState<Job[]>([])
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null)
  const [jobSearch, setJobSearch] = useState('')
  const [jobsLoading, setJobsLoading] = useState(false)

  const [result, setResult] = useState<MatchResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [activeStep, setActiveStep] = useState<string>('')
  const [completedSteps, setCompletedSteps] = useState<string[]>([])
  const [useStream, setUseStream] = useState(false)

  const loadJobs = useCallback(async (q = '') => {
    setJobsLoading(true)
    try {
      const res = await api.listJobs({ q, size: 50 })
      setJobs(res.items)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setJobsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadJobs()
  }, [loadJobs])

  const selectedJob = jobs.find((j) => j.id === selectedJobId) || null

  const skills = skillsText.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
  const targetJobTitles = targetText.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
  const canMatch = name.trim().length > 0 && skills.length > 0 && selectedJobId !== null && !loading

  const applyExample = (ex: typeof EXAMPLE_PROFILES[0]) => {
    setName(ex.name)
    setSkillsText(ex.skills)
    setExperienceLevel(ex.experience)
    setTargetText(ex.target)
    setResult(null)
    setError('')
  }

  const handleMatch = async () => {
    if (!canMatch || !selectedJobId) return
    setLoading(true)
    setError('')
    setResult(null)
    setActiveStep('')
    setCompletedSteps([])

    try {
      const profile = await api.createProfile({
        name: name.trim(),
        skills,
        experience_level: experienceLevel,
        target_job_titles: targetJobTitles,
      })

      if (useStream) {
        const res = await api.matchStream(
          { profile_id: profile.id, job_id: selectedJobId },
          (event) => {
            const node = event.node || event.status
            if (node) {
              setActiveStep(node)
              setCompletedSteps((prev) => (prev.includes(node) ? prev : [...prev, node]))
            }
          },
        )
        if (res) setResult(res)
      } else {
        const res = await api.createMatch(profile.id, selectedJobId)
        setResult(res)
      }
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
      setActiveStep('')
    }
  }

  const radarSkills = useMemo(() => {
    if (!selectedJob) return []
    const required = selectedJob.required_skills
    const userSet = new Set(skills)
    const matchedSet = new Set(result?.matched_skills ?? [])
    const allSkills = Array.from(new Set([...required, ...userSet]))
    return allSkills.slice(0, 12).map((name) => ({
      name,
      userScore: matchedSet.has(name) ? 90 : userSet.has(name) ? 80 : 0,
      requiredScore: required.includes(name) ? 100 : 0,
    }))
  }, [selectedJob, skills, result])

  return (
    <div>
      <h2>岗位技能匹配</h2>

      {/* ---- 画像输入 ---- */}
      <div className="card">
        <h3>1. 填写技能画像</h3>
        <div style={{ marginBottom: 12 }}>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="画像名称，例如：高级 Java 后端"
          />
        </div>
        <div style={{ marginBottom: 12 }}>
          <textarea
            value={skillsText}
            onChange={(e) => setSkillsText(e.target.value)}
            placeholder="输入技能，用逗号分隔，例如：Java, Spring Boot, MySQL, Redis"
          />
          <div className="input-meta">
            <div className="example-btns">
              <span className="muted-text">快速示例：</span>
              {EXAMPLE_PROFILES.map((ex) => (
                <button
                  key={ex.label}
                  className="btn-sm btn-outline"
                  onClick={() => applyExample(ex)}
                  disabled={loading}
                >
                  {ex.label}
                </button>
              ))}
            </div>
            <span className="muted-text">{skills.length} 项技能</span>
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 12, marginBottom: 12 }}>
          <select value={experienceLevel} onChange={(e) => setExperienceLevel(e.target.value)}>
            {EXPERIENCE_LEVELS.map((level) => (
              <option key={level} value={level}>{level}</option>
            ))}
          </select>
          <input
            value={targetText}
            onChange={(e) => setTargetText(e.target.value)}
            placeholder="目标岗位，用逗号分隔（可选）"
          />
        </div>
      </div>

      {/* ---- 岗位选择 ---- */}
      <div className="card">
        <h3>2. 选择目标岗位</h3>
        <div className="filter-bar" style={{ marginBottom: 12 }}>
          <input
            value={jobSearch}
            onChange={(e) => setJobSearch(e.target.value)}
            placeholder="搜索岗位"
            style={{ maxWidth: 260 }}
            onKeyDown={(e) => e.key === 'Enter' && loadJobs(jobSearch)}
          />
          <button className="btn btn-sm" onClick={() => loadJobs(jobSearch)} disabled={jobsLoading}>
            {jobsLoading ? '搜索中...' : '搜索'}
          </button>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 14, marginLeft: 'auto' }}>
            <input
              type="checkbox"
              checked={useStream}
              onChange={(e) => setUseStream(e.target.checked)}
              disabled={loading}
            />
            流式分析
          </label>
        </div>

        {error && <div className="error-banner">{error}</div>}

        <div style={{ maxHeight: 320, overflow: 'auto', border: '1px solid var(--border)', borderRadius: 8 }}>
          {jobs.length ? (
            <table className="table">
              <thead>
                <tr>
                  <th style={{ width: 40 }}>选择</th>
                  <th>岗位</th>
                  <th>公司</th>
                  <th>城市</th>
                  <th>薪资</th>
                  <th>经验</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr
                    key={job.id}
                    className="clickable-row"
                    onClick={() => setSelectedJobId(job.id)}
                    style={selectedJobId === job.id ? { background: '#eff6ff' } : {}}
                  >
                    <td>
                      <input
                        type="radio"
                        checked={selectedJobId === job.id}
                        onChange={() => setSelectedJobId(job.id)}
                        onClick={(e) => e.stopPropagation()}
                      />
                    </td>
                    <td>{job.title}</td>
                    <td>{job.company.name}</td>
                    <td>{job.city}</td>
                    <td>¥{job.salary_min.toLocaleString()}-{job.salary_max.toLocaleString()}</td>
                    <td>{job.experience_level}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="muted-text" style={{ padding: 20, textAlign: 'center' }}>
              {jobsLoading ? '加载中...' : '暂无岗位'}
            </div>
          )}
        </div>
      </div>

      {/* ---- 匹配按钮 ---- */}
      <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div className="muted-text">
          {selectedJob ? `已选择：${selectedJob.title} @ ${selectedJob.company.name}` : '请选择目标岗位'}
        </div>
        <button className="btn" onClick={handleMatch} disabled={!canMatch}>
          {loading ? '匹配中...' : `开始匹配${useStream ? '（流式）' : ''}`}
        </button>
      </div>

      {/* ---- 流式进度 ---- */}
      {loading && useStream && (
        <div className="card stream-progress-card">
          <h3>匹配进度</h3>
          <div className="stream-steps">
            {completedSteps.map((s, i) => (
              <div key={i} className="stream-step-item stream-step-done">
                <span className="stream-step-icon">&#10003;</span>
                <span>{STEP_LABELS[s] || s}</span>
              </div>
            ))}
            {activeStep && !completedSteps.includes(activeStep) && (
              <div className="stream-step-item stream-step-active">
                <span className="stream-step-icon stream-step-spinner" />
                <span>{STEP_LABELS[activeStep] || activeStep}</span>
              </div>
            )}
            {completedSteps.length === 0 && !activeStep && (
              <div className="stream-step-item stream-step-active">
                <span className="stream-step-icon stream-step-spinner" />
                <span>初始化...</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ---- 匹配结果 ---- */}
      {result && (
        <>
          <MatchResultCard matchResult={result} jobTitle={selectedJob?.title} />
          {radarSkills.length > 0 && (
            <div className="card chart-card">
              <h3>技能对比雷达图</h3>
              <SkillRadarChart skills={radarSkills} />
            </div>
          )}
        </>
      )}
    </div>
  )
}
