import { loadStoredAnalysis } from '../api/recommend.js'
import { learningResources } from '../data/mockData.js'

function groupBySkill(resources) {
  return resources.reduce((groups, resource) => {
    if (!groups[resource.skill]) {
      groups[resource.skill] = []
    }

    groups[resource.skill].push(resource)
    return groups
  }, {})
}

function LearningResources({ standalone = false, resources: providedResources, isLoading = false, error = null }) {
  const stored = loadStoredAnalysis()

  if (isLoading) {
    return (
      <section className={standalone ? 'detail-page' : 'panel-section'}>
        <div className="loading-container" style={{ textAlign: 'center', padding: '40px 20px' }}>
          <p className="loading-text" style={{ fontStyle: 'italic', color: 'var(--slate)' }}>
            Curating high-alignment learning resources...
          </p>
        </div>
      </section>
    )
  }

  if (error && !providedResources?.length && !stored?.resources?.length) {
    return (
      <section className={standalone ? 'detail-page' : 'panel-section'}>
        <div className="error-container" style={{ textAlign: 'center', padding: '30px 20px', background: 'rgba(232, 93, 117, 0.08)', borderRadius: '8px', border: '1px solid var(--coral)' }}>
          <p style={{ color: 'var(--coral)', fontWeight: 'bold' }}>{error}</p>
        </div>
      </section>
    )
  }

  const resolvedResources = providedResources?.length
    ? providedResources
    : stored?.resources?.length
      ? stored.resources
      : null

  const groupedResources = resolvedResources
    ? resolvedResources
    : groupBySkill(learningResources)

  return (
    <section className={standalone ? 'detail-page' : 'panel-section'}>
      {standalone && (
        <div className="page-heading">
          <p className="eyebrow">Learning resources</p>
          <h1>Your focused study map</h1>
          <p>Resources are grouped around the gaps with the strongest career signal.</p>
        </div>
      )}

      <div className="resource-groups">
        {resolvedResources
          ? groupedResources.map((group) => (
              <section className="resource-group" key={group.skill_id || group.skill}>
                <h2>{group.skill}</h2>

                <div className="resource-grid">
                  {group.resources.map((resource) => (
                    <article
                      className="resource-card"
                      key={`${group.skill}-${resource.title}`}
                    >
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                          <span className="chip chip-blue">{resource.level}</span>
                          {resource.gap_priority && (
                            <span className={`level-badge level-${resource.gap_priority.toLowerCase()}`} style={{ fontSize: '10px', padding: '3px 8px' }}>
                              {resource.gap_priority} Priority
                            </span>
                          )}
                        </div>
                        <h3>{resource.title}</h3>
                        <p>{resource.platform}</p>
                      </div>

                      <div className="resource-card-footer">
                        <span>{resource.hours}h</span>
                        <a href={resource.url} target="_blank" rel="noreferrer">
                          Open
                        </a>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            ))
          : Object.entries(groupedResources).map(([skill, resources]) => (
              <section className="resource-group" key={skill}>
                <h2>{skill}</h2>

                <div className="resource-grid">
                  {resources.map((resource) => (
                    <article
                      className="resource-card"
                      key={`${resource.skill}-${resource.title}`}
                    >
                      <div>
                        <span className="chip chip-blue">{resource.level}</span>
                        <h3>{resource.title}</h3>
                        <p>{resource.platform}</p>
                      </div>

                      <div className="resource-card-footer">
                        <span>{resource.hours}h</span>
                        <a href={resource.url} target="_blank" rel="noreferrer">
                          Open
                        </a>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            ))}
      </div>
    </section>
  )
}

export default LearningResources
