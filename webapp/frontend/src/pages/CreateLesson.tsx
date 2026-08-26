import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, type EnvironmentStatus } from '../api'
import { useT } from '../i18n'

const DURATION_PRESETS = [30, 45, 60]

export default function CreateLesson() {
  const t = useT()
  const navigate = useNavigate()

  const [env, setEnv] = useState<EnvironmentStatus | null>(null)
  const [envError, setEnvError] = useState<string | null>(null)

  const [mode, setMode] = useState<'paste' | 'upload'>('paste')
  const [sourceText, setSourceText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [sourceLanguage, setSourceLanguage] = useState('auto')
  const [duration, setDuration] = useState<number>(45)
  const [customDuration, setCustomDuration] = useState<string>('')
  const [reviewMode, setReviewMode] = useState<'STRICT' | 'PROTOTYPE'>('STRICT')
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  useEffect(() => {
    api.environment().then(setEnv).catch((e) => setEnvError(String(e.message || e)))
  }, [])

  const effectiveDuration = customDuration ? parseInt(customDuration, 10) : duration
  const canSubmit = (sourceText.trim().length > 0 || file) && !submitting && env?.ok !== false

  async function handleSubmit() {
    setSubmitting(true)
    setSubmitError(null)
    try {
      const form = new FormData()
      if (mode === 'upload' && file) form.append('source_file', file)
      else form.append('source_text', sourceText)
      form.append('source_language', sourceLanguage)
      form.append('target_duration', String(effectiveDuration || 45))
      form.append('review_mode', reviewMode)
      const res = await api.createJob(form)
      navigate(`/jobs/${res.job_id}/progress`)
    } catch (e: any) {
      setSubmitError(e.message || String(e))
      setSubmitting(false)
    }
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      {envError && (
        <div className="status-banner error">Could not reach backend: {envError}. Is the FastAPI server running?</div>
      )}
      {env && !env.ok && (
        <div className="status-banner error">
          <div>
            <strong>Environment not ready.</strong>
            <ul style={{ margin: '6px 0 0', paddingInlineStart: 18 }}>
              {env.problems.map((p, i) => (<li key={i}>{p}</li>))}
            </ul>
          </div>
        </div>
      )}

      <div className="card">
        <div className="tab-row">
          <button type="button" className={mode === 'paste' ? 'active' : ''} onClick={() => setMode('paste')}>
            {t('source_paste')}
          </button>
          <button type="button" className={mode === 'upload' ? 'active' : ''} onClick={() => setMode('upload')}>
            {t('source_upload')}
          </button>
        </div>

        {mode === 'paste' ? (
          <textarea
            value={sourceText}
            onChange={(e) => setSourceText(e.target.value)}
            placeholder={t('source_placeholder')}
          />
        ) : (
          <div>
            <label className="file-drop" htmlFor="source-file-input">
              <span className="file-drop-icon" aria-hidden="true">⬆</span>
              <span className="file-drop-text">
                {file ? file.name : t('file_choose')}
              </span>
              <span className="btn-secondary">{t('file_browse')}</span>
            </label>
            <input
              id="source-file-input"
              type="file"
              accept=".txt,.md"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              style={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', clip: 'rect(0,0,0,0)' }}
            />
            <p className="hint">{t('file_hint')}</p>
          </div>
        )}

        <div className="field">
          <label>{t('config_language')}</label>
          <select value={sourceLanguage} onChange={(e) => setSourceLanguage(e.target.value)}>
            <option value="auto">{t('config_language_auto')}</option>
            <option value="en">{t('config_language_en')}</option>
            <option value="ar">{t('config_language_ar')}</option>
          </select>
        </div>

        <div className="field">
          <label>{t('config_duration')}</label>
          <div className="duration-row">
            {DURATION_PRESETS.map((d) => (
              <button
                key={d}
                type="button"
                className={`btn-secondary ${!customDuration && duration === d ? 'selected' : ''}`}
                onClick={() => { setDuration(d); setCustomDuration('') }}
              >
                {d}s
              </button>
            ))}
            <input
              type="number"
              min={10}
              max={180}
              placeholder={t('config_duration_custom')}
              value={customDuration}
              onChange={(e) => setCustomDuration(e.target.value)}
            />
          </div>
          <p className="hint">The pipeline selects the largest coherent educational subset that fits this target — see Duration Planning in the progress view.</p>
        </div>

        <div className="field">
          <label>{t('config_target')}</label>
          <p style={{ margin: 0, fontSize: 14 }}>{t('config_target_value')}</p>
        </div>

        <div className="field">
          <label>{t('config_review')}</label>
          <div className="radio-group">
            <label className={reviewMode === 'STRICT' ? 'selected' : ''}>
              <input type="radio" name="review" checked={reviewMode === 'STRICT'} onChange={() => setReviewMode('STRICT')} />
              <span>{t('config_review_strict')}</span>
            </label>
            <label className={reviewMode === 'PROTOTYPE' ? 'selected' : ''}>
              <input type="radio" name="review" checked={reviewMode === 'PROTOTYPE'} onChange={() => setReviewMode('PROTOTYPE')} />
              <span>{t('config_review_prototype')}</span>
            </label>
          </div>
          <p className="hint">
            <strong>STRICT:</strong> Stop when expert review is required. &nbsp;·&nbsp;
            <strong>PROTOTYPE:</strong> Render a review-marked prototype where safe.
          </p>
        </div>

        {submitError && <div className="status-banner error">{submitError}</div>}

        <button className="btn-primary" style={{ marginTop: 30 }} disabled={!canSubmit} onClick={handleSubmit}>
          {submitting ? t('generating') : t('generate')}
        </button>
      </div>

      <p className="footnote">{t('networkDisclosure')}</p>
    </div>
  )
}
