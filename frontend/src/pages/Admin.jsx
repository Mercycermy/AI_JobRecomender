import { useMemo, useState } from 'react'
import {
  adminActivity,
  adminJobs,
  adminMetrics,
  adminQuestions,
  adminResources,
  categories,
} from '../data/mockData.js'

const adminTabs = ['Overview', 'Jobs', 'Questions', 'Resources', 'Content']

function statusClass(status) {
  return `admin-status admin-status-${status.toLowerCase().replace(/\s+/g, '-')}`
}

function Admin() {
  const [activeTab, setActiveTab] = useState(adminTabs[0])
  const [category, setCategory] = useState('All categories')
  const [search, setSearch] = useState('')
  const [resourceStatus, setResourceStatus] = useState('All statuses')

  const filteredJobs = useMemo(
    () =>
      adminJobs.filter((job) => {
        const categoryMatches = category === 'All categories' || job.category === category
        const searchMatches = `${job.title} ${job.source}`
          .toLowerCase()
          .includes(search.toLowerCase())

        return categoryMatches && searchMatches
      }),
    [category, search],
  )

  const filteredResources = useMemo(
    () =>
      adminResources.filter(
        (resource) => resourceStatus === 'All statuses' || resource.status === resourceStatus,
      ),
    [resourceStatus],
  )

  return (
    <section className="admin-page">
      <div className="admin-header">
        <div>
          <p className="eyebrow">Admin command center</p>
          <h1>Manage recommendations, content quality, and AI coverage.</h1>
          <p>
            Monitor the recommendation pipeline, review job data, tune quiz
            signals, and keep learning content fresh from one focused surface.
          </p>
        </div>

        <div className="admin-actions">
          <button className="button button-ghost" type="button">
            Export Report
          </button>
          <button className="button button-primary" type="button">
            Rebuild Vectors
          </button>
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
            {adminMetrics.map((metric) => (
              <article className="admin-metric-card" key={metric.label}>
                <span className="metric-label">{metric.label}</span>
                <strong>{metric.value}</strong>
                <span className={`metric-delta metric-${metric.tone}`}>{metric.delta}</span>
              </article>
            ))}
          </div>

          <div className="admin-grid">
            <section className="admin-panel">
              <div className="admin-panel-heading">
                <span>Pipeline Health</span>
                <strong>98.6%</strong>
              </div>

              <div className="pipeline-list">
                <div>
                  <span>Data ingestion</span>
                  <strong>Synced</strong>
                </div>
                <div>
                  <span>Vector index</span>
                  <strong>Fresh</strong>
                </div>
                <div>
                  <span>Question bank</span>
                  <strong>12 review items</strong>
                </div>
              </div>
            </section>

            <section className="admin-panel">
              <div className="admin-panel-heading">
                <span>Recent Activity</span>
                <strong>Live</strong>
              </div>

              <div className="activity-feed">
                {adminActivity.map((activity) => (
                  <article key={`${activity.time}-${activity.title}`}>
                    <time>{activity.time}</time>
                    <div>
                      <h2>{activity.title}</h2>
                      <p>{activity.detail}</p>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          </div>
        </div>
      )}

      {activeTab === 'Jobs' && (
        <section className="admin-panel">
          <div className="admin-toolbar">
            <label>
              Search jobs
              <input
                type="search"
                value={search}
                placeholder="Title or source"
                onChange={(event) => setSearch(event.target.value)}
              />
            </label>

            <label>
              Category
              <select value={category} onChange={(event) => setCategory(event.target.value)}>
                <option>All categories</option>
                {categories.map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </label>
          </div>

          <div className="admin-table" role="table" aria-label="Job catalog">
            <div className="admin-table-row admin-table-head" role="row">
              <span>Job</span>
              <span>Category</span>
              <span>Status</span>
              <span>Quality</span>
              <span>Updated</span>
            </div>

            {filteredJobs.map((job) => (
              <div className="admin-table-row" role="row" key={job.id}>
                <span>
                  <strong>{job.title}</strong>
                  <small>{job.source}</small>
                </span>
                <span>{job.category}</span>
                <span className={statusClass(job.status)}>{job.status}</span>
                <span>{job.quality}%</span>
                <span>{job.updated}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {activeTab === 'Questions' && (
        <section className="admin-panel">
          <div className="admin-panel-heading">
            <span>Adaptive Question Bank</span>
            <strong>{adminQuestions.length} prompts</strong>
          </div>

          <div className="question-review-list">
            {adminQuestions.map((question) => (
              <article className="question-review-card" key={question.id}>
                <div>
                  <span className="chip chip-blue">{question.type}</span>
                  <h2>{question.stem}</h2>
                  <p>{question.signal}</p>
                </div>

                <div className="question-review-actions">
                  <span className={statusClass(question.status)}>{question.status}</span>
                  <button className="button button-ghost" type="button">
                    Edit
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      {activeTab === 'Resources' && (
        <section className="admin-panel">
          <div className="admin-toolbar">
            <label>
              Resource status
              <select
                value={resourceStatus}
                onChange={(event) => setResourceStatus(event.target.value)}
              >
                <option>All statuses</option>
                <option>Verified</option>
                <option>Review</option>
              </select>
            </label>
          </div>

          <div className="resource-admin-grid">
            {filteredResources.map((resource) => (
              <article className="resource-admin-card" key={resource.id}>
                <div>
                  <span className={statusClass(resource.status)}>{resource.status}</span>
                  <h2>{resource.title}</h2>
                  <p>
                    {resource.platform} / {resource.skill}
                  </p>
                </div>
                <strong>{resource.score}</strong>
              </article>
            ))}
          </div>
        </section>
      )}

      {activeTab === 'Content' && (
        <section className="admin-panel">
          <div className="content-controls">
            <article>
              <span className="chip chip-blue">Resume Tips</span>
              <h2>Resume guidance library</h2>
              <p>16 active tips across summary, experience, skills, and keywords.</p>
              <button className="button button-ghost" type="button">
                Review Tips
              </button>
            </article>

            <article>
              <span className="chip chip-coral">Skill Taxonomy</span>
              <h2>Skill normalization rules</h2>
              <p>42 aliases queued for approval after the latest import pass.</p>
              <button className="button button-ghost" type="button">
                Open Queue
              </button>
            </article>

            <article>
              <span className="chip chip-blue">Model Prompts</span>
              <h2>AI evaluation prompts</h2>
              <p>Prompt set v2.3 is live with stable confidence thresholds.</p>
              <button className="button button-ghost" type="button">
                Inspect
              </button>
            </article>
          </div>
        </section>
      )}
    </section>
  )
}

export default Admin
