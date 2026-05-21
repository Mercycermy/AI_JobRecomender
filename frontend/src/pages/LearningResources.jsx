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

function LearningResources({ standalone = false, resources: providedResources }) {
  const stored = loadStoredAnalysis()
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
