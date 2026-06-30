import {
  loadStoredAnalysis,
  loadStoredProfile,
  loadStoredRecommendations,
} from '../api/recommend.js'

const flowDefinitions = [
  {
    id: 'profile',
    label: 'Profile',
    href: '/manual',
    activePaths: ['/manual', '/quiz'],
  },
  {
    id: 'matches',
    label: 'Matches',
    href: '/results',
    activePaths: ['/results'],
  },
  {
    id: 'gaps',
    label: 'Gaps',
    href: '/results',
    activePaths: ['/results/gap'],
  },
  {
    id: 'learning',
    label: 'Learning',
    href: '/results/resources',
    activePaths: ['/results/resources'],
  },
  {
    id: 'resume',
    label: 'Resume',
    href: '/results/resume',
    activePaths: ['/results/resume', '/resume-builder'],
  },
  {
    id: 'jobs',
    label: 'Jobs',
    href: '/telegram-jobs',
    activePaths: ['/telegram-jobs'],
  },
]

function getCurrentPath() {
  if (typeof window === 'undefined') {
    return '/'
  }

  return window.location.pathname
}

function uniqueItems(values = []) {
  return [...new Set(values.filter(Boolean).map((value) => String(value)))]
}

function countProfileSkills(profile) {
  return uniqueItems(
    profile?.skill_ids ||
      profile?.detected_skills ||
      profile?.skills ||
      Object.keys(profile?.skill_scores || {}),
  ).length
}

function getFlowMeta(stepId, profile, recommendations, analysis) {
  const skillCount = countProfileSkills(profile)
  const matchCount = recommendations?.length || 0
  const gapCount = analysis?.gaps?.length || 0
  const resourceCount = analysis?.resources?.length || 0

  if (stepId === 'profile') {
    return skillCount ? `${skillCount} skills` : 'Start'
  }

  if (stepId === 'matches') {
    return matchCount ? `${matchCount} roles` : 'Pending'
  }

  if (stepId === 'gaps') {
    return gapCount ? `${gapCount} gaps` : 'Pending'
  }

  if (stepId === 'learning') {
    return resourceCount ? `${resourceCount} paths` : 'Pending'
  }

  if (stepId === 'resume') {
    return profile ? 'Ready' : 'Pending'
  }

  return 'Live feed'
}

function isStepComplete(stepId, profile, recommendations, analysis) {
  if (stepId === 'profile') {
    return countProfileSkills(profile) > 0
  }

  if (stepId === 'matches') {
    return Boolean(recommendations?.length)
  }

  if (stepId === 'gaps') {
    return Boolean(analysis?.gaps?.length)
  }

  if (stepId === 'learning') {
    return Boolean(analysis?.resources?.length)
  }

  if (stepId === 'resume') {
    return Boolean(profile)
  }

  return true
}

function isStepActive(step, currentPath) {
  if (step.id === 'matches') {
    return currentPath === '/results'
  }

  return step.activePaths.some(
    (path) => currentPath === path || currentPath.startsWith(`${path}/`),
  )
}

function FlowProgress({
  currentPath = getCurrentPath(),
  profile: providedProfile,
  recommendations: providedRecommendations,
  analysis: providedAnalysis,
}) {
  const profile = providedProfile ?? loadStoredProfile()
  const recommendations = providedRecommendations ?? loadStoredRecommendations()
  const analysis = providedAnalysis ?? loadStoredAnalysis()

  return (
    <nav className="flow-progress" aria-label="Product flow status">
      <div className="flow-steps">
        {flowDefinitions.map((step, index) => {
          const isComplete = isStepComplete(step.id, profile, recommendations, analysis)
          const isActive = isStepActive(step, currentPath)

          return (
            <a
              className={`flow-step ${isComplete ? 'is-complete' : ''} ${isActive ? 'is-active' : ''}`}
              href={step.href}
              key={step.id}
              aria-current={isActive ? 'step' : undefined}
            >
              <span className="flow-index">{index + 1}</span>
              <span className="flow-step-copy">
                <strong>{step.label}</strong>
                <small>{getFlowMeta(step.id, profile, recommendations, analysis)}</small>
              </span>
            </a>
          )
        })}
      </div>
    </nav>
  )
}

export default FlowProgress
