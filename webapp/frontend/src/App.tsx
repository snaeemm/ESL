import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { useT, useUiLang } from './i18n'
import CreateLesson from './pages/CreateLesson'
import Progress from './pages/Progress'
import Results from './pages/Results'
import History from './pages/History'
import Demo from './pages/Demo'
import moeLogo from './assets/moe_logo.png'

export default function App() {
  const t = useT()
  const { lang, setLang } = useUiLang()
  const location = useLocation()

  // Demo/presentation mode (route /demo, or ?presentation=true on any
  // route) hides developer chrome — nav links, language toggle — for a
  // recording-clean surface, per the case-study demo requirements. It
  // still keeps the MoE brand strip so the recording clearly reads as
  // part of the application, not a separate marketing page.
  const isPresentation = location.pathname.startsWith('/demo')
    || new URLSearchParams(location.search).get('presentation') === 'true'

  if (isPresentation) {
    return (
      <>
        <div className="brand-strip">
          <div className="brand-strip-inner">
            <img src={moeLogo} alt="United Arab Emirates — Ministry of Education" className="moe-logo" />
            <span className="badge">{t('prototypeBadge')}</span>
          </div>
        </div>
        <main className="demo-main">
          <Routes>
            <Route path="/demo" element={<Demo />} />
            <Route path="/jobs/:jobId/results" element={<Results />} />
          </Routes>
        </main>
      </>
    )
  }

  return (
    <>
      {/* Logo bar — see brand/README.md and CLAUDE.md §Logo for usage rules
          (clear space, no recolour/stretch/rotation). object-fit: contain
          + fixed height enforces proportional scaling. */}
      <div className="brand-strip">
        <div className="brand-strip-inner">
          <img src={moeLogo} alt="United Arab Emirates — Ministry of Education" className="moe-logo" />
          <span className="badge">{t('prototypeBadge')}</span>
        </div>
      </div>

      <div className="app-header">
        <div className="app-header-inner">
          <div>
            <h1 className="app-title">{t('appTitle')}</h1>
            <p className="app-subtitle">{t('appSubtitle')}</p>
          </div>
          <div className="nav">
            <NavLink to="/" end className={({ isActive }) => (isActive ? 'active' : '')}>{t('nav_create')}</NavLink>
            <NavLink to="/history" className={({ isActive }) => (isActive ? 'active' : '')}>{t('nav_history')}</NavLink>
            <div className="lang-toggle" role="group" aria-label="UI language">
              <button className={lang === 'en' ? 'active' : ''} onClick={() => setLang('en')} aria-pressed={lang === 'en'}>EN</button>
              <button className={lang === 'ar' ? 'active' : ''} onClick={() => setLang('ar')} aria-pressed={lang === 'ar'}>ع</button>
            </div>
          </div>
        </div>
      </div>

      <main>
        <div className="container">
          <Routes>
            <Route path="/" element={<CreateLesson />} />
            <Route path="/jobs/:jobId/progress" element={<Progress />} />
            <Route path="/jobs/:jobId/results" element={<Results />} />
            <Route path="/history" element={<History />} />
            {/* /demo is intercepted by the isPresentation branch above; this
                route only exists so react-router doesn't warn about an
                unmatched path if that branch's guard is ever bypassed. */}
            <Route path="/demo" element={<Demo />} />
          </Routes>
        </div>
      </main>

      <footer className="app-footer">
        <div className="container">
          <p>{t('notOfficial')}</p>
        </div>
      </footer>
    </>
  )
}
