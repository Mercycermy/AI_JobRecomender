import { useEffect, useState } from 'react'
import { experienceLevels } from '../data/mockData.js'
import FlowProgress from '../components/FlowProgress.jsx'
import {
  clearStoredRecommendations,
  fetchRecommendations,
  fetchSkillSuggestions,
  normalizeSkillValues,
  persistRecommendationSession,
  recordFlowEvent,
  toApiProfile,
} from '../api/recommend.js'

const targetRoles = [
  ['backend-dev', 'Backend Developer'],
  ['frontend-dev', 'Frontend Developer'],
  ['fullstack-dev', 'Full Stack Developer'],
  ['mobile-dev', 'Mobile Developer'],
  ['devops', 'DevOps Engineer'],
  ['data-analyst', 'Data Analyst'],
  ['data-scientist', 'Data Scientist'],
  ['ml-engineer', 'Machine Learning Engineer'],
  ['ui-ux-designer', 'UI/UX Designer'],
  ['graphic-designer', 'Graphic Designer'],
  ['project-manager', 'Project Manager'],
  ['sales', 'Sales Representative'],
  ['digital-marketer', 'Digital Marketer'],
  ['accounting', 'Accountant'],
  ['admin', 'Administration / HR'],
  ['architect', 'Architect'],
  ['teacher', 'Teacher'],
  ['transport', 'Transport / Logistics'],
]

const skillLevels = [
  ['beginner', 'Beginner'],
  ['intermediate', 'Intermediate'],
  ['advanced', 'Advanced'],
  ['expert', 'Expert'],
]

function ManualInput({ navigate }) {
  const [skillInput, setSkillInput] = useState('')
  const [skills, setSkills] = useState([])
  const [suggestions, setSuggestions] = useState([])
  const [isSuggesting, setIsSuggesting] = useState(false)
  const [skillError, setSkillError] = useState('')
  const [experience, setExperience] = useState(experienceLevels[1])
  const [experienceYears, setExperienceYears] = useState('')
  const [category, setCategory] = useState('backend-dev')
  const [location, setLocation] = useState('remote')
  const [hasProjects, setHasProjects] = useState(false)
  const [portfolioUrl, setPortfolioUrl] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    clearStoredRecommendations()
  }, [])

  useEffect(() => {
    const query = skillInput.trim()
    if (!query) {
      return undefined
    }

    let active = true
    const timer = window.setTimeout(() => {
      fetchSkillSuggestions(query)
        .catch(() => [])
        .then((items) => {
          if (active) {
            setSuggestions(items)
          }
        })
        .finally(() => {
          if (active) {
            setIsSuggesting(false)
          }
        })
    }, 180)

    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [skillInput])

  const updateSkillInput = (value) => {
    setSkillInput(value)
    setSkillError('')
    setSuggestions([])
    setIsSuggesting(Boolean(value.trim()))
  }

  const addCanonicalSkill = (skill) => {
    setSkills((current) => {
      if (current.some((item) => item.skill_id === skill.skill_id)) {
        return current
      }
      return [
        ...current,
        {
          skill_id: skill.skill_id,
          skill_name: skill.skill_name,
          level: 'intermediate',
        },
      ]
    })
    setSkillInput('')
    setSuggestions([])
    setIsSuggesting(false)
    setSkillError('')
  }

  const addTypedSkill = async () => {
    const value = skillInput.trim()
    if (!value) {
      return
    }
    try {
      const result = await normalizeSkillValues([value])
      if (result.unresolved?.length || !result.skills?.length) {
        setSkillError(`"${value}" is not in the skill taxonomy. Try a suggestion.`)
        return
      }
      result.skills.forEach(addCanonicalSkill)
    } catch (err) {
      setSkillError(err.message || 'Could not validate that skill.')
    }
  }

  const handleSkillKeyDown = (event) => {
    if (event.key === 'Enter') {
      event.preventDefault()
      addTypedSkill()
    }
  }

  const removeSkill = (skillId) => {
    setSkills((current) => current.filter((skill) => skill.skill_id !== skillId))
  }

  const changeSkillLevel = (skillId, level) => {
    setSkills((current) =>
      current.map((skill) =>
        skill.skill_id === skillId ? { ...skill, level } : skill,
      ),
    )
  }

  const submitManualInput = async (event) => {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)

    const levelMap = Object.fromEntries(
      skills.map((skill) => [skill.skill_id, skill.level]),
    )
    const profile = toApiProfile({
      skills,
      skillLevels: levelMap,
      experience,
      category,
      location,
      experienceYears,
      hasProjects,
      portfolioUrl,
    })

    try {
      const result = await fetchRecommendations(profile)
      persistRecommendationSession(result.profile, result.jobs, result.rawRecs)
      const topJob = result.jobs[0]
      recordFlowEvent({
        event_type: 'intake_completed',
        source: 'manual',
        profile_id: result.profile?.profile_id,
        role: result.profile?.target_role || result.profile?.top_category || category,
        job_id: topJob?.id,
        job_title: topJob?.title,
        match_score: topJob?.match,
        matched_skills: result.jobs.flatMap((job) => job.matchedSkillNames || job.skills || []).slice(0, 16),
        gap_skills: result.jobs.flatMap((job) => job.missingSkillNames || job.missing_skills || []).slice(0, 16),
      }).catch(() => {})
      navigate('/results', { replace: true })
    } catch (err) {
      setError(err.message || 'Could not reach the recommendation API.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="input-page">
      <div className="page-heading">
        <p className="eyebrow">Manual signal entry</p>
        <h1>Build an evidence-aware skill profile.</h1>
        <p>
          Choose skills from the taxonomy, set your real level, and add enough
          evidence for a recommendation you can trust.
        </p>
      </div>

      <FlowProgress currentPath="/manual" />

      <form className="manual-form" onSubmit={submitManualInput}>
        <div className="field-group skill-builder">
          <label htmlFor="skill-input">Skills</label>
          <div className="skill-search-wrap">
            <div className="chip-input">
              <input
                id="skill-input"
                type="text"
                value={skillInput}
                placeholder="Search Python, React, accounting, design..."
                autoComplete="off"
                onChange={(event) => updateSkillInput(event.target.value)}
                onKeyDown={handleSkillKeyDown}
              />
            </div>

            {(suggestions.length > 0 || isSuggesting) && (
              <div className="skill-suggestions">
                {isSuggesting && suggestions.length === 0 && (
                  <span className="suggestion-status">Searching skills...</span>
                )}
                {suggestions.map((skill) => (
                  <button
                    type="button"
                    key={skill.skill_id}
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => addCanonicalSkill(skill)}
                  >
                    <strong>{skill.skill_name}</strong>
                    <span>{skill.category || skill.domain}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {skillError && <p className="form-error">{skillError}</p>}

          {skills.length > 0 && (
            <div className="selected-skill-list" aria-label="Selected skills">
              {skills.map((skill) => (
                <div className="selected-skill-row" key={skill.skill_id}>
                  <div>
                    <strong>{skill.skill_name}</strong>
                    <span>{skill.skill_id}</span>
                  </div>
                  <select
                    aria-label={`${skill.skill_name} level`}
                    value={skill.level}
                    onChange={(event) =>
                      changeSkillLevel(skill.skill_id, event.target.value)
                    }
                  >
                    {skillLevels.map(([value, label]) => (
                      <option value={value} key={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    aria-label={`Remove ${skill.skill_name}`}
                    onClick={() => removeSkill(skill.skill_id)}
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="manual-form-grid">
          <div className="field-group">
            <label htmlFor="experience">General experience</label>
            <select
              id="experience"
              value={experience}
              onChange={(event) => setExperience(event.target.value)}
            >
              {experienceLevels.map((level) => (
                <option key={level} value={level}>
                  {level}
                </option>
              ))}
            </select>
          </div>

          <div className="field-group">
            <label htmlFor="experience-years">Years of experience</label>
            <input
              id="experience-years"
              type="number"
              min="0"
              max="50"
              step="0.5"
              value={experienceYears}
              placeholder="Example: 2"
              onChange={(event) => setExperienceYears(event.target.value)}
            />
          </div>

          <div className="field-group">
            <label htmlFor="category">Target role</label>
            <select
              id="category"
              value={category}
              onChange={(event) => setCategory(event.target.value)}
            >
              {targetRoles.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          <div className="field-group">
            <label htmlFor="location">Preferred location</label>
            <input
              id="location"
              value={location}
              placeholder="Remote, Nairobi, Addis Ababa..."
              onChange={(event) => setLocation(event.target.value)}
            />
          </div>
        </div>

        <div className="manual-evidence">
          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={hasProjects}
              onChange={(event) => setHasProjects(event.target.checked)}
            />
            <span>I have projects or work samples that demonstrate these skills.</span>
          </label>

          <div className="field-group">
            <label htmlFor="portfolio-url">Portfolio or project link (optional)</label>
            <input
              id="portfolio-url"
              type="url"
              value={portfolioUrl}
              placeholder="https://github.com/... or portfolio URL"
              onChange={(event) => setPortfolioUrl(event.target.value)}
            />
          </div>
        </div>

        {error && <p className="form-error">{error}</p>}

        <button
          className="button button-primary manual-submit"
          type="submit"
          disabled={isSubmitting || skills.length === 0}
        >
          {isSubmitting ? 'Generating...' : 'Generate Recommendations'}
        </button>
      </form>
    </section>
  )
}

export default ManualInput
