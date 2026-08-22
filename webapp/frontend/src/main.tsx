import { StrictMode, useState, useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import { I18nContext, type UiLang } from './i18n.ts'

function Root() {
  const [lang, setLang] = useState<UiLang>(() => (localStorage.getItem('ui_lang') as UiLang) || 'en')

  useEffect(() => {
    document.documentElement.lang = lang
    document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr'
    localStorage.setItem('ui_lang', lang)
  }, [lang])

  return (
    <I18nContext.Provider value={{ lang, setLang }}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </I18nContext.Provider>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Root />
  </StrictMode>,
)
