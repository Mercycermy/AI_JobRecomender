import { useState } from 'react'

import FlowProgress from '../components/FlowProgress.jsx'
import {
  generateResumeDocument,
  loadStoredProfile,
  loadStoredRecommendations,
  loadStoredSessionId,
  recordFlowEvent,
} from '../api/recommend.js'

const emptyExperience = () => ({
  title: '',
  company: '',
  location: '',
  start: '',
  end: '',
  bullets: '',
})

const emptyEducation = () => ({
  school: '',
  degree: '',
  location: '',
  year: '',
  details: '',
})

const emptyProject = () => ({
  name: '',
  link: '',
  bullets: '',
})

const emptyLink = () => ({
  label: '',
  url: '',
})

function splitLines(value) {
  return value
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean)
}

function uniqueItems(values = []) {
  return [...new Set(values.filter(Boolean).map((value) => String(value)))]
}

function sourceForProfile(profile) {
  return profile?.source === 'adaptive_quiz' || profile?.source === 'quiz'
    ? 'quiz'
    : 'manual'
}

function initialResume() {
  const profile = loadStoredProfile()
  const recommendations = loadStoredRecommendations() || []
  const targetJob = recommendations[0]
  const title = targetJob?.title || profile?.target_role || profile?.top_category || profile?.category || ''
  const skills = uniqueItems([
    ...(targetJob?.matchedSkillNames || targetJob?.skills || []),
    ...(profile?.detected_skills || profile?.skill_ids || profile?.skills || []),
  ]).slice(0, 14)
  const summary = targetJob
    ? `Targeting ${targetJob.title}. Emphasize ${skills.slice(0, 4).join(', ') || 'the strongest matched skills'} and add measurable proof for the highest-fit job.`
    : ''

  return {
    name: '',
    title,
    email: '',
    phone: '',
    location: '',
    summary,
    skills: skills.join(', '),
    certifications: '',
    experience: [emptyExperience()],
    education: [emptyEducation()],
    projects: [emptyProject()],
    links: [emptyLink()],
  }
}

function buildPayload(form) {
  return {
    name: form.name,
    title: form.title,
    email: form.email,
    phone: form.phone,
    location: form.location,
    summary: form.summary,
    skills: form.skills,
    certifications: form.certifications,
    experience: form.experience.map((item) => ({
      ...item,
      bullets: splitLines(item.bullets),
    })),
    education: form.education.map((item) => ({
      ...item,
      details: splitLines(item.details),
    })),
    projects: form.projects.map((item) => ({
      ...item,
      bullets: splitLines(item.bullets),
    })),
    links: form.links,
  }
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

function pdfBlobFromBase64(value) {
  const binary = atob(value)
  const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0))
  return new Blob([bytes], { type: 'application/pdf' })
}

function ResumeBuilder() {
  const [form, setForm] = useState(initialResume)
  const [targetJob] = useState(() => (loadStoredRecommendations() || [])[0] || null)
  const [generated, setGenerated] = useState(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState(null)

  const updateField = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }))
  }

  const updateItem = (section, index, field, value) => {
    setForm((current) => ({
      ...current,
      [section]: current[section].map((item, itemIndex) =>
        itemIndex === index ? { ...item, [field]: value } : item,
      ),
    }))
  }

  const addItem = (section, factory) => {
    setForm((current) => ({ ...current, [section]: [...current[section], factory()] }))
  }

  const removeItem = (section, index) => {
    setForm((current) => ({
      ...current,
      [section]: current[section].filter((_, itemIndex) => itemIndex !== index),
    }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setIsGenerating(true)
    setError(null)
    try {
      const payload = await generateResumeDocument(buildPayload(form))
      setGenerated(payload)
      const profile = loadStoredProfile()
      recordFlowEvent({
        event_type: 'resume_generated',
        source: sourceForProfile(profile),
        session_id: loadStoredSessionId() || profile?.session_id,
        role: form.title || profile?.target_role || profile?.top_category,
        job_id: targetJob?.id,
        job_title: targetJob?.title,
        match_score: targetJob?.match,
        matched_skills: uniqueItems(targetJob?.matchedSkillNames || targetJob?.skills || splitLines(form.skills)),
        gap_skills: uniqueItems(targetJob?.missingSkillNames || targetJob?.missing_skills || []),
      }).catch(() => {})
    } catch (err) {
      setError(err.message || 'Could not generate resume.')
    } finally {
      setIsGenerating(false)
    }
  }

  const downloadPdf = () => {
    if (!generated?.pdf_base64) {
      return
    }
    downloadBlob(pdfBlobFromBase64(generated.pdf_base64), `${generated.filename}.pdf`)
  }

  const downloadPng = async () => {
    if (!generated?.svg) {
      return
    }

    const svgBlob = new Blob([generated.svg], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(svgBlob)
    const image = new Image()

    try {
      await new Promise((resolve, reject) => {
        image.onload = () => {
          const canvas = document.createElement('canvas')
          canvas.width = image.naturalWidth
          canvas.height = image.naturalHeight
          const context = canvas.getContext('2d')
          context.fillStyle = '#ffffff'
          context.fillRect(0, 0, canvas.width, canvas.height)
          context.drawImage(image, 0, 0)
          canvas.toBlob((blob) => {
            if (blob) {
              downloadBlob(blob, `${generated.filename}.png`)
              resolve()
            } else {
              reject(new Error('Could not export PNG.'))
            }
          }, 'image/png')
        }
        image.onerror = () => reject(new Error('Could not render resume image.'))
        image.src = url
      })
    } catch (err) {
      setError(err.message || 'Could not download image.')
    } finally {
      URL.revokeObjectURL(url)
    }
  }

  return (
    <section className="detail-page resume-builder-page">
      <div className="page-heading">
        <p className="eyebrow">Resume builder</p>
        <h1>Build a job-targeted resume and export it.</h1>
        <p>
          The builder uses your latest match context to seed the title, skills,
          and summary. Generate the preview, then download the same layout.
        </p>
      </div>

      <FlowProgress currentPath="/resume-builder" />

      <div className="resume-builder-layout">
        <form className="resume-builder-form" onSubmit={handleSubmit}>
          <section className="resume-builder-section">
            <div className="resume-builder-section-title">
              <h2>Target</h2>
            </div>
            {targetJob && (
              <div className="resume-target-job">
                <span className="chip chip-blue">{targetJob.match}% match</span>
                <strong>{targetJob.title}</strong>
                <p>{uniqueItems(targetJob.matchedSkillNames || targetJob.skills || []).slice(0, 5).join(', ')}</p>
              </div>
            )}
          </section>

          <section className="resume-builder-section">
            <div className="resume-builder-section-title">
              <h2>Contact</h2>
            </div>
            <div className="manual-form-grid">
              <label className="field-group">
                <span>Name</span>
                <input value={form.name} onChange={(event) => updateField('name', event.target.value)} />
              </label>
              <label className="field-group">
                <span>Title</span>
                <input value={form.title} onChange={(event) => updateField('title', event.target.value)} />
              </label>
              <label className="field-group">
                <span>Email</span>
                <input type="email" value={form.email} onChange={(event) => updateField('email', event.target.value)} />
              </label>
              <label className="field-group">
                <span>Phone</span>
                <input value={form.phone} onChange={(event) => updateField('phone', event.target.value)} />
              </label>
              <label className="field-group">
                <span>Location</span>
                <input value={form.location} onChange={(event) => updateField('location', event.target.value)} />
              </label>
            </div>
          </section>

          <section className="resume-builder-section">
            <div className="resume-builder-section-title">
              <h2>Summary</h2>
            </div>
            <label className="field-group">
              <span>Profile summary</span>
              <textarea value={form.summary} onChange={(event) => updateField('summary', event.target.value)} rows={4} />
            </label>
          </section>

          <section className="resume-builder-section">
            <div className="resume-builder-section-title">
              <h2>Skills</h2>
            </div>
            <label className="field-group">
              <span>Skills</span>
              <textarea value={form.skills} onChange={(event) => updateField('skills', event.target.value)} rows={4} />
            </label>
          </section>

          <section className="resume-builder-section">
            <div className="resume-builder-section-title">
              <h2>Work experience</h2>
              <button type="button" onClick={() => addItem('experience', emptyExperience)}>Add</button>
            </div>
            {form.experience.map((item, index) => (
              <div className="resume-repeat-item" key={`experience-${index}`}>
                <div className="resume-repeat-actions">
                  <strong>Role {index + 1}</strong>
                  {form.experience.length > 1 && (
                    <button type="button" onClick={() => removeItem('experience', index)}>Remove</button>
                  )}
                </div>
                <div className="manual-form-grid">
                  <label className="field-group">
                    <span>Role title</span>
                    <input value={item.title} onChange={(event) => updateItem('experience', index, 'title', event.target.value)} />
                  </label>
                  <label className="field-group">
                    <span>Company</span>
                    <input value={item.company} onChange={(event) => updateItem('experience', index, 'company', event.target.value)} />
                  </label>
                  <label className="field-group">
                    <span>Location</span>
                    <input value={item.location} onChange={(event) => updateItem('experience', index, 'location', event.target.value)} />
                  </label>
                  <div className="resume-date-grid">
                    <label className="field-group">
                      <span>Start</span>
                      <input value={item.start} onChange={(event) => updateItem('experience', index, 'start', event.target.value)} />
                    </label>
                    <label className="field-group">
                      <span>End</span>
                      <input value={item.end} onChange={(event) => updateItem('experience', index, 'end', event.target.value)} />
                    </label>
                  </div>
                </div>
                <label className="field-group">
                  <span>Bullets</span>
                  <textarea value={item.bullets} onChange={(event) => updateItem('experience', index, 'bullets', event.target.value)} rows={4} />
                </label>
              </div>
            ))}
          </section>

          <section className="resume-builder-section">
            <div className="resume-builder-section-title">
              <h2>Education</h2>
              <button type="button" onClick={() => addItem('education', emptyEducation)}>Add</button>
            </div>
            {form.education.map((item, index) => (
              <div className="resume-repeat-item" key={`education-${index}`}>
                <div className="resume-repeat-actions">
                  <strong>School {index + 1}</strong>
                  {form.education.length > 1 && (
                    <button type="button" onClick={() => removeItem('education', index)}>Remove</button>
                  )}
                </div>
                <div className="manual-form-grid">
                  <label className="field-group">
                    <span>School</span>
                    <input value={item.school} onChange={(event) => updateItem('education', index, 'school', event.target.value)} />
                  </label>
                  <label className="field-group">
                    <span>Degree</span>
                    <input value={item.degree} onChange={(event) => updateItem('education', index, 'degree', event.target.value)} />
                  </label>
                  <label className="field-group">
                    <span>Location</span>
                    <input value={item.location} onChange={(event) => updateItem('education', index, 'location', event.target.value)} />
                  </label>
                  <label className="field-group">
                    <span>Year</span>
                    <input value={item.year} onChange={(event) => updateItem('education', index, 'year', event.target.value)} />
                  </label>
                </div>
                <label className="field-group">
                  <span>Details</span>
                  <textarea value={item.details} onChange={(event) => updateItem('education', index, 'details', event.target.value)} rows={3} />
                </label>
              </div>
            ))}
          </section>

          <section className="resume-builder-section">
            <div className="resume-builder-section-title">
              <h2>Projects</h2>
              <button type="button" onClick={() => addItem('projects', emptyProject)}>Add</button>
            </div>
            {form.projects.map((item, index) => (
              <div className="resume-repeat-item" key={`project-${index}`}>
                <div className="resume-repeat-actions">
                  <strong>Project {index + 1}</strong>
                  {form.projects.length > 1 && (
                    <button type="button" onClick={() => removeItem('projects', index)}>Remove</button>
                  )}
                </div>
                <div className="manual-form-grid">
                  <label className="field-group">
                    <span>Name</span>
                    <input value={item.name} onChange={(event) => updateItem('projects', index, 'name', event.target.value)} />
                  </label>
                  <label className="field-group">
                    <span>Link</span>
                    <input value={item.link} onChange={(event) => updateItem('projects', index, 'link', event.target.value)} />
                  </label>
                </div>
                <label className="field-group">
                  <span>Bullets</span>
                  <textarea value={item.bullets} onChange={(event) => updateItem('projects', index, 'bullets', event.target.value)} rows={3} />
                </label>
              </div>
            ))}
          </section>

          <section className="resume-builder-section">
            <div className="resume-builder-section-title">
              <h2>Certifications</h2>
            </div>
            <label className="field-group">
              <span>Certifications</span>
              <textarea value={form.certifications} onChange={(event) => updateField('certifications', event.target.value)} rows={3} />
            </label>
          </section>

          <section className="resume-builder-section">
            <div className="resume-builder-section-title">
              <h2>Links</h2>
              <button type="button" onClick={() => addItem('links', emptyLink)}>Add</button>
            </div>
            {form.links.map((item, index) => (
              <div className="manual-form-grid" key={`link-${index}`}>
                <label className="field-group">
                  <span>Label</span>
                  <input value={item.label} onChange={(event) => updateItem('links', index, 'label', event.target.value)} />
                </label>
                <label className="field-group">
                  <span>URL</span>
                  <input value={item.url} onChange={(event) => updateItem('links', index, 'url', event.target.value)} />
                </label>
                {form.links.length > 1 && (
                  <button className="resume-remove-link" type="button" onClick={() => removeItem('links', index)}>Remove</button>
                )}
              </div>
            ))}
          </section>

          {error && <p className="form-error">{error}</p>}
          <button className="button button-primary manual-submit" type="submit" disabled={isGenerating}>
            {isGenerating ? 'Building...' : 'Build Ready-to-Use Resume'}
          </button>
        </form>

        <aside className="resume-preview-panel">
          <div className="resume-builder-section-title">
            <h2>Preview</h2>
            <div className="resume-export-actions">
              <button type="button" disabled={!generated} onClick={downloadPdf}>PDF</button>
              <button type="button" disabled={!generated} onClick={downloadPng}>PNG</button>
            </div>
          </div>
          {generated ? (
            <>
              <div className="resume-ready-banner">
                Improved resume is ready. Download as PDF or PNG and apply to the matched job.
              </div>
              <div className="resume-preview-frame" dangerouslySetInnerHTML={{ __html: generated.html }} />
            </>
          ) : (
            <div className="empty-state">
              <p>Build a ready-to-use resume to preview and download it.</p>
            </div>
          )}
        </aside>
      </div>
    </section>
  )
}

export default ResumeBuilder
