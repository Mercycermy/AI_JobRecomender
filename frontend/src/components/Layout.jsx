import { useEffect, useState } from 'react'

function Layout({ children, currentPath }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [theme, setTheme] = useState(() => {
    const savedTheme = localStorage.getItem('ai-job-theme')

    return savedTheme === 'dark' ? 'dark' : 'light'
  })

  const closeMenu = () => setMenuOpen(false)
  const isDark = theme === 'dark'
  const nextTheme = isDark ? 'light' : 'dark'
  const navItems = [
    { href: '/', label: 'Home', exact: true },
    { href: '/quiz', label: 'Quiz' },
    { href: '/manual', label: 'Manual' },
    { href: '/telegram-jobs', label: 'Telegram Jobs' },
  ]
  const isCurrent = (item) => {
    if (item.match) {
      return item.match(currentPath)
    }

    if (item.exact) {
      return currentPath === item.href
    }

    return currentPath.startsWith(item.href)
  }

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('ai-job-theme', theme)
  }, [theme])

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

          <div className="nav-actions">
            <button
              className="theme-toggle"
              type="button"
              aria-label={`Switch to ${nextTheme} theme`}
              aria-pressed={isDark}
              onClick={() => setTheme(nextTheme)}
            >
              <span className="theme-icon" aria-hidden="true"></span>
              {isDark ? 'Dark' : 'Light'}
            </button>
            <a className="header-job-link" href="/telegram-jobs" onClick={closeMenu}>
              Current jobs
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
          </div>

          <div className={`nav-links ${menuOpen ? 'is-open' : ''}`}>
            {navItems.map((item) => (
              <a
                href={item.href}
                aria-current={isCurrent(item) ? 'page' : undefined}
                onClick={closeMenu}
                key={item.href}
              >
                {item.label}
              </a>
            ))}
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
