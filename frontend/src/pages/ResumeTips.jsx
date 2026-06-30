import { useState } from 'react'

import FlowProgress from '../components/FlowProgress.jsx'
import {
  loadStoredProfile,
  loadStoredRawRecommendations,
  uploadResumeForTips,
} from '../api/recommend.js'

const emphasisTerms = [
  'measurable',
  'domain signal',
  'impact',
  'metrics',
  'workflow',
  'matched skills',
  'job posting language',
  'role-specific nouns',
]

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function emphasizeTip(tip) {
  const pattern = new RegExp(`(${emphasisTerms.map(escapeRegExp).join('|')})`, 'gi')

  return tip.split(pattern).map((part) => {
    const shouldEmphasize = emphasisTerms.some(
      (term) => term.toLowerCase() === part.toLowerCase(),
    )

    return shouldEmphasize ? <strong key={part}>{part}</strong> : part
  })
}

function ResumeTips({ standalone = false, coaching = null, isLoading = false, error = null }) {
  const [resumeFile, setResumeFile] = useState(null)
  const [uploadResult, setUploadResult] = useState(null)
  const [uploadError, setUploadError] = useState(null)
  const [isUploading, setIsUploading] = useState(false)

  const handleUpload = async (event) => {
    event.preventDefault()
    if (!resumeFile) {
      setUploadError('Choose a PDF, DOCX, or TXT resume.')
      return
    }
    setIsUploading(true)
    setUploadError(null)
    try {
      const profile = loadStoredProfile()
      const rawRecommendations = loadStoredRawRecommendations()
      const payload = await uploadResumeForTips(resumeFile, profile, rawRecommendations)
      setUploadResult(payload)
    } catch (err) {
      setUploadError(err.message || 'Resume upload failed.')
    } finally {
      setIsUploading(false)
    }
  }

  if (isLoading) {
    return (
      <section className={standalone ? 'detail-page' : 'panel-section'}>
        <div className="loading-container" style={{ textAlign: 'center', padding: '40px 20px' }}>
          <p className="loading-text" style={{ fontStyle: 'italic', color: 'var(--slate)' }}>
            Generating personalized resume strategy...
          </p>
        </div>
      </section>
    )
  }

  const resolvedTips = coaching?.tips?.length ? coaching.tips : []
  const emptyTipsMessage = error
    ? error
    : coaching?.is_ai === false
      ? 'Set GROQ_API_KEY on the server to generate personalized resume coaching.'
      : 'Complete the assessment to generate AI resume tips.'

  return (
    <section className={standalone ? 'detail-page' : 'panel-section'}>
      {standalone && (
        <>
          <div className="page-heading">
            <p className="eyebrow">Resume tips</p>
            <h1>Sharpen the story your profile already tells.</h1>
            <p>Use these sections to turn raw experience into a stronger match signal.</p>
          </div>
          <FlowProgress currentPath="/results/resume" />
        </>
      )}

      {coaching?.is_ai && (
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', background: 'rgba(46, 134, 193, 0.12)', border: '1px solid rgba(46, 134, 193, 0.3)', borderRadius: '999px', padding: '6px 14px', marginBottom: '24px' }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--mint)', boxShadow: '0 0 8px var(--mint)' }}></span>
          <span style={{ fontSize: '11px', fontWeight: '800', textTransform: 'uppercase', color: 'var(--blue)', letterSpacing: '0.5px' }}>
            Personalized AI Coaching Active
          </span>
        </div>
      )}

      <form className="resume-upload-panel" onSubmit={handleUpload}>
        <div>
          <p className="eyebrow">Resume upload</p>
          <h2>ATS review</h2>
        </div>
        <div className="resume-upload-controls">
          <input
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={(event) => setResumeFile(event.target.files?.[0] || null)}
          />
          <button type="submit" disabled={isUploading}>
            {isUploading ? 'Reviewing...' : 'Review Resume'}
          </button>
          <a className="button button-ghost" href="/resume-builder">
            Open Builder
          </a>
        </div>
        {uploadError && <p className="upload-error">{uploadError}</p>}
      </form>

      {uploadResult && (
        <div className="resume-upload-result">
          <div className="resume-upload-summary">
            <span>{uploadResult.resume?.file_type?.toUpperCase()}</span>
            <span>{uploadResult.resume?.word_count} words</span>
            <span>{uploadResult.detected_skills?.length || 0} skills found</span>
          </div>

          {uploadResult.missing_keywords?.length > 0 && (
            <section>
              <h2>Missing keywords</h2>
              <div className="resume-keyword-list">
                {uploadResult.missing_keywords.slice(0, 8).map((keyword) => (
                  <span key={keyword.skill_id}>{keyword.skill}</span>
                ))}
              </div>
            </section>
          )}

          {uploadResult.weak_sections?.length > 0 && (
            <section>
              <h2>Weak sections</h2>
              <ul>
                {uploadResult.weak_sections.slice(0, 5).map((section) => (
                  <li key={section.section}>{section.recommendation}</li>
                ))}
              </ul>
            </section>
          )}

          {uploadResult.ats_improvements?.length > 0 && (
            <section>
              <h2>ATS improvements</h2>
              <ul>
                {uploadResult.ats_improvements.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}

      {resolvedTips.length > 0 ? (
        <div className="tips-grid">
          {resolvedTips.map((section) => (
            <article className="tips-section" key={section.section}>
              <div className="tips-section-title">
                <span aria-hidden="true">{section.icon}</span>
                <h2>{section.section}</h2>
              </div>

              <ul>
                {section.tips.map((tip) => (
                  <li key={tip}>{emphasizeTip(tip)}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      ) : (
        <div className="empty-state" style={{ textAlign: 'center', padding: '32px 20px' }}>
          <p>{emptyTipsMessage}</p>
        </div>
      )}

      {coaching?.schedule?.length > 0 && (
        <div className="study-schedule-section" style={{ marginTop: '48px', paddingTop: '32px', borderTop: '1px solid rgba(255, 255, 255, 0.08)' }}>
          <div className="page-heading" style={{ marginBottom: '24px' }}>
            <p className="eyebrow" style={{ fontSize: '11px', fontWeight: '800', textTransform: 'uppercase', color: 'var(--coral)', letterSpacing: '1.5px', marginBottom: '8px' }}>Personalized roadmap</p>
            <h2 style={{ fontSize: '24px', fontWeight: '800', color: 'var(--navy)', margin: '0 0 8px 0' }}>Weekly Study Schedule</h2>
            <p style={{ color: 'var(--slate)', fontSize: '14px', margin: 0 }}>
              Follow this structured 4-week plan to systematically close your high-leverage skill gaps.
            </p>
          </div>

          <div className="schedule-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '20px' }}>
            {coaching.schedule.map((week) => (
              <article className="schedule-card" key={week.week} style={{ background: 'rgba(255, 255, 255, 0.02)', border: '1px solid rgba(255, 255, 255, 0.06)', borderRadius: '12px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <span className="week-badge" style={{ fontSize: '10px', fontWeight: '900', textTransform: 'uppercase', color: 'var(--coral)', letterSpacing: '1px' }}>
                  {week.week}
                </span>
                <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '800', color: 'var(--navy)' }}>{week.focus}</h3>
                <ul style={{ margin: 0, paddingLeft: '16px', color: 'var(--slate)', fontSize: '13px', lineHeight: '1.6' }}>
                  {week.tasks.map((task) => (
                    <li key={task} style={{ marginBottom: '6px' }}>{task}</li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}

export default ResumeTips
