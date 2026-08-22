import { Routes, Route, NavLink } from 'react-router-dom'
import { useT, useUiLang } from './i18n'
import CreateLesson from './pages/CreateLesson'
import Progress from './pages/Progress'
import Results from './pages/Results'
import History from './pages/History'
import moeLogo from './assets/moe_logo.png'

export default function App() {
  const t = useT()
  const { lang, setLang } = useUiLang()

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
