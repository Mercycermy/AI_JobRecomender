import { loadStoredAnalysis } from '../api/recommend.js'
import { skillGaps } from '../data/mockData.js'

function SkillGap({ gaps: providedGaps, job, standalone = false, isLoading = false, error = null }) {
  const stored = loadStoredAnalysis()
  
  if (isLoading) {
    return (
      <section className={standalone ? 'detail-page' : 'panel-section'}>
        <div className="loading-container" style={{ textAlign: 'center', padding: '40px 20px' }}>
          <p className="loading-text" style={{ fontStyle: 'italic', color: 'var(--slate)' }}>
            Calibrating skill gap analysis...
          </p>
        </div>
      </section>
    )
  }

  if (error && !providedGaps?.length && !stored?.gaps?.length) {
    return (
      <section className={standalone ? 'detail-page' : 'panel-section'}>
        <div className="error-container" style={{ textAlign: 'center', padding: '30px 20px', background: 'rgba(232, 93, 117, 0.08)', borderRadius: '8px', border: '1px solid var(--coral)' }}>
          <p style={{ color: 'var(--coral)', fontWeight: 'bold' }}>{error}</p>
        </div>
      </section>
    )
  }

  const sourceGaps = providedGaps?.length
    ? providedGaps
    : stored?.gaps?.length
      ? stored.gaps
      : skillGaps

  const gaps = [...sourceGaps].sort((left, right) => right.priority - left.priority)

  return (
    <section className={standalone ? 'detail-page' : 'panel-section'}>
      {standalone && (
        <div className="page-heading">
          <p className="eyebrow">Prioritized gap list</p>
          <h1>{job ? `${job.title} Skill Gap` : 'Skill Gap'}</h1>
          <p>
            Compare your current readiness with the level this path expects, then
            start with the biggest leverage point.
          </p>
        </div>
      )}

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
            </article>
          )
        })}
      </div>
    </section>
  )
}

export default SkillGap
