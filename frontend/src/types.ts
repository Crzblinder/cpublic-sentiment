export interface ApiResponse<T> {
  code: number
  data: T
  message: string
}

export interface PaginatedResponse<T> {
  total: number
  items: T[]
}

export interface PagedResponse<T> {
  total: number
  page: number
  size: number
  items: T[]
}

/* ---- Skill ---- */

export interface Skill {
  id: number
  name: string
  category: string
  aliases: string[]
  definition: string
}

export interface SkillListResponse {
  total: number
  items: Skill[]
}

export interface RelatedSkill {
  skill: string
  relation_type: string
  weight: number
  target_skill: string
}

export interface SkillStatistics {
  total_skills: number
  total_relations: number
  category_distribution: Array<{ category: string; count: number }>
  hot_skills: Array<{ skill: string; count: number }>
  relation_type_distribution: Array<{ relation_type: string; count: number }>
}

/* ---- Company ---- */

export interface Company {
  id: number
  name: string
  industry: string
  size: string
  city: string
}

/* ---- Job ---- */

export interface Job {
  id: number
  title: string
  company: Company
  city: string
  salary_min: number
  salary_max: number
  experience_level: string
  education_level: string
  required_skills: string[]
  description: string
  posted_at: string | null
}

export interface JobListResponse {
  total: number
  page: number
  size: number
  items: Job[]
}

export interface JobSearchResult {
  id: string
  document: string
  metadata: Record<string, unknown>
  score?: number
  keyword_score?: number
  hybrid_score?: number
  source: string
}

export interface ParsedJD {
  title: string
  company: string
  required_skills: string[]
  experience_level: string
  education_level: string
  implicit_needs: string[]
}

export interface JobStatistics {
  total_jobs: number
  total_companies: number
  avg_salary_min: number
  avg_salary_max: number
  top_cities: Array<{ city: string; count: number }>
  top_industries: Array<{ industry: string; count: number }>
  hot_skills: Array<{ skill: string; count: number }>
  experience_distribution: Array<{ experience_level: string; count: number }>
}

/* ---- UserSkillProfile ---- */

export interface UserSkillProfile {
  id: number
  name: string
  skills: string[]
  experience_level: string
  target_job_titles: string[]
  created_at: string | null
}

export interface UserSkillProfileListResponse {
  total: number
  items: UserSkillProfile[]
}

/* ---- MatchResult ---- */

export interface MatchResult {
  id: number
  user_profile_id: number
  job_id: number
  match_score: number
  matched_skills: string[]
  missing_skills: string[]
  transferable_skills: string[]
  analysis_summary: string | null
  created_at: string | null
}

export interface LearningPathItem {
  skill: string
  difficulty: string
  estimated_weeks: number
  resource_type: string
  prerequisites: string[]
}

export interface LearningPath {
  profile_id: number
  job_id: number
  learning_path: LearningPathItem[]
}

/* ---- Trend ---- */

export interface TrendAnalysis {
  summary: string
  top_skills: string[]
  avg_salary_range: string
  hot_job_titles: string[]
  key_metrics: Record<string, number | string>
}

/* ---- Dashboard ---- */

export interface DashboardData {
  jobs: JobStatistics
  skills: SkillStatistics
  trends: TrendAnalysis
}

/* ---- Stream ---- */

export interface MatchStreamEvent {
  node?: string
  status?: string
  message?: string
  final_result?: MatchResult
}
