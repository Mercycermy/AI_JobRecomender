import { useEffect, useRef, useState } from 'react'
import { fallbackQuestions } from '../data/mockData.js'
import {
  clearStoredRecommendations,
  mapJobToCard,
  persistQuizSessionId,
  persistRecommendationSession,
} from '../api/recommend.js'

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000'

function normalizeOptions(rawOptions, fallbackOptions = []) {
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

  return (fallbackOptions || []).map((option) => ({ value: option, label: String(option) }))
}

function normalizeQuestion(payload, fallbackIndex) {
  const source = payload?.question || payload || fallbackQuestions[fallbackIndex]
  const fallback = fallbackQuestions[fallbackIndex] || {}

  const rawOpts = source?.options || source?.choices
  return {
    id: source?.id || source?.questionId || `q${fallbackIndex + 1}`,
    number: source.number || fallbackIndex + 1,
    total: source.total || fallbackQuestions.length,
    stem: source?.stem || source?.text || source?.question || fallback.stem || '',
    context: source?.context || '',
    practicalTask: source?.practical_task || source?.practicalTask || null,
    options: rawOpts ? normalizeOptions(rawOpts, fallback.options || []) : [],
  }
}

function Quiz({ navigate }) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [question, setQuestion] = useState(null)
  const [selectedOption, setSelectedOption] = useState('')
  const [textAnswer, setTextAnswer] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isAdvancing, setIsAdvancing] = useState(false)
  const [apiError, setApiError] = useState('')
  const [progressInfo, setProgressInfo] = useState(null)
  const sessionIdRef = useRef('')

  useEffect(() => {
    let isMounted = true

    async function loadFirstQuestion() {
      try {
        clearStoredRecommendations()
        const response = await fetch(`${API_BASE}/quiz`)
        const payload = await response.json()
  sessionIdRef.current = response.headers.get('X-Session-Id') || ''
  persistQuizSessionId(sessionIdRef.current)

        if (isMounted) {
          setQuestion(normalizeQuestion(payload, 0))
          setProgressInfo(payload.progress || null)
          setApiError('')
        }
      } catch {
        if (isMounted) {
          setQuestion(null)
          setApiError('Unable to reach the quiz service. Make sure the backend is running.')
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
      const payload = await response.json().catch(() => ({}))

      if (!response.ok || payload.error) {
        const message = payload.error || `Quiz request failed (${response.status})`
        setApiError(message)
        return
      }

      if (payload.done) {
        const profile = payload.skill_profile
        const rawRecs = payload.recommendations || []
        const jobs = rawRecs.map(mapJobToCard)
        if (profile) {
          persistRecommendationSession(profile, jobs, rawRecs)
        }
        persistQuizSessionId(sessionIdRef.current)
        navigate('/results')
        return
      }

      const nextIndex = currentIndex + 1
      setCurrentIndex(nextIndex)
      setQuestion(normalizeQuestion(payload, nextIndex))
  setProgressInfo(payload.progress || null)
      setSelectedOption('')
      setTextAnswer('')
    } catch (err) {
      setApiError(err?.message || 'Quiz submission failed. Please refresh and try again.')
    } finally {
      setIsAdvancing(false)
    }
  }

  if (isLoading) {
    return (
      <section className="quiz-page">
        <div className="quiz-card quiz-loading">Calibrating your first question...</div>
      </section>
    )
  }

  if (apiError) {
    return (
      <section className="quiz-page">
        <div className="quiz-card quiz-loading">
          <p>{apiError}</p>
          <button
            className="button button-primary"
            type="button"
            onClick={() => window.location.reload()}
          >
            Retry
          </button>
        </div>
      </section>
    )
  }

  if (!question) {
    return null
  }

  const progress = Math.round((question.number / question.total) * 100)
  const routingGate = question.gate ?? '—'
  const routingDomain = progressInfo?.detected_domain || '—'
  const routingRole = progressInfo?.detected_role || '—'

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

        <div className="quiz-routing-badge">
          Gate {routingGate} · Domain {routingDomain} · Role {routingRole}
        </div>

        <h1>{question.stem}</h1>

        {question.options.length > 0 ? (
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
        ) : (
          <div className="freetext-area">
            {question.context && (
              <p className="freetext-context">{question.context}</p>
            )}
            {question.practicalTask && question.practicalTask.starter_code && (
              <pre className="freetext-code"><code>{question.practicalTask.starter_code}</code></pre>
            )}
            <textarea
              className="freetext-input"
              id="freetext-answer"
              rows={6}
              placeholder="Type your answer here..."
              value={textAnswer}
              onChange={(e) => setTextAnswer(e.target.value)}
              disabled={isAdvancing}
            />
            <button
              className="button button-primary freetext-submit"
              type="button"
              disabled={isAdvancing || !textAnswer.trim()}
              onClick={() => answerQuestion(textAnswer.trim())}
            >
              {isAdvancing ? 'Submitting...' : 'Submit Answer'}
            </button>
          </div>
        )}
      </div>
    </section>
  )
}

export default Quiz
