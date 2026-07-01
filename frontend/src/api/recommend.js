const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000'

export const PROFILE_STORAGE_KEY = 'skillProfile'
export const RECOMMENDATIONS_STORAGE_KEY = 'jobRecommendations'
export const RAW_RECOMMENDATIONS_STORAGE_KEY = 'rawJobRecommendations'
export const ANALYSIS_STORAGE_KEY = 'recommendationAnalysis'
export const QUIZ_SESSION_STORAGE_KEY = 'quizSessionId'
export const QUIZ_PROGRESS_STORAGE_KEY = 'quizProgress'
export const QUIZ_HISTORY_STORAGE_KEY = 'quizAttemptHistory'

const EXPERIENCE_MAP = {
  Internship: 'intern',
  'Junior (0-2 yr)': 'junior',
  'Mid (3-5 yr)': 'mid',
  'Senior (6+ yr)': 'senior',
}

const CATEGORY_MAP = {
  Engineering: 'backend-dev',
  Design: 'frontend-dev',
  'Data Science': 'data-scientist',
  Product: 'software-engineer',
  Marketing: 'business-analyst',
}

export function toApiProfile({
  skills,
  skillLevels = {},
  experience,
  category,
  location = 'remote',
  experienceYears = '',
  hasProjects = false,
  portfolioUrl = '',
}) {
  const skillIds = skills.map((skill) =>
    typeof skill === 'string' ? skill : skill.skill_id,
  )
  return {
    detected_skills: skillIds,
    skill_levels: skillLevels,
    experience_level: EXPERIENCE_MAP[experience] || 'junior',
    top_category: CATEGORY_MAP[category] || category?.toLowerCase?.() || '',
    location,
    experience_years: experienceYears === '' ? null : Number(experienceYears),
    has_projects: hasProjects,
    portfolio_url: portfolioUrl.trim(),
  }
}

export async function fetchSkillSuggestions(query, limit = 8) {
  if (!query.trim()) {
    return []
  }
  const params = new URLSearchParams({ q: query.trim(), limit: String(limit) })
  const response = await fetch(`${API_BASE}/skills/suggest?${params}`)
  if (!response.ok) {
    return []
  }
  const data = await response.json()
  return data.suggestions || []
}

export async function normalizeSkillValues(skills) {
  const response = await fetch(`${API_BASE}/skills/normalize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ skills }),
  })
  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || 'Could not normalize skills.')
  }
  return response.json()
}

export function mapJobToCard(job) {
  return {
    id: job.job_id,
    title: job.job_title,
    company: job.source || job.category?.replace(/-/g, ' ') || 'Open role',
    category: job.category,
    experience: job.exp_level,
    match: job.match_score,
    readiness: Math.round(
      (job.breakdown?.skill_fit ?? job.breakdown?.skill_overlap ?? 0) * 0.7 +
        (job.breakdown?.experience_match ?? 0) * 0.3,
    ),
    skills: job.matched_skill_names?.length
      ? job.matched_skill_names
      : (job.missing_skill_names || job.missing_skills || []).slice(0, 3),
    breakdown: job.breakdown,
    weightedContributions: job.weighted_contributions,
    scoreWeights: job.score_weights,
    description: job.description,
    missing_skills: job.missing_skills,
    missingSkillNames: job.missing_skill_names,
    matchedSkillNames: job.matched_skill_names,
    explanation: job.explanation,
    explanationPoints: job.explanation_points,
    location: job.location,
    dateAdded: job.date_added,
    requiredSkillCount: job.required_skill_count,
  }
}

export async function fetchRecommendations(profile, topN = 10) {
  const response = await fetch(`${API_BASE}/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...profile, top_n: topN }),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || `Recommend API failed (${response.status})`)
  }

  const data = await response.json()
  const rawRecs = data.recommendations || []
  return {
    jobs: rawRecs.map(mapJobToCard),
    profile: data.skill_profile || profile,
    rawRecs,
    engine: data.engine || null,
  }
}

export function persistRecommendationSession(profile, jobs, rawRecs = null) {
  sessionStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile))
  sessionStorage.setItem(RECOMMENDATIONS_STORAGE_KEY, JSON.stringify(jobs))
  if (rawRecs) {
    sessionStorage.setItem(RAW_RECOMMENDATIONS_STORAGE_KEY, JSON.stringify(rawRecs))
  } else {
    sessionStorage.removeItem(RAW_RECOMMENDATIONS_STORAGE_KEY)
  }

  sessionStorage.removeItem(ANALYSIS_STORAGE_KEY)
  sessionStorage.removeItem('resumeTipsCoaching')
  if (profile?.source !== 'quiz') {
    sessionStorage.removeItem(QUIZ_SESSION_STORAGE_KEY)
  }
}

export function persistQuizSessionId(sessionId) {
  if (sessionId) {
    sessionStorage.setItem(QUIZ_SESSION_STORAGE_KEY, sessionId)
  }
}

export function persistQuizProgress(progress) {
  if (progress) {
    sessionStorage.setItem(QUIZ_PROGRESS_STORAGE_KEY, JSON.stringify(progress))
  } else {
    sessionStorage.removeItem(QUIZ_PROGRESS_STORAGE_KEY)
  }
}

export function loadStoredQuizHistory() {
  try {
    const raw = localStorage.getItem(QUIZ_HISTORY_STORAGE_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function persistQuizAttempt(profile, progress = null, jobs = []) {
  if (!profile) {
    return
  }

  const history = loadStoredQuizHistory()
  const id = profile.session_id || progress?.session_id || `quiz-${Date.now()}`
  const entry = {
    id,
    completed_at: new Date().toISOString(),
    profile,
    progress,
    jobs,
  }
  const nextHistory = [
    entry,
    ...history.filter((item) => item?.id !== id),
  ].slice(0, 25)

  localStorage.setItem(QUIZ_HISTORY_STORAGE_KEY, JSON.stringify(nextHistory))
}

export function persistAnalysis(analysis) {
  sessionStorage.setItem(ANALYSIS_STORAGE_KEY, JSON.stringify(analysis))
}

export function loadStoredRecommendations() {
  try {
    const raw = sessionStorage.getItem(RECOMMENDATIONS_STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function loadStoredProfile() {
  try {
    const raw = sessionStorage.getItem(PROFILE_STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function loadStoredAnalysis() {
  try {
    const raw = sessionStorage.getItem(ANALYSIS_STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function loadStoredSessionId() {
  try {
    return sessionStorage.getItem(QUIZ_SESSION_STORAGE_KEY) || ''
  } catch {
    return ''
  }
}

export function loadStoredQuizProgress() {
  try {
    const raw = sessionStorage.getItem(QUIZ_PROGRESS_STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function loadStoredRawRecommendations() {
  try {
    const raw = sessionStorage.getItem(RAW_RECOMMENDATIONS_STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function clearStoredRecommendations() {
  sessionStorage.removeItem(PROFILE_STORAGE_KEY)
  sessionStorage.removeItem(RECOMMENDATIONS_STORAGE_KEY)
  sessionStorage.removeItem(RAW_RECOMMENDATIONS_STORAGE_KEY)
  sessionStorage.removeItem(ANALYSIS_STORAGE_KEY)
  sessionStorage.removeItem('resumeTipsCoaching')
  sessionStorage.removeItem(QUIZ_SESSION_STORAGE_KEY)
  sessionStorage.removeItem(QUIZ_PROGRESS_STORAGE_KEY)
}

export async function fetchAnalysis(sessionId, profile = null, recommendations = null) {
  const response = await fetch(`${API_BASE}/analysis`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(
      sessionId
        ? { session_id: sessionId }
        : { skill_profile: profile, recommendations },
    ),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || `Analysis API failed (${response.status})`)
  }

  return response.json()
}

function mapFlatTipsToSections(flatTips) {
  if (!Array.isArray(flatTips) || !flatTips.length) {
    return []
  }

  return [
    {
      section: 'Coaching',
      icon: '01',
      tips: flatTips,
    },
  ]
}

export async function fetchResumeTips(sessionId, profile = null, recommendations = null) {
  const response = await fetch(`${API_BASE}/resume-tips`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(
      sessionId
        ? { session_id: sessionId }
        : { skill_profile: profile, recommendations },
    ),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || `Resume Tips API failed (${response.status})`)
  }

  const data = await response.json()
  const tips = data.tips?.length
    ? data.tips
    : mapFlatTipsToSections(data.resume_tips)

  return {
    summary: data.summary,
    tips,
    schedule: data.schedule || [],
    is_ai: data.is_ai,
    resume_tips: data.resume_tips,
    resource_explanations: data.resource_explanations,
  }
}

export async function uploadResumeForTips(file, profile = null, recommendations = null) {
  const formData = new FormData()
  formData.append('resume', file)
  if (profile) {
    formData.append('profile', JSON.stringify(profile))
  }
  if (recommendations) {
    formData.append('recommendations', JSON.stringify(recommendations))
  }
  const targetRole = profile?.target_role || profile?.top_category || profile?.category
  if (targetRole) {
    formData.append('target_role', targetRole)
  }

  const response = await fetch(`${API_BASE}/resume/upload`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || `Resume upload failed (${response.status})`)
  }

  return response.json()
}

export async function generateResumeDocument(payload) {
  const response = await fetch(`${API_BASE}/resume/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || `Resume generator failed (${response.status})`)
  }

  return response.json()
}

export async function fetchTelegramJobs({ query = '', limit = 50 } = {}) {
  const params = new URLSearchParams({ limit: String(limit) })
  if (query.trim()) {
    params.set('q', query.trim())
  }
  const response = await fetch(`${API_BASE}/telegram/jobs?${params}`)

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || `Telegram jobs failed (${response.status})`)
  }

  return response.json()
}

export async function fetchTelegramJobMatches(profile, { query = '', limit = 60 } = {}) {
  const response = await fetch(`${API_BASE}/telegram/jobs/match`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      skill_profile: profile,
      query,
      limit,
    }),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || `Telegram match failed (${response.status})`)
  }

  return response.json()
}

export async function ingestTelegramJobs(posts) {
  const response = await fetch(`${API_BASE}/telegram/jobs/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ posts }),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || `Telegram ingest failed (${response.status})`)
  }

  return response.json()
}

export async function refreshTelegramJobs(channels = null, perChannelLimit = 12) {
  const response = await fetch(`${API_BASE}/telegram/jobs/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      channels,
      per_channel_limit: perChannelLimit,
    }),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || `Telegram refresh failed (${response.status})`)
  }

  return response.json()
}
