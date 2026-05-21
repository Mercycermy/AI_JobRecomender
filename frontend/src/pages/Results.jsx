import { useEffect, useMemo, useState } from 'react'
import {
  categories,
  experienceLevels,
  jobRecommendations as mockJobRecommendations,
} from '../data/mockData.js'
import {
  fetchAnalysis,
  fetchResumeTips,
  loadStoredAnalysis,
  loadStoredProfile,
  loadStoredRecommendations,
  loadStoredRawRecommendations,
  persistAnalysis,
} from '../api/recommend.js'
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

function formatCategoryLabel(slug) {
  if (!slug) {
    return 'Unknown'
  }
  return slug
    .split('-')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function Results({ navigate }) {
  const [category, setCategory] = useState('All categories')
  const [experience, setExperience] = useState('All experience')
  const [activeTab, setActiveTab] = useState(tabs[0])
  
  const [analysis, setAnalysis] = useState(() => loadStoredAnalysis())
  const [isAnalysisLoading, setIsAnalysisLoading] = useState(!loadStoredAnalysis())
  const [analysisError, setAnalysisError] = useState(null)

  const [resumeTipsData, setResumeTipsData] = useState(() => {
    try {
      const raw = sessionStorage.getItem('resumeTipsCoaching')
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  })
  const [isResumeTipsLoading, setIsResumeTipsLoading] = useState(false)
  const [resumeTipsError, setResumeTipsError] = useState(null)

  const jobRecommendations = useMemo(() => {
    const stored = loadStoredRecommendations()
    return stored?.length ? stored : mockJobRecommendations
  }, [])

  useEffect(() => {
    let isMounted = true
    const profile = loadStoredProfile()
    const rawRecs = loadStoredRawRecommendations() || loadStoredRecommendations()

    if (!profile || !rawRecs?.length) {
      setIsAnalysisLoading(false)
      return () => {
        isMounted = false
      }
    }

    setIsAnalysisLoading(true)
    setAnalysisError(null)

    fetchAnalysis(profile, rawRecs)
      .then((payload) => {
        if (!isMounted) {
          return
        }
        setAnalysis(payload)
        persistAnalysis(payload)
        setIsAnalysisLoading(false)
      })
      .catch((err) => {
        if (!isMounted) {
          return
        }
        setAnalysisError(err.message || 'Failed to load analysis')
        setIsAnalysisLoading(false)
      })

    return () => {
      isMounted = false
    }
  }, [])

  useEffect(() => {
    let isMounted = true
    const profile = loadStoredProfile()
    if (!profile || !analysis?.gaps?.length) {
      return
    }

    // Only fetch if not already loaded
    if (resumeTipsData) {
      return
    }

    setIsResumeTipsLoading(true)
    setResumeTipsError(null)

    fetchResumeTips(profile, analysis.gaps)
      .then((payload) => {
        if (!isMounted) {
          return
        }
        setResumeTipsData(payload)
        sessionStorage.setItem('resumeTipsCoaching', JSON.stringify(payload))
        setIsResumeTipsLoading(false)
      })
      .catch((err) => {
        if (!isMounted) {
          return
        }
        setResumeTipsError(err.message || 'Failed to load resume tips')
        setIsResumeTipsLoading(false)
      })

    return () => {
      isMounted = false
    }
  }, [analysis?.gaps])

  const categoryOptions = useMemo(() => {
    const fromJobs = [...new Set(jobRecommendations.map((j) => j.category).filter(Boolean))]
    return fromJobs.length ? fromJobs.map(formatCategoryLabel) : categories
  }, [jobRecommendations])

  const filteredJobs = useMemo(
    () =>
      jobRecommendations.filter((job) => {
        const jobCategoryLabel = formatCategoryLabel(job.category)
        const categoryMatches =
          category === 'All categories' || job.category === category || jobCategoryLabel === category
        const experienceMatches =
          experience === 'All experience' || job.experience === experience

        return categoryMatches && experienceMatches
      }),
    [category, experience, jobRecommendations],
  )

  const readinessScore = Math.round(
    jobRecommendations.reduce((total, job) => total + (job.readiness ?? job.match ?? 0), 0) /
      Math.max(jobRecommendations.length, 1),
  )

  const lowerPanel = {
    'Skill Gap': (
      <SkillGap
        gaps={analysis?.gaps}
        isLoading={isAnalysisLoading}
        error={analysisError}
      />
    ),
    'Learning Resources': (
      <LearningResources
        resources={analysis?.resources}
        isLoading={isAnalysisLoading}
        error={analysisError}
      />
    ),
    'Resume Tips': (
      <ResumeTips
        coaching={resumeTipsData}
        isLoading={isResumeTipsLoading}
        error={resumeTipsError}
      />
    ),
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
              {categoryOptions.map((item) => (
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
