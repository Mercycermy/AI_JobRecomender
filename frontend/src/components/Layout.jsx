import { useState } from 'react'

function Layout({ children }) {
  const [menuOpen, setMenuOpen] = useState(false)

  const closeMenu = () => setMenuOpen(false)

  return (
    <div className="app-shell">
      <header className="site-header">
        <nav className="navbar" aria-label="Primary navigation">
          <a className="brand" href="/" onClick={closeMenu}>
            <span className="brand-mark" aria-hidden="true">
              AI
            </span>
            <span>Job Compass</span>
          </a>

          <button
            className="nav-toggle"
            type="button"
            aria-label="Toggle navigation"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((isOpen) => !isOpen)}
          >
            <span></span>
            <span></span>
            <span></span>
          </button>

          <div className={`nav-links ${menuOpen ? 'is-open' : ''}`}>
            <a href="/" aria-current="page" onClick={closeMenu}>
              Home
            </a>
            <a href="/quiz" onClick={closeMenu}>
              Quiz
            </a>
            <a href="/manual" onClick={closeMenu}>
              Manual
            </a>
          </div>
        </nav>
      </header>

      <main className="main-content">{children}</main>

      <footer className="site-footer">
        <span>AI Job Recommender</span>
        <span>Signal-first career matching</span>
      </footer>
    </div>
  )
}

export default Layout
