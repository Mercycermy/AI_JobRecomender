import { useEffect, useState } from 'react'

import FlowProgress from '../components/FlowProgress.jsx'
import {
  fetchPublicLearningResources,
  loadOrFetchStoredAnalysis,
  loadStoredAnalysis,
} from '../api/recommend.js'

function groupPublicResources(items = []) {
  const groups = new Map()
  items.forEach((item, index) => {
    const label = item.skill || item.role || 'Admin recommended'
    const key = item.skill_id || label.toLowerCase().replace(/[^a-z0-9]+/g, '-')
    const group = groups.get(key) || {
      skill_id: key,
      skill: label,
      priority_label: 'Admin',
      resources: [],
    }
    group.resources.push({
      resource_id: item.id || `admin-resource-${index}`,
      title: item.title,
      platform: item.platform || 'Admin catalog',
      level: item.level || 'Recommended',
      hours: item.hours || '',
      url: item.url || '#',
      cost: 'free',
      gap_priority: 'Admin',
      recommendation_score: 100,
      explanation: item.role ? `Added by admin for ${item.role}.` : 'Added by admin.',
    })
    groups.set(key, group)
  })
  return [...groups.values()]
}

function mergeResourceGroups(primary = [], secondary = []) {
  const merged = new Map()
  primary.forEach((group, index) => {
    const key = group.skill_id || group.skill || `group-${index}`
    merged.set(key, { ...group, resources: [...(group.resources || [])] })
  })
  secondary.forEach((group, index) => {
    const key = group.skill_id || group.skill || `admin-group-${index}`
    if (!merged.has(key)) {
      merged.set(key, { ...group, resources: [...(group.resources || [])] })
      return
    }
    const existing = merged.get(key)
    const ids = new Set(existing.resources.map((item) => item.resource_id || item.title))
    group.resources?.forEach((resource) => {
      const resourceId = resource.resource_id || resource.title
      if (!ids.has(resourceId)) {
        existing.resources.push(resource)
        ids.add(resourceId)
      }
    })
  })
  return [...merged.values()]
}

function LearningResources({ standalone = false, resources: providedResources, isLoading = false, error = null }) {
  const [storedAnalysis, setStoredAnalysis] = useState(() => loadStoredAnalysis())
  const [publicResourceGroups, setPublicResourceGroups] = useState([])
  const [analysisState, setAnalysisState] = useState({
    error: null,
    isLoading: false,
  })
  const stored = storedAnalysis
  const hasProvidedResourceContext = Array.isArray(providedResources)
  const hasStoredResourceContext = Boolean(stored)
  const standaloneHeader = standalone ? (
    <>
      <div className="page-heading">
        <p className="eyebrow">Learning resources</p>
        <h1>Your focused study map</h1>
        <p>Resources are grouped around the gaps with the strongest career signal.</p>
      </div>
      <FlowProgress currentPath="/results/resources" />
    </>
  ) : null

  useEffect(() => {
    if (!standalone || hasProvidedResourceContext || stored?.resources?.length) {
      return undefined
    }

    let cancelled = false

    Promise.resolve()
      .then(() => {
        if (!cancelled) {
          setAnalysisState({ error: null, isLoading: true })
        }
        return loadOrFetchStoredAnalysis()
      })
      .then((analysis) => {
        if (cancelled) {
          return
        }
        setStoredAnalysis(analysis)
        setAnalysisState({ error: null, isLoading: false })
      })
      .catch((err) => {
        if (cancelled) {
          return
        }
        setAnalysisState({
          error: err.message || 'Could not load learning resources.',
          isLoading: false,
        })
      })

    return () => {
      cancelled = true
    }
  }, [hasProvidedResourceContext, standalone, stored?.resources?.length])

  useEffect(() => {
    let cancelled = false

    fetchPublicLearningResources()
      .then((payload) => {
        if (!cancelled) {
          setPublicResourceGroups(groupPublicResources(payload.items || []))
        }
      })
      .catch(() => {
        if (!cancelled) {
          setPublicResourceGroups([])
        }
      })

    return () => {
      cancelled = true
    }
  }, [])

  const resolvedLoading = isLoading || analysisState.isLoading
  const resolvedError = error || analysisState.error

  if (resolvedLoading) {
    return (
      <section className={standalone ? 'detail-page' : 'panel-section'}>
        {standaloneHeader}
        <div className="loading-container" style={{ textAlign: 'center', padding: '40px 20px' }}>
          <p className="loading-text" style={{ fontStyle: 'italic', color: 'var(--slate)' }}>
            Curating high-alignment learning resources...
          </p>
        </div>
      </section>
    )
  }

  if (resolvedError && !providedResources?.length && !stored?.resources?.length) {
    return (
      <section className={standalone ? 'detail-page' : 'panel-section'}>
        {standaloneHeader}
        <div className="error-container" style={{ textAlign: 'center', padding: '30px 20px', background: 'rgba(232, 93, 117, 0.08)', borderRadius: '8px', border: '1px solid var(--coral)' }}>
          <p style={{ color: 'var(--coral)', fontWeight: 'bold' }}>{resolvedError}</p>
        </div>
      </section>
    )
  }

  const baseResources = providedResources?.length
    ? providedResources
    : hasProvidedResourceContext
      ? []
      : stored?.resources?.length
        ? stored.resources
        : []
  const resolvedResources = mergeResourceGroups(baseResources, publicResourceGroups)

  if (!resolvedResources.length) {
    return (
      <section className={standalone ? 'detail-page' : 'panel-section'}>
        {standaloneHeader}
        <div className="empty-state" style={{ textAlign: 'center', padding: '32px 20px' }}>
          <p>
            {resolvedError
              ? resolvedError
              : hasProvidedResourceContext || hasStoredResourceContext
                ? 'No curated learning resources were found for the current gaps yet. Review the gap list and keep the matched role skills visible in your profile.'
                : 'Complete the assessment to load curated resources from the learning catalog.'}
          </p>
        </div>
      </section>
    )
  }

  const groupedResources = resolvedResources

  return (
    <section className={standalone ? 'detail-page' : 'panel-section'}>
      {standaloneHeader}

      <div className="resource-groups">
        {groupedResources.map((group) => (
          <section className="resource-group" key={group.skill_id || group.skill}>
            <h2>{group.skill}</h2>

            <div className="resource-grid">
              {group.resources.map((resource) => (
                <article
                  className="resource-card"
                  key={`${group.skill}-${resource.resource_id || resource.title}`}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                      <span className="chip chip-blue">{resource.level}</span>
                      {resource.gap_priority && (
                        <span className={`level-badge level-${resource.gap_priority.toLowerCase()}`} style={{ fontSize: '10px', padding: '3px 8px' }}>
                          {resource.gap_priority} Priority
                        </span>
                      )}
                    </div>
                    <h3>{resource.title}</h3>
                    <p>{resource.platform}</p>
                    {resource.explanation && (
                      <p className="resource-explanation">{resource.explanation}</p>
                    )}
                  </div>

                  <div className="resource-card-footer">
                    <span>
                      {resource.hours}h
                      {resource.cost && ` / ${resource.cost}`}
                      {resource.recommendation_score !== undefined && ` / ${resource.recommendation_score}%`}
                    </span>
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
