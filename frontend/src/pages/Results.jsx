import { useMemo, useState } from 'react'
import {
  categories,
  experienceLevels,
  jobRecommendations,
} from '../data/mockData.js'
import LearningResources from './LearningResources.jsx'
import ResumeTips from './ResumeTips.jsx'
import SkillGap from './SkillGap.jsx'

const tabs = ['Skill Gap', 'Learning Resources', 'Resume Tips']

function getBadgeClass(match) {
  if (match >= 75) {
    return 'match-high'
  }

  if (match >= 50) {
    return 'match-mid'
  }

  return 'match-low'
}

function Results({ navigate }) {
  const [category, setCategory] = useState('All categories')
  const [experience, setExperience] = useState('All experience')
  const [activeTab, setActiveTab] = useState(tabs[0])

  const filteredJobs = useMemo(
    () =>
      jobRecommendations.filter((job) => {
        const categoryMatches = category === 'All categories' || job.category === category
        const experienceMatches = experience === 'All experience' || job.experience === experience

        return categoryMatches && experienceMatches
      }),
    [category, experience],
  )

  const readinessScore = Math.round(
    jobRecommendations.reduce((total, job) => total + job.readiness, 0) /
      jobRecommendations.length,
  )

  const lowerPanel = {
    'Skill Gap': <SkillGap />,
    'Learning Resources': <LearningResources />,
    'Resume Tips': <ResumeTips />,
  }[activeTab]

  return (
    <section className="results-page">
      <div className="results-header">
        <div>
          <p className="eyebrow">Based on your assessment</p>
          <h1>Your Recommendations</h1>
        </div>
        <button
          className="button button-ghost"
          type="button"
          onClick={() => navigate('/')}
        >
          Start New Assessment
        </button>
      </div>

      <div className="dashboard-summary">
        <div
          className="readiness-ring"
          style={{ '--score': `${readinessScore}%` }}
          aria-label={`Overall readiness score ${readinessScore}%`}
        >
          <strong>{readinessScore}%</strong>
          <span>Overall readiness</span>
        </div>

        <div className="filter-bar">
          <label>
            Category
            <select value={category} onChange={(event) => setCategory(event.target.value)}>
              <option>All categories</option>
              {categories.map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </label>

          <label>
            Experience
            <select value={experience} onChange={(event) => setExperience(event.target.value)}>
              <option>All experience</option>
              {experienceLevels.map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <div className="job-grid">
        {filteredJobs.map((job) => (
          <article className="job-card" key={job.id}>
            <div className="job-card-top">
              <div>
                <h2>{job.title}</h2>
                <p>{job.company}</p>
              </div>
              <span className={`match-badge ${getBadgeClass(job.match)}`}>
                {job.match}% match
              </span>
            </div>

            <div className="skill-pills">
              {job.skills.slice(0, 3).map((skill) => (
                <span className="chip chip-blue" key={skill}>
                  {skill}
                </span>
              ))}
            </div>

            <a className="details-link" href={`/results/gap/${job.id}`}>
              View Details -&gt;
            </a>
          </article>
        ))}
      </div>

      {filteredJobs.length === 0 && (
        <div className="empty-state">
          No jobs match those filters yet. Try a broader category or experience level.
        </div>
      )}

      <div className="bottom-tabs" role="tablist" aria-label="Recommendation panels">
        {tabs.map((tab) => (
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

      <div className="tab-panel">{lowerPanel}</div>
    </section>
  )
}

export default Results
