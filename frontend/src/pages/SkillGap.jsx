import { skillGaps } from '../data/mockData.js'

function SkillGap({ job, standalone = false }) {
  const gaps = [...skillGaps].sort((left, right) => right.priority - left.priority)

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
        {gaps.map((gap) => (
          <article className="gap-row" key={gap.skill}>
            <div className="gap-row-header">
              <div>
                <h2>{gap.skill}</h2>
                <p>Priority {gap.priority}</p>
              </div>
              <span className={`level-badge level-${gap.level.toLowerCase()}`}>
                {gap.level}
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
        ))}
      </div>
    </section>
  )
}

export default SkillGap
