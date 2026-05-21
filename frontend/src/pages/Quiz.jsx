import { useEffect, useRef, useState } from 'react'
import { fallbackQuestions } from '../data/mockData.js'
import { mapJobToCard, persistRecommendationSession } from '../api/recommend.js'

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000'

function normalizeOptions(rawOptions, fallbackOptions) {
  if (Array.isArray(rawOptions)) {
    return rawOptions.map((option) => {
      if (option && typeof option === 'object') {
        const value = option.value ?? option.id ?? option.label
        return {
          value,
          label: option.label ?? option.text ?? String(value ?? ''),
        }
      }
      return { value: option, label: String(option) }
    })
  }

  if (rawOptions && typeof rawOptions === 'object') {
    return Object.entries(rawOptions).map(([key, meta]) => ({
      value: key,
      label: meta?.text ?? meta?.label ?? `Option ${key}`,
    }))
  }

  return fallbackOptions.map((option) => ({ value: option, label: String(option) }))
}

function normalizeQuestion(payload, fallbackIndex) {
  const source = payload?.question || payload || fallbackQuestions[fallbackIndex]
  const fallback = fallbackQuestions[fallbackIndex]

  return {
    id: source.id || source.questionId || `q${fallbackIndex + 1}`,
    number: source.number || fallbackIndex + 1,
    total: source.total || fallbackQuestions.length,
    stem: source.stem || source.text || source.question || fallback.stem,
    options: normalizeOptions(source.options || source.choices, fallback.options),
  }
}

function Quiz({ navigate }) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [question, setQuestion] = useState(null)
  const [selectedOption, setSelectedOption] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isAdvancing, setIsAdvancing] = useState(false)
  const sessionIdRef = useRef('')

  useEffect(() => {
    let isMounted = true

    async function loadFirstQuestion() {
      try {
        const response = await fetch(`${API_BASE}/quiz`)
        const payload = await response.json()
        sessionIdRef.current = response.headers.get('X-Session-Id') || ''

        if (isMounted) {
          setQuestion(normalizeQuestion(payload, 0))
        }
      } catch {
        if (isMounted) {
          setQuestion(normalizeQuestion(null, 0))
        }
      } finally {
        if (isMounted) {
          setIsLoading(false)
        }
      }
    }

    loadFirstQuestion()

    return () => {
      isMounted = false
    }
  }, [])

  const answerQuestion = async (option) => {
    if (!question || isAdvancing) {
      return
    }

    setSelectedOption(option)
    setIsAdvancing(true)

    try {
      const headers = { 'Content-Type': 'application/json' }
      if (sessionIdRef.current) {
        headers['X-Session-Id'] = sessionIdRef.current
      }

      const response = await fetch(`${API_BASE}/quiz/answer`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          questionId: question.id,
          selectedOption: option,
        }),
      })
      const payload = await response.json()

      if (payload.done) {
        const profile = payload.skill_profile
        const rawRecs = payload.recommendations || []
        const jobs = rawRecs.map(mapJobToCard)
        if (profile && jobs.length) {
          persistRecommendationSession(profile, jobs, rawRecs)
        }
        navigate('/results')
        return
      }

      const nextIndex = currentIndex + 1
      setCurrentIndex(nextIndex)
      setQuestion(normalizeQuestion(payload, nextIndex))
      setSelectedOption('')
    } catch {
      const nextIndex = currentIndex + 1

      if (nextIndex >= fallbackQuestions.length) {
        navigate('/results')
        return
      }

      setCurrentIndex(nextIndex)
      setQuestion(normalizeQuestion(null, nextIndex))
      setSelectedOption('')
    } finally {
      setIsAdvancing(false)
    }
  }

  if (isLoading || !question) {
    return (
      <section className="quiz-page">
        <div className="quiz-card quiz-loading">Calibrating your first question...</div>
      </section>
    )
  }

  const progress = Math.round((question.number / question.total) * 100)

  return (
    <section className="quiz-page">
      <div className="quiz-card" key={question.id}>
        <div className="quiz-progress" aria-label={`Question progress ${progress}%`}>
          <span style={{ width: `${progress}%` }}></span>
        </div>

        <div className="quiz-meta">
          <span>
            Question {question.number} / {question.total}
          </span>
          <span>{progress}% mapped</span>
        </div>

        <h1>{question.stem}</h1>

        <div className="option-grid">
          {question.options.map((option) => (
            <button
              className={`option-card ${selectedOption === option.value ? 'is-selected' : ''}`}
              type="button"
              key={option.value}
              disabled={isAdvancing}
              onClick={() => answerQuestion(option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>
    </section>
  )
}

export default Quiz
