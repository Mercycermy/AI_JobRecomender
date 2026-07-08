import { useEffect, useState } from 'react'

import FlowProgress from '../components/FlowProgress.jsx'
import { loadOrFetchStoredAnalysis, loadStoredAnalysis } from '../api/recommend.js'

function uniqueSkillNames(values = []) {
  return [...new Set(values.filter(Boolean).map((value) => String(value)))]
}

function getJobMissingSkillNames(job) {
  return uniqueSkillNames(
    job?.missingSkillNames ||
      job?.missing_skill_names ||
      job?.missing_skills ||
      [],
  )
}

function getJobGapRows(job) {
  return getJobMissingSkillNames(job).map((skill, index) => ({
    skill,
    level: index < 2 ? 'High' : 'Medium',
    current: 45,
    required: 80,
    priority: Math.max(60, 90 - index * 8),
  }))
}

function SkillGap({ gaps: providedGaps, job, standalone = false, isLoading = false, error = null }) {
  const [storedAnalysis, setStoredAnalysis] = useState(() => loadStoredAnalysis())
  const [analysisState, setAnalysisState] = useState({
    error: null,
    isLoading: false,
  })
  const stored = storedAnalysis
  const hasStandaloneJobContext = Boolean(standalone && job)
  const jobGaps = hasStandaloneJobContext ? getJobGapRows(job) : []
  const standaloneHeader = standalone ? (
    <>
      <div className="page-heading">
        <p className="eyebrow">Prioritized gap list</p>
        <h1>{job ? `${job.title} Skill Gap` : 'Skill Gap'}</h1>
        <p>
          Compare your current readiness with the level this path expects, then
          start with the biggest leverage point.
        </p>
      </div>
      <FlowProgress currentPath="/results/gap" />
    </>
  ) : null

  useEffect(() => {
    if (!standalone || providedGaps?.length || jobGaps.length || stored?.gaps?.length) {
      return undefined
    }

    let cancelled = false

    Promise.resolve()
      .then(() => {
        if (!cancelled) {
          setAnalysisState({ error: null, isLoading: true })
        }
        return loadOrFetchStoredAnalysis()
      })
      .then((analysis) => {
        if (cancelled) {
          return
        }
        setStoredAnalysis(analysis)
        setAnalysisState({ error: null, isLoading: false })
      })
      .catch((err) => {
        if (cancelled) {
          return
        }
        setAnalysisState({
          error: err.message || 'Could not load skill gap analysis.',
          isLoading: false,
        })
      })

    return () => {
      cancelled = true
    }
  }, [jobGaps.length, providedGaps?.length, standalone, stored?.gaps?.length])

  const resolvedLoading = isLoading || analysisState.isLoading
  const resolvedError = error || analysisState.error
  
  if (resolvedLoading) {
    return (
      <section className={standalone ? 'detail-page' : 'panel-section'}>
        {standaloneHeader}
        <div className="loading-container" style={{ textAlign: 'center', padding: '40px 20px' }}>
          <p className="loading-text" style={{ fontStyle: 'italic', color: 'var(--slate)' }}>
            Calibrating skill gap analysis...
          </p>
        </div>
      </section>
    )
  }

  if (resolvedError && !providedGaps?.length && !stored?.gaps?.length && !jobGaps.length) {
    return (
      <section className={standalone ? 'detail-page' : 'panel-section'}>
        {standaloneHeader}
        <div className="error-container" style={{ textAlign: 'center', padding: '30px 20px', background: 'rgba(232, 93, 117, 0.08)', borderRadius: '8px', border: '1px solid var(--coral)' }}>
          <p style={{ color: 'var(--coral)', fontWeight: 'bold' }}>{resolvedError}</p>
        </div>
      </section>
    )
  }

  const sourceGaps = providedGaps?.length
    ? providedGaps
    : hasStandaloneJobContext && jobGaps.length
      ? jobGaps
      : stored?.gaps?.length
        ? stored.gaps
        : []

  if (!sourceGaps.length) {
    return (
      <section className={standalone ? 'detail-page' : 'panel-section'}>
        {standaloneHeader}
        <div className="empty-state" style={{ textAlign: 'center', padding: '32px 20px' }}>
          <p>
            {resolvedError
              ? resolvedError
              : hasStandaloneJobContext
                ? `${job.title} does not show critical missing skills against your current profile. Keep strengthening the matched skills and review the score breakdown for smaller fit factors.`
                : 'Complete the skills assessment to see your real skill gaps from quiz results.'}
          </p>
        </div>
      </section>
    )
  }

  const gaps = [...sourceGaps].sort((left, right) => right.priority - left.priority)

  return (
    <section className={standalone ? 'detail-page' : 'panel-section'}>
      {standaloneHeader}

      <div className="gap-list">
        {gaps.map((gap) => {
          const rawLabel = gap.priority_label || gap.level || 'Low'
          const displayLabel = rawLabel.toLowerCase().includes('priority') ? rawLabel : `${rawLabel} Priority`
          const cssClass = rawLabel.toLowerCase().replace(' priority', '')

          return (
            <article className="gap-row" key={gap.skill}>
              <div className="gap-row-header">
                <div>
                  <h2>{gap.skill}</h2>
                  <p>
                    Priority {gap.priority}%
                    {gap.occurrences !== undefined && (
                      <> &bull; Missing in {gap.occurrences} recommended job{gap.occurrences === 1 ? '' : 's'}</>
                    )}
                  </p>
                </div>
                <span className={`level-badge level-${cssClass}`}>
                  {displayLabel}
                </span>
              </div>

              <div
                className="gap-bar"
                style={{
                  '--current': `${gap.current}%`,
                  '--required': `${gap.required}%`,
                }}
                aria-label={`${gap.skill} current ${gap.current}% required ${gap.required}%`}
              >
                <span className="gap-current"></span>
                <span className="gap-required"></span>
              </div>

              <div className="gap-values">
                <span>Current {gap.current}%</span>
                <span>Required {gap.required}%</span>
              </div>

              {gap.affected_jobs?.length > 0 && (
                <div className="gap-job-list">
                  <span>Shows up in</span>
                  {gap.affected_jobs.slice(0, 3).map((affectedJob) => (
                    <span className="gap-job-pill" key={`${gap.skill_id}-${affectedJob.job_id || affectedJob.rank}`}>
                      {affectedJob.title}
                    </span>
                  ))}
                </div>
              )}

              {gap.learning_path?.length > 0 && (
                <ol className="gap-learning-path">
                  {gap.learning_path.map((step) => (
                    <li key={`${gap.skill_id}-${step.order || step.title}`}>
                      <strong>{step.title}</strong>
                      <span>{step.description}</span>
                    </li>
                  ))}
                </ol>
              )}
            </article>
          )
        })}
      </div>
    </section>
  )
}

export default SkillGap
