import { useEffect, useState } from 'react'
import { fallbackQuestions } from '../data/mockData.js'

const API_BASE = import.meta.env.VITE_API_URL || ''

function normalizeQuestion(payload, fallbackIndex) {
  const source = payload?.question || payload || fallbackQuestions[fallbackIndex]

  return {
    id: source.id || source.questionId || `q${fallbackIndex + 1}`,
    number: source.number || fallbackIndex + 1,
    total: source.total || fallbackQuestions.length,
    stem: source.stem || source.text || source.question || fallbackQuestions[fallbackIndex].stem,
    options: source.options || source.choices || fallbackQuestions[fallbackIndex].options,
  }
}

function Quiz({ navigate }) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [question, setQuestion] = useState(null)
  const [selectedOption, setSelectedOption] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isAdvancing, setIsAdvancing] = useState(false)

  useEffect(() => {
    let isMounted = true

    async function loadFirstQuestion() {
      try {
        const response = await fetch(`${API_BASE}/quiz`)
        const payload = await response.json()

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
      const response = await fetch(`${API_BASE}/quiz/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          questionId: question.id,
          selectedOption: option,
        }),
      })
      const payload = await response.json()

      if (payload.done) {
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
          {question.options.slice(0, 4).map((option) => (
            <button
              className={`option-card ${selectedOption === option ? 'is-selected' : ''}`}
              type="button"
              key={option}
              disabled={isAdvancing}
              onClick={() => answerQuestion(option)}
            >
              {option}
            </button>
          ))}
        </div>
      </div>
    </section>
  )
}

export default Quiz
