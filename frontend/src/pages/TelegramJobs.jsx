import { useCallback, useEffect, useState } from 'react'

import FlowProgress from '../components/FlowProgress.jsx'
import {
  fetchTelegramJobMatches,
  fetchTelegramJobs,
  loadStoredProfile,
  loadStoredSessionId,
  recordFlowEvent,
} from '../api/recommend.js'
import { formatRoleFilterLabel, getProfileRoleFilter } from '../utils/roleFilters.js'

function getBadgeClass(match) {
  if (match >= 75) {
    return 'match-high'
  }
  if (match >= 50) {
    return 'match-mid'
  }
  return 'match-low'
}

function hasUsableProfile(profile) {
  const skills =
    profile?.skill_ids ||
    profile?.detected_skills ||
    profile?.skills ||
    Object.keys(profile?.skill_scores || {})

  return Boolean(profile && skills?.length)
}

function uniqueItems(values = []) {
  return [...new Set(values.filter(Boolean).map((value) => String(value)))]
}

function sourceForProfile(profile) {
  return profile?.source === 'adaptive_quiz' || profile?.source === 'quiz'
    ? 'quiz'
    : 'manual'
}

function TelegramJobs() {
  const [jobs, setJobs] = useState([])
  const [query, setQuery] = useState('')
  const [roleFilter, setRoleFilter] = useState(() => getProfileRoleFilter(loadStoredProfile()))
  const [roleOptions, setRoleOptions] = useState(() =>
    uniqueItems([getProfileRoleFilter(loadStoredProfile())]),
  )
  const [error, setError] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  const loadJobs = useCallback(async (search = '', role = undefined) => {
    setIsLoading(true)
    setError(null)
    try {
      const profile = loadStoredProfile()
      const personalized = hasUsableProfile(profile)
      const profileRole = getProfileRoleFilter(profile)
      const activeRole = role ?? profileRole
      const payload = personalized
        ? await fetchTelegramJobMatches(profile, { query: search, role: activeRole, limit: 80 })
        : await fetchTelegramJobs({ query: search, role: activeRole, limit: 80 })

      setJobs(payload.jobs || [])
      setRoleOptions((current) =>
        uniqueItems([
          profileRole,
          activeRole,
          ...current,
          ...(payload.jobs || []).map((job) => job.category || job.role),
        ]),
      )
    } catch (err) {
      setError(err.message || 'Could not load Telegram jobs.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    const initialRole = getProfileRoleFilter(loadStoredProfile())
    const timer = window.setTimeout(() => loadJobs('', initialRole), 0)
    return () => window.clearTimeout(timer)
  }, [loadJobs])

  const handleSearch = (event) => {
    event.preventDefault()
    loadJobs(query, roleFilter)
  }

  const handleRoleChange = (event) => {
    const nextRole = event.target.value
    setRoleFilter(nextRole)
    loadJobs(query, nextRole)
  }

  const trackJobView = (job) => {
    const profile = loadStoredProfile()
    recordFlowEvent({
      event_type: 'job_viewed',
      source: sourceForProfile(profile),
      session_id: loadStoredSessionId() || profile?.session_id,
      role: profile?.target_role || profile?.top_category || profile?.detected_role || job.category,
      job_id: job.job_id,
      job_title: job.job_title,
      match_score: job.match_score,
      matched_skills: job.matched_skill_names || job.required_skill_names || [],
      gap_skills: job.missing_skill_names || [],
      summary: 'telegram_feed',
    }).catch(() => {})
  }

  return (
    <section className="detail-page telegram-page">
      <div className="page-heading">
        <p className="eyebrow">Telegram jobs</p>
        <h1>Active jobs that are still open.</h1>
        <p>
          Search by job title or skill. If you finished the quiz or manual input,
          the feed is ranked against your current profile.
        </p>
      </div>

      <FlowProgress currentPath="/telegram-jobs" />

      <div className="telegram-feed-panel telegram-feed-panel-full">
        <form className="telegram-search" onSubmit={handleSearch}>
          <label className="field-group">
            <span>Job or skill</span>
            <input
              value={query}
              placeholder="React, accounting, driver, data..."
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          <label className="field-group">
            <span>Role</span>
            <select value={roleFilter} onChange={handleRoleChange}>
              <option value="">All roles</option>
              {roleOptions.map((role) => (
                <option value={role} key={role}>{formatRoleFilterLabel(role)}</option>
              ))}
            </select>
          </label>
          <button className="button button-ghost" type="submit" disabled={isLoading}>
            {isLoading ? 'Searching...' : 'Search'}
          </button>
        </form>

        {error && <p className="form-error">{error}</p>}

        <div className="telegram-job-list">
          {jobs.length > 0 ? (
            jobs.map((job) => {
              const matchScore = Number(job.match_score)
              const hasMatchScore = Number.isFinite(matchScore)
              const matchedSkills = job.matched_skill_names || []
              const missingSkills = job.missing_skill_names || []
              const displaySkills = matchedSkills.length
                ? matchedSkills
                : job.required_skill_names || []

              return (
                <article className="telegram-job-card" key={job.job_id}>
                  <div className="telegram-job-top">
                    <div>
                      <span className="chip chip-blue">{job.source_channel || job.source || 'Telegram'}</span>
                      <h2>{job.job_title}</h2>
                      <p>{job.company || job.category || 'Current opening'}</p>
                    </div>
                    <div className="telegram-job-status">
                      {hasMatchScore && (
                        <span className={`match-badge ${getBadgeClass(matchScore)}`}>
                          {Math.round(matchScore)}% match
                        </span>
                      )}
                      <strong>{job.deadline_date ? `Deadline ${job.deadline_date}` : 'Open now'}</strong>
                    </div>
                  </div>

                  <div className="telegram-meta">
                    {job.location && <span>{job.location}</span>}
                    {job.salary && <span>{job.salary}</span>}
                    {job.exp_level && <span>{job.exp_level}</span>}
                    {job.posted_at && <span>Posted {job.posted_at}</span>}
                  </div>

                  <div className="skill-pills">
                    {displaySkills.slice(0, 8).map((skill) => (
                      <span className="chip chip-blue" key={`${job.job_id}-${skill}`}>{skill}</span>
                    ))}
                  </div>

                  {missingSkills.length > 0 && (
                    <details className="match-details telegram-match-details">
                      <summary>Skill gap</summary>
                      <div className="skill-pills">
                        {missingSkills.slice(0, 6).map((skill) => (
                          <span className="chip chip-coral" key={`${job.job_id}-${skill}`}>
                            {skill}
                          </span>
                        ))}
                      </div>
                      {job.explanation && <p className="match-explanation">{job.explanation}</p>}
                    </details>
                  )}

                  {job.apply_link && (
                    <a
                      className="button button-primary telegram-apply-link"
                      href={job.apply_link}
                      target="_blank"
                      rel="noreferrer"
                      onClick={() => trackJobView(job)}
                    >
                      View post
                    </a>
                  )}
                </article>
              )
            })
          ) : (
            <div className="empty-state">
              <p>{isLoading ? 'Loading active Telegram jobs...' : 'No active jobs found for that filter.'}</p>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

export default TelegramJobs
