import { useEffect, useState } from 'react'
import {
  fetchAnalysis,
  fetchRecommendations,
  fetchResumeTips,
  fetchTelegramJobs,
  loadStoredAnalysis,
  loadStoredProfile,
  loadStoredQuizHistory,
  loadStoredQuizProgress,
  loadStoredRecommendations,
  persistAnalysis,
  persistRecommendationSession,
} from '../api/recommend.js'
const adminTabs = ['Overview', 'Profile', 'Matching', 'Learning', 'Resume', 'Telegram']
const profilePages = ['Quiz Intake', 'Match Graph', 'Completion Detail', 'Quiz Prompts']
const ADMIN_QUIZ_PROMPTS_STORAGE_KEY = 'adminQuizPrompts'
const ADMIN_RESOURCES_STORAGE_KEY = 'adminLearningResources'
const WORK_TYPE_OPTIONS = [
  {
    id: 'SOFTWARE',
    label: 'Build software, websites, or apps',
    aliases: [
      'software',
      'website',
      'web',
      'apps',
      'app',
      'frontend',
      'backend',
      'fullstack',
      'mobile',
      'devops',
      'developer',
      'programming',
      'engineering',
    ],
  },
  {
    id: 'DATA_AI',
    label: 'Work with data, analytics, or AI models',
    aliases: ['data', 'analytics', 'analyst', 'ai', 'machine learning', 'ml', 'model', 'statistics'],
  },
  {
    id: 'CREATIVE',
    label: 'Design visuals, interfaces, or creative content',
    aliases: ['design', 'visual', 'interface', 'creative', 'ux', 'ui', 'content', 'brand'],
  },
  {
    id: 'BUSINESS',
    label: 'Business, product, or project management',
    aliases: ['business', 'product', 'project', 'manager', 'management', 'operations', 'scrum'],
  },
  {
    id: 'SALES_MKT',
    label: 'Sales, marketing, or customer-facing work',
    aliases: ['sales', 'marketing', 'customer', 'support', 'account manager', 'growth', 'community'],
  },
  {
    id: 'ACCOUNTING',
    label: 'Accounting, finance, or banking',
    aliases: ['accounting', 'finance', 'banking', 'audit', 'bookkeeping', 'payroll'],
  },
  {
    id: 'ADMIN',
    label: 'Administration, office management, or HR',
    aliases: ['administration', 'admin', 'office', 'hr', 'human resources', 'recruiting'],
  },
  {
    id: 'ENGINEERING',
    label: 'Architecture, engineering, or construction',
    aliases: ['architecture', 'construction', 'civil', 'mechanical', 'electrical', 'architect'],
  },
  {
    id: 'EDUCATION',
    label: 'Education, training, or instruction',
    aliases: ['education', 'training', 'instruction', 'teacher', 'trainer', 'curriculum'],
  },
  {
    id: 'LOGISTICS',
    label: 'Logistics, delivery, or transport',
    aliases: ['logistics', 'delivery', 'transport', 'driver', 'fleet', 'supply chain', 'warehouse'],
  },
  {
    id: 'MEDICAL',
    label: 'Healthcare or medical work',
    aliases: ['healthcare', 'medical', 'medicine', 'nurse', 'clinical', 'pharmacy'],
  },
  {
    id: 'GENERAL',
    label: 'General or other',
    aliases: ['general', 'other'],
  },
]
const DEFAULT_QUIZ_ROLE = 'General or other'
const ALL_QUIZ_ROLES = 'All work types'
const EMPTY_PROMPT_DRAFT = {
  role: DEFAULT_QUIZ_ROLE,
  stem: '',
  optionsText: '',
}
const EMPTY_RESOURCE_DRAFT = {
  skill: '',
  title: '',
  platform: '',
  level: '',
  hours: '',
  url: '',
}
const MAIN_WORK_TYPE_PROMPTS = [
  {
    id: 'main-work-type-router',
    role: DEFAULT_QUIZ_ROLE,
    stem: 'What best describes the kind of work you do or want to do?',
    options: WORK_TYPE_OPTIONS.map((item) => item.label),
    status: 'Live',
    updated: 'Main quiz router',
  },
]

const defaultChannels = [
  '@freelance_ethio',
  '@effoyjobs',
  '@josad_software',
  '@ethiojobsofficial',
  '@geezjobs_ethiopia',
  '@Maroset',
]

function statusClass(status) {
  return `admin-status admin-status-${status.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`
}

function uniqueItems(values = []) {
  return [...new Set(values.filter(Boolean).map((value) => String(value)))]
}

function formatLabel(value, fallback = 'Not set') {
  if (value === null || value === undefined || value === '') {
    return fallback
  }

  return String(value)
    .replace(/[_-]/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

function normalizeText(value) {
  return String(value || '')
    .replace(/[_-]/g, ' ')
    .toLowerCase()
    .trim()
}

function getWorkTypeLabel(value, fallback = DEFAULT_QUIZ_ROLE) {
  const raw = String(value || '').trim()
  if (!raw) {
    return fallback
  }

  const normalized = normalizeText(raw)
  const directMatch = WORK_TYPE_OPTIONS.find((item) =>
    normalizeText(item.id) === normalized || normalizeText(item.label) === normalized,
  )

  if (directMatch) {
    return directMatch.label
  }

  const aliasMatch = WORK_TYPE_OPTIONS.find((item) =>
    item.aliases.some((alias) => normalized.includes(normalizeText(alias))),
  )

  return aliasMatch?.label || fallback
}

function getWorkTypeOptionLabels() {
  return WORK_TYPE_OPTIONS.map((item) => item.label)
}

function loadCachedResumeTips() {
  if (typeof window === 'undefined') {
    return null
  }

  try {
    const raw = sessionStorage.getItem('resumeTipsCoaching')
    if (raw) {
      return JSON.parse(raw)
    }

    const localRaw = localStorage.getItem('resumeTipsCoaching')
    return localRaw ? JSON.parse(localRaw) : null
  } catch {
    return null
  }
}

function persistCachedResumeTips(payload) {
  if (!payload) {
    return
  }

  try {
    sessionStorage.setItem('resumeTipsCoaching', JSON.stringify(payload))
    localStorage.setItem('resumeTipsCoaching', JSON.stringify(payload))
  } catch {
    // The in-memory admin state still updates if browser storage is unavailable.
  }
}

function getProfileSkills(profile) {
  return uniqueItems(
    profile?.skill_ids ||
      profile?.detected_skills ||
      profile?.skills ||
      Object.keys(profile?.skill_scores || {}),
  )
}

function normalizeResource(resource, index) {
  const source = resource || {}
  const title = source.title || source.name || ''
  const skill = source.skill || source.skill_name || source.work_type || ''

  return {
    id: source.id || source.resource_id || `resource-${index + 1}-${normalizeText(title || skill || 'item')}`,
    skill,
    title,
    platform: source.platform || source.source || '',
    level: source.level || source.gap_priority || '',
    hours: source.hours ?? source.duration ?? '',
    url: source.url || source.link || '',
    recommendation_score: source.recommendation_score,
    updated: source.updated || 'Saved locally',
  }
}

function hasStoredAdminResources() {
  if (typeof window === 'undefined') {
    return false
  }

  return localStorage.getItem(ADMIN_RESOURCES_STORAGE_KEY) !== null
}

function loadAdminResources() {
  if (typeof window === 'undefined') {
    return []
  }

  try {
    const raw = localStorage.getItem(ADMIN_RESOURCES_STORAGE_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed.map(normalizeResource) : []
  } catch {
    return []
  }
}

function saveAdminResources(resources) {
  if (typeof window === 'undefined') {
    return
  }

  try {
    localStorage.setItem(ADMIN_RESOURCES_STORAGE_KEY, JSON.stringify(resources))
  } catch {
    // Resource edits remain in component state when local storage is unavailable.
  }
}

function createResourceId(title) {
  const slug = normalizeText(title).replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '')
  return `resource-${slug || 'item'}-${Date.now()}`
}

function flattenResourceGroups(groups = []) {
  return groups.flatMap((group) =>
    (group.resources || []).map((resource) => ({
      ...resource,
      skill: resource.skill || group.skill,
      skill_id: resource.skill_id || group.skill_id,
    })),
  )
}

function getDerivedGaps(signals) {
  return signals.map((signal, index) => ({
    skill: signal,
    skill_id: normalizeText(signal).replace(/\s+/g, '-'),
    priority: Math.max(45, 90 - index * 8),
    priority_label: 'Stored signal',
    current: 'Observed',
    required: 'Recommended',
  }))
}

function getJobTitle(job) {
  return job.title || job.job_title || 'Recommended role'
}

function getJobCompany(job) {
  return job.company || job.source || job.source_channel || formatLabel(job.category, 'Open role')
}

function getJobCategory(job) {
  return formatLabel(job.category || job.role_category)
}

function getJobWorkType(job) {
  return getWorkTypeLabel(
    [
      job.category,
      job.role_category,
      job.title,
      job.job_title,
      job.company,
      job.description,
    ].filter(Boolean).join(' '),
  )
}

function getJobMatch(job) {
  const value = Number(job.match ?? job.match_score ?? job.match_percent)
  return Number.isFinite(value) ? Math.round(value) : null
}

function getMatchClass(match) {
  if (match >= 75) {
    return 'match-high'
  }

  if (match >= 50) {
    return 'match-mid'
  }

  return 'match-low'
}

function getMissingSkills(job) {
  return uniqueItems(job.missingSkillNames || job.missing_skill_names || job.missing_skills || [])
}

function getMatchedSkills(job) {
  return uniqueItems(
    job.matchedSkillNames ||
      job.matched_skill_names ||
      job.required_skill_names ||
      job.skills ||
      [],
  )
}

function getAverageMatch(jobs) {
  const scores = jobs.map(getJobMatch).filter((value) => Number.isFinite(value))

  if (!scores.length) {
    return null
  }

  return Math.round(scores.reduce((sum, value) => sum + value, 0) / scores.length)
}

function getGapName(gap) {
  return gap.skill || formatLabel(gap.skill_id, 'Coverage gap')
}

function getGapPriority(gap) {
  const value = Number(gap.priority ?? gap.gap_score ?? gap.score)
  if (!Number.isFinite(value)) {
    return null
  }

  return value <= 1 ? Math.round(value * 100) : Math.round(value)
}

function getResumeSectionCount(coaching) {
  return coaching?.tips?.length || 0
}

function formatPercent(value, fallback = 'Pending') {
  const numeric = Number(value)

  if (!Number.isFinite(numeric)) {
    return fallback
  }

  return `${Math.round(numeric <= 1 ? numeric * 100 : numeric)}%`
}

function getTopMatchedJobs(jobs, limit = 3) {
  return [...jobs]
    .sort((left, right) => (getJobMatch(right) ?? -1) - (getJobMatch(left) ?? -1))
    .slice(0, limit)
}

function getProfileFillItems(profile, skills) {
  const evidence = profile?.evidence || {}
  const targetRole = profile?.role_count > 1
    ? `${profile.role_count} work types`
    : profile?.target_role || profile?.top_category || profile?.category || profile?.detected_role
  const hasExperience = Boolean(profile?.experience_level || profile?.experience)
  const hasLocation = Boolean(profile?.location)
  const hasEvidence = Boolean(
    evidence.experience_years !== null && evidence.experience_years !== undefined ||
      evidence.has_projects ||
      evidence.portfolio_url,
  )

  return [
    {
      label: 'Supporting signals',
      value: skills.length ? `${skills.length} signals` : 'Missing',
      score: Math.min(100, Math.round((skills.length / 6) * 100)),
    },
    {
      label: 'Work type',
      value: formatLabel(targetRole),
      score: targetRole ? 100 : 0,
    },
    {
      label: 'Experience',
      value: formatLabel(profile?.experience_level || profile?.experience),
      score: hasExperience ? 100 : 0,
    },
    {
      label: 'Evidence',
      value: hasEvidence ? 'Added' : 'Light',
      score: hasEvidence ? 100 : profile ? 35 : 0,
    },
    {
      label: 'Location',
      value: formatLabel(profile?.location, 'Remote-friendly'),
      score: hasLocation ? 100 : profile ? 65 : 0,
    },
  ]
}

function getQuizSummary(profile, progress) {
  const answered = Number(progress?.questions_answered ?? profile?.question_count ?? 0)
  const estimated = Number(progress?.estimated_total ?? (answered ? Math.max(answered, 12) : 0))
  const percent = Number(progress?.percent ?? (estimated ? (answered / estimated) * 100 : 0))
  const confidence = progress?.confidence ?? profile?.confidence

  return {
    answered: Number.isFinite(answered) ? answered : 0,
    estimated: Number.isFinite(estimated) && estimated > 0 ? estimated : 0,
    percent: Number.isFinite(percent) ? Math.min(100, Math.round(percent)) : 0,
    confidence,
    detectedDomain: progress?.detected_domain || profile?.detected_domain,
    detectedRole: progress?.detected_role || profile?.detected_role || profile?.target_role,
    difficulty: progress?.difficulty_reached || profile?.difficulty_reached || 'Not reached',
    performanceCounts: progress?.performance_counts || profile?.performance_counts || {},
  }
}

function normalizeRole(value, fallback = DEFAULT_QUIZ_ROLE) {
  return getWorkTypeLabel(value, fallback)
}

function parsePromptOptions(optionsText) {
  return optionsText
    .split('\n')
    .map((option) => option.trim())
    .filter(Boolean)
}

function normalizePrompt(question, index) {
  return {
    id: question.id || `prompt-${index + 1}`,
    role: normalizeRole(question.role || question.role_category || question.target_role || question.category),
    stem: question.stem || question.text || '',
    options: Array.isArray(question.options) ? question.options.map(String) : [],
    status: 'Live',
    updated: 'Local draft',
  }
}

function getDefaultQuizPrompts() {
  return MAIN_WORK_TYPE_PROMPTS.map((question, index) => normalizePrompt(question, index))
}

function normalizeStoredPrompt(prompt, index) {
  const source = prompt || {}
  const basePrompt = normalizePrompt(source, index)

  return {
    ...basePrompt,
    role: normalizeRole(source.role || basePrompt.role),
    status: source.status || basePrompt.status,
    updated: source.updated || basePrompt.updated,
  }
}

function loadAdminQuizPrompts() {
  if (typeof window === 'undefined') {
    return getDefaultQuizPrompts()
  }

  try {
    const raw = localStorage.getItem(ADMIN_QUIZ_PROMPTS_STORAGE_KEY)
    if (!raw) {
      return getDefaultQuizPrompts()
    }

    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) {
      return getDefaultQuizPrompts()
    }

    return parsed.map((prompt, index) => normalizeStoredPrompt(prompt, index))
  } catch {
    return getDefaultQuizPrompts()
  }
}

function saveAdminQuizPrompts(prompts) {
  if (typeof window === 'undefined') {
    return
  }

  try {
    localStorage.setItem(ADMIN_QUIZ_PROMPTS_STORAGE_KEY, JSON.stringify(prompts))
  } catch {
    // Admin prompt edits can still work for the current session if browser storage is unavailable.
  }
}

function createPromptId(role) {
  const roleSlug = role.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '')
  return `prompt-${roleSlug || 'role'}-${Date.now()}`
}

function getAttemptProfile(attempt) {
  return attempt?.profile || {}
}

function getAttemptProgress(attempt) {
  return attempt?.progress || {}
}

function getAttemptJobs(attempt) {
  return Array.isArray(attempt?.jobs) ? attempt.jobs : []
}

function getAttemptWorkType(attempt) {
  const profile = getAttemptProfile(attempt)
  const progress = getAttemptProgress(attempt)

  return getWorkTypeLabel(
    progress?.detected_domain ||
      progress?.detected_role ||
      profile.detected_domain ||
      profile.target_role ||
      profile.detected_role ||
      profile.top_category ||
      profile.category,
    '',
  )
}

function buildMatchGraphRows(attempts, defaultJobs) {
  const rows = new Map()
  const sourceAttempts = attempts.length
    ? attempts
    : [{ id: 'current-matches', jobs: defaultJobs }]

  sourceAttempts.forEach((attempt) => {
    const attemptJobs = getAttemptJobs(attempt)
    const attemptWorkType = getAttemptWorkType(attempt)

    if (!attemptJobs.length && attemptWorkType) {
      const current = rows.get(attemptWorkType) || {
        title: attemptWorkType,
        category: 'General AI work area',
        count: 0,
        scoreTotal: 0,
        maxScore: 0,
      }

      current.count += 1
      rows.set(attemptWorkType, current)
      return
    }

    attemptJobs.forEach((job) => {
      const title = getJobWorkType(job)
      const score = getJobMatch(job)

      if (!title || score === null) {
        return
      }

      const current = rows.get(title) || {
        title,
        category: 'General AI work area',
        count: 0,
        scoreTotal: 0,
        maxScore: 0,
      }

      current.count += 1
      current.scoreTotal += score
      current.maxScore = Math.max(current.maxScore, score)
      rows.set(title, current)
    })
  })

  return [...rows.values()]
    .map((row) => ({
      ...row,
      averageScore: Math.round(row.scoreTotal / Math.max(row.count, 1)),
    }))
    .sort((left, right) => right.averageScore - left.averageScore)
    .slice(0, 8)
}

function countWorkTypeSignals(values) {
  const counts = new Map()

  values.forEach((value) => {
    const workType = getWorkTypeLabel(value, '')
    if (!workType) {
      return
    }

    counts.set(workType, (counts.get(workType) || 0) + 1)
  })

  return [...counts.entries()]
    .map(([workType, count]) => ({ workType, count }))
    .sort((left, right) => right.count - left.count || left.workType.localeCompare(right.workType))
}

function Admin() {
  const [activeTab, setActiveTab] = useState(adminTabs[0])
  const [activeProfilePage, setActiveProfilePage] = useState(profilePages[0])
  const [jobSearch, setJobSearch] = useState('')
  const [quizPrompts, setQuizPrompts] = useState(loadAdminQuizPrompts)
  const [selectedPromptRole, setSelectedPromptRole] = useState(ALL_QUIZ_ROLES)
  const [newPromptDraft, setNewPromptDraft] = useState({ ...EMPTY_PROMPT_DRAFT })
  const [editingPromptId, setEditingPromptId] = useState('')
  const [promptDraft, setPromptDraft] = useState({ ...EMPTY_PROMPT_DRAFT })
  const [analysis, setAnalysis] = useState(() => loadStoredAnalysis())
  const [resumeCoaching, setResumeCoaching] = useState(() => loadCachedResumeTips())
  const [storedRecommendations, setStoredRecommendations] = useState(() => loadStoredRecommendations() || [])
  const [managedResources, setManagedResources] = useState(loadAdminResources)
  const [hasManagedResourceStore, setHasManagedResourceStore] = useState(hasStoredAdminResources)
  const [editingResourceId, setEditingResourceId] = useState('')
  const [resourceDraft, setResourceDraft] = useState({ ...EMPTY_RESOURCE_DRAFT })
  const [telegramState, setTelegramState] = useState({
    error: '',
    isLoading: true,
    jobs: [],
    updatedAt: '',
  })

  const profile = loadStoredProfile()
  const recommendations = storedRecommendations
  const quizHistory = loadStoredQuizHistory()
  const quizProgress = loadStoredQuizProgress()

  const currentProfileSkills = getProfileSkills(profile)
  const currentQuizSummary = getQuizSummary(profile, quizProgress)
  const visibleRecommendations = recommendations
  const currentQuizAttempt = profile || quizProgress
    ? {
        id: profile?.session_id || 'active-session',
        completed_at: profile?.session_id ? 'Current quiz session' : 'In progress',
        profile,
        progress: quizProgress,
        jobs: visibleRecommendations,
        isCurrent: true,
      }
    : null
  const quizAttempts = [
    ...(currentQuizAttempt ? [currentQuizAttempt] : []),
    ...quizHistory.filter((attempt) => attempt?.id !== currentQuizAttempt?.id),
  ]
  const aggregateRecommendationRows = quizAttempts.flatMap(getAttemptJobs)
  const aggregateRecommendations = aggregateRecommendationRows.length
    ? aggregateRecommendationRows
    : visibleRecommendations
  const hasStoredRecommendations = aggregateRecommendationRows.length > 0 || recommendations.length > 0
  const recommendationSource = aggregateRecommendationRows.length
    ? 'Stored quiz history'
    : recommendations.length
      ? 'Current session'
      : 'Awaiting AI'
  const matchGraphRows = buildMatchGraphRows(quizAttempts, visibleRecommendations)
  const quizAttemptSummaries = quizAttempts.map((attempt, index) => {
    const attemptProfile = getAttemptProfile(attempt)
    const attemptProgress = getAttemptProgress(attempt)
    const attemptSkills = getProfileSkills(attemptProfile)
    const summary = getQuizSummary(attemptProfile, attemptProgress)
    const jobs = getAttemptJobs(attempt)
    const bestJob = getTopMatchedJobs(jobs, 1)[0]

    return {
      id: attempt.id || `attempt-${index + 1}`,
      label: attempt.isCurrent ? 'Current session' : `Quiz ${index + 1}`,
      completedAt: attempt.completed_at || 'Saved attempt',
      source: attempt.isCurrent ? 'Active browser session' : 'Saved local history',
      skills: attemptSkills.length,
      answered: summary.answered,
      estimated: summary.estimated,
      role: getWorkTypeLabel(
        summary.detectedDomain ||
          summary.detectedRole ||
          attemptProfile.detected_domain ||
          attemptProfile.target_role ||
          attemptProfile.top_category ||
          attemptProfile.category,
      ),
      confidence: summary.confidence,
      bestJob,
      jobs: jobs.length,
    }
  })
  const totalQuizAnswers = quizAttemptSummaries.reduce((total, attempt) => total + attempt.answered, 0)
  const totalEstimatedQuizAnswers = quizAttemptSummaries.reduce(
    (total, attempt) => total + Math.max(attempt.estimated, attempt.answered),
    0,
  )
  const profilesWithSkills = quizAttemptSummaries.filter((attempt) => attempt.skills > 0).length
  const quizProfiles = quizAttempts.map(getAttemptProfile).filter((attemptProfile) =>
    Object.keys(attemptProfile).length,
  )
  const quizProgressRows = quizAttempts.map(getAttemptProgress)
  const workTypeCoverage = countWorkTypeSignals([
    ...quizAttemptSummaries.map((attempt) => attempt.role),
    ...quizProgressRows.map((progress) => progress?.detected_role),
    ...quizProgressRows.map((progress) => progress?.detected_domain),
    ...quizProfiles.map((attemptProfile) =>
      attemptProfile.detected_domain ||
      attemptProfile.target_role ||
        attemptProfile.detected_role ||
        attemptProfile.top_category ||
        attemptProfile.category,
    ),
  ])
  const workTypeNames = workTypeCoverage.map((item) => item.workType)
  const quizDomains = uniqueItems([
    ...quizProgressRows.map((progress) => progress?.detected_domain),
    ...quizProfiles.map((attemptProfile) => attemptProfile.detected_domain || attemptProfile.domain),
  ])
  const quizConfidenceValues = quizAttemptSummaries
    .map((attempt) => Number(attempt.confidence))
    .filter((value) => Number.isFinite(value))
  const aggregateConfidence = quizConfidenceValues.length
    ? Math.round(quizConfidenceValues.reduce((total, value) => total + value, 0) / quizConfidenceValues.length)
    : currentQuizSummary.confidence
  const profileSkills = uniqueItems([
    ...currentProfileSkills,
    ...quizProfiles.flatMap(getProfileSkills),
  ])
  const firstProfileValue = (field) =>
    quizProfiles.map((attemptProfile) => attemptProfile?.[field]).find(Boolean) || profile?.[field]
  const aggregateEvidence = {
    experience_years: quizProfiles
      .map((attemptProfile) => attemptProfile?.evidence?.experience_years ?? attemptProfile?.experience_years)
      .find((value) => value !== null && value !== undefined),
    has_projects: quizProfiles.some((attemptProfile) =>
      attemptProfile?.evidence?.has_projects || attemptProfile?.has_projects,
    ),
    portfolio_url: quizProfiles
      .map((attemptProfile) => attemptProfile?.evidence?.portfolio_url || attemptProfile?.portfolio_url)
      .find(Boolean),
  }
  const aggregateProfile = {
    ...profile,
    detected_skills: profileSkills,
    skill_ids: profileSkills,
    skills: profileSkills,
    target_role: workTypeNames[0] || profile?.target_role,
    role_count: workTypeNames.length,
    experience_level: firstProfileValue('experience_level') || firstProfileValue('experience'),
    experience: firstProfileValue('experience'),
    location: firstProfileValue('location'),
    evidence: aggregateEvidence,
    question_count: totalQuizAnswers || currentQuizSummary.answered,
    confidence: aggregateConfidence,
    detected_domain: quizDomains[0] || currentQuizSummary.detectedDomain,
  }
  const profileFillItems = getProfileFillItems(aggregateProfile, profileSkills)
  const filledProfileFields = profileFillItems.filter((item) => item.score >= 100).length
  const quizSummary = {
    ...currentQuizSummary,
    answered: totalQuizAnswers || currentQuizSummary.answered,
    estimated: totalEstimatedQuizAnswers || currentQuizSummary.estimated,
    percent: totalEstimatedQuizAnswers
      ? Math.min(100, Math.round((totalQuizAnswers / totalEstimatedQuizAnswers) * 100))
      : currentQuizSummary.percent,
    confidence: aggregateConfidence,
    detectedDomain: quizDomains.length > 1
      ? `${quizDomains.length} domains`
      : quizDomains[0] || currentQuizSummary.detectedDomain,
    detectedRole: workTypeNames.length > 1
      ? `${workTypeNames.length} work types`
      : workTypeNames[0] || currentQuizSummary.detectedRole,
  }
  const aggregateJobCount = uniqueItems(aggregateRecommendations.map(getJobTitle)).length
  const averageMatch = getAverageMatch(aggregateRecommendations)
  const topMissingSkills = uniqueItems(aggregateRecommendations.flatMap(getMissingSkills)).slice(0, 6)
  const derivedGaps = getDerivedGaps(topMissingSkills)
  const gaps = analysis?.gaps?.length ? analysis.gaps : derivedGaps
  const aiResourceRows = analysis?.resources?.length ? flattenResourceGroups(analysis.resources) : []
  const aiResources = aiResourceRows.map(normalizeResource)
  const resources = hasManagedResourceStore ? managedResources : aiResources
  const gapStatus = analysis?.gaps?.length ? 'AI ready' : derivedGaps.length ? 'Stored data' : 'Pending'
  const learningStatus = hasManagedResourceStore
    ? managedResources.length
      ? 'Stored data'
      : 'Needs resources'
    : aiResourceRows.length
      ? 'AI ready'
      : profileSkills.length || quizAttempts.length
        ? 'Awaiting AI'
        : 'Needs profile'
  const resumeStatus = resumeCoaching
    ? 'AI ready'
    : profileSkills.length || quizAttempts.length
      ? 'Awaiting AI'
      : 'Needs profile'
  const topMatchedJobs = getTopMatchedJobs(aggregateRecommendations)
  const promptRoleOptions = uniqueItems([
    DEFAULT_QUIZ_ROLE,
    ...getWorkTypeOptionLabels(),
    ...workTypeNames,
    ...quizPrompts.map((prompt) => normalizeRole(prompt.role)),
    ...aggregateRecommendations.map(getJobWorkType),
    getWorkTypeLabel(profile?.target_role, ''),
    getWorkTypeLabel(profile?.detected_role, ''),
    getWorkTypeLabel(profile?.top_category, ''),
  ]).sort((left, right) => {
    if (left === DEFAULT_QUIZ_ROLE) {
      return -1
    }

    if (right === DEFAULT_QUIZ_ROLE) {
      return 1
    }

    return left.localeCompare(right)
  })
  const filteredQuizPrompts = selectedPromptRole === ALL_QUIZ_ROLES
    ? quizPrompts
    : quizPrompts.filter((prompt) => normalizeRole(prompt.role) === selectedPromptRole)
  const promptCoverageByRole = promptRoleOptions.map((role) => ({
    role,
    count: quizPrompts.filter((prompt) => normalizeRole(prompt.role) === role).length,
  }))
  const newPromptOptions = parsePromptOptions(newPromptDraft.optionsText)
  const canAddPrompt = Boolean(newPromptDraft.stem.trim()) && newPromptOptions.length >= 2

  const filteredJobs = visibleRecommendations.filter((job) =>
    `${getJobTitle(job)} ${getJobCompany(job)} ${getJobCategory(job)} ${getJobWorkType(job)}`
      .toLowerCase()
      .includes(jobSearch.toLowerCase()),
  )
  const canBuildRecommendations = profileSkills.length > 0 || quizAttempts.length > 0
  const aggregateProfilePayload = JSON.stringify(aggregateProfile)
  const aggregateRecommendationsPayload = JSON.stringify(aggregateRecommendations)
  const adminAiRequestKey = [
    aggregateProfilePayload,
    aggregateRecommendationsPayload,
  ].join('::')
  const canRequestAdminAi = hasStoredRecommendations && (profileSkills.length > 0 || quizAttempts.length > 0)

  useEffect(() => {
    if (storedRecommendations.length || !canBuildRecommendations) {
      return
    }

    let cancelled = false
    const profilePayload = JSON.parse(aggregateProfilePayload)

    fetchRecommendations(profilePayload)
      .then((result) => {
        if (cancelled) {
          return
        }

        setStoredRecommendations(result.jobs)
        persistRecommendationSession(result.profile, result.jobs, result.rawRecs)
      })
      .catch(() => {
        // Fallback recommendations remain visible until the backend can score the stored profile.
      })

    return () => {
      cancelled = true
    }
  }, [adminAiRequestKey, aggregateProfilePayload, canBuildRecommendations, storedRecommendations.length])

  useEffect(() => {
    if (!canRequestAdminAi || analysis?.gaps?.length || analysis?.resources?.length) {
      return
    }

    let cancelled = false
    const profilePayload = JSON.parse(aggregateProfilePayload)
    const recommendationsPayload = JSON.parse(aggregateRecommendationsPayload)

    fetchAnalysis(null, profilePayload, recommendationsPayload)
      .then((payload) => {
        if (cancelled) {
          return
        }

        setAnalysis(payload)
        persistAnalysis(payload)
      })
      .catch(() => {
        // Derived gaps/resources keep admin useful when the AI analysis endpoint is unavailable.
      })

    return () => {
      cancelled = true
    }
  }, [
    adminAiRequestKey,
    aggregateProfilePayload,
    aggregateRecommendationsPayload,
    canRequestAdminAi,
    analysis?.gaps?.length,
    analysis?.resources?.length,
  ])

  useEffect(() => {
    if (!canRequestAdminAi || resumeCoaching) {
      return
    }

    let cancelled = false
    const profilePayload = JSON.parse(aggregateProfilePayload)
    const recommendationsPayload = JSON.parse(aggregateRecommendationsPayload)

    fetchResumeTips(null, profilePayload, recommendationsPayload)
      .then((payload) => {
        if (cancelled) {
          return
        }

        setResumeCoaching(payload)
        persistCachedResumeTips(payload)
      })
      .catch(() => {
        // Stored profile guidance remains visible until AI coaching is available.
      })

    return () => {
      cancelled = true
    }
  }, [
    adminAiRequestKey,
    aggregateProfilePayload,
    aggregateRecommendationsPayload,
    canRequestAdminAi,
    resumeCoaching,
  ])

  useEffect(() => {
    let cancelled = false

    fetchTelegramJobs({ limit: 20 })
      .then((payload) => {
        if (cancelled) {
          return
        }

        setTelegramState({
          error: '',
          isLoading: false,
          jobs: payload.jobs || [],
          updatedAt: payload.updated_at || '',
        })
      })
      .catch((err) => {
        if (cancelled) {
          return
        }

        setTelegramState({
          error: err.message || 'Could not load Telegram jobs.',
          isLoading: false,
          jobs: [],
          updatedAt: '',
        })
      })

    return () => {
      cancelled = true
    }
  }, [])

  const metrics = [
    {
      label: 'Profile',
      value: workTypeNames.length || quizAttempts.length
        ? `${workTypeNames.length || 1} work types`
        : 'Not started',
      status: profileSkills.length || quizAttempts.length ? 'Ready' : 'Pending',
    },
    {
      label: 'Matches',
      value: `${aggregateJobCount || visibleRecommendations.length} recommendations`,
      status: hasStoredRecommendations ? 'Stored data' : canBuildRecommendations ? 'Loading' : 'Needs profile',
    },
    {
      label: 'Coverage gaps',
      value: gaps.length ? `${gaps.length} active` : 'Awaiting AI',
      status: gapStatus,
    },
    {
      label: 'Learning',
      value: `${resources.length} resources`,
      status: learningStatus,
    },
    {
      label: 'Resume',
      value: `${getResumeSectionCount(resumeCoaching)} sections`,
      status: resumeStatus,
    },
    {
      label: 'Telegram',
      value: telegramState.isLoading ? 'Loading' : `${telegramState.jobs.length} jobs`,
      status: telegramState.error ? 'Review' : 'Live',
    },
  ]

  const featureMap = [
    {
      title: 'Quiz and manual profile',
      route: '/quiz, /manual',
      status: profileSkills.length || quizAttempts.length ? 'Ready' : 'Pending',
      detail: 'Aggregates every main quiz attempt, work-type signal, and answer row into the admin profile.',
    },
    {
      title: 'Job recommendations',
      route: '/results',
      status: hasStoredRecommendations ? 'Stored data' : canBuildRecommendations ? 'Loading' : 'Needs profile',
      detail: hasStoredRecommendations
        ? 'Rolls up stored AI recommendations and match scores by the broad work type selected in the main quiz.'
        : 'Uses the stored profile to request AI recommendations before falling back to demo data.',
    },
    {
      title: 'Recommendation gap analysis',
      route: '/results/gap/:jobId',
      status: gapStatus,
      detail: analysis?.gaps?.length
        ? 'Uses cached AI analysis for recommendation coverage gaps.'
        : 'Derives coverage gaps from stored recommendation data while AI analysis loads.',
    },
    {
      title: 'Learning resources',
      route: '/results/resources',
      status: learningStatus,
      detail: analysis?.resources?.length
        ? 'Uses AI resource recommendations from the learner-facing study map.'
        : 'Uses stored recommendation gaps to choose the closest resources before AI resources are available.',
    },
    {
      title: 'Resume coaching and builder',
      route: '/results/resume, /resume-builder',
      status: resumeStatus,
      detail: resumeCoaching
        ? 'Mirrors AI resume tips, upload readiness, and generated resume coverage.'
        : 'Uses the stored profile and recommendations while AI resume coaching loads.',
    },
    {
      title: 'Telegram jobs',
      route: '/telegram-jobs',
      status: telegramState.isLoading ? 'Loading' : telegramState.error ? 'Review' : 'Live',
      detail: 'Monitors the same current-job feed that can be ranked against the active profile.',
    },
  ]

  const completionItems = [
    {
      label: 'Quiz answers',
      value: `${quizSummary.answered}/${quizSummary.estimated}`,
      score: quizSummary.percent,
    },
    {
      label: 'Profile fields',
      value: `${filledProfileFields}/${profileFillItems.length}`,
      score: Math.round((filledProfileFields / profileFillItems.length) * 100),
    },
    {
      label: 'AI recommendations',
      value: `${aggregateJobCount || visibleRecommendations.length} items`,
      score: Math.min(100, Math.round(((aggregateJobCount || visibleRecommendations.length) / 10) * 100)),
    },
    {
      label: 'Gap analysis',
      value: gaps.length ? `${gaps.length} gaps` : 'Pending',
      score: gaps.length ? 100 : 0,
    },
    {
      label: 'Learning resources',
      value: `${resources.length} resources`,
      score: Math.min(100, Math.round((resources.length / 6) * 100)),
    },
  ]
  const overviewCompletion = Math.round(
    completionItems.reduce((total, item) => total + item.score, 0) / completionItems.length,
  )
  const readyFeatureCount = featureMap.filter(
    (feature) => !['Pending', 'Review', 'Loading'].includes(feature.status),
  ).length
  const mostFilledItem = [...completionItems].sort((left, right) => right.score - left.score)[0]
  const topGap = gaps[0]
  const analysisNotes = [
    {
      label: 'Best all-quiz match',
      value: topMatchedJobs[0] ? getJobTitle(topMatchedJobs[0]) : 'No match yet',
      detail: topMatchedJobs[0] ? `${getJobMatch(topMatchedJobs[0]) ?? '--'}% match` : 'Run profile scoring',
    },
    {
      label: 'Most complete',
      value: mostFilledItem?.label || 'Pending',
      detail: mostFilledItem ? `${mostFilledItem.value} / ${mostFilledItem.score}%` : 'No coverage yet',
    },
    {
      label: 'Main gap',
      value: topGap ? getGapName(topGap) : formatLabel(topMissingSkills[0], 'No repeated gap'),
      detail: topGap ? `${getGapPriority(topGap) ?? '--'} priority` : 'Based on all quiz matches',
    },
    {
      label: 'Quiz confidence',
      value: formatPercent(quizSummary.confidence),
      detail: formatLabel(quizSummary.detectedRole || quizSummary.difficulty),
    },
  ]
  const startPromptEdit = (prompt) => {
    setEditingPromptId(prompt.id)
    setPromptDraft({
      role: normalizeRole(prompt.role),
      stem: prompt.stem,
      optionsText: prompt.options.join('\n'),
    })
  }
  const cancelPromptEdit = () => {
    setEditingPromptId('')
    setPromptDraft({ ...EMPTY_PROMPT_DRAFT })
  }
  const addPrompt = (event) => {
    event.preventDefault()

    const role = normalizeRole(newPromptDraft.role)
    const stem = newPromptDraft.stem.trim()
    const options = parsePromptOptions(newPromptDraft.optionsText)

    if (!stem || options.length < 2) {
      return
    }

    const nextPrompt = {
      id: createPromptId(role),
      role,
      stem,
      options,
      status: 'Live',
      updated: 'Added locally',
    }

    setQuizPrompts((prompts) => {
      const nextPrompts = [nextPrompt, ...prompts]
      saveAdminQuizPrompts(nextPrompts)
      return nextPrompts
    })
    setSelectedPromptRole(role)
    setNewPromptDraft({ ...EMPTY_PROMPT_DRAFT, role })
  }
  const updatePrompt = () => {
    const role = normalizeRole(promptDraft.role)
    const normalizedOptions = parsePromptOptions(promptDraft.optionsText)

    setQuizPrompts((prompts) => {
      const nextPrompts = prompts.map((prompt) =>
        prompt.id === editingPromptId
          ? {
              ...prompt,
              role,
              stem: promptDraft.stem.trim() || prompt.stem,
              options: normalizedOptions.length ? normalizedOptions : prompt.options,
              updated: 'Saved locally',
            }
          : prompt,
      )

      saveAdminQuizPrompts(nextPrompts)
      return nextPrompts
    })
    setSelectedPromptRole(role)
    cancelPromptEdit()
  }
  const deletePrompt = (promptId) => {
    setQuizPrompts((prompts) => {
      const nextPrompts = prompts.filter((prompt) => prompt.id !== promptId)
      saveAdminQuizPrompts(nextPrompts)
      return nextPrompts
    })
    if (editingPromptId === promptId) {
      cancelPromptEdit()
    }
  }
  const startResourceEdit = (resource) => {
    setEditingResourceId(resource.id)
    setResourceDraft({
      skill: resource.skill || '',
      title: resource.title || '',
      platform: resource.platform || '',
      level: resource.level || '',
      hours: resource.hours || '',
      url: resource.url || '',
    })
  }
  const cancelResourceEdit = () => {
    setEditingResourceId('')
    setResourceDraft({ ...EMPTY_RESOURCE_DRAFT })
  }
  const saveResource = (event) => {
    event.preventDefault()

    const title = resourceDraft.title.trim()
    if (!title) {
      return
    }

    const resource = normalizeResource({
      id: editingResourceId || createResourceId(title),
      ...resourceDraft,
      title,
      updated: editingResourceId ? 'Updated locally' : 'Added locally',
    }, resources.length)

    const nextResources = editingResourceId
      ? resources.map((item) => (item.id === editingResourceId ? resource : item))
      : [resource, ...resources]

    setManagedResources(nextResources)
    saveAdminResources(nextResources)
    setHasManagedResourceStore(true)
    cancelResourceEdit()
  }
  const deleteResource = (resourceId) => {
    const nextResources = resources.filter((resource) => resource.id !== resourceId)

    setManagedResources(nextResources)
    saveAdminResources(nextResources)
    setHasManagedResourceStore(true)
    if (editingResourceId === resourceId) {
      cancelResourceEdit()
    }
  }

  return (
    <section className="admin-page">
      <div className="admin-header">
        <div>
          <p className="eyebrow">Admin command center</p>
          <h1>Feature operations for the active career workflow.</h1>
          <p>
            Admin now rolls up all main quiz attempts into the same flow: profile,
            matches, gaps, learning, resume, and current jobs. Use the direct path <code>/admin</code>.
          </p>
        </div>

        <div className="admin-route-note" aria-label="Admin access mode">
          <span>Access</span>
          <strong>/admin</strong>
          <small>Hidden from primary navigation</small>
        </div>
      </div>

      <div className="admin-tabs" role="tablist" aria-label="Admin sections">
        {adminTabs.map((tab) => (
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === tab}
            className={activeTab === tab ? 'is-active' : ''}
            key={tab}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === 'Overview' && (
        <div className="admin-overview">
          <div className="admin-metrics">
            {metrics.map((metric) => (
              <article className="admin-metric-card" key={metric.label}>
                <span className="metric-label">{metric.label}</span>
                <strong>{metric.value}</strong>
                <span className={statusClass(metric.status)}>{metric.status}</span>
              </article>
            ))}
          </div>

          <div className="admin-feature-grid">
            {featureMap.map((feature) => (
              <article className="admin-feature-card" key={feature.title}>
                <div className="admin-card-kicker">
                  <span>{feature.route}</span>
                  <strong className={statusClass(feature.status)}>{feature.status}</strong>
                </div>
                <h2>{feature.title}</h2>
                <p>{feature.detail}</p>
              </article>
            ))}
          </div>

          <div className="admin-grid">
            <section className="admin-panel">
              <div className="admin-panel-heading">
                <span>Workflow coverage</span>
                <strong>{overviewCompletion}% complete</strong>
              </div>

              <div className="pipeline-list">
                <div>
                  <span>Profile intake</span>
                  <strong>{quizAttempts.length ? `${quizAttempts.length} quizzes / ${workTypeNames.length || 1} work types` : 'Pending'}</strong>
                </div>
                <div>
                  <span>Matching engine</span>
                  <strong>{aggregateJobCount || visibleRecommendations.length} recommendations across work types</strong>
                </div>
                <div>
                  <span>Analysis layer</span>
                  <strong>{gaps.length ? 'Generated' : 'Pending'}</strong>
                </div>
                <div>
                  <span>Resume support</span>
                  <strong>{getResumeSectionCount(resumeCoaching)} guidance sections</strong>
                </div>
              </div>
            </section>

            <section className="admin-panel">
              <div className="admin-panel-heading">
                <span>Feature readiness</span>
                <strong>{readyFeatureCount} / {featureMap.length} live</strong>
              </div>

              <div className="pipeline-list">
                {featureMap.map((feature) => (
                  <div key={feature.title}>
                    <span>{feature.title}</span>
                    <strong className={statusClass(feature.status)}>{feature.status}</strong>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </div>
      )}

      {activeTab === 'Profile' && (
        <section className="admin-panel admin-profile-page">
          <div className="admin-panel-heading">
            <span>Profile workspace</span>
            <strong>{activeProfilePage}</strong>
          </div>

          <div className="admin-subtabs" role="tablist" aria-label="Profile admin pages">
            {profilePages.map((page) => (
              <button
                type="button"
                role="tab"
                aria-selected={activeProfilePage === page}
                className={activeProfilePage === page ? 'is-active' : ''}
                key={page}
                onClick={() => setActiveProfilePage(page)}
              >
                {page}
              </button>
            ))}
          </div>

          {activeProfilePage === 'Quiz Intake' && (
            <div className="admin-profile-dashboard">
              <div className="admin-stat-grid">
                <article>
                  <span>Taken quizzes</span>
                  <strong>{quizAttemptSummaries.length}</strong>
                  <small>{quizHistory.length} saved history</small>
                </article>
                <article>
                  <span>Answered questions</span>
                  <strong>{totalQuizAnswers}</strong>
                  <small>Across cached quizzes</small>
                </article>
                <article>
                  <span>Quiz profiles</span>
                  <strong>{profilesWithSkills}</strong>
                  <small>{profileSkills.length} supporting signals</small>
                </article>
                <article>
                  <span>Work types</span>
                  <strong>{workTypeNames.length || 0}</strong>
                  <small>{recommendationSource}</small>
                </article>
              </div>

              {workTypeCoverage.length > 0 && (
                <div className="admin-analysis-list" aria-label="Main quiz work type coverage">
                  {workTypeCoverage.map((item) => (
                    <article key={item.workType}>
                      <span>Main quiz work type</span>
                      <strong>{item.workType}</strong>
                      <small>{item.count} quiz signal{item.count === 1 ? '' : 's'}</small>
                    </article>
                  ))}
                </div>
              )}

              {quizAttemptSummaries.length ? (
                <div className="admin-table" role="table" aria-label="Profile intake for all taken quizzes">
                  <div className="admin-table-row admin-table-head" role="row">
                    <span>Quiz</span>
                    <span>Work type</span>
                    <span>Answers</span>
                    <span>Signals</span>
                    <span>Best match</span>
                  </div>

                  {quizAttemptSummaries.map((attempt) => (
                    <div className="admin-table-row" role="row" key={attempt.id}>
                      <span>
                        <strong>{attempt.label}</strong>
                        <small>{attempt.source} / {attempt.completedAt}</small>
                      </span>
                      <span>{formatLabel(attempt.role)}</span>
                      <span>{attempt.answered} / {attempt.estimated}</span>
                      <span>{attempt.skills}</span>
                      <span>{attempt.bestJob ? `${getJobTitle(attempt.bestJob)} (${getJobMatch(attempt.bestJob)}%)` : `${attempt.jobs} matches`}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="admin-empty">
                  No quiz attempts are stored yet. Completed quizzes will appear here for admin review.
                </div>
              )}
            </div>
          )}

          {activeProfilePage === 'Match Graph' && (
            <div className="admin-profile-dashboard">
              <div className="admin-panel-heading">
                <span>Most matched work types across quizzes</span>
                <strong>{matchGraphRows.length} work types</strong>
              </div>

              <div className="admin-match-graph" aria-label="Most matched work types graph">
                {matchGraphRows.map((row) => (
                  <article className="admin-graph-row" key={row.title}>
                    <div className="admin-graph-copy">
                      <strong>{row.title}</strong>
                      <span>{row.category} / seen {row.count}x / peak {row.maxScore}%</span>
                    </div>
                    <div className="admin-graph-track" aria-label={`${row.title} average match ${row.averageScore}%`}>
                      <span style={{ width: `${row.averageScore}%` }}></span>
                    </div>
                    <strong className="admin-graph-score">{row.averageScore}%</strong>
                  </article>
                ))}
              </div>

              {!matchGraphRows.length && (
                <div className="admin-empty">
                  No work-type match scores are available yet. Run quizzes or recommendations to populate this graph.
                </div>
              )}
            </div>
          )}

          {activeProfilePage === 'Completion Detail' && (
            <div className="admin-profile-dashboard">
              <div className="admin-dashboard-grid">
                <section className="admin-dashboard-card">
                  <div className="admin-panel-heading">
                    <span>Most filled quiz or recommendations</span>
                    <strong>{mostFilledItem ? `${mostFilledItem.score}%` : 'Pending'}</strong>
                  </div>

                  <div className="admin-progress-list">
                    {completionItems.map((item) => (
                      <div className="admin-progress-row" key={item.label}>
                        <div>
                          <span>{item.label}</span>
                          <strong>{item.value}</strong>
                        </div>
                        <div className="admin-progress-meter" aria-label={`${item.label} ${item.score}%`}>
                          <span style={{ width: `${item.score}%` }}></span>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>

                <section className="admin-dashboard-card">
                  <div className="admin-panel-heading">
                    <span>Profile field detail</span>
                    <strong>{filledProfileFields} / {profileFillItems.length} filled</strong>
                  </div>

                  <div className="admin-progress-list">
                    {profileFillItems.map((item) => (
                      <div className="admin-progress-row" key={item.label}>
                        <div>
                          <span>{item.label}</span>
                          <strong>{item.value}</strong>
                        </div>
                        <div className="admin-progress-meter" aria-label={`${item.label} ${item.score}%`}>
                          <span style={{ width: `${item.score}%` }}></span>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              </div>

              <div className="admin-analysis-list">
                {analysisNotes.map((item) => (
                  <article key={item.label}>
                    <span>{item.label}</span>
                    <strong>{item.value}</strong>
                    <small>{item.detail}</small>
                  </article>
                ))}
              </div>
            </div>
          )}

          {activeProfilePage === 'Quiz Prompts' && (
            <div className="admin-profile-dashboard">
              <div className="admin-panel-heading">
                <span>Quiz prompt coverage</span>
                <strong>{filteredQuizPrompts.length} shown</strong>
              </div>

              <div className="admin-role-quiz-controls">
                <label>
                  Work type filter
                  <select
                    value={selectedPromptRole}
                    onChange={(event) => setSelectedPromptRole(event.target.value)}
                  >
                    <option value={ALL_QUIZ_ROLES}>{ALL_QUIZ_ROLES}</option>
                    {promptRoleOptions.map((role) => (
                      <option value={role} key={role}>{role}</option>
                    ))}
                  </select>
                </label>

                <div className="admin-role-counts" aria-label="Quiz prompt coverage by work type">
                  {promptCoverageByRole.map((item) => (
                    <span className="chip chip-blue" key={item.role}>
                      {item.role} {item.count}
                    </span>
                  ))}
                </div>
              </div>

              <form className="admin-role-quiz-form" onSubmit={addPrompt}>
                <div className="admin-role-quiz-form-grid">
                  <label>
                    Work type
                    <select
                      value={newPromptDraft.role}
                      onChange={(event) => setNewPromptDraft((draft) => ({
                        ...draft,
                        role: event.target.value,
                      }))}
                    >
                      {promptRoleOptions.map((role) => (
                        <option value={role} key={role}>{role}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Quiz question
                    <textarea
                      value={newPromptDraft.stem}
                      onChange={(event) => setNewPromptDraft((draft) => ({
                        ...draft,
                        stem: event.target.value,
                      }))}
                    />
                  </label>
                  <label>
                    Answer options
                    <textarea
                      value={newPromptDraft.optionsText}
                      placeholder="One option per line"
                      onChange={(event) => setNewPromptDraft((draft) => ({
                        ...draft,
                        optionsText: event.target.value,
                      }))}
                    />
                  </label>
                </div>

                <div className="admin-role-quiz-actions">
                  <button className="button button-primary" type="submit" disabled={!canAddPrompt}>
                    Add quiz question
                  </button>
                  <small>{newPromptOptions.length} options ready</small>
                </div>
              </form>

              <div className="question-review-list">
                {filteredQuizPrompts.map((prompt) => {
                  const isEditing = editingPromptId === prompt.id

                  return (
                    <article className="question-review-card" key={prompt.id}>
                      {isEditing ? (
                        <div className="admin-prompt-editor">
                          <label>
                            Work type
                            <select
                              value={promptDraft.role}
                              onChange={(event) => setPromptDraft((draft) => ({
                                ...draft,
                                role: event.target.value,
                              }))}
                            >
                              {promptRoleOptions.map((role) => (
                                <option value={role} key={role}>{role}</option>
                              ))}
                            </select>
                          </label>
                          <label>
                            Prompt
                            <textarea
                              value={promptDraft.stem}
                              onChange={(event) => setPromptDraft((draft) => ({
                                ...draft,
                                stem: event.target.value,
                              }))}
                            />
                          </label>
                          <label>
                            Options
                            <textarea
                              value={promptDraft.optionsText}
                              onChange={(event) => setPromptDraft((draft) => ({
                                ...draft,
                                optionsText: event.target.value,
                              }))}
                            />
                          </label>
                        </div>
                      ) : (
                        <div>
                          <span className="chip chip-blue">{normalizeRole(prompt.role)}</span>
                          <h2>{prompt.stem}</h2>
                          <p>{prompt.options.join(' / ')}</p>
                          <small className="admin-small-note">{prompt.updated}</small>
                        </div>
                      )}

                      <div className="question-review-actions">
                        {isEditing ? (
                          <>
                            <button className="button button-primary" type="button" onClick={updatePrompt}>
                              Update
                            </button>
                            <button className="button button-ghost" type="button" onClick={cancelPromptEdit}>
                              Cancel
                            </button>
                          </>
                        ) : (
                          <>
                            <button className="button button-ghost" type="button" onClick={() => startPromptEdit(prompt)}>
                              Edit
                            </button>
                            <button className="button button-ghost" type="button" onClick={() => deletePrompt(prompt.id)}>
                              Delete
                            </button>
                          </>
                        )}
                      </div>
                    </article>
                  )
                })}
              </div>

              {!filteredQuizPrompts.length && (
                <div className="admin-empty">
                  No quiz questions are saved for {selectedPromptRole === ALL_QUIZ_ROLES ? 'any work type' : selectedPromptRole}.
                </div>
              )}
            </div>
          )}
        </section>
      )}

      {activeTab === 'Matching' && (
        <section className="admin-panel">
          <div className="admin-panel-heading">
            <span>Recommendation engine</span>
            <strong>{averageMatch === null ? recommendationSource : `${averageMatch}% avg match`}</strong>
          </div>

          <div className="admin-toolbar">
            <label>
              Search recommendations
              <input
                type="search"
                value={jobSearch}
                placeholder="Recommendation, company, work type"
                onChange={(event) => setJobSearch(event.target.value)}
              />
            </label>

            <label>
              Source
              <input value={recommendationSource} readOnly />
            </label>
          </div>

          <div className="admin-table" role="table" aria-label="Recommendation alignment">
            <div className="admin-table-row admin-table-head" role="row">
              <span>Recommendation</span>
              <span>Work type</span>
              <span>Match</span>
              <span>Coverage gaps</span>
              <span>Signals</span>
            </div>

            {filteredJobs.map((job) => {
              const match = getJobMatch(job)
              const missingSkills = getMissingSkills(job)
              const matchedSkills = getMatchedSkills(job)

              return (
                <div className="admin-table-row" role="row" key={job.id || job.job_id || getJobTitle(job)}>
                  <span>
                    <strong>{getJobTitle(job)}</strong>
                    <small>{getJobCompany(job)}</small>
                  </span>
                  <span>{getJobWorkType(job)}</span>
                  <span>
                    {match === null ? (
                      <span className={statusClass('Pending')}>Pending</span>
                    ) : (
                      <span className={`match-badge ${getMatchClass(match)}`}>{match}%</span>
                    )}
                  </span>
                  <span>{missingSkills.length ? `${missingSkills.length} gaps` : 'None'}</span>
                  <span>{matchedSkills.slice(0, 2).map(formatLabel).join(', ') || 'Scored factors'}</span>
                </div>
              )
            })}
          </div>

          {!filteredJobs.length && (
            <div className="admin-empty">
              No real recommendations are stored yet. Complete the quiz or manual profile so AI recommendations can be generated.
            </div>
          )}
        </section>
      )}

      {activeTab === 'Learning' && (
        <div className="admin-section-stack">
          <section className="admin-panel">
            <div className="admin-panel-heading">
              <span>Recommendation coverage gaps</span>
              <strong>{gaps.length ? `${gaps.length} active gaps / ${gapStatus}` : 'Awaiting AI'}</strong>
            </div>

            {gaps.length ? (
              <div className="question-review-list">
                {gaps.map((gap) => {
                  const priority = getGapPriority(gap)

                  return (
                    <article className="question-review-card" key={gap.skill_id || getGapName(gap)}>
                      <div>
                        <span className="chip chip-coral">{gap.priority_label || 'Gap'}</span>
                        <h2>{getGapName(gap)}</h2>
                        <p>
                          Current {gap.current ?? 'n/a'} / required {gap.required ?? 'n/a'}
                        </p>
                      </div>

                      <div className="question-review-actions">
                        <span className={statusClass('Ready')}>
                          {priority === null ? 'Ready' : `${priority}%`}
                        </span>
                      </div>
                    </article>
                  )
                })}
              </div>
            ) : (
              <div className="admin-empty">
                No active gap analysis is cached. Recommendations will populate this after the
                profile has been scored.
              </div>
            )}
          </section>

          <section className="admin-panel">
            <div className="admin-panel-heading">
              <span>Learning resources</span>
              <strong>{learningStatus}</strong>
            </div>

            <form className="admin-role-quiz-form" onSubmit={saveResource}>
              <div className="admin-role-quiz-form-grid">
                <label>
                  Coverage area
                  <input
                    value={resourceDraft.skill}
                    onChange={(event) => setResourceDraft((draft) => ({
                      ...draft,
                      skill: event.target.value,
                    }))}
                  />
                </label>
                <label>
                  Resource title
                  <input
                    value={resourceDraft.title}
                    onChange={(event) => setResourceDraft((draft) => ({
                      ...draft,
                      title: event.target.value,
                    }))}
                  />
                </label>
                <label>
                  Platform
                  <input
                    value={resourceDraft.platform}
                    onChange={(event) => setResourceDraft((draft) => ({
                      ...draft,
                      platform: event.target.value,
                    }))}
                  />
                </label>
                <label>
                  Level
                  <input
                    value={resourceDraft.level}
                    onChange={(event) => setResourceDraft((draft) => ({
                      ...draft,
                      level: event.target.value,
                    }))}
                  />
                </label>
                <label>
                  Hours
                  <input
                    value={resourceDraft.hours}
                    onChange={(event) => setResourceDraft((draft) => ({
                      ...draft,
                      hours: event.target.value,
                    }))}
                  />
                </label>
                <label>
                  URL
                  <input
                    value={resourceDraft.url}
                    onChange={(event) => setResourceDraft((draft) => ({
                      ...draft,
                      url: event.target.value,
                    }))}
                  />
                </label>
              </div>

              <div className="admin-role-quiz-actions">
                <button className="button button-primary" type="submit" disabled={!resourceDraft.title.trim()}>
                  {editingResourceId ? 'Update resource' : 'Add resource'}
                </button>
                {editingResourceId && (
                  <button className="button button-ghost" type="button" onClick={cancelResourceEdit}>
                    Cancel
                  </button>
                )}
                <small>{resources.length} resources listed</small>
              </div>
            </form>

            {resources.length ? (
              <div className="question-review-list">
                {resources.map((resource) => (
                  <article className="question-review-card" key={resource.id}>
                    <div>
                      <span className="chip chip-blue">{resource.level || 'Resource'}</span>
                      <h2>{resource.title}</h2>
                      <p>
                        {formatLabel(resource.skill, 'General coverage')} / {resource.platform || 'AI resource'}
                      </p>
                      <small className="admin-small-note">
                        {resource.hours ? `${resource.hours} hours` : resource.recommendation_score ?? 'No duration'} / {resource.updated}
                      </small>
                    </div>

                    <div className="question-review-actions">
                      <button className="button button-ghost" type="button" onClick={() => startResourceEdit(resource)}>
                        Edit
                      </button>
                      <button className="button button-ghost" type="button" onClick={() => deleteResource(resource.id)}>
                        Delete
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="admin-empty">
                No learning resources are stored yet. AI-generated resources will appear here, or add one manually.
              </div>
            )}
          </section>
        </div>
      )}

      {activeTab === 'Resume' && (
        <section className="admin-panel">
          <div className="admin-panel-heading">
            <span>Resume workflow</span>
            <strong>{resumeStatus}</strong>
          </div>

          <div className="admin-feature-grid">
            <article className="admin-feature-card">
              <div className="admin-card-kicker">
                <span>/results/resume</span>
                <strong className={statusClass(resumeStatus)}>
                  {resumeStatus}
                </strong>
              </div>
              <h2>Resume tips</h2>
              <p>
                {resumeCoaching?.summary ||
                  'Uses profile, work-type, and gap context to produce recommendation-aware coaching.'}
              </p>
            </article>

            <article className="admin-feature-card">
              <div className="admin-card-kicker">
                <span>/resume/upload</span>
                <strong className={statusClass(profile ? 'Ready' : 'Pending')}>
                  {profile ? 'Ready' : 'Pending'}
                </strong>
              </div>
              <h2>Resume upload review</h2>
              <p>Uses the active profile and recommendations when a user uploads a resume.</p>
            </article>

            <article className="admin-feature-card">
              <div className="admin-card-kicker">
                <span>/resume-builder</span>
                <strong className={statusClass('Ready')}>Ready</strong>
              </div>
              <h2>Resume builder</h2>
              <p>Generates preview markup and exportable resume assets from structured form data.</p>
            </article>
          </div>

          <div className="admin-panel-divider"></div>

          {resumeCoaching?.tips?.length ? (
            <div className="tips-grid">
              {resumeCoaching.tips.map((section) => (
                <article className="tips-section" key={section.section}>
                  <div className="tips-section-title">
                    <span>{section.icon || 'AI'}</span>
                    <h2>{section.section}</h2>
                  </div>
                  <ul>
                    {(section.tips || []).slice(0, 3).map((tip) => (
                      <li key={tip}>{tip}</li>
                    ))}
                  </ul>
                </article>
              ))}
            </div>
          ) : (
            <div className="admin-empty">
              No AI resume coaching is stored yet. Admin will request it when a real profile and recommendations are available.
            </div>
          )}
        </section>
      )}

      {activeTab === 'Telegram' && (
        <section className="admin-panel">
          <div className="admin-panel-heading">
            <span>Current job feed</span>
            <strong>
              {telegramState.isLoading
                ? 'Loading'
                : telegramState.error
                  ? 'Needs review'
                  : `${telegramState.jobs.length} jobs`}
            </strong>
          </div>

          <div className="telegram-channel-list" aria-label="Tracked Telegram channels">
            {defaultChannels.map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>

          {telegramState.updatedAt && (
            <div className="admin-small-note">Last feed update: {telegramState.updatedAt}</div>
          )}

          {telegramState.error && <p className="form-error">{telegramState.error}</p>}

          <div className="admin-table" role="table" aria-label="Telegram feed alignment">
            <div className="admin-table-row admin-table-head" role="row">
              <span>Opening</span>
              <span>Channel</span>
              <span>Experience</span>
              <span>Signals</span>
              <span>Posted</span>
            </div>

            {telegramState.jobs.slice(0, 8).map((job) => (
              <div className="admin-table-row" role="row" key={job.job_id}>
                <span>
                  <strong>{job.job_title}</strong>
                  <small>{job.company || job.location || 'Current opening'}</small>
                </span>
                <span>{job.source_channel}</span>
                <span>{formatLabel(job.exp_level)}</span>
                <span>{(job.required_skill_names || []).slice(0, 3).map(formatLabel).join(', ') || 'Pending'}</span>
                <span>{job.posted_at || 'Recent'}</span>
              </div>
            ))}
          </div>

          {!telegramState.isLoading && !telegramState.error && telegramState.jobs.length === 0 && (
            <div className="admin-empty">No current Telegram jobs are available from the feed yet.</div>
          )}
        </section>
      )}
    </section>
  )
}

export default Admin
