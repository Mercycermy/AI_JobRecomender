import { useEffect, useState } from 'react'
import {
  fetchTelegramJobs,
  loadStoredAnalysis,
  loadStoredProfile,
  loadStoredQuizHistory,
  loadStoredQuizProgress,
  loadStoredRecommendations,
} from '../api/recommend.js'
import {
  fallbackQuestions,
  jobRecommendations as fallbackJobRecommendations,
  learningResources as fallbackLearningResources,
  resumeTips as fallbackResumeTips,
} from '../data/mockData.js'

const adminTabs = ['Overview', 'Profile', 'Matching', 'Learning', 'Resume', 'Telegram']
const profilePages = ['Quiz Intake', 'Match Graph', 'Completion Detail', 'Quiz Prompts']
const ADMIN_QUIZ_PROMPTS_STORAGE_KEY = 'adminQuizPrompts'

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

function loadCachedResumeTips() {
  if (typeof window === 'undefined') {
    return null
  }

  try {
    const raw = sessionStorage.getItem('resumeTipsCoaching')
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
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

function groupFallbackResources(resources) {
  const groups = new Map()

  resources.forEach((resource) => {
    const skill = resource.skill || 'Recommended'
    if (!groups.has(skill)) {
      groups.set(skill, { skill, resources: [] })
    }
    groups.get(skill).resources.push(resource)
  })

  return [...groups.values()]
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

function getJobTitle(job) {
  return job.title || job.job_title || 'Recommended role'
}

function getJobCompany(job) {
  return job.company || job.source || job.source_channel || formatLabel(job.category, 'Open role')
}

function getJobCategory(job) {
  return formatLabel(job.category || job.role_category)
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
  return gap.skill || formatLabel(gap.skill_id, 'Skill gap')
}

function getGapPriority(gap) {
  const value = Number(gap.priority ?? gap.gap_score ?? gap.score)
  if (!Number.isFinite(value)) {
    return null
  }

  return value <= 1 ? Math.round(value * 100) : Math.round(value)
}

function getResumeSectionCount(coaching) {
  return coaching?.tips?.length || fallbackResumeTips.length
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
  const targetRole = profile?.target_role || profile?.top_category || profile?.category || profile?.detected_role
  const hasExperience = Boolean(profile?.experience_level || profile?.experience)
  const hasLocation = Boolean(profile?.location)
  const hasEvidence = Boolean(
    evidence.experience_years !== null && evidence.experience_years !== undefined ||
      evidence.has_projects ||
      evidence.portfolio_url,
  )

  return [
    {
      label: 'Skills mapped',
      value: skills.length ? `${skills.length} skills` : 'Missing',
      score: Math.min(100, Math.round((skills.length / 6) * 100)),
    },
    {
      label: 'Target role',
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
  const estimated = Number(progress?.estimated_total ?? (answered ? Math.max(answered, 12) : fallbackQuestions.length))
  const percent = Number(progress?.percent ?? (estimated ? (answered / estimated) * 100 : 0))
  const confidence = progress?.confidence ?? profile?.confidence

  return {
    answered: Number.isFinite(answered) ? answered : 0,
    estimated: Number.isFinite(estimated) && estimated > 0 ? estimated : fallbackQuestions.length,
    percent: Number.isFinite(percent) ? Math.min(100, Math.round(percent)) : 0,
    confidence,
    detectedDomain: progress?.detected_domain || profile?.detected_domain,
    detectedRole: progress?.detected_role || profile?.detected_role || profile?.target_role,
    difficulty: progress?.difficulty_reached || profile?.difficulty_reached || 'Not reached',
    performanceCounts: progress?.performance_counts || profile?.performance_counts || {},
  }
}

function normalizePrompt(question, index) {
  return {
    id: question.id || `prompt-${index + 1}`,
    stem: question.stem || question.text || '',
    options: Array.isArray(question.options) ? question.options.map(String) : [],
    status: 'Live',
    updated: 'Local draft',
  }
}

function getDefaultQuizPrompts() {
  return fallbackQuestions.map((question, index) => normalizePrompt(question, index))
}

function normalizeStoredPrompt(prompt, index) {
  const source = prompt || {}
  const basePrompt = normalizePrompt(source, index)

  return {
    ...basePrompt,
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

function buildMatchGraphRows(attempts, fallbackJobs) {
  const rows = new Map()
  const sourceAttempts = attempts.length
    ? attempts
    : [{ id: 'current-matches', jobs: fallbackJobs }]

  sourceAttempts.forEach((attempt) => {
    getAttemptJobs(attempt).forEach((job) => {
      const title = getJobTitle(job)
      const score = getJobMatch(job)

      if (!title || score === null) {
        return
      }

      const current = rows.get(title) || {
        title,
        category: getJobCategory(job),
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

function Admin() {
  const [activeTab, setActiveTab] = useState(adminTabs[0])
  const [activeProfilePage, setActiveProfilePage] = useState(profilePages[0])
  const [jobSearch, setJobSearch] = useState('')
  const [quizPrompts, setQuizPrompts] = useState(loadAdminQuizPrompts)
  const [editingPromptId, setEditingPromptId] = useState('')
  const [promptDraft, setPromptDraft] = useState({ stem: '', optionsText: '' })
  const [telegramState, setTelegramState] = useState({
    error: '',
    isLoading: true,
    jobs: [],
    updatedAt: '',
  })

  const profile = loadStoredProfile()
  const recommendations = loadStoredRecommendations() || []
  const analysis = loadStoredAnalysis()
  const quizHistory = loadStoredQuizHistory()
  const quizProgress = loadStoredQuizProgress()
  const resumeCoaching = loadCachedResumeTips()

  const profileSkills = getProfileSkills(profile)
  const profileFillItems = getProfileFillItems(profile, profileSkills)
  const filledProfileFields = profileFillItems.filter((item) => item.score >= 100).length
  const quizSummary = getQuizSummary(profile, quizProgress)
  const visibleRecommendations = recommendations.length
    ? recommendations
    : fallbackJobRecommendations
  const recommendationSource = recommendations.length ? 'Current session' : 'Demo catalog'
  const averageMatch = getAverageMatch(visibleRecommendations)
  const gaps = analysis?.gaps || []
  const resourceGroups = analysis?.resources?.length
    ? analysis.resources
    : groupFallbackResources(fallbackLearningResources)
  const resources = flattenResourceGroups(resourceGroups)
  const topMissingSkills = uniqueItems(visibleRecommendations.flatMap(getMissingSkills)).slice(0, 6)
  const topMatchedJobs = getTopMatchedJobs(visibleRecommendations)
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
      role: summary.detectedRole || attemptProfile.target_role || attemptProfile.top_category,
      confidence: summary.confidence,
      bestJob,
      jobs: jobs.length,
    }
  })
  const totalQuizAnswers = quizAttemptSummaries.reduce((total, attempt) => total + attempt.answered, 0)
  const profilesWithSkills = quizAttemptSummaries.filter((attempt) => attempt.skills > 0).length

  const filteredJobs = visibleRecommendations.filter((job) =>
    `${getJobTitle(job)} ${getJobCompany(job)} ${getJobCategory(job)}`
      .toLowerCase()
      .includes(jobSearch.toLowerCase()),
  )

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
      value: profileSkills.length ? `${profileSkills.length} skills` : 'Not started',
      status: profileSkills.length ? 'Ready' : 'Pending',
    },
    {
      label: 'Matches',
      value: recommendations.length ? `${recommendations.length} roles` : `${visibleRecommendations.length} demo`,
      status: recommendations.length ? 'Current' : 'Demo',
    },
    {
      label: 'Skill gaps',
      value: gaps.length ? `${gaps.length} active` : 'Awaiting analysis',
      status: gaps.length ? 'Ready' : 'Pending',
    },
    {
      label: 'Learning',
      value: `${resources.length} resources`,
      status: analysis?.resources?.length ? 'Current' : 'Catalog',
    },
    {
      label: 'Resume',
      value: `${getResumeSectionCount(resumeCoaching)} sections`,
      status: resumeCoaching ? 'Personalized' : 'Template',
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
      status: profileSkills.length ? 'Ready' : 'Pending',
      detail: 'Feeds the canonical skill profile used by every downstream recommendation feature.',
    },
    {
      title: 'Job recommendations',
      route: '/results',
      status: recommendations.length ? 'Current' : 'Demo',
      detail: 'Uses the same ranked roles, match scores, missing skills, and score factors shown to users.',
    },
    {
      title: 'Skill gap analysis',
      route: '/results/gap/:jobId',
      status: gaps.length ? 'Ready' : 'Pending',
      detail: 'Tracks the highest-impact missing skills from the active recommendation set.',
    },
    {
      title: 'Learning resources',
      route: '/results/resources',
      status: analysis?.resources?.length ? 'Current' : 'Catalog',
      detail: 'Audits resources by the same skill groups used in the learner-facing study map.',
    },
    {
      title: 'Resume coaching and builder',
      route: '/results/resume, /resume-builder',
      status: resumeCoaching ? 'Personalized' : 'Template',
      detail: 'Mirrors resume tips, upload readiness, and generated resume coverage.',
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
      label: 'Matched jobs',
      value: `${visibleRecommendations.length} roles`,
      score: Math.min(100, Math.round((visibleRecommendations.length / 10) * 100)),
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
      label: 'Best match',
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
      detail: topGap ? `${getGapPriority(topGap) ?? '--'} priority` : 'Based on current matches',
    },
    {
      label: 'Quiz confidence',
      value: formatPercent(quizSummary.confidence),
      detail: formatLabel(quizSummary.difficulty),
    },
  ]
  const startPromptEdit = (prompt) => {
    setEditingPromptId(prompt.id)
    setPromptDraft({
      stem: prompt.stem,
      optionsText: prompt.options.join('\n'),
    })
  }
  const cancelPromptEdit = () => {
    setEditingPromptId('')
    setPromptDraft({ stem: '', optionsText: '' })
  }
  const updatePrompt = () => {
    const normalizedOptions = promptDraft.optionsText
      .split('\n')
      .map((option) => option.trim())
      .filter(Boolean)

    setQuizPrompts((prompts) => {
      const nextPrompts = prompts.map((prompt) =>
        prompt.id === editingPromptId
          ? {
              ...prompt,
              stem: promptDraft.stem.trim() || prompt.stem,
              options: normalizedOptions.length ? normalizedOptions : prompt.options,
              updated: 'Saved locally',
            }
          : prompt,
      )

      saveAdminQuizPrompts(nextPrompts)
      return nextPrompts
    })
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

  return (
    <section className="admin-page">
      <div className="admin-header">
        <div>
          <p className="eyebrow">Admin command center</p>
          <h1>Feature operations for the active career workflow.</h1>
          <p>
            Admin now follows the same user-facing flow: profile, matches, gaps,
            learning, resume, and current jobs. Use the direct path <code>/admin</code>.
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
                  <strong>{profileSkills.length ? 'Active' : 'Pending'}</strong>
                </div>
                <div>
                  <span>Matching engine</span>
                  <strong>{visibleRecommendations.length} roles available</strong>
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
                  <span>Profiles with skills</span>
                  <strong>{profilesWithSkills}</strong>
                  <small>{profileSkills.length} current skills</small>
                </article>
                <article>
                  <span>Current source</span>
                  <strong>{formatLabel(profile?.source, profile ? 'Manual' : 'Pending')}</strong>
                  <small>{recommendationSource}</small>
                </article>
              </div>

              {quizAttemptSummaries.length ? (
                <div className="admin-table" role="table" aria-label="Profile intake for all taken quizzes">
                  <div className="admin-table-row admin-table-head" role="row">
                    <span>Quiz</span>
                    <span>Role</span>
                    <span>Answers</span>
                    <span>Skills</span>
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
                <span>Most matched jobs across quizzes</span>
                <strong>{matchGraphRows.length} roles</strong>
              </div>

              <div className="admin-match-graph" aria-label="Most matched jobs graph">
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
                  No match scores are available yet. Run quizzes or recommendations to populate this graph.
                </div>
              )}
            </div>
          )}

          {activeProfilePage === 'Completion Detail' && (
            <div className="admin-profile-dashboard">
              <div className="admin-dashboard-grid">
                <section className="admin-dashboard-card">
                  <div className="admin-panel-heading">
                    <span>Most filled quiz or jobs</span>
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
                <strong>{quizPrompts.length} prompts</strong>
              </div>

              <div className="question-review-list">
                {quizPrompts.map((prompt) => {
                  const isEditing = editingPromptId === prompt.id

                  return (
                    <article className="question-review-card" key={prompt.id}>
                      {isEditing ? (
                        <div className="admin-prompt-editor">
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
                          <span className="chip chip-blue">{prompt.status}</span>
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

              {!quizPrompts.length && (
                <div className="admin-empty">All local quiz prompts have been removed from this admin view.</div>
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
                placeholder="Role, company, category"
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
              <span>Role</span>
              <span>Category</span>
              <span>Match</span>
              <span>Gaps</span>
              <span>Evidence</span>
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
                  <span>{getJobCategory(job)}</span>
                  <span>
                    {match === null ? (
                      <span className={statusClass('Pending')}>Pending</span>
                    ) : (
                      <span className={`match-badge ${getMatchClass(match)}`}>{match}%</span>
                    )}
                  </span>
                  <span>{missingSkills.length ? `${missingSkills.length} skills` : 'None'}</span>
                  <span>{matchedSkills.slice(0, 2).map(formatLabel).join(', ') || 'Scored factors'}</span>
                </div>
              )
            })}
          </div>
        </section>
      )}

      {activeTab === 'Learning' && (
        <div className="admin-section-stack">
          <section className="admin-panel">
            <div className="admin-panel-heading">
              <span>Skill gap analysis</span>
              <strong>{gaps.length ? `${gaps.length} active gaps` : 'Awaiting matches'}</strong>
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
              <strong>{analysis?.resources?.length ? 'Personalized' : 'Catalog fallback'}</strong>
            </div>

            <div className="resource-admin-grid">
              {resources.slice(0, 6).map((resource) => (
                <article
                  className="resource-admin-card"
                  key={`${resource.skill}-${resource.resource_id || resource.title}`}
                >
                  <div>
                    <span className={statusClass(resource.gap_priority || 'Verified')}>
                      {resource.gap_priority || resource.level || 'Verified'}
                    </span>
                    <h2>{resource.title}</h2>
                    <p>
                      {resource.platform} / {formatLabel(resource.skill)}
                    </p>
                  </div>
                  <strong>{resource.recommendation_score ?? resource.hours ?? '--'}</strong>
                </article>
              ))}
            </div>
          </section>
        </div>
      )}

      {activeTab === 'Resume' && (
        <section className="admin-panel">
          <div className="admin-panel-heading">
            <span>Resume workflow</span>
            <strong>{resumeCoaching ? 'Personalized coaching cached' : 'Template guidance'}</strong>
          </div>

          <div className="admin-feature-grid">
            <article className="admin-feature-card">
              <div className="admin-card-kicker">
                <span>/results/resume</span>
                <strong className={statusClass(resumeCoaching ? 'Personalized' : 'Template')}>
                  {resumeCoaching ? 'Personalized' : 'Template'}
                </strong>
              </div>
              <h2>Resume tips</h2>
              <p>
                {resumeCoaching?.summary ||
                  'Uses profile and gap context to produce role-specific coaching.'}
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

          <div className="tips-grid">
            {(resumeCoaching?.tips?.length ? resumeCoaching.tips : fallbackResumeTips).map((section) => (
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
              <span>Role</span>
              <span>Channel</span>
              <span>Experience</span>
              <span>Skills</span>
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
