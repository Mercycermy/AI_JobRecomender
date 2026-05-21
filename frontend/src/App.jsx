import { useCallback, useEffect, useMemo, useState } from 'react'
import Layout from './components/Layout.jsx'
import Admin from './pages/Admin.jsx'
import Home from './pages/Home.jsx'
import LearningResources from './pages/LearningResources.jsx'
import ManualInput from './pages/ManualInput.jsx'
import Quiz from './pages/Quiz.jsx'
import Results from './pages/Results.jsx'
import ResumeTips from './pages/ResumeTips.jsx'
import SkillGap from './pages/SkillGap.jsx'
import { jobRecommendations as mockJobRecommendations } from './data/mockData.js'
import { loadStoredRecommendations } from './api/recommend.js'
import './App.css'

const getPath = () => window.location.pathname

function App() {
  const [path, setPath] = useState(getPath)

  const navigate = useCallback((to) => {
    window.history.pushState({}, '', to)
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

    if (path.startsWith('/results/gap/')) {
      const jobId = path.split('/').filter(Boolean).at(-1)
      const stored = loadStoredRecommendations()
      const jobs = stored?.length ? stored : mockJobRecommendations
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
