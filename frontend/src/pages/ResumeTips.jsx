import { resumeTips } from '../data/mockData.js'

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

function ResumeTips({ standalone = false }) {
  return (
    <section className={standalone ? 'detail-page' : 'panel-section'}>
      {standalone && (
        <div className="page-heading">
          <p className="eyebrow">Resume tips</p>
          <h1>Sharpen the story your profile already tells.</h1>
          <p>Use these sections to turn raw experience into a stronger match signal.</p>
        </div>
      )}

      <div className="tips-grid">
        {resumeTips.map((section) => (
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
    </section>
  )
}

export default ResumeTips
