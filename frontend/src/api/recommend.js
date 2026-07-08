const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000'

export const PROFILE_STORAGE_KEY = 'skillProfile'
export const RECOMMENDATIONS_STORAGE_KEY = 'jobRecommendations'
export const RAW_RECOMMENDATIONS_STORAGE_KEY = 'rawJobRecommendations'
export const ANALYSIS_STORAGE_KEY = 'recommendationAnalysis'
export const QUIZ_SESSION_STORAGE_KEY = 'quizSessionId'
export const QUIZ_PROGRESS_STORAGE_KEY = 'quizProgress'
export const QUIZ_HISTORY_STORAGE_KEY = 'quizAttemptHistory'
export const ADMIN_ACCESS_STORAGE_KEY = 'adminAccessKey'
export const ANALYTICS_SESSION_STORAGE_KEY = 'analyticsSessionId'

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

function readStoredValue(storage, key) {
  try {
    return storage.getItem(key) || ''
  } catch {
    return ''
  }
}

function createAnalyticsSessionId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }

  return `visitor-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

export function getAnalyticsSessionId() {
  if (typeof window === 'undefined') {
    return ''
  }

  const stored =
    readStoredValue(localStorage, ANALYTICS_SESSION_STORAGE_KEY) ||
    readStoredValue(sessionStorage, ANALYTICS_SESSION_STORAGE_KEY)

  if (stored) {
    return stored
  }

  const sessionId = createAnalyticsSessionId()
  try {
    localStorage.setItem(ANALYTICS_SESSION_STORAGE_KEY, sessionId)
    sessionStorage.setItem(ANALYTICS_SESSION_STORAGE_KEY, sessionId)
  } catch {
    // Activity still records without a persistent browser id.
  }
  return sessionId
}

function withSessionHeader(headers = {}) {
  const sessionId = getAnalyticsSessionId()
  return sessionId ? { ...headers, 'X-Session-Id': sessionId } : headers
}

function jsonHeaders(headers = {}) {
  return withSessionHeader({ 'Content-Type': 'application/json', ...headers })
}

export function getStoredAdminAccessKey() {
  if (typeof window === 'undefined') {
    return ''
  }

  return readStoredValue(sessionStorage, ADMIN_ACCESS_STORAGE_KEY) || readStoredValue(localStorage, ADMIN_ACCESS_STORAGE_KEY)
}

export function setStoredAdminAccessKey(accessKey) {
  if (typeof window === 'undefined') {
    return
  }

  try {
    sessionStorage.setItem(ADMIN_ACCESS_STORAGE_KEY, accessKey)
    localStorage.setItem(ADMIN_ACCESS_STORAGE_KEY, accessKey)
  } catch {
    // Session storage still keeps the active admin login available.
  }
}

export function clearStoredAdminAccessKey() {
  if (typeof window === 'undefined') {
    return
  }

  sessionStorage.removeItem(ADMIN_ACCESS_STORAGE_KEY)
  try {
    localStorage.removeItem(ADMIN_ACCESS_STORAGE_KEY)
  } catch {
    // The active session is still cleared even if local storage is unavailable.
  }
}

function getAdminHeaders() {
  const accessKey = getStoredAdminAccessKey()
  return accessKey ? { 'X-Admin-Key': accessKey } : {}
}

export async function verifyAdminAccess(accessKey) {
  const response = await fetch(`${API_BASE}/admin/login`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({ access_key: accessKey }),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || `Admin login failed (${response.status})`)
  }

  return response.json()
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
  const response = await fetch(`${API_BASE}/skills/suggest?${params}`, {
    headers: withSessionHeader(),
  })
  if (!response.ok) {
    return []
  }
  const data = await response.json()
  return data.suggestions || []
}

export async function normalizeSkillValues(skills) {
  const response = await fetch(`${API_BASE}/skills/normalize`, {
    method: 'POST',
    headers: jsonHeaders(),
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
    deadlineDate: job.deadline_date || job.deadline,
    postedAt: job.posted_at,
    sourceChannel: job.source_channel,
    applyLink: job.apply_link,
    requiredSkillCount: job.required_skill_count,
  }
}

export async function fetchRecommendations(profile, topN = 10) {
  const response = await fetch(`${API_BASE}/recommend`, {
    method: 'POST',
    headers: jsonHeaders(),
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
    localStorage.removeItem(QUIZ_HISTORY_STORAGE_KEY)
  } catch {
    // Old browser history is intentionally discarded for the main website flow.
  }
  return []
}

export function persistQuizAttempt(profile, progress = null, jobs = []) {
  void profile
  void progress
  void jobs
}

export function persistAnalysis(analysis) {
  sessionStorage.setItem(ANALYSIS_STORAGE_KEY, JSON.stringify(analysis))
}

export function loadStoredRecommendations() {
  try {
    const raw = sessionStorage.getItem(RECOMMENDATIONS_STORAGE_KEY)
    if (raw) {
      return JSON.parse(raw)
    }
    return null
  } catch {
    return null
  }
}

export function loadStoredProfile() {
  try {
    const raw = sessionStorage.getItem(PROFILE_STORAGE_KEY)
    if (raw) {
      return JSON.parse(raw)
    }
    return null
  } catch {
    return null
  }
}

export function loadStoredAnalysis() {
  try {
    const raw = sessionStorage.getItem(ANALYSIS_STORAGE_KEY)
    if (raw) {
      return JSON.parse(raw)
    }
    return null
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
    if (raw) {
      return JSON.parse(raw)
    }
    return null
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
  try {
    localStorage.removeItem(PROFILE_STORAGE_KEY)
    localStorage.removeItem(RECOMMENDATIONS_STORAGE_KEY)
    localStorage.removeItem(RAW_RECOMMENDATIONS_STORAGE_KEY)
    localStorage.removeItem(ANALYSIS_STORAGE_KEY)
    localStorage.removeItem(QUIZ_HISTORY_STORAGE_KEY)
    localStorage.removeItem('resumeTipsCoaching')
  } catch {
    // Clearing session storage is enough for the active flow.
  }
}

export async function fetchAnalysis(sessionId, profile = null, recommendations = null) {
  const body = {
    ...(sessionId ? { session_id: sessionId } : {}),
    ...(profile ? { skill_profile: profile } : {}),
    ...(recommendations ? { recommendations } : {}),
  }

  const response = await fetch(`${API_BASE}/analysis`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || `Analysis API failed (${response.status})`)
  }

  return response.json()
}

export async function loadOrFetchStoredAnalysis() {
  const stored = loadStoredAnalysis()
  if (stored) {
    return stored
  }

  const profile = loadStoredProfile()
  const recommendations = loadStoredRawRecommendations() || loadStoredRecommendations()
  if (!profile || !recommendations?.length) {
    throw new Error('Complete an assessment first so gaps and learning resources can be generated.')
  }

  const analysis = await fetchAnalysis(loadStoredSessionId(), profile, recommendations)
  persistAnalysis(analysis)
  return analysis
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
  const body = {
    ...(sessionId ? { session_id: sessionId } : {}),
    ...(profile ? { skill_profile: profile } : {}),
    ...(recommendations ? { recommendations } : {}),
  }

  const response = await fetch(`${API_BASE}/resume-tips`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify(body),
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
    headers: withSessionHeader(),
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
    headers: jsonHeaders(),
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || `Resume generator failed (${response.status})`)
  }

  return response.json()
}

export async function fetchTelegramJobs({ query = '', role = '', limit = 50 } = {}) {
  const params = new URLSearchParams({ limit: String(limit) })
  if (query.trim()) {
    params.set('q', query.trim())
  }
  if (role.trim()) {
    params.set('role', role.trim())
  }
  const response = await fetch(`${API_BASE}/telegram/jobs?${params}`, {
    headers: withSessionHeader(),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || `Telegram jobs failed (${response.status})`)
  }

  return response.json()
}

export async function fetchTelegramJobMatches(profile, { query = '', role = '', limit = 60 } = {}) {
  const response = await fetch(`${API_BASE}/telegram/jobs/match`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({
      skill_profile: profile,
      query,
      role,
      limit,
    }),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || `Telegram match failed (${response.status})`)
  }

  return response.json()
}

export async function recordFlowEvent(payload) {
  const sessionId = payload?.session_id || getAnalyticsSessionId()
  const response = await fetch(`${API_BASE}/analytics/event`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({ ...payload, session_id: sessionId }),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || `Analytics event failed (${response.status})`)
  }

  return response.json()
}

export function recordSiteActivity(eventType, details = {}) {
  if (typeof window === 'undefined' || window.location.pathname.startsWith('/admin')) {
    return Promise.resolve({ skipped: true })
  }

  const path = details.path || window.location.pathname
  return recordFlowEvent({
    event_type: eventType,
    source: 'website',
    path,
    route: path,
    summary: details.summary || details.label || path,
    label: details.label,
    href: details.href,
    method: details.method,
    status: details.status,
  })
}

export async function fetchAdminAnalytics({ limit = 1000 } = {}) {
  const params = new URLSearchParams({ limit: String(limit) })
  const response = await fetch(`${API_BASE}/admin/analytics?${params}`, {
    headers: withSessionHeader(getAdminHeaders()),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || `Admin analytics failed (${response.status})`)
  }

  return response.json()
}

export async function fetchAdminQuizAttempts({ limit = 100 } = {}) {
  const params = new URLSearchParams({ limit: String(limit) })
  const response = await fetch(`${API_BASE}/admin/quiz/attempts?${params}`, {
    headers: withSessionHeader(getAdminHeaders()),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || `Admin quiz attempts failed (${response.status})`)
  }

  return response.json()
}

export async function fetchAdminQuizQuestions({
  role = '',
  query = '',
  status = 'active',
  limit = 500,
} = {}) {
  const params = new URLSearchParams({ status, limit: String(limit) })
  if (role.trim()) {
    params.set('role', role.trim())
  }
  if (query.trim()) {
    params.set('q', query.trim())
  }
  const response = await fetch(`${API_BASE}/admin/quiz/questions?${params}`, {
    headers: withSessionHeader(getAdminHeaders()),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || `Admin quiz questions failed (${response.status})`)
  }

  return response.json()
}

export async function saveAdminQuizQuestion(question) {
  const id = question?.id
  const response = await fetch(
    id ? `${API_BASE}/admin/quiz/questions/${encodeURIComponent(id)}` : `${API_BASE}/admin/quiz/questions`,
    {
      method: id ? 'PUT' : 'POST',
      headers: jsonHeaders(getAdminHeaders()),
      body: JSON.stringify(question),
    },
  )

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || `Save quiz question failed (${response.status})`)
  }

  return response.json()
}

export async function deleteAdminQuizQuestion(questionId) {
  const response = await fetch(`${API_BASE}/admin/quiz/questions/${encodeURIComponent(questionId)}`, {
    method: 'DELETE',
    headers: withSessionHeader(getAdminHeaders()),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || `Delete quiz question failed (${response.status})`)
  }

  return response.json()
}

export async function ingestTelegramJobs(posts) {
  const response = await fetch(`${API_BASE}/telegram/jobs/ingest`, {
    method: 'POST',
    headers: jsonHeaders(),
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
    headers: jsonHeaders(),
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
