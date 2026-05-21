const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000'

export const PROFILE_STORAGE_KEY = 'skillProfile'
export const RECOMMENDATIONS_STORAGE_KEY = 'jobRecommendations'
export const ANALYSIS_STORAGE_KEY = 'recommendationAnalysis'

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

export function toApiProfile({ skills, experience, category, location = 'remote' }) {
  return {
    detected_skills: skills.map((s) => s.toLowerCase()),
    experience_level: EXPERIENCE_MAP[experience] || 'junior',
    top_category: CATEGORY_MAP[category] || category?.toLowerCase?.() || '',
    location,
  }
}

export function mapJobToCard(job) {
  return {
    id: job.job_id,
    title: job.job_title,
    company: job.category?.replace(/-/g, ' ') || 'Open role',
    category: job.category,
    experience: job.exp_level,
    match: job.match_score,
    readiness: Math.round(
      (job.breakdown?.skill_overlap ?? 0) * 0.6 +
        (job.breakdown?.experience_match ?? 0) * 0.4,
    ),
    skills: job.matched_skills?.length
      ? job.matched_skills
      : (job.missing_skills || []).slice(0, 3),
    breakdown: job.breakdown,
    description: job.description,
    missing_skills: job.missing_skills,
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
  return (data.recommendations || []).map(mapJobToCard)
}

export function persistRecommendationSession(profile, jobs) {
  sessionStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile))
  sessionStorage.setItem(RECOMMENDATIONS_STORAGE_KEY, JSON.stringify(jobs))
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

export async function fetchAnalysis(profile, recommendations) {
  const response = await fetch(`${API_BASE}/analysis`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ profile, recommendations }),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.error || `Analysis API failed (${response.status})`)
  }

  return response.json()
}
