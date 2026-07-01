import { useCallback, useEffect, useState } from 'react'

import FlowProgress from '../components/FlowProgress.jsx'
import {
  fetchTelegramJobMatches,
  fetchTelegramJobs,
  ingestTelegramJobs,
  loadStoredProfile,
  refreshTelegramJobs,
} from '../api/recommend.js'

const defaultChannels = [
  '@freelance_ethio',
  '@effoyjobs',
  '@josad_software',
  '@ethiojobsofficial',
  '@geezjobs_ethiopia',
  '@Maroset',
]

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

function hasUsableProfile(profile) {
  const skills =
    profile?.skill_ids ||
    profile?.detected_skills ||
    profile?.skills ||
    Object.keys(profile?.skill_scores || {})

  return Boolean(profile && skills?.length)
}

function splitPosts(rawText, channel) {
  return rawText
    .split(/\n\s*\n/)
    .map((text) => text.trim())
    .filter(Boolean)
    .map((text, index) => ({
      channel_name: channel || 'manual-import',
      message_id: String(index + 1),
      raw_text: text,
    }))
}

function TelegramJobs() {
  const [jobs, setJobs] = useState([])
  const [query, setQuery] = useState('')
  const [channel, setChannel] = useState('telegram-channel')
  const [rawPosts, setRawPosts] = useState('')
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isIngesting, setIsIngesting] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [isPersonalized, setIsPersonalized] = useState(false)

  const loadJobs = useCallback(async (search = '') => {
    setIsLoading(true)
    setError(null)
    try {
      const profile = loadStoredProfile()
      const payload = hasUsableProfile(profile)
        ? await fetchTelegramJobMatches(profile, { query: search, limit: 60 })
        : await fetchTelegramJobs({ query: search, limit: 60 })
      setIsPersonalized(hasUsableProfile(profile))
      setJobs(payload.jobs || [])
    } catch (err) {
      setError(err.message || 'Could not load Telegram jobs.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    const profile = loadStoredProfile()
    const request = hasUsableProfile(profile)
      ? fetchTelegramJobMatches(profile, { query: '', limit: 60 })
      : fetchTelegramJobs({ query: '', limit: 60 })

    request
      .then((payload) => {
        if (!cancelled) {
          setIsPersonalized(hasUsableProfile(profile))
          setJobs(payload.jobs || [])
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message || 'Could not load Telegram jobs.')
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [])

  const handleSearch = (event) => {
    event.preventDefault()
    loadJobs(query)
  }

  const handleIngest = async (event) => {
    event.preventDefault()
    const posts = splitPosts(rawPosts, channel)
    if (!posts.length) {
      setError('Paste at least one Telegram post.')
      return
    }
    setIsIngesting(true)
    setError(null)
    try {
      const payload = await ingestTelegramJobs(posts)
      setSummary(payload)
      setRawPosts('')
      await loadJobs(query)
    } catch (err) {
      setError(err.message || 'Could not ingest Telegram posts.')
    } finally {
      setIsIngesting(false)
    }
  }

  const handleRefresh = async () => {
    setIsRefreshing(true)
    setError(null)
    try {
      const payload = await refreshTelegramJobs(defaultChannels, 12)
      setSummary(payload)
      await loadJobs(query)
    } catch (err) {
      setError(err.message || 'Could not refresh Telegram channels.')
    } finally {
      setIsRefreshing(false)
    }
  }

  return (
    <section className="detail-page telegram-page">
      <div className="page-heading">
        <p className="eyebrow">Telegram jobs</p>
        <h1>Current roles from channel posts.</h1>
        <p>Structured jobs from Telegram flow into the same matching engine as the main feed.</p>
      </div>

      <FlowProgress currentPath="/telegram-jobs" />

      <div className="telegram-layout">
        <form className="telegram-import-panel" onSubmit={handleIngest}>
          <div className="resume-builder-section-title">
            <h2>Current channels</h2>
          </div>
          <div className="telegram-channel-list" aria-label="Tracked Telegram channels">
            {defaultChannels.map((item) => (
              <span key={item}>{item}</span>
            ))}
          </div>
          <button
            className="button button-primary manual-submit"
            type="button"
            disabled={isRefreshing}
            onClick={handleRefresh}
          >
            {isRefreshing ? 'Refreshing...' : 'Refresh Current Jobs'}
          </button>
          <div className="telegram-divider"></div>
          <div className="resume-builder-section-title">
            <h2>Import posts</h2>
          </div>
          <label className="field-group">
            <span>Channel</span>
            <input value={channel} onChange={(event) => setChannel(event.target.value)} />
          </label>
          <label className="field-group">
            <span>Posts</span>
            <textarea
              value={rawPosts}
              onChange={(event) => setRawPosts(event.target.value)}
              rows={10}
            />
          </label>
          {summary && (
            <div className="telegram-summary">
              {summary.fetched_posts !== undefined && <span>{summary.fetched_posts} fetched</span>}
              <span>{summary.inserted} inserted</span>
              <span>{summary.updated} updated</span>
              <span>{summary.deduped} deduped</span>
              <span>{summary.skipped} skipped</span>
              {summary.active_total !== undefined && <span>{summary.active_total} active</span>}
            </div>
          )}
          {error && <p className="form-error">{error}</p>}
          <button className="button button-primary manual-submit" type="submit" disabled={isIngesting}>
            {isIngesting ? 'Importing...' : 'Import Telegram Jobs'}
          </button>
        </form>

        <div className="telegram-feed-panel">
          <form className="telegram-search" onSubmit={handleSearch}>
            <label className="field-group">
              <span>Search</span>
              <input value={query} onChange={(event) => setQuery(event.target.value)} />
            </label>
            <button className="button button-ghost" type="submit" disabled={isLoading}>
              {isLoading ? 'Searching...' : 'Search'}
            </button>
          </form>

          {isPersonalized && (
            <div className="telegram-summary">
              <span>{jobs.length} profile-ranked</span>
              <span>Current jobs only</span>
            </div>
          )}

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
                        <span className="chip chip-blue">{job.source_channel}</span>
                        <h2>{job.job_title}</h2>
                        <p>{job.company || job.category}</p>
                      </div>
                      <div className="telegram-job-status">
                        {hasMatchScore && (
                          <span className={`match-badge ${getBadgeClass(matchScore)}`}>
                            {Math.round(matchScore)}% match
                          </span>
                        )}
                        <strong>{job.posted_at}</strong>
                      </div>
                    </div>

                    <div className="telegram-meta">
                      <span>{job.location}</span>
                      {job.salary && <span>{job.salary}</span>}
                      {job.deadline_date && <span>Deadline {job.deadline_date}</span>}
                      <span>{job.exp_level}</span>
                      {job.match_label && <span>{job.match_label} fit</span>}
                      <span>{Math.round((job.confidence || 0) * 100)}% extraction</span>
                    </div>

                    <div className="skill-pills">
                      {displaySkills.slice(0, 8).map((skill) => (
                        <span className="chip chip-blue" key={`${job.job_id}-${skill}`}>{skill}</span>
                      ))}
                    </div>

                    {missingSkills.length > 0 && (
                      <div className="missing-skill-strip">
                        <span>Missing skills</span>
                        <div className="skill-pills">
                          {missingSkills.slice(0, 5).map((skill) => (
                            <span className="chip chip-coral" key={`${job.job_id}-${skill}`}>
                              {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {job.explanation && <p className="match-explanation">{job.explanation}</p>}

                    <p>{job.description}</p>

                    {hasMatchScore && (
                      <details className="match-details telegram-match-details">
                        <summary>Score breakdown</summary>
                        <div className="match-breakdown-grid">
                          {matchFactors.map(([key, label]) => (
                            <div key={key}>
                              <span>{label}</span>
                              <strong>{Math.round(job.breakdown?.[key] ?? 0)}%</strong>
                              <small>{job.score_weights?.[key] ?? 0}% weight</small>
                            </div>
                          ))}
                        </div>
                      </details>
                    )}

                    {job.apply_link && (
                      <a className="button button-primary telegram-apply-link" href={job.apply_link} target="_blank" rel="noreferrer">
                        Apply / View Post
                      </a>
                    )}
                  </article>
                )
              })
            ) : (
              <div className="empty-state">
                <p>{isLoading ? 'Loading Telegram jobs...' : 'No Telegram jobs found.'}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}

export default TelegramJobs
