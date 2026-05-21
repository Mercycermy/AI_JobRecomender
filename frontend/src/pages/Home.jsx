function Home() {
  const updatePointer = (event) => {
    const rect = event.currentTarget.getBoundingClientRect()
    const x = (event.clientX - rect.left) / rect.width - 0.5
    const y = (event.clientY - rect.top) / rect.height - 0.5

    event.currentTarget.style.setProperty('--cursor-x', x.toFixed(3))
    event.currentTarget.style.setProperty('--cursor-y', y.toFixed(3))
  }

  const resetPointer = (event) => {
    event.currentTarget.style.setProperty('--cursor-x', '0')
    event.currentTarget.style.setProperty('--cursor-y', '0')
  }

  return (
    <section
      className="home-page"
      onPointerMove={updatePointer}
      onPointerLeave={resetPointer}
    >
      <div className="hero-grid" aria-hidden="true"></div>
      <div className="signal-lines" aria-hidden="true">
        <span></span>
        <span></span>
        <span></span>
        <span></span>
      </div>

      <div className="home-hero">
        <div className="hero-copy">
          <div className="ai-mark reveal reveal-one" aria-hidden="true">
            <svg viewBox="0 0 72 72" role="presentation">
              <path d="M36 7 60 21v30L36 65 12 51V21L36 7Z" />
              <path d="M25 31h22M25 42h15" />
              <circle cx="24" cy="24" r="3.8" />
              <circle cx="48" cy="48" r="3.8" />
              <circle cx="48" cy="24" r="3.8" />
            </svg>
            <span className="pulse-ring"></span>
          </div>

          <p className="eyebrow reveal reveal-one">Adaptive AI career signal</p>
          <h1 className="reveal reveal-two">
            Find the role your skills are already reaching for.
          </h1>
          <p className="tagline reveal reveal-three">
            A focused recommender that reads your strengths, maps your gaps, and
            turns job discovery into a clear next move.
          </p>

          <div className="hero-actions reveal reveal-four">
            <a className="button button-primary" href="/quiz">
              Start Quiz
            </a>
            <a className="button button-ghost" href="/manual">
              Enter Skills
            </a>
          </div>
        </div>

        <div className="hero-visual reveal reveal-five" aria-label="AI job match preview">
          <div className="scan-panel">
            <div className="panel-topline">
              <span>Live Fit Map</span>
              <span className="status-dot">Online</span>
            </div>

            <div className="radar-stage" aria-hidden="true">
              <div className="radar-ring ring-one"></div>
              <div className="radar-ring ring-two"></div>
              <div className="radar-ring ring-three"></div>
              <div className="radar-sweep"></div>
              <div className="node node-one">Data</div>
              <div className="node node-two">UX</div>
              <div className="node node-three">ML</div>
              <div className="node node-four">API</div>
              <div className="core-node">AI</div>
            </div>

            <div className="match-stack">
              <div className="match-row">
                <span>Product Analyst</span>
                <strong>92%</strong>
              </div>
              <div className="meter">
                <span style={{ width: '92%' }}></span>
              </div>
              <div className="match-row">
                <span>Data Associate</span>
                <strong>84%</strong>
              </div>
              <div className="meter">
                <span style={{ width: '84%' }}></span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="stats-row reveal reveal-six" aria-label="Product stats">
        <div className="stat-card">
          <strong>50+</strong>
          <span>Data Points</span>
        </div>
        <div className="stat-card">
          <strong>500+</strong>
          <span>Jobs Analyzed</span>
        </div>
        <div className="stat-card">
          <strong>AI</strong>
          <span>Precision</span>
        </div>
      </div>
    </section>
  )
}

export default Home
