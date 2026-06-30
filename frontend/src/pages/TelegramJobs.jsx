import { useCallback, useEffect, useState } from 'react'

import { fetchTelegramJobs, ingestTelegramJobs } from '../api/recommend.js'

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

  const loadJobs = useCallback(async (search = '') => {
    setIsLoading(true)
    setError(null)
    try {
      const payload = await fetchTelegramJobs({ query: search, limit: 60 })
      setJobs(payload.jobs || [])
    } catch (err) {
      setError(err.message || 'Could not load Telegram jobs.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    fetchTelegramJobs({ query: '', limit: 60 })
      .then((payload) => {
        if (!cancelled) {
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

  return (
    <section className="detail-page telegram-page">
      <div className="page-heading">
        <p className="eyebrow">Telegram jobs</p>
        <h1>Current roles from channel posts.</h1>
        <p>Structured jobs from Telegram flow into the same matching engine as the main feed.</p>
      </div>

      <div className="telegram-layout">
        <form className="telegram-import-panel" onSubmit={handleIngest}>
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
              <span>{summary.inserted} inserted</span>
              <span>{summary.updated} updated</span>
              <span>{summary.deduped} deduped</span>
              <span>{summary.skipped} skipped</span>
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

          <div className="telegram-job-list">
            {jobs.length > 0 ? (
              jobs.map((job) => (
                <article className="telegram-job-card" key={job.job_id}>
                  <div className="telegram-job-top">
                    <div>
                      <span className="chip chip-blue">{job.source_channel}</span>
                      <h2>{job.job_title}</h2>
                      <p>{job.company || job.category}</p>
                    </div>
                    <strong>{job.posted_at}</strong>
                  </div>

                  <div className="telegram-meta">
                    <span>{job.location}</span>
                    {job.salary && <span>{job.salary}</span>}
                    <span>{job.exp_level}</span>
                    <span>{Math.round((job.confidence || 0) * 100)}% confidence</span>
                  </div>

                  <div className="skill-pills">
                    {(job.required_skill_names || []).slice(0, 8).map((skill) => (
                      <span className="chip chip-coral" key={`${job.job_id}-${skill}`}>{skill}</span>
                    ))}
                  </div>

                  <p>{job.description}</p>

                  {job.apply_link && (
                    <a className="telegram-apply-link" href={job.apply_link} target="_blank" rel="noreferrer">
                      Apply
                    </a>
                  )}
                </article>
              ))
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
