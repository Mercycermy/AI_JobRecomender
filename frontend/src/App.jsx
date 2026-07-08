import { useCallback, useEffect, useMemo, useState } from 'react'
import Layout from './components/Layout.jsx'
import Admin from './pages/Admin.jsx'
import Home from './pages/Home.jsx'
import LearningResources from './pages/LearningResources.jsx'
import ManualInput from './pages/ManualInput.jsx'
import Quiz from './pages/Quiz.jsx'
import Results from './pages/Results.jsx'
import ResumeBuilder from './pages/ResumeBuilder.jsx'
import ResumeTips from './pages/ResumeTips.jsx'
import SkillGap from './pages/SkillGap.jsx'
import TelegramJobs from './pages/TelegramJobs.jsx'
import { loadStoredRecommendations, recordSiteActivity } from './api/recommend.js'
import './App.css'

const getPath = () => window.location.pathname

function compactActivityText(value, fallback = 'site action') {
  const text = String(value || '')
    .replace(/\s+/g, ' ')
    .trim()

  return (text || fallback).slice(0, 140)
}

function activityLabelForElement(element) {
  const href = element.getAttribute?.('href')
  const label =
    element.getAttribute?.('aria-label') ||
    element.getAttribute?.('title') ||
    element.innerText ||
    element.textContent ||
    element.name ||
    href ||
    element.tagName

  return {
    href,
    label: compactActivityText(label),
    tag: String(element.tagName || 'element').toLowerCase(),
  }
}

function App() {
  const [path, setPath] = useState(getPath)

  const navigate = useCallback((to, options = {}) => {
    const method = options.replace ? 'replaceState' : 'pushState'
    window.history[method]({}, '', to)
    setPath(getPath())
    window.scrollTo({ top: 0, left: 0 })
  }, [])

  useEffect(() => {
    const handlePopState = () => setPath(getPath())
    const handleClick = (event) => {
      const link = event.target.closest('a[href^="/"]')

      if (!link || link.target || event.metaKey || event.ctrlKey || event.shiftKey) {
        return
      }

      event.preventDefault()
      navigate(link.getAttribute('href'))
    }

    window.addEventListener('popstate', handlePopState)
    document.addEventListener('click', handleClick)

    return () => {
      window.removeEventListener('popstate', handlePopState)
      document.removeEventListener('click', handleClick)
    }
  }, [navigate])

  useEffect(() => {
    recordSiteActivity('page_viewed', {
      path,
      label: `Viewed ${path}`,
      summary: path,
    }).catch(() => {})
  }, [path])

  useEffect(() => {
    const handleActivityClick = (event) => {
      const target = event.target.closest?.('a, button, summary, input[type="checkbox"], input[type="radio"]')
      if (!target || target.closest?.('[data-skip-analytics]')) {
        return
      }

      const { href, label, tag } = activityLabelForElement(target)
      recordSiteActivity('site_action', {
        href,
        label,
        summary: `${tag}: ${label}`,
      }).catch(() => {})
    }

    const handleActivitySubmit = (event) => {
      const form = event.target
      const label = compactActivityText(
        form.getAttribute?.('aria-label') ||
          form.getAttribute?.('name') ||
          form.className ||
          'form submitted',
      )

      recordSiteActivity('site_action', {
        label,
        method: 'SUBMIT',
        summary: `form: ${label}`,
      }).catch(() => {})
    }

    const handleActivityChange = (event) => {
      const target = event.target
      if (!target?.matches?.('select, input[type="checkbox"], input[type="radio"], input[type="file"]')) {
        return
      }

      const { label, tag } = activityLabelForElement(target)
      recordSiteActivity('site_action', {
        label,
        summary: `${tag} changed: ${label}`,
      }).catch(() => {})
    }

    document.addEventListener('click', handleActivityClick)
    document.addEventListener('submit', handleActivitySubmit)
    document.addEventListener('change', handleActivityChange)

    return () => {
      document.removeEventListener('click', handleActivityClick)
      document.removeEventListener('submit', handleActivitySubmit)
      document.removeEventListener('change', handleActivityChange)
    }
  }, [])

  const route = useMemo(() => {
    if (path.startsWith('/admin')) {
      return <Admin />
    }

    if (path === '/quiz') {
      return <Quiz navigate={navigate} />
    }

    if (path === '/manual') {
      return <ManualInput navigate={navigate} />
    }

    if (path === '/results/resources') {
      return <LearningResources standalone />
    }

    if (path === '/results/resume') {
      return <ResumeTips standalone />
    }

    if (path === '/resume-builder') {
      return <ResumeBuilder />
    }

    if (path === '/telegram-jobs') {
      return <TelegramJobs />
    }

    if (path.startsWith('/results/gap/')) {
      const jobId = path.split('/').filter(Boolean).at(-1)
      const stored = loadStoredRecommendations()
      const jobs = stored?.length ? stored : []
      const job = jobs.find((item) => item.id === jobId)

      return <SkillGap job={job} standalone />
    }

    if (path === '/results') {
      return <Results navigate={navigate} />
    }

    return <Home />
  }, [navigate, path])

  return (
    <Layout currentPath={path}>
      {route}
    </Layout>
  )
}

export default App
