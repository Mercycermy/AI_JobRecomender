import { useState } from 'react'
import { categories, experienceLevels } from '../data/mockData.js'

function ManualInput({ navigate }) {
  const [skillInput, setSkillInput] = useState('')
  const [skills, setSkills] = useState(['SQL', 'React', 'Research'])
  const [experience, setExperience] = useState(experienceLevels[1])
  const [category, setCategory] = useState(categories[0])

  const addSkill = () => {
    const nextSkill = skillInput.trim()

    if (!nextSkill || skills.some((skill) => skill.toLowerCase() === nextSkill.toLowerCase())) {
      setSkillInput('')
      return
    }

    setSkills((currentSkills) => [...currentSkills, nextSkill])
    setSkillInput('')
  }

  const handleSkillKeyDown = (event) => {
    if (event.key === 'Enter') {
      event.preventDefault()
      addSkill()
    }
  }

  const removeSkill = (skillToRemove) => {
    setSkills((currentSkills) => currentSkills.filter((skill) => skill !== skillToRemove))
  }

  const submitManualInput = (event) => {
    event.preventDefault()
    navigate('/results')
  }

  return (
    <section className="input-page">
      <div className="page-heading">
        <p className="eyebrow">Manual signal entry</p>
        <h1>Build your recommendation from the skills you already know.</h1>
        <p>
          Add a compact skill profile, choose your level, and let the recommender
          shape a focused results dashboard.
        </p>
      </div>

      <form className="manual-form" onSubmit={submitManualInput}>
        <div className="field-group skill-builder">
          <label htmlFor="skill-input">Skills</label>
          <div className="chip-input">
            <div className="chip-list" aria-label="Selected skills">
              {skills.map((skill) => (
                <button
                  className="chip chip-coral"
                  type="button"
                  key={skill}
                  onClick={() => removeSkill(skill)}
                >
                  {skill}
                  <span aria-hidden="true">x</span>
                </button>
              ))}
            </div>
            <input
              id="skill-input"
              type="text"
              value={skillInput}
              placeholder="Type a skill and press Enter"
              onBlur={addSkill}
              onChange={(event) => setSkillInput(event.target.value)}
              onKeyDown={handleSkillKeyDown}
            />
          </div>
        </div>

        <div className="manual-form-grid">
          <div className="field-group">
            <label htmlFor="experience">Experience</label>
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
            <label htmlFor="category">Field</label>
            <select
              id="category"
              value={category}
              onChange={(event) => setCategory(event.target.value)}
            >
              {categories.map((field) => (
                <option key={field} value={field}>
                  {field}
                </option>
              ))}
            </select>
          </div>
        </div>

        <button className="button button-primary manual-submit" type="submit">
          Generate Recommendations
        </button>
      </form>
    </section>
  )
}

export default ManualInput
