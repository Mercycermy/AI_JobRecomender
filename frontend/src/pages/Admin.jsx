import { useEffect, useState } from 'react'
import {
  deleteAdminQuizQuestion,
  clearStoredAdminAccessKey,
  fetchAdminQuizAttempts,
  fetchAdminAnalytics,
  fetchAdminQuizQuestions,
  fetchAnalysis,
  fetchRecommendations,
  fetchResumeTips,
  fetchTelegramJobs,
  getStoredAdminAccessKey,
  loadStoredAnalysis,
  loadStoredProfile,
  loadStoredQuizHistory,
  loadStoredQuizProgress,
  loadStoredRecommendations,
  persistAnalysis,
  persistRecommendationSession,
  saveAdminQuizQuestion,
  setStoredAdminAccessKey,
  verifyAdminAccess,
} from '../api/recommend.js'
const adminTabs = ['Overview', 'Profile', 'Matching', 'Learning', 'Resume', 'Telegram']
const profilePages = ['Quiz Intake', 'Match Graph', 'Quiz Prompts']
const ADMIN_QUIZ_PROMPTS_STORAGE_KEY = 'adminQuizPrompts'
const ADMIN_RESOURCES_STORAGE_KEY = 'adminLearningResources'
const ADMIN_RESUME_STORAGE_KEY = 'adminResumePlaybook'
const ALL_ROLE_FILTERS = 'All roles'
const ADMIN_LOGIN_TITLE = 'Admin access required'
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
  difficulty: 'beginner',
  gate: '2',
}
const EMPTY_RESOURCE_DRAFT = {
  role: '',
  skill: '',
  title: '',
  platform: '',
  level: '',
  hours: '',
  url: '',
}
const EMPTY_RESUME_DRAFT = {
  role: '',
  section: '',
  tipsText: '',
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
  const role = source.role || source.role_filter || getWorkTypeLabel(
    [
      source.role_category,
      source.category,
      source.work_type,
      source.skill,
      source.skill_name,
      title,
    ].filter(Boolean).join(' '),
    '',
  )

  return {
    id: source.id || source.resource_id || `resource-${index + 1}-${normalizeText(title || skill || 'item')}`,
    role,
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

function normalizeResumeSection(section, index, fallbackRole = '') {
  const source = section || {}
  const title = source.section || source.title || `Resume section ${index + 1}`
  const tips = Array.isArray(source.tips)
    ? source.tips
    : String(source.tipsText || source.tip || '')
      .split('\n')
      .map((tip) => tip.trim())
      .filter(Boolean)

  return {
    id: source.id || `resume-${index + 1}-${normalizeText(title).replace(/[^a-z0-9]+/g, '-')}`,
    role: source.role || source.role_filter || fallbackRole,
    section: title,
    icon: source.icon || 'AI',
    tips,
    updated: source.updated || 'Saved locally',
  }
}

function loadAdminResumeSections() {
  if (typeof window === 'undefined') {
    return []
  }

  try {
    const raw = localStorage.getItem(ADMIN_RESUME_STORAGE_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed.map(normalizeResumeSection) : []
  } catch {
    return []
  }
}

function hasStoredAdminResumeSections() {
  if (typeof window === 'undefined') {
    return false
  }

  return localStorage.getItem(ADMIN_RESUME_STORAGE_KEY) !== null
}

function saveAdminResumeSections(sections) {
  if (typeof window === 'undefined') {
    return
  }

  try {
    localStorage.setItem(ADMIN_RESUME_STORAGE_KEY, JSON.stringify(sections))
  } catch {
    // Resume playbook edits remain available in memory for the active admin session.
  }
}

function createResumeSectionId(section) {
  const slug = normalizeText(section).replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '')
  return `resume-${slug || 'section'}-${Date.now()}`
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

function mergeCatalogEntries(baseItems = [], overrideItems = []) {
  const merged = new Map()

  baseItems.forEach((item) => {
    if (item?.id) {
      merged.set(item.id, item)
    }
  })

  overrideItems.forEach((item) => {
    if (item?.id) {
      merged.set(item.id, item)
    }
  })

  return [...merged.values()]
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

function getResourceRole(resource) {
  return resource.role || getWorkTypeLabel(
    [
      resource.skill,
      resource.title,
      resource.platform,
      resource.level,
    ].filter(Boolean).join(' '),
    '',
  )
}

function getResumeRole(section, fallback = '') {
  return section.role || fallback
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

function parsePromptOptions(optionsText) {
  return optionsText
    .split('\n')
    .map((option) => option.trim())
    .filter(Boolean)
}

function optionLabelsFromQuestionOptions(options) {
  if (!options) {
    return []
  }

  if (Array.isArray(options)) {
    return options
      .map((option) => {
        if (option && typeof option === 'object') {
          return option.label || option.text || option.value || option.id
        }
        return option
      })
      .filter(Boolean)
      .map(String)
  }

  if (typeof options === 'object') {
    return Object.entries(options)
      .map(([key, meta]) => {
        if (meta && typeof meta === 'object') {
          return meta.text || meta.label || meta.value || key
        }
        return meta || key
      })
      .filter(Boolean)
      .map(String)
  }

  return String(options)
    .split('\n')
    .map((option) => option.trim())
    .filter(Boolean)
}

function normalizeQuizRole(value, fallback = DEFAULT_QUIZ_ROLE) {
  const raw = String(value || '').trim()
  if (!raw) {
    return fallback
  }

  if (/[-_]/.test(raw) || raw === raw.toUpperCase()) {
    return raw
  }

  return getWorkTypeLabel(raw, raw || fallback)
}

function getPromptRoles(prompt) {
  const roles = Array.isArray(prompt?.role_targets) && prompt.role_targets.length
    ? prompt.role_targets
    : [prompt?.role]

  return uniqueItems(roles.map((role) => normalizeQuizRole(role, '')).filter(Boolean))
}

function normalizePrompt(question, index) {
  const roleTargets = Array.isArray(question.role_targets)
    ? question.role_targets.map((role) => normalizeQuizRole(role))
    : question.role
      ? [normalizeQuizRole(question.role)]
      : []

  return {
    id: question.id || `prompt-${index + 1}`,
    role: roleTargets[0] || normalizeQuizRole(question.role || question.role_category || question.target_role || question.category),
    role_targets: roleTargets,
    stem: question.stem || question.text || '',
    options: optionLabelsFromQuestionOptions(question.options),
    status: question.is_active === false ? 'Archived' : question.status || 'Live',
    updated: question.updated || (question.response_count ? `${question.response_count} responses` : 'Live quiz bank'),
    gate: question.gate ?? 2,
    difficulty: question.difficulty || 'beginner',
    question_type: question.question_type || 'multiple_choice',
    answer_mode: question.answer_mode || 'single_choice',
    response_count: question.response_count || 0,
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
    role: normalizeQuizRole(source.role || basePrompt.role),
    role_targets: Array.isArray(source.role_targets) ? source.role_targets : basePrompt.role_targets,
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

function getAttemptProfile(attempt) {
  return attempt?.profile || {}
}

function getAttemptProgress(attempt) {
  return attempt?.progress || {}
}

function getAttemptJobs(attempt) {
  return Array.isArray(attempt?.jobs) ? attempt.jobs : []
}

function normalizeAdminAttempt(attempt) {
  const profile = attempt?.profile || {}
  const progress = attempt?.progress || {}

  return {
    id: attempt?.id || profile.session_id || `admin-attempt-${Date.now()}`,
    completed_at: attempt?.completed_at || attempt?.last_answered_at || attempt?.started_at || 'Stored backend attempt',
    profile: {
      ...profile,
      session_id: profile.session_id || attempt?.id,
    },
    progress,
    answers: attempt?.answers || [],
    jobs: [],
    sourceLabel: attempt?.status === 'completed' ? 'Backend completed quiz' : 'Backend in-progress quiz',
    status: attempt?.status || 'active',
  }
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
  const [adminAccessKey, setAdminAccessKeyInput] = useState(() => getStoredAdminAccessKey())
  const [adminAuthState, setAdminAuthState] = useState(() => ({
    error: '',
    isAuthorized: false,
    isLoading: Boolean(getStoredAdminAccessKey()),
  }))
  const [activeTab, setActiveTab] = useState(adminTabs[0])
  const [activeProfilePage, setActiveProfilePage] = useState(profilePages[0])
  const [jobSearch, setJobSearch] = useState('')
  const [quizPrompts, setQuizPrompts] = useState(loadAdminQuizPrompts)
  const [selectedPromptRole, setSelectedPromptRole] = useState(ALL_QUIZ_ROLES)
  const [newPromptDraft, setNewPromptDraft] = useState({ ...EMPTY_PROMPT_DRAFT })
  const [editingPromptId, setEditingPromptId] = useState('')
  const [promptDraft, setPromptDraft] = useState({ ...EMPTY_PROMPT_DRAFT })
  const [quizBankState, setQuizBankState] = useState({
    error: '',
    isLoading: true,
    roles: [],
    total: 0,
  })
  const [quizCrudError, setQuizCrudError] = useState('')
  const [adminQuizAttempts, setAdminQuizAttempts] = useState([])
  const [adminAttemptState, setAdminAttemptState] = useState({
    error: '',
    isLoading: true,
    total: 0,
    completed: 0,
  })
  const [adminAnalytics, setAdminAnalytics] = useState(null)
  const [adminAnalyticsState, setAdminAnalyticsState] = useState({
    error: '',
    isLoading: true,
  })
  const [analysis, setAnalysis] = useState(() => loadStoredAnalysis())
  const [resumeCoaching, setResumeCoaching] = useState(() => loadCachedResumeTips())
  const [storedRecommendations, setStoredRecommendations] = useState(() => loadStoredRecommendations() || [])
  const [managedResources, setManagedResources] = useState(loadAdminResources)
  const [hasManagedResourceStore, setHasManagedResourceStore] = useState(hasStoredAdminResources)
  const [selectedLearningRole, setSelectedLearningRole] = useState(ALL_ROLE_FILTERS)
  const [editingResourceId, setEditingResourceId] = useState('')
  const [resourceDraft, setResourceDraft] = useState({ ...EMPTY_RESOURCE_DRAFT })
  const [managedResumeSections, setManagedResumeSections] = useState(loadAdminResumeSections)
  const [hasManagedResumeStore, setHasManagedResumeStore] = useState(hasStoredAdminResumeSections)
  const [selectedResumeRole, setSelectedResumeRole] = useState(ALL_ROLE_FILTERS)
  const [editingResumeId, setEditingResumeId] = useState('')
  const [resumeDraft, setResumeDraft] = useState({ ...EMPTY_RESUME_DRAFT })
  const [selectedTelegramRole, setSelectedTelegramRole] = useState(ALL_ROLE_FILTERS)
  const [telegramState, setTelegramState] = useState({
    error: '',
    isLoading: true,
    jobs: [],
    updatedAt: '',
  })

  useEffect(() => {
    let cancelled = false
    const storedKey = getStoredAdminAccessKey()

    if (!storedKey) {
      return () => {
        cancelled = true
      }
    }

    verifyAdminAccess(storedKey)
      .then(() => {
        if (cancelled) {
          return
        }

        setAdminAuthState({
          error: '',
          isAuthorized: true,
          isLoading: false,
        })
      })
      .catch((err) => {
        if (cancelled) {
          return
        }

        clearStoredAdminAccessKey()
        setAdminAccessKeyInput('')
        setAdminAuthState({
          error: err.message || 'Admin access key is invalid.',
          isAuthorized: false,
          isLoading: false,
        })
      })

    return () => {
      cancelled = true
    }
  }, [])

  const profile = loadStoredProfile()
  const recommendations = storedRecommendations
  const quizHistory = loadStoredQuizHistory()
  const quizProgress = loadStoredQuizProgress()
  const backendQuizAttempts = adminQuizAttempts.map(normalizeAdminAttempt)

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
    ...backendQuizAttempts,
    ...quizHistory.map((attempt) => ({ ...attempt, sourceLabel: 'Saved browser quiz' })),
    ...(currentQuizAttempt ? [currentQuizAttempt] : []),
  ].filter((attempt, index, attempts) =>
    attempt?.id && attempts.findIndex((item) => item?.id === attempt.id) === index,
  )
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
      source: attempt.isCurrent ? 'Active browser session' : attempt.sourceLabel || 'Saved quiz history',
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
  const resources = mergeCatalogEntries(aiResources, managedResources)
  const aiResumeSections = (resumeCoaching?.tips || []).map((section, index) =>
    normalizeResumeSection(section, index, workTypeNames[0] || aggregateProfile.target_role || ''),
  )
  const resumeSections = mergeCatalogEntries(aiResumeSections, managedResumeSections)
  const learningRoleOptions = uniqueItems([
    ...workTypeNames,
    ...resources.map(getResourceRole),
    ...gaps.map((gap) => getWorkTypeLabel(getGapName(gap), '')),
  ]).filter(Boolean)
  const resumeRoleOptions = uniqueItems([
    ...workTypeNames,
    ...resumeSections.map((section) => getResumeRole(section, workTypeNames[0] || '')),
  ]).filter(Boolean)
  const telegramRoleOptions = uniqueItems(
    telegramState.jobs.map((job) => job.category || job.role || getJobWorkType(job)),
  ).filter(Boolean)
  const filteredResources = selectedLearningRole === ALL_ROLE_FILTERS
    ? resources
    : resources.filter((resource) => getResourceRole(resource) === selectedLearningRole)
  const filteredGaps = selectedLearningRole === ALL_ROLE_FILTERS
    ? gaps
    : gaps.filter((gap) =>
        getWorkTypeLabel(getGapName(gap), '') === selectedLearningRole ||
        getGapName(gap).toLowerCase().includes(selectedLearningRole.toLowerCase()),
      )
  const filteredResumeSections = selectedResumeRole === ALL_ROLE_FILTERS
    ? resumeSections
    : resumeSections.filter((section) =>
        getResumeRole(section, workTypeNames[0] || '') === selectedResumeRole,
      )
  const filteredTelegramJobs = selectedTelegramRole === ALL_ROLE_FILTERS
    ? telegramState.jobs
    : telegramState.jobs.filter((job) =>
        [job.category, job.role, getJobWorkType(job), job.job_title, job.description]
          .filter(Boolean)
          .join(' ')
          .toLowerCase()
          .includes(selectedTelegramRole.toLowerCase()),
      )
  const gapStatus = analysis?.gaps?.length ? 'AI ready' : derivedGaps.length ? 'Stored data' : 'Pending'
  const learningStatus = hasManagedResourceStore
    ? aiResourceRows.length
      ? 'AI + admin catalog'
      : 'Admin catalog'
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
  const resumeAdminStatus = resumeSections.length ? resumeStatus : 'Needs profile'
  const topMatchedJobs = getTopMatchedJobs(aggregateRecommendations)
  const promptRoleOptions = uniqueItems([
    DEFAULT_QUIZ_ROLE,
    ...quizBankState.roles,
    ...quizPrompts.flatMap(getPromptRoles),
    ...workTypeNames,
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
    : quizPrompts.filter((prompt) => getPromptRoles(prompt).includes(selectedPromptRole))
  const promptCoverageByRole = promptRoleOptions.map((role) => ({
    role,
    count: quizPrompts.filter((prompt) => getPromptRoles(prompt).includes(role)).length,
  }))
  const newPromptOptions = parsePromptOptions(newPromptDraft.optionsText)
  const canAddPrompt = Boolean(newPromptDraft.stem.trim()) && newPromptOptions.length >= 2

  const filteredJobs = aggregateRecommendations.filter((job) =>
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
    if (!adminAuthState.isAuthorized) {
      return
    }

    let cancelled = false

    fetchAdminQuizAttempts({ limit: 250 })
      .then((payload) => {
        if (cancelled) {
          return
        }

        setAdminQuizAttempts(payload.attempts || [])
        setAdminAttemptState({
          error: '',
          isLoading: false,
          total: payload.total || 0,
          completed: payload.completed || 0,
        })
      })
      .catch((err) => {
        if (cancelled) {
          return
        }

        setAdminAttemptState({
          error: err.message || 'Could not load backend quiz attempts.',
          isLoading: false,
          total: 0,
          completed: 0,
        })
      })

    return () => {
      cancelled = true
    }
  }, [adminAuthState.isAuthorized])

  useEffect(() => {
    if (!adminAuthState.isAuthorized) {
      return
    }

    let cancelled = false

    fetchAdminAnalytics({ limit: 1500 })
      .then((payload) => {
        if (cancelled) {
          return
        }

        setAdminAnalytics(payload)
        setAdminAnalyticsState({ error: '', isLoading: false })
      })
      .catch((err) => {
        if (cancelled) {
          return
        }

        setAdminAnalyticsState({
          error: err.message || 'Could not load admin analytics.',
          isLoading: false,
        })
      })

    return () => {
      cancelled = true
    }
  }, [adminAuthState.isAuthorized])

  useEffect(() => {
    if (!adminAuthState.isAuthorized) {
      return
    }

    let cancelled = false

    fetchAdminQuizQuestions({ status: 'active', limit: 1000 })
      .then((payload) => {
        if (cancelled) {
          return
        }

        const questions = (payload.questions || []).map(normalizeStoredPrompt)
        setQuizPrompts(questions.length ? questions : loadAdminQuizPrompts())
        setQuizBankState({
          error: '',
          isLoading: false,
          roles: payload.roles || [],
          total: payload.total || questions.length,
        })
      })
      .catch((err) => {
        if (cancelled) {
          return
        }

        setQuizPrompts(loadAdminQuizPrompts())
        setQuizBankState({
          error: err.message || 'Using local quiz prompts because the live quiz bank could not load.',
          isLoading: false,
          roles: [],
          total: 0,
        })
      })

    return () => {
      cancelled = true
    }
  }, [adminAuthState.isAuthorized])

  useEffect(() => {
    if (!adminAuthState.isAuthorized) {
      return
    }

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
  }, [
    adminAuthState.isAuthorized,
    adminAiRequestKey,
    aggregateProfilePayload,
    canBuildRecommendations,
    storedRecommendations.length,
  ])

  useEffect(() => {
    if (!adminAuthState.isAuthorized) {
      return
    }

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
    adminAuthState.isAuthorized,
    adminAiRequestKey,
    aggregateProfilePayload,
    aggregateRecommendationsPayload,
    canRequestAdminAi,
    analysis?.gaps?.length,
    analysis?.resources?.length,
  ])

  useEffect(() => {
    if (!adminAuthState.isAuthorized) {
      return
    }

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
    adminAuthState.isAuthorized,
    adminAiRequestKey,
    aggregateProfilePayload,
    aggregateRecommendationsPayload,
    canRequestAdminAi,
    resumeCoaching,
  ])

  useEffect(() => {
    if (!adminAuthState.isAuthorized) {
      return
    }

    let cancelled = false

    fetchTelegramJobs({ limit: 80 })
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
  }, [adminAuthState.isAuthorized])

  const handleAdminLogin = async (event) => {
    event.preventDefault()
    const trimmedKey = adminAccessKey.trim()

    if (!trimmedKey) {
      setAdminAuthState({
        error: 'Enter the admin access key.',
        isAuthorized: false,
        isLoading: false,
      })
      return
    }

    setAdminAuthState((current) => ({
      ...current,
      error: '',
      isLoading: true,
    }))

    try {
      await verifyAdminAccess(trimmedKey)
      setStoredAdminAccessKey(trimmedKey)
      setAdminAuthState({
        error: '',
        isAuthorized: true,
        isLoading: false,
      })
    } catch (err) {
      clearStoredAdminAccessKey()
      setAdminAuthState({
        error: err.message || 'Admin access key is invalid.',
        isAuthorized: false,
        isLoading: false,
      })
    }
  }

  const handleAdminLogout = () => {
    clearStoredAdminAccessKey()
    setAdminAccessKeyInput('')
    setAdminAuthState({
      error: '',
      isAuthorized: false,
      isLoading: false,
    })
  }

  const analyticsTotals = adminAnalytics?.totals || {}
  const analyticsPeriods = adminAnalytics?.periods || {}
  const analyticsRoleRows = adminAnalytics?.roles || []
  const analyticsMatchedSkillRows = adminAnalytics?.matched_skills || []
  const analyticsGapRows = adminAnalytics?.gaps || []
  const analyticsWatchedJobRows = adminAnalytics?.watched_jobs || []
  const intakePeriodRows = [
    { label: 'Daily', count: analyticsPeriods.daily || 0 },
    { label: 'Weekly', count: analyticsPeriods.weekly || 0 },
    { label: 'Monthly', count: analyticsPeriods.monthly || 0 },
    { label: 'Yearly', count: analyticsPeriods.yearly || 0 },
  ]
  const analyticsIntakeCount = analyticsTotals.intakes || quizAttemptSummaries.length
  const manualIntakeCount = analyticsTotals.manual_intakes || 0
  const quizIntakeCount = analyticsTotals.quiz_intakes || adminAttemptState.completed || quizAttemptSummaries.length

  const metrics = [
    {
      label: 'Users assessed',
      value: `${analyticsIntakeCount} total`,
      status: analyticsIntakeCount ? 'Ready' : 'Pending',
    },
    {
      label: 'Quiz / manual',
      value: `${quizIntakeCount} / ${manualIntakeCount}`,
      status: analyticsIntakeCount ? 'Ready' : 'Pending',
    },
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

  const overviewGraphRows = [
    {
      label: 'Daily intakes',
      value: analyticsPeriods.daily || 0,
      score: Math.min(100, Math.round(((analyticsPeriods.daily || 0) / Math.max(analyticsIntakeCount, 1)) * 100)),
      detail: `${analyticsPeriods.weekly || 0} this week`,
    },
    {
      label: 'Quiz history',
      value: quizIntakeCount,
      score: Math.min(100, Math.round((quizIntakeCount / Math.max(analyticsIntakeCount || adminAttemptState.total || quizAttemptSummaries.length, 1)) * 100)),
      detail: `${adminAttemptState.completed || quizHistory.length} completed`,
    },
    {
      label: 'Manual input',
      value: manualIntakeCount,
      score: Math.min(100, Math.round((manualIntakeCount / Math.max(analyticsIntakeCount, 1)) * 100)),
      detail: `${analyticsIntakeCount} total intakes`,
    },
    {
      label: 'Profile signals',
      value: profileSkills.length,
      score: Math.min(100, Math.round((profileSkills.length / 12) * 100)),
      detail: `${workTypeNames.length || 0} work types`,
    },
    {
      label: 'Match quality',
      value: averageMatch ?? 0,
      score: averageMatch ?? 0,
      detail: averageMatch === null ? 'Awaiting scores' : `${averageMatch}% average`,
    },
    {
      label: 'Learning coverage',
      value: filteredResources.length || resources.length,
      score: Math.min(100, Math.round(((filteredResources.length || resources.length) / 10) * 100)),
      detail: `${gaps.length} gaps tracked`,
    },
  ]
  const learningGraphRows = [
    ...filteredGaps.slice(0, 4).map((gap) => ({
      label: getGapName(gap),
      score: getGapPriority(gap) ?? 50,
      detail: gap.priority_label || 'Gap priority',
    })),
    ...filteredResources.slice(0, 4).map((resource) => ({
      label: resource.title,
      score: Math.min(100, Number(resource.recommendation_score) || Number(resource.hours) * 8 || 60),
      detail: getResourceRole(resource) || resource.platform || 'Resource',
    })),
  ].slice(0, 6)
  const resumeGraphRows = filteredResumeSections.slice(0, 6).map((section) => ({
    label: section.section,
    score: Math.min(100, (section.tips?.length || 0) * 25),
    detail: `${section.tips?.length || 0} tips`,
  }))
  const telegramGraphRows = countWorkTypeSignals(filteredTelegramJobs.map((job) => job.category || job.role || getJobWorkType(job)))
    .slice(0, 6)
    .map((item) => ({
      label: item.workType,
      score: Math.min(100, Math.round((item.count / Math.max(filteredTelegramJobs.length, 1)) * 100)),
      detail: `${item.count} jobs`,
    }))
  const startPromptEdit = (prompt) => {
    setEditingPromptId(prompt.id)
    setPromptDraft({
      role: getPromptRoles(prompt)[0] || normalizeQuizRole(prompt.role),
      stem: prompt.stem,
      optionsText: prompt.options.join('\n'),
      difficulty: prompt.difficulty || 'beginner',
      gate: String(prompt.gate ?? 2),
    })
  }
  const cancelPromptEdit = () => {
    setEditingPromptId('')
    setPromptDraft({ ...EMPTY_PROMPT_DRAFT })
  }
  const addPrompt = async (event) => {
    event.preventDefault()

    const role = normalizeQuizRole(newPromptDraft.role)
    const stem = newPromptDraft.stem.trim()
    const options = parsePromptOptions(newPromptDraft.optionsText)

    if (!stem || options.length < 2) {
      return
    }

    setQuizCrudError('')
    try {
      const payload = await saveAdminQuizQuestion({
        role_targets: [role],
        stem,
        options,
        gate: Number(newPromptDraft.gate || 2),
        difficulty: newPromptDraft.difficulty || 'beginner',
      })
      const nextPrompt = normalizeStoredPrompt(payload.question, 0)

      setQuizPrompts((prompts) => {
        const nextPrompts = [nextPrompt, ...prompts.filter((prompt) => prompt.id !== nextPrompt.id)]
        saveAdminQuizPrompts(nextPrompts)
        return nextPrompts
      })
      setSelectedPromptRole(role)
      setNewPromptDraft({ ...EMPTY_PROMPT_DRAFT, role })
      setQuizBankState((current) => ({
        ...current,
        roles: uniqueItems([...current.roles, role]),
        total: current.total + 1,
      }))
    } catch (err) {
      setQuizCrudError(err.message || 'Could not save quiz question.')
    }
  }
  const updatePrompt = async () => {
    const role = normalizeQuizRole(promptDraft.role)
    const normalizedOptions = parsePromptOptions(promptDraft.optionsText)

    setQuizCrudError('')
    try {
      const payload = await saveAdminQuizQuestion({
        id: editingPromptId,
        role_targets: [role],
        stem: promptDraft.stem.trim(),
        options: normalizedOptions,
        gate: Number(promptDraft.gate || 2),
        difficulty: promptDraft.difficulty || 'beginner',
      })
      const updatedPrompt = normalizeStoredPrompt(payload.question, 0)

      setQuizPrompts((prompts) => {
        const nextPrompts = prompts.map((prompt) =>
          prompt.id === editingPromptId ? updatedPrompt : prompt,
        )

        saveAdminQuizPrompts(nextPrompts)
        return nextPrompts
      })
      setSelectedPromptRole(role)
      cancelPromptEdit()
    } catch (err) {
      setQuizCrudError(err.message || 'Could not update quiz question.')
    }
  }
  const deletePrompt = async (promptId) => {
    setQuizCrudError('')
    try {
      await deleteAdminQuizQuestion(promptId)
      setQuizPrompts((prompts) => {
        const nextPrompts = prompts.filter((prompt) => prompt.id !== promptId)
        saveAdminQuizPrompts(nextPrompts)
        return nextPrompts
      })
      if (editingPromptId === promptId) {
        cancelPromptEdit()
      }
    } catch (err) {
      setQuizCrudError(err.message || 'Could not delete quiz question.')
    }
  }
  const startResourceEdit = (resource) => {
    setEditingResourceId(resource.id)
    setResourceDraft({
      role: resource.role || '',
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
      role: resourceDraft.role,
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
  const startResumeEdit = (section) => {
    setEditingResumeId(section.id)
    setResumeDraft({
      role: section.role || '',
      section: section.section || '',
      tipsText: (section.tips || []).join('\n'),
    })
  }
  const cancelResumeEdit = () => {
    setEditingResumeId('')
    setResumeDraft({ ...EMPTY_RESUME_DRAFT })
  }
  const saveResumeSection = (event) => {
    event.preventDefault()

    const sectionTitle = resumeDraft.section.trim()
    const tips = parsePromptOptions(resumeDraft.tipsText)
    if (!sectionTitle || !tips.length) {
      return
    }

    const nextSection = normalizeResumeSection({
      id: editingResumeId || createResumeSectionId(sectionTitle),
      role: resumeDraft.role,
      section: sectionTitle,
      tips,
      updated: editingResumeId ? 'Updated locally' : 'Added locally',
    }, resumeSections.length)
    const nextSections = editingResumeId
      ? resumeSections.map((section) => (section.id === editingResumeId ? nextSection : section))
      : [nextSection, ...resumeSections]

    setManagedResumeSections(nextSections)
    saveAdminResumeSections(nextSections)
    setHasManagedResumeStore(true)
    cancelResumeEdit()
  }
  const deleteResumeSection = (sectionId) => {
    const nextSections = resumeSections.filter((section) => section.id !== sectionId)

    setManagedResumeSections(nextSections)
    saveAdminResumeSections(nextSections)
    setHasManagedResumeStore(true)
    if (editingResumeId === sectionId) {
      cancelResumeEdit()
    }
  }

  if (adminAuthState.isLoading || !adminAuthState.isAuthorized) {
    return (
      <section className="admin-page admin-login-page">
        <div className="admin-login-card">
          <p className="eyebrow">{ADMIN_LOGIN_TITLE}</p>
          <h1>Admin portal</h1>

          <form className="admin-login-form" onSubmit={handleAdminLogin}>
            <label className="field-group">
              <span>Access key</span>
              <input
                type="password"
                value={adminAccessKey}
                onChange={(event) => setAdminAccessKeyInput(event.target.value)}
                placeholder="Enter admin access key"
                autoComplete="current-password"
              />
            </label>

            {adminAuthState.error && <p className="form-error">{adminAuthState.error}</p>}

            <button type="submit" className="button button-primary" disabled={adminAuthState.isLoading}>
              {adminAuthState.isLoading ? 'Verifying...' : 'Open admin'}
            </button>
          </form>
        </div>
      </section>
    )
  }

  return (
    <section className="admin-page">
      <div className="admin-header">
        <div>
          <p className="eyebrow">Admin command center</p>
          <h1>Workflow overview and content controls.</h1>
        </div>

        <div className="admin-route-note" aria-label="Admin access mode">
          <span>Access</span>
          <strong>/admin</strong>
          <small>
            <button type="button" className="button button-ghost admin-logout-link" onClick={handleAdminLogout}>
              Sign out
            </button>
          </small>
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

          <section className="admin-panel">
            <div className="admin-panel-heading">
              <span>Overall site data</span>
              <strong>
                {adminAttemptState.isLoading
                  ? 'Loading quiz history'
                  : `${adminAttemptState.total || quizAttemptSummaries.length} quiz records`}
              </strong>
            </div>

            {adminAttemptState.error && <p className="form-error">{adminAttemptState.error}</p>}
            {adminAnalyticsState.error && <p className="form-error">{adminAnalyticsState.error}</p>}

            <div className="admin-insight-grid">
              {overviewGraphRows.map((row) => (
                <article className="admin-insight-card" key={row.label}>
                  <div className="admin-insight-copy">
                    <span>{row.label}</span>
                    <strong>{row.detail}</strong>
                  </div>
                  <div className="admin-graph-track" aria-label={`${row.label} ${row.score}%`}>
                    <span style={{ width: `${Math.min(100, row.score)}%` }}></span>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <div className="admin-grid">
            <section className="admin-panel">
              <div className="admin-panel-heading">
                <span>Quiz and manual intake volume</span>
                <strong>{adminAnalyticsState.isLoading ? 'Loading' : `${analyticsIntakeCount} users`}</strong>
              </div>

              <div className="admin-stat-grid">
                {intakePeriodRows.map((row) => (
                  <article className="admin-dashboard-card" key={row.label}>
                    <span className="metric-label">{row.label}</span>
                    <strong>{row.count}</strong>
                    <small className="admin-small-note">completed intakes</small>
                  </article>
                ))}
              </div>
            </section>

            <section className="admin-panel">
              <div className="admin-panel-heading">
                <span>All role demand</span>
                <strong>{analyticsRoleRows.length ? `${analyticsRoleRows.length} roles` : 'No role data'}</strong>
              </div>

              <div className="admin-bar-list" aria-label="All roles graph">
                {(analyticsRoleRows.length ? analyticsRoleRows : workTypeCoverage.map((item) => ({
                  label: item.workType,
                  count: item.count,
                }))).slice(0, 8).map((row) => (
                  <article className="admin-graph-row" key={row.label}>
                    <div className="admin-graph-copy">
                      <strong>{formatLabel(row.label)}</strong>
                      <span>{row.count} users</span>
                    </div>
                    <div className="admin-graph-track" aria-label={`${row.label} ${row.count}`}>
                      <span style={{ width: `${Math.min(100, Math.round((row.count / Math.max(analyticsIntakeCount, 1)) * 100))}%` }}></span>
                    </div>
                    <strong className="admin-graph-score">{row.count}</strong>
                  </article>
                ))}
              </div>
            </section>
          </div>

          <div className="admin-grid">
            <section className="admin-panel">
              <div className="admin-panel-heading">
                <span>Highest matched skills</span>
                <strong>{analyticsMatchedSkillRows.length ? 'Recorded' : 'Awaiting matches'}</strong>
              </div>
              <div className="admin-bar-list" aria-label="Highest matched skills graph">
                {(analyticsMatchedSkillRows.length ? analyticsMatchedSkillRows : profileSkills.map((skill) => ({
                  label: skill,
                  count: 1,
                }))).slice(0, 8).map((row) => (
                  <article className="admin-graph-row" key={row.label}>
                    <div className="admin-graph-copy">
                      <strong>{formatLabel(row.label)}</strong>
                      <span>{row.count} matches</span>
                    </div>
                    <div className="admin-graph-track" aria-label={`${row.label} ${row.count}`}>
                      <span style={{ width: `${Math.min(100, row.count * 18)}%` }}></span>
                    </div>
                    <strong className="admin-graph-score">{row.count}</strong>
                  </article>
                ))}
              </div>
            </section>

            <section className="admin-panel">
              <div className="admin-panel-heading">
                <span>Top gaps and watched jobs</span>
                <strong>{analyticsWatchedJobRows.length ? `${analyticsWatchedJobRows.length} watched` : 'No views yet'}</strong>
              </div>
              <div className="admin-bar-list" aria-label="Top gaps graph">
                {analyticsGapRows.slice(0, 4).map((row) => (
                  <article className="admin-graph-row" key={`gap-${row.label}`}>
                    <div className="admin-graph-copy">
                      <strong>{formatLabel(row.label)}</strong>
                      <span>{row.count} gap signals</span>
                    </div>
                    <div className="admin-graph-track" aria-label={`${row.label} ${row.count}`}>
                      <span style={{ width: `${Math.min(100, row.count * 18)}%` }}></span>
                    </div>
                    <strong className="admin-graph-score">{row.count}</strong>
                  </article>
                ))}
                {analyticsWatchedJobRows.slice(0, 4).map((row) => (
                  <article className="admin-graph-row" key={`job-${row.label}`}>
                    <div className="admin-graph-copy">
                      <strong>{row.label}</strong>
                      <span>{row.count} views</span>
                    </div>
                    <div className="admin-graph-track" aria-label={`${row.label} ${row.count}`}>
                      <span style={{ width: `${Math.min(100, row.count * 18)}%` }}></span>
                    </div>
                    <strong className="admin-graph-score">{row.count}</strong>
                  </article>
                ))}
              </div>
              {!analyticsGapRows.length && !analyticsWatchedJobRows.length && (
                <div className="admin-empty">Gap and job-view records will appear after users open matched jobs.</div>
              )}
            </section>
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
                  <small>{quizHistory.length} browser / {adminAttemptState.total || 0} backend</small>
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
                <strong>
                  {quizBankState.isLoading
                    ? 'Loading live bank'
                    : `${filteredQuizPrompts.length} shown / ${quizBankState.total || quizPrompts.length} live`}
                </strong>
              </div>

              {quizBankState.error && <p className="form-error">{quizBankState.error}</p>}
              {quizCrudError && <p className="form-error">{quizCrudError}</p>}

              <div className="admin-role-quiz-controls">
                <label>
                  Work type filter
                  <select
                    value={selectedPromptRole}
                    onChange={(event) => setSelectedPromptRole(event.target.value)}
                  >
                    <option value={ALL_QUIZ_ROLES}>{ALL_QUIZ_ROLES}</option>
                    {promptRoleOptions.map((role) => (
                      <option value={role} key={role}>{formatLabel(role)}</option>
                    ))}
                  </select>
                </label>

                <div className="admin-role-counts" aria-label="Quiz prompt coverage by work type">
                  {promptCoverageByRole.map((item) => (
                    <span className="chip chip-blue" key={item.role}>
                      {formatLabel(item.role)} {item.count}
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
                        <option value={role} key={role}>{formatLabel(role)}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Gate
                    <input
                      value={newPromptDraft.gate}
                      onChange={(event) => setNewPromptDraft((draft) => ({
                        ...draft,
                        gate: event.target.value,
                      }))}
                    />
                  </label>
                  <label>
                    Difficulty
                    <select
                      value={newPromptDraft.difficulty}
                      onChange={(event) => setNewPromptDraft((draft) => ({
                        ...draft,
                        difficulty: event.target.value,
                      }))}
                    >
                      <option value="beginner">Beginner</option>
                      <option value="intermediate">Intermediate</option>
                      <option value="advanced">Advanced</option>
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
                                <option value={role} key={role}>{formatLabel(role)}</option>
                              ))}
                            </select>
                          </label>
                          <label>
                            Gate
                            <input
                              value={promptDraft.gate}
                              onChange={(event) => setPromptDraft((draft) => ({
                                ...draft,
                                gate: event.target.value,
                              }))}
                            />
                          </label>
                          <label>
                            Difficulty
                            <select
                              value={promptDraft.difficulty}
                              onChange={(event) => setPromptDraft((draft) => ({
                                ...draft,
                                difficulty: event.target.value,
                              }))}
                            >
                              <option value="beginner">Beginner</option>
                              <option value="intermediate">Intermediate</option>
                              <option value="advanced">Advanced</option>
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
                          <span className="chip chip-blue">{getPromptRoles(prompt).map(formatLabel).join(', ') || formatLabel(prompt.role)}</span>
                          <h2>{prompt.stem}</h2>
                          <p>{prompt.options.join(' / ')}</p>
                          <small className="admin-small-note">{prompt.updated}</small>
                          <small className="admin-small-note">
                            Gate {prompt.gate} / {formatLabel(prompt.difficulty)} / {formatLabel(prompt.question_type)}
                          </small>
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
              <strong>{filteredGaps.length ? `${filteredGaps.length} active gaps / ${gapStatus}` : 'Awaiting AI'}</strong>
            </div>

            <div className="admin-toolbar">
              <label>
                Role filter
                <select
                  value={selectedLearningRole}
                  onChange={(event) => setSelectedLearningRole(event.target.value)}
                >
                  <option value={ALL_ROLE_FILTERS}>{ALL_ROLE_FILTERS}</option>
                  {learningRoleOptions.map((role) => (
                    <option value={role} key={role}>{formatLabel(role)}</option>
                  ))}
                </select>
              </label>
              <label>
                Source
                <input
                  value={hasManagedResourceStore ? 'AI + admin catalog' : 'AI resource analysis'}
                  readOnly
                />
              </label>
            </div>

            {learningGraphRows.length > 0 && (
              <div className="admin-bar-list" aria-label="Learning insight graph">
                {learningGraphRows.map((row) => (
                  <article className="admin-graph-row" key={`${row.label}-${row.detail}`}>
                    <div className="admin-graph-copy">
                      <strong>{row.label}</strong>
                      <span>{row.detail}</span>
                    </div>
                    <div className="admin-graph-track" aria-label={`${row.label} ${row.score}%`}>
                      <span style={{ width: `${Math.min(100, row.score)}%` }}></span>
                    </div>
                    <strong className="admin-graph-score">{Math.round(row.score)}%</strong>
                  </article>
                ))}
              </div>
            )}

            {filteredGaps.length ? (
              <div className="question-review-list">
                {filteredGaps.map((gap) => {
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
                  Role
                  <select
                    value={resourceDraft.role}
                    onChange={(event) => setResourceDraft((draft) => ({
                      ...draft,
                      role: event.target.value,
                    }))}
                  >
                    <option value="">General</option>
                    {learningRoleOptions.map((role) => (
                      <option value={role} key={role}>{formatLabel(role)}</option>
                    ))}
                  </select>
                </label>
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
                <small>{filteredResources.length} of {resources.length} resources listed</small>
              </div>
            </form>

            {filteredResources.length ? (
              <div className="question-review-list">
                {filteredResources.map((resource) => (
                  <article className="question-review-card" key={resource.id}>
                    <div>
                      <span className="chip chip-blue">{formatLabel(getResourceRole(resource), resource.level || 'Resource')}</span>
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
            <strong>{resumeAdminStatus}</strong>
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

          <div className="admin-toolbar">
            <label>
              Role filter
              <select
                value={selectedResumeRole}
                onChange={(event) => setSelectedResumeRole(event.target.value)}
              >
                <option value={ALL_ROLE_FILTERS}>{ALL_ROLE_FILTERS}</option>
                {resumeRoleOptions.map((role) => (
                  <option value={role} key={role}>{formatLabel(role)}</option>
                ))}
              </select>
            </label>
            <label>
              Source
              <input
                value={hasManagedResumeStore ? 'AI + admin playbook' : 'AI resume coaching'}
                readOnly
              />
            </label>
          </div>

          {resumeGraphRows.length > 0 && (
            <div className="admin-bar-list" aria-label="Resume insight graph">
              {resumeGraphRows.map((row) => (
                <article className="admin-graph-row" key={row.label}>
                  <div className="admin-graph-copy">
                    <strong>{row.label}</strong>
                    <span>{row.detail}</span>
                  </div>
                  <div className="admin-graph-track" aria-label={`${row.label} ${row.score}%`}>
                    <span style={{ width: `${Math.min(100, row.score)}%` }}></span>
                  </div>
                  <strong className="admin-graph-score">{Math.round(row.score)}%</strong>
                </article>
              ))}
            </div>
          )}

          <form className="admin-role-quiz-form" onSubmit={saveResumeSection}>
            <div className="admin-role-quiz-form-grid">
              <label>
                Role
                <select
                  value={resumeDraft.role}
                  onChange={(event) => setResumeDraft((draft) => ({
                    ...draft,
                    role: event.target.value,
                  }))}
                >
                  <option value="">General</option>
                  {resumeRoleOptions.map((role) => (
                    <option value={role} key={role}>{formatLabel(role)}</option>
                  ))}
                </select>
              </label>
              <label>
                Section
                <input
                  value={resumeDraft.section}
                  onChange={(event) => setResumeDraft((draft) => ({
                    ...draft,
                    section: event.target.value,
                  }))}
                />
              </label>
              <label>
                Tips
                <textarea
                  value={resumeDraft.tipsText}
                  placeholder="One resume recommendation per line"
                  onChange={(event) => setResumeDraft((draft) => ({
                    ...draft,
                    tipsText: event.target.value,
                  }))}
                />
              </label>
            </div>

            <div className="admin-role-quiz-actions">
              <button className="button button-primary" type="submit" disabled={!resumeDraft.section.trim() || !resumeDraft.tipsText.trim()}>
                {editingResumeId ? 'Update resume section' : 'Add resume section'}
              </button>
              {editingResumeId && (
                <button className="button button-ghost" type="button" onClick={cancelResumeEdit}>
                  Cancel
                </button>
              )}
              <small>{filteredResumeSections.length} of {resumeSections.length} sections listed</small>
            </div>
          </form>

          {filteredResumeSections.length ? (
            <div className="tips-grid">
              {filteredResumeSections.map((section) => (
                <article className="tips-section" key={section.id}>
                  <div className="tips-section-title">
                    <span>{section.icon || 'AI'}</span>
                    <h2>{section.section}</h2>
                  </div>
                  <ul>
                    {(section.tips || []).slice(0, 3).map((tip) => (
                      <li key={tip}>{tip}</li>
                    ))}
                  </ul>
                  <div className="question-review-actions">
                    <span className="chip chip-blue">{formatLabel(getResumeRole(section, workTypeNames[0] || ''), 'General')}</span>
                    <button className="button button-ghost" type="button" onClick={() => startResumeEdit(section)}>
                      Edit
                    </button>
                    <button className="button button-ghost" type="button" onClick={() => deleteResumeSection(section.id)}>
                      Delete
                    </button>
                  </div>
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

          <div className="admin-toolbar">
            <label>
              Role filter
              <select
                value={selectedTelegramRole}
                onChange={(event) => setSelectedTelegramRole(event.target.value)}
              >
                <option value={ALL_ROLE_FILTERS}>{ALL_ROLE_FILTERS}</option>
                {telegramRoleOptions.map((role) => (
                  <option value={role} key={role}>{formatLabel(role)}</option>
                ))}
              </select>
            </label>
            <label>
              Filtered jobs
              <input value={`${filteredTelegramJobs.length} of ${telegramState.jobs.length}`} readOnly />
            </label>
          </div>

          {telegramGraphRows.length > 0 && (
            <div className="admin-bar-list" aria-label="Telegram role insight graph">
              {telegramGraphRows.map((row) => (
                <article className="admin-graph-row" key={row.label}>
                  <div className="admin-graph-copy">
                    <strong>{row.label}</strong>
                    <span>{row.detail}</span>
                  </div>
                  <div className="admin-graph-track" aria-label={`${row.label} ${row.score}%`}>
                    <span style={{ width: `${Math.min(100, row.score)}%` }}></span>
                  </div>
                  <strong className="admin-graph-score">{Math.round(row.score)}%</strong>
                </article>
              ))}
            </div>
          )}

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

            {filteredTelegramJobs.slice(0, 12).map((job) => (
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

          {!telegramState.isLoading && !telegramState.error && filteredTelegramJobs.length === 0 && (
            <div className="admin-empty">No current Telegram jobs are available from the feed yet.</div>
          )}
        </section>
      )}
    </section>
  )
}

export default Admin
