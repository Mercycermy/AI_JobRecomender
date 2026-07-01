import { useEffect, useState } from 'react'
import {
  fetchTelegramJobs,
  loadStoredAnalysis,
  loadStoredProfile,
  loadStoredRawRecommendations,
  loadStoredRecommendations,
  loadStoredSessionId,
} from '../api/recommend.js'
import {
  fallbackQuestions,
  jobRecommendations as fallbackJobRecommendations,
  learningResources as fallbackLearningResources,
  resumeTips as fallbackResumeTips,
} from '../data/mockData.js'

const adminTabs = ['Overview', 'Profile', 'Matching', 'Learning', 'Resume', 'Telegram']

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

function getSkillLevel(profile, skill) {
  const levels = profile?.skill_levels || profile?.skillScores || {}
  const value = levels[skill] ?? profile?.skill_scores?.[skill]

  if (value === null || value === undefined || value === '') {
    return 'Mapped'
  }

  if (typeof value === 'number') {
    return value <= 1 ? `${Math.round(value * 100)}%` : `${Math.round(value)}%`
  }

  return formatLabel(value)
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

function Admin() {
  const [activeTab, setActiveTab] = useState(adminTabs[0])
  const [jobSearch, setJobSearch] = useState('')
  const [telegramState, setTelegramState] = useState({
    error: '',
    isLoading: true,
    jobs: [],
    updatedAt: '',
  })

  const profile = loadStoredProfile()
  const recommendations = loadStoredRecommendations() || []
  const rawRecommendations = loadStoredRawRecommendations() || []
  const analysis = loadStoredAnalysis()
  const sessionId = loadStoredSessionId()
  const resumeCoaching = loadCachedResumeTips()

  const profileSkills = getProfileSkills(profile)
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
                <span>Active context</span>
                <strong>{profileSkills.length ? 'Profile loaded' : 'No profile'}</strong>
              </div>

              <div className="pipeline-list">
                <div>
                  <span>Profile source</span>
                  <strong>{formatLabel(profile?.source, profile ? 'Manual' : 'Pending')}</strong>
                </div>
                <div>
                  <span>Recommendation source</span>
                  <strong>{recommendationSource}</strong>
                </div>
                <div>
                  <span>Raw scoring payload</span>
                  <strong>{rawRecommendations.length ? `${rawRecommendations.length} rows` : 'Not cached'}</strong>
                </div>
                <div>
                  <span>Quiz session</span>
                  <strong>{sessionId || 'Not active'}</strong>
                </div>
              </div>
            </section>

            <section className="admin-panel">
              <div className="admin-panel-heading">
                <span>Coverage focus</span>
                <strong>{topMissingSkills.length ? `${topMissingSkills.length} skills` : 'Clear'}</strong>
              </div>

              {topMissingSkills.length ? (
                <div className="admin-skill-list">
                  {topMissingSkills.map((skill) => (
                    <span className="chip chip-coral" key={skill}>
                      {formatLabel(skill)}
                    </span>
                  ))}
                </div>
              ) : (
                <div className="admin-empty">No repeated missing skills are visible yet.</div>
              )}
            </section>
          </div>
        </div>
      )}

      {activeTab === 'Profile' && (
        <section className="admin-panel">
          <div className="admin-panel-heading">
            <span>Profile intake</span>
            <strong>{profileSkills.length ? `${profileSkills.length} mapped skills` : 'Not started'}</strong>
          </div>

          <div className="admin-inline-grid">
            <article>
              <span>Target role</span>
              <strong>{formatLabel(profile?.target_role || profile?.top_category || profile?.category)}</strong>
            </article>
            <article>
              <span>Experience</span>
              <strong>{formatLabel(profile?.experience_level || profile?.experience)}</strong>
            </article>
            <article>
              <span>Location</span>
              <strong>{formatLabel(profile?.location, 'Remote-friendly')}</strong>
            </article>
            <article>
              <span>Source</span>
              <strong>{formatLabel(profile?.source, profile ? 'Manual' : 'Pending')}</strong>
            </article>
          </div>

          {profileSkills.length ? (
            <div className="admin-profile-grid">
              {profileSkills.map((skill) => (
                <article className="admin-skill-row" key={skill}>
                  <strong>{formatLabel(skill)}</strong>
                  <span>{getSkillLevel(profile, skill)}</span>
                </article>
              ))}
            </div>
          ) : (
            <div className="admin-empty">
              Complete the quiz or manual profile first. The admin page will then reflect the same
              canonical profile used by recommendations, learning, and resume guidance.
            </div>
          )}

          <div className="admin-panel-divider"></div>

          <div className="admin-panel-heading">
            <span>Quiz prompt coverage</span>
            <strong>{fallbackQuestions.length} fallback prompts</strong>
          </div>

          <div className="question-review-list">
            {fallbackQuestions.slice(0, 4).map((question) => (
              <article className="question-review-card" key={question.id}>
                <div>
                  <span className="chip chip-blue">Assessment</span>
                  <h2>{question.stem}</h2>
                  <p>{question.options.slice(0, 2).join(' / ')}</p>
                </div>

                <div className="question-review-actions">
                  <span className={statusClass('Live')}>Live</span>
                </div>
              </article>
            ))}
          </div>
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
