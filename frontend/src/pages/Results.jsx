import { useEffect, useMemo, useState } from 'react'
import {
  categories,
  experienceLevels,
} from '../data/mockData.js'
import FlowProgress from '../components/FlowProgress.jsx'
import {
  clearStoredRecommendations,
  fetchAnalysis,
  fetchRecommendations,
  fetchResumeTips,
  fetchTelegramJobMatches,
  loadStoredAnalysis,
  loadStoredProfile,
  loadStoredRecommendations,
  loadStoredRawRecommendations,
  loadStoredSessionId,
  persistAnalysis,
  persistRecommendationSession,
  recordFlowEvent,
} from '../api/recommend.js'
import LearningResources from './LearningResources.jsx'
import ResumeTips from './ResumeTips.jsx'
import SkillGap from './SkillGap.jsx'
import { getProfileRoleFilter } from '../utils/roleFilters.js'

const tabs = ['Skill Gap', 'Learning Resources', 'Resume Tips']
const matchFactors = [
  ['skill_fit', 'Skills'],
  ['semantic_similarity', 'Semantic'],
  ['experience_match', 'Experience'],
  ['role_match', 'Role'],
  ['location_match', 'Location'],
  ['freshness', 'Freshness'],
]

function getBadgeClass(match) {
  if (match >= 75) {
    return 'match-high'
  }

  if (match >= 50) {
    return 'match-mid'
  }

  return 'match-low'
}

function formatCategoryLabel(slug) {
  if (!slug) {
    return 'Unknown'
  }
  return slug
    .split('-')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function loadCachedResumeTips() {
  try {
    const raw = sessionStorage.getItem('resumeTipsCoaching')
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function uniqueItems(values = []) {
  return [...new Set(values.filter(Boolean).map((value) => String(value)))]
}

function getProfileSkills(profile) {
  return uniqueItems(
    profile?.skill_ids ||
      profile?.detected_skills ||
      profile?.skills ||
      Object.keys(profile?.skill_scores || {}),
  )
}

function getAverageSkillScore(profile) {
  const scores = Object.values(profile?.skill_scores || {})
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value))

  if (!scores.length) {
    return null
  }

  const normalizedScores = scores.map((value) => (value <= 1 ? value * 100 : value))
  const average =
    normalizedScores.reduce((total, value) => total + value, 0) / normalizedScores.length

  return Math.round(average)
}

function getTargetRole(profile) {
  return formatCategoryLabel(
    profile?.target_role ||
      profile?.top_category ||
      profile?.category ||
      profile?.detected_role ||
      '',
  )
}

function sourceForProfile(profile) {
  return profile?.source === 'adaptive_quiz' || profile?.source === 'quiz'
    ? 'quiz'
    : 'manual'
}

function buildFallbackSummary(profile, topJob, topGap) {
  if (!profile || !topJob) {
    return 'Finish the quiz or manual skill input to generate your match dashboard, current jobs, gap reasons, learning resources, and resume actions.'
  }

  const target = getTargetRole(profile)
  const matched = uniqueItems(topJob.matchedSkillNames || topJob.skills || []).slice(0, 3)
  const missing = uniqueItems(topJob.missingSkillNames || topJob.missing_skills || []).slice(0, 2)
  const matchedText = matched.length ? `Your strongest signals are ${matched.join(', ')}.` : 'Your strongest signals are still being calibrated.'
  const missingText = missing.length || topGap
    ? `To win more roles in the current market, close ${[...missing, topGap?.skill].filter(Boolean).slice(0, 2).join(', ')} first.`
    : 'Keep applying to high-fit roles while building proof projects around your matched skills.'

  return `${target} is the clearest direction from your input, with ${topJob.title} as the highest current fit. ${matchedText} ${missingText}`
}

function Results({ navigate }) {
  const [category, setCategory] = useState('All categories')
  const [experience, setExperience] = useState('All experience')
  const [activeTab, setActiveTab] = useState(tabs[0])
  const [profile, setProfile] = useState(() => loadStoredProfile())

  const [analysis, setAnalysis] = useState(() => loadStoredAnalysis())
  const [isAnalysisLoading, setIsAnalysisLoading] = useState(() => {
    const profile = loadStoredProfile()
    const rawRecs = loadStoredRawRecommendations() || loadStoredRecommendations()
    return Boolean(!loadStoredAnalysis() && profile && rawRecs?.length)
  })
  const [analysisError, setAnalysisError] = useState(null)
  const [analysisTick, setAnalysisTick] = useState(0)

  const [resumeTipsData, setResumeTipsData] = useState(() => loadCachedResumeTips())
  const [isResumeTipsLoading, setIsResumeTipsLoading] = useState(() =>
    Boolean(loadStoredProfile() && !loadCachedResumeTips()),
  )
  const [resumeTipsError, setResumeTipsError] = useState(null)

  const [jobRecommendations, setJobRecommendations] = useState(() => {
    const stored = loadStoredRecommendations()
    if (stored?.length) {
      return stored
    }
    return []
  })
  const [jobsError, setJobsError] = useState(null)
  const [currentJobState, setCurrentJobState] = useState({
    error: null,
    isLoading: Boolean(loadStoredProfile()),
    jobs: [],
  })

  useEffect(() => {
    let isMounted = true
    const profile = loadStoredProfile()

    if (!profile) {
      return () => {
        isMounted = false
      }
    }

    fetchRecommendations(profile)
      .then((result) => {
        if (!isMounted) {
          return
        }
        setJobRecommendations(result.jobs)
        setProfile(result.profile)
        persistRecommendationSession(result.profile, result.jobs, result.rawRecs)
        setJobsError(null)
      })
      .catch((err) => {
        if (!isMounted) {
          return
        }
        setJobsError(err.message || 'Failed to load recommendations')
        setJobRecommendations([])
      })

    return () => {
      isMounted = false
    }
  }, [])

  useEffect(() => {
    let isMounted = true
    if (!profile) {
      return () => {
        isMounted = false
      }
    }

    fetchTelegramJobMatches(profile, { role: getProfileRoleFilter(profile), limit: 6 })
      .then((payload) => {
        if (!isMounted) {
          return
        }
        setCurrentJobState({
          error: null,
          isLoading: false,
          jobs: payload.jobs || [],
        })
      })
      .catch((err) => {
        if (!isMounted) {
          return
        }
        setCurrentJobState({
          error: err.message || 'Could not load current Telegram matches.',
          isLoading: false,
          jobs: [],
        })
      })

    return () => {
      isMounted = false
    }
  }, [profile])

  useEffect(() => {
    let isMounted = true
    const profile = loadStoredProfile()
    const rawRecs = loadStoredRawRecommendations() || loadStoredRecommendations()
    const sessionId = loadStoredSessionId()

    if (!profile || !rawRecs?.length) {
      const retry = window.setTimeout(() => {
        if (isMounted) {
          setAnalysisTick((value) => value + 1)
        }
      }, 200)
      return () => {
        isMounted = false
        window.clearTimeout(retry)
      }
    }

    fetchAnalysis(sessionId, profile, rawRecs)
      .then((payload) => {
        if (!isMounted) {
          return
        }
        setAnalysis(payload)
        persistAnalysis(payload)
        setIsAnalysisLoading(false)
      })
      .catch((err) => {
        if (!isMounted) {
          return
        }
        setAnalysisError(err.message || 'Failed to load analysis')
        setIsAnalysisLoading(false)
      })

    return () => {
      isMounted = false
    }
  }, [jobRecommendations, analysisTick])

  useEffect(() => {
    let isMounted = true
    const profile = loadStoredProfile()
    const sessionId = loadStoredSessionId()
    const rawRecs = loadStoredRawRecommendations() || loadStoredRecommendations()
    if (!profile) {
      return
    }

    // Only fetch if not already loaded
    if (resumeTipsData) {
      return
    }

    fetchResumeTips(sessionId, profile, rawRecs)
      .then((payload) => {
        if (!isMounted) {
          return
        }
        setResumeTipsData(payload)
        sessionStorage.setItem('resumeTipsCoaching', JSON.stringify(payload))
        setIsResumeTipsLoading(false)
      })
      .catch((err) => {
        if (!isMounted) {
          return
        }
        setResumeTipsError(err.message || 'Failed to load resume tips')
        setIsResumeTipsLoading(false)
      })

    return () => {
      isMounted = false
    }
  }, [analysis?.gaps?.length, resumeTipsData])

  const categoryOptions = useMemo(() => {
    const fromJobs = [...new Set(jobRecommendations.map((j) => j.category).filter(Boolean))]
    return fromJobs.length ? fromJobs.map(formatCategoryLabel) : categories
  }, [jobRecommendations])

  const filteredJobs = useMemo(
    () =>
      jobRecommendations.filter((job) => {
        const jobCategoryLabel = formatCategoryLabel(job.category)
        const categoryMatches =
          category === 'All categories' || job.category === category || jobCategoryLabel === category
        const experienceMatches =
          experience === 'All experience' || job.experience === experience

        return categoryMatches && experienceMatches
      }),
    [category, experience, jobRecommendations],
  )

  const readinessScore = Math.round(
    jobRecommendations.reduce((total, job) => total + (job.readiness ?? job.match ?? 0), 0) /
      Math.max(jobRecommendations.length, 1),
  )
  const profileSkills = useMemo(() => getProfileSkills(profile), [profile])
  const averageSkillScore = useMemo(() => getAverageSkillScore(profile), [profile])
  const sortedGaps = useMemo(
    () => [...(analysis?.gaps || [])].sort((left, right) => right.priority - left.priority),
    [analysis?.gaps],
  )
  const topGap = sortedGaps[0]
  const topJob = filteredJobs[0]
  const otherJobs = filteredJobs.slice(1)
  const skillLevelLabel = averageSkillScore !== null
    ? `${averageSkillScore}%`
    : profileSkills.length
      ? `${profileSkills.length} skills`
      : 'Not mapped'
  const nextLearningAction =
    topGap?.skill || topJob?.missingSkillNames?.[0] || topJob?.missing_skills?.[0] || 'Review gaps'
  const resumeAction = resumeTipsData?.tips?.length ? 'Tips ready' : profile ? 'Review resume' : 'Add profile'
  const marketSummary = analysis?.summary || buildFallbackSummary(profile, jobRecommendations[0], topGap)

  const handleStartNew = () => {
    clearStoredRecommendations()
    navigate('/', { replace: true })
  }

  const trackJobView = (job, surface = 'results') => {
    if (!job) {
      return
    }
    recordFlowEvent({
      event_type: 'job_viewed',
      source: sourceForProfile(profile),
      session_id: loadStoredSessionId() || profile?.session_id,
      role: profile?.target_role || profile?.top_category || profile?.detected_role,
      job_id: job.id || job.job_id,
      job_title: job.title || job.job_title,
      match_score: job.match ?? job.match_score,
      matched_skills: job.matchedSkillNames || job.matched_skill_names || job.skills || [],
      gap_skills: job.missingSkillNames || job.missing_skill_names || job.missing_skills || [],
      summary: surface,
    }).catch(() => {})
  }

  const lowerPanel = {
    'Skill Gap': (
      <SkillGap
        gaps={analysis?.gaps}
        isLoading={isAnalysisLoading}
        error={analysisError}
      />
    ),
    'Learning Resources': (
      <LearningResources
        resources={analysis?.resources}
        isLoading={isAnalysisLoading}
        error={analysisError}
      />
    ),
    'Resume Tips': (
      <ResumeTips
        coaching={resumeTipsData}
        isLoading={isResumeTipsLoading}
        error={resumeTipsError}
      />
    ),
  }[activeTab]

  return (
    <section className="results-page">
      <div className="results-header">
        <div>
          <p className="eyebrow">Based on your assessment</p>
          <h1>Your Recommendations</h1>
        </div>
        <button
          className="button button-ghost"
          type="button"
          onClick={handleStartNew}
        >
          Start New Assessment
        </button>
      </div>

      <FlowProgress
        currentPath="/results"
        profile={profile}
        recommendations={jobRecommendations}
        analysis={analysis}
      />

      <div className="dashboard-summary">
        <div
          className="readiness-ring"
          style={{ '--score': `${readinessScore}%` }}
          aria-label={`Overall readiness score ${readinessScore}%`}
        >
          <strong>{readinessScore}%</strong>
          <span>Overall readiness</span>
        </div>

        <div className="filter-bar">
          <label>
            Category
            <select value={category} onChange={(event) => setCategory(event.target.value)}>
              <option>All categories</option>
              {categoryOptions.map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </label>

          <label>
            Experience
            <select value={experience} onChange={(event) => setExperience(event.target.value)}>
              <option>All experience</option>
              {experienceLevels.map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <div className="profile-summary-grid" aria-label="Recommendation summary">
        <article>
          <span>Skill level</span>
          <strong>{skillLevelLabel}</strong>
          <p>{profileSkills.length ? `${profileSkills.length} mapped skills` : 'Complete an assessment'}</p>
        </article>
        <article>
          <span>Target role</span>
          <strong>{getTargetRole(profile)}</strong>
          <p>{profile?.location || 'Remote-friendly'}</p>
        </article>
        <article>
          <span>Next learning action</span>
          <strong>{nextLearningAction}</strong>
          <a href="/results/resources">Open resources</a>
        </article>
        <article>
          <span>Resume action</span>
          <strong>{resumeAction}</strong>
          <a href="/results/resume">Review resume</a>
          <a href="/resume-builder">Build resume</a>
        </article>
        <article>
          <span>Current jobs</span>
          <strong>Telegram feed</strong>
          <a href="/telegram-jobs">Open feed</a>
        </article>
      </div>

      {jobsError && (
        <div className="error-container" style={{ textAlign: 'center', padding: '16px 20px', marginBottom: '16px', background: 'rgba(232, 93, 117, 0.08)', borderRadius: '8px', border: '1px solid var(--coral)' }}>
          <p style={{ color: 'var(--coral)', fontWeight: 'bold' }}>{jobsError}</p>
        </div>
      )}

      <section className="analysis-summary-panel" aria-label="AI user summary">
        <div>
          <p className="eyebrow">{analysis?.is_ai ? 'AI market summary' : 'Market summary'}</p>
          <h2>How your input reads against collected jobs</h2>
        </div>
        <p>{marketSummary}</p>
      </section>

      {topJob && (
        <article className="job-card is-top-match">
          <div className="job-card-top">
            <div>
              <span className="chip chip-blue">Highest match</span>
              <h2><strong>{topJob.title}</strong></h2>
              <p>{topJob.company}</p>
            </div>
            <span className={`match-badge ${getBadgeClass(topJob.match)}`}>
              {topJob.match}% match
            </span>
          </div>

          <div className="skill-pills">
            {uniqueItems(topJob.matchedSkillNames || topJob.skills || []).slice(0, 6).map((skill) => (
              <span className="chip chip-blue" key={skill}>{skill}</span>
            ))}
          </div>

          {uniqueItems(topJob.missingSkillNames || topJob.missing_skills || []).length > 0 && (
            <div className="missing-skill-strip">
              <span>Gap to close</span>
              <div className="skill-pills">
                {uniqueItems(topJob.missingSkillNames || topJob.missing_skills || []).slice(0, 5).map((skill) => (
                  <span className="chip chip-coral" key={`${topJob.id}-${skill}`}>{skill}</span>
                ))}
              </div>
            </div>
          )}

          {topJob.explanation && <p className="match-explanation">{topJob.explanation}</p>}

          <details className="match-details" open>
            <summary>Why this is the best fit</summary>
            <div className="match-breakdown-grid">
              {matchFactors.map(([key, label]) => (
                <div key={key}>
                  <span>{label}</span>
                  <strong>{Math.round(topJob.breakdown?.[key] ?? 0)}%</strong>
                  <small>{topJob.scoreWeights?.[key] ?? 0}% weight</small>
                </div>
              ))}
            </div>
          </details>

          <div className="job-card-actions">
            <a className="details-link" href={`/results/gap/${topJob.id}`} onClick={() => trackJobView(topJob, 'gap_details')}>
              See gap reason
            </a>
            <a className="details-link" href="/results/resources" onClick={() => trackJobView(topJob, 'learning')}>
              Learning resources
            </a>
            <a className="details-link" href="/resume-builder" onClick={() => trackJobView(topJob, 'resume_builder')}>
              Build resume
            </a>
          </div>
        </article>
      )}

      <div className="job-grid compact-job-grid">
        {otherJobs.map((job) => {
          const missingSkills = uniqueItems(job.missingSkillNames || job.missing_skills || [])
          const shownSkills = uniqueItems(job.matchedSkillNames || job.skills || missingSkills)

          return (
            <article className="job-card job-card-compact" key={job.id}>
              <div className="job-card-top">
                <div>
                  <h2>{job.title}</h2>
                  <p>{shownSkills.slice(0, 4).join(', ') || job.company}</p>
                </div>
                <span className={`match-badge ${getBadgeClass(job.match)}`}>
                  {job.match}% match
                </span>
              </div>

              <div className="skill-pills">
                {shownSkills.slice(0, 5).map((skill) => (
                  <span className="chip chip-blue" key={`${job.id}-${skill}`}>{skill}</span>
                ))}
              </div>

              {missingSkills.length > 0 && (
                <details className="match-details">
                  <summary>Gap and why</summary>
                  <div className="skill-pills">
                    {missingSkills.slice(0, 5).map((skill) => (
                      <span className="chip chip-coral" key={`${job.id}-gap-${skill}`}>{skill}</span>
                    ))}
                  </div>
                  {job.explanation && <p className="match-explanation">{job.explanation}</p>}
                </details>
              )}

              <div className="job-card-actions">
                <a className="details-link" href={`/results/gap/${job.id}`} onClick={() => trackJobView(job, 'gap_details')}>
                  Gap
                </a>
                <a className="details-link" href="/resume-builder" onClick={() => trackJobView(job, 'resume_builder')}>
                  Resume
                </a>
              </div>
            </article>
          )
        })}
      </div>

      {filteredJobs.length === 0 && (
        <div className="empty-state">
          {profile
            ? 'No jobs match those filters yet. Try a broader category or experience level.'
            : 'Start with the quiz or manual skill input to generate a fresh recommendation dashboard.'}
        </div>
      )}

      <section className="current-jobs-panel">
        <div className="admin-panel-heading">
          <span>Current Telegram matches</span>
          <strong>{currentJobState.isLoading ? 'Loading' : `${currentJobState.jobs.length} active jobs`}</strong>
        </div>
        {currentJobState.error && <p className="form-error">{currentJobState.error}</p>}
        <div className="current-job-list">
          {currentJobState.jobs.slice(0, 5).map((job) => {
            const matchedSkills = uniqueItems(job.matched_skill_names || job.required_skill_names || [])
            return (
              <article className="current-job-row" key={job.job_id}>
                <div>
                  <strong>{job.job_title}</strong>
                  <span>{matchedSkills.slice(0, 4).join(', ') || job.category || 'Current opening'}</span>
                </div>
                <span className={`match-badge ${getBadgeClass(job.match_score || 0)}`}>
                  {Math.round(job.match_score || 0)}%
                </span>
                <a
                  href={job.apply_link || '/telegram-jobs'}
                  target={job.apply_link ? '_blank' : undefined}
                  rel={job.apply_link ? 'noreferrer' : undefined}
                  onClick={() => trackJobView(job, 'telegram_current_job')}
                >
                  View
                </a>
              </article>
            )
          })}
        </div>
        {!currentJobState.isLoading && currentJobState.jobs.length === 0 && (
          <div className="empty-state">No active Telegram jobs matched this profile yet.</div>
        )}
        <a className="button button-ghost current-jobs-link" href="/telegram-jobs">
          Open Telegram job feed
        </a>
      </section>

      <div className="bottom-tabs" role="tablist" aria-label="Recommendation panels">
        {tabs.map((tab) => (
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

      <div className="tab-panel">{lowerPanel}</div>
    </section>
  )
}

export default Results
