import FlowProgress from '../components/FlowProgress.jsx'
import { loadStoredAnalysis } from '../api/recommend.js'

function LearningResources({ standalone = false, resources: providedResources, isLoading = false, error = null }) {
  const stored = loadStoredAnalysis()
  const hasProvidedResourceContext = Array.isArray(providedResources)
  const hasStoredResourceContext = Boolean(stored)
  const standaloneHeader = standalone ? (
    <>
      <div className="page-heading">
        <p className="eyebrow">Learning resources</p>
        <h1>Your focused study map</h1>
        <p>Resources are grouped around the gaps with the strongest career signal.</p>
      </div>
      <FlowProgress currentPath="/results/resources" />
    </>
  ) : null

  if (isLoading) {
    return (
      <section className={standalone ? 'detail-page' : 'panel-section'}>
        {standaloneHeader}
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
        {standaloneHeader}
        <div className="error-container" style={{ textAlign: 'center', padding: '30px 20px', background: 'rgba(232, 93, 117, 0.08)', borderRadius: '8px', border: '1px solid var(--coral)' }}>
          <p style={{ color: 'var(--coral)', fontWeight: 'bold' }}>{error}</p>
        </div>
      </section>
    )
  }

  const resolvedResources = providedResources?.length
    ? providedResources
    : hasProvidedResourceContext
      ? []
      : stored?.resources?.length
        ? stored.resources
        : []

  if (!resolvedResources.length) {
    return (
      <section className={standalone ? 'detail-page' : 'panel-section'}>
        {standaloneHeader}
        <div className="empty-state" style={{ textAlign: 'center', padding: '32px 20px' }}>
          <p>
            {error
              ? error
              : hasProvidedResourceContext || hasStoredResourceContext
                ? 'No curated learning resources were found for the current gaps yet. Review the gap list and keep the matched role skills visible in your profile.'
                : 'Complete the assessment to load curated resources from the learning catalog.'}
          </p>
        </div>
      </section>
    )
  }

  const groupedResources = resolvedResources

  return (
    <section className={standalone ? 'detail-page' : 'panel-section'}>
      {standaloneHeader}

      <div className="resource-groups">
        {groupedResources.map((group) => (
          <section className="resource-group" key={group.skill_id || group.skill}>
            <h2>{group.skill}</h2>

            <div className="resource-grid">
              {group.resources.map((resource) => (
                <article
                  className="resource-card"
                  key={`${group.skill}-${resource.resource_id || resource.title}`}
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
                    {resource.explanation && (
                      <p className="resource-explanation">{resource.explanation}</p>
                    )}
                  </div>

                  <div className="resource-card-footer">
                    <span>
                      {resource.hours}h
                      {resource.cost && ` / ${resource.cost}`}
                      {resource.recommendation_score !== undefined && ` / ${resource.recommendation_score}%`}
                    </span>
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
