import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api, type JobResult } from '../api'
import { useT } from '../i18n'
import StatusChip from '../components/StatusChip'

type Tab = 'lesson' | 'signplan' | 'review' | 'traceability' | 'technical'

export default function Results() {
  const { jobId } = useParams()
  const t = useT()
  const [result, setResult] = useState<JobResult | null>(null)
  const [trace, setTrace] = useState<any>(null)
  const [, setReviewData] = useState<any>(null)
  const [artifacts, setArtifacts] = useState<{ name: string; size_bytes: number }[]>([])
  const [tab, setTab] = useState<Tab>('lesson')
  const [traceFilter, setTraceFilter] = useState<string>('ALL')

  useEffect(() => {
    if (!jobId) return
    api.jobResult(jobId).then(setResult).catch(() => {})
    api.jobTraceability(jobId).then(setTrace).catch(() => {})
    api.jobReview(jobId).then(setReviewData).catch(() => {})
    api.jobArtifacts(jobId).then(setArtifacts).catch(() => {})
  }, [jobId])

  if (!result) return <p>Loading…</p>

  const cov = result.validation?.checks?.coverage
  const dp = result.validation?.duration_plan
  const status = result.validation?.overall_status
  const units = result.episode?.units || []
  const includedUnits = units.filter((u: any) => u.included_in_episode !== false)

  const bannerClass = status === 'PASS' ? 'ok' : status === 'PASS_WITH_FALLBACK' ? 'ok' : 'warn'

  const filteredTrace = trace?.segments?.filter((s: any) =>
    traceFilter === 'ALL' ? true : s.sign_decision.status === traceFilter,
  ) || []

  return (
    <div>
      <h2 className="page-title">{t('results_title')}</h2>

      <div style={{ display: 'flex', gap: 32, flexWrap: 'wrap', alignItems: 'flex-start' }}>
        <div>
          {result.has_video ? (
            <video className="lesson-video" controls src={api.jobVideoUrl(jobId!)} />
          ) : (
            <div className="card">No video was rendered for this run (see Review tab).</div>
          )}
        </div>
        <div style={{ minWidth: 260 }}>
          <table style={{ fontSize: '0.85rem' }}>
            <tbody>
              <tr><td className="hint">Requested duration</td><td>{dp?.requested_duration_s ?? '—'}s</td></tr>
              <tr><td className="hint">Estimated duration</td><td>{dp?.estimated_duration_s ?? '—'}s</td></tr>
              <tr><td className="hint">Actual duration</td><td>{dp?.actual_duration_s ?? '—'}s</td></tr>
              <tr><td className="hint">Source language</td><td>{result.source_manifest?.source_language}</td></tr>
              <tr><td className="hint">Local model</td><td>{result.understanding_summary?.model}</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className={`status-banner ${bannerClass}`}>
        <div>
          <strong>{status === 'PASS' ? t('passTitle') : t('reviewRequiredTitle')}</strong>
          <p style={{ margin: '4px 0 0', fontWeight: 400 }}>{t('reviewRequiredBody')}</p>
        </div>
      </div>

      <div className="metric-grid">
        <div className="metric-card">
          <div className="metric-value">{cov ? `${includedUnits.filter((u:any)=>u.source_span_verified).length}/${includedUnits.length}` : '—'}</div>
          <div className="metric-label">{t('metric_traceability')}</div>
        </div>
        <div className="metric-card">
          <div className="metric-value">{cov?.full_verified_lexical_coverage_pct ?? cov?.verified_lexical_sign_coverage_pct ?? '—'}%</div>
          <div className="metric-label">{t('metric_lexical')}</div>
          {!!cov?.partial_lexical_representation_pct && (
            <div className="hint" style={{ marginTop: 2 }}>+{cov.partial_lexical_representation_pct}% partial (modifier lost)</div>
          )}
        </div>
        <div className="metric-card">
          <div className="metric-value">{cov?.renderable_coverage_with_fallback_pct ?? '—'}%</div>
          <div className="metric-label">{t('metric_fallback')}</div>
        </div>
        <div className="metric-card">
          <div className="metric-value">{cov?.review_required_units ?? 0}</div>
          <div className="metric-label">{t('metric_review')}</div>
        </div>
        <div className="metric-card">
          <div className="metric-value" style={{ fontSize: '1.1rem' }}>{(result.understanding_summary?.model || '').split('/').pop()}</div>
          <div className="metric-label">{t('metric_model')}</div>
        </div>
        <div className="metric-card">
          <div className="metric-value">{t('localValue')}</div>
          <div className="metric-label">{t('metric_local')}</div>
        </div>
      </div>

      <div className="tabs">
        <button className={tab === 'lesson' ? 'active' : ''} onClick={() => setTab('lesson')}>{t('tab_lesson')}</button>
        <button className={tab === 'signplan' ? 'active' : ''} onClick={() => setTab('signplan')}>{t('tab_signplan')}</button>
        <button className={tab === 'review' ? 'active' : ''} onClick={() => setTab('review')}>{t('tab_review')}</button>
        <button className={tab === 'traceability' ? 'active' : ''} onClick={() => setTab('traceability')}>{t('tab_traceability')}</button>
        <button className={tab === 'technical' ? 'active' : ''} onClick={() => setTab('technical')}>{t('tab_technical')}</button>
      </div>

      {tab === 'lesson' && (
        <div>
          <p className="hint">{result.source_manifest?.source_path} — SHA-256: {result.source_manifest?.source_id}</p>
          {includedUnits.map((u: any) => (
            <div className="unit-card" key={u.unit_id}>
              <strong>{u.concept}</strong>
              <p>{u.educational_sentence}</p>
              <details>
                <summary>{t('viewSource')}</summary>
                <p className="source-span-quote">"{u.source_span}"</p>
                <p className="hint">source_span_verified: {String(u.source_span_verified)}</p>
              </details>
            </div>
          ))}
        </div>
      )}

      {tab === 'signplan' && (
        <div>
          {includedUnits.map((u: any) => (
            <div className="unit-card" key={u.unit_id}>
              <strong>{u.educational_sentence}</strong>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 10 }}>
                {(u.sign_resolution || []).map((r: any, i: number) => (
                  <div key={i} style={{ border: '1px solid var(--border)', borderRadius: 4, padding: '8px 10px', minWidth: 140 }}>
                    <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>{r.term}</div>
                    <StatusChip status={r.status} t={t} />
                    {r.status === 'VERIFIED_SIGN' && r.catalog_ref && (
                      <p className="hint" style={{ margin: '4px 0 0' }}>
                        ZHO: {r.catalog_ref.word_en}{r.catalog_ref.word_ar ? ` — ${r.catalog_ref.word_ar}` : ''} ({r.catalog_ref.category})
                        {r.information_loss && r.information_loss !== 'FULL' && (
                          <> · <span title="This match preserves the core meaning but not every word (e.g. an intensity modifier was dropped) — see Traceability for detail.">{r.information_loss}</span></>
                        )}
                      </p>
                    )}
                    {r.status === 'FINGERSPELL_CANDIDATE' && r.terminology && (
                      <p className="hint" style={{ margin: '4px 0 0' }}>
                        → {r.terminology.arabic_term} → {r.fingerspell?.letters?.join('-')}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === 'review' && (
        <div>
          <div className="disclaimer-box">{t('developerDisclaimer')}</div>
          <h3>{t('academicReview')}</h3>
          <p className="hint">{t('academicReviewDesc')}</p>
          <h3 style={{ marginTop: 24 }}>{t('signLanguageReview')}</h3>
          <p className="hint">{t('signLanguageReviewDesc')}</p>
          {includedUnits.filter((u: any) => u.review_required || (u.sign_resolution || []).some((r: any) => r.review_required)).map((u: any) => (
            <div className="unit-card" key={u.unit_id}>
              <strong>{u.unit_id} — {u.concept}</strong>
              <p className="source-span-quote">"{u.source_span}"</p>
              {(u.sign_resolution || []).filter((r: any) => r.review_required).map((r: any, i: number) => (
                <div key={i} style={{ marginTop: 6 }}>
                  <StatusChip status={r.status} t={t} /> <strong>{r.term}</strong>
                  <p className="hint">{r.match_reason}</p>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      {tab === 'traceability' && (
        <div>
          <div className="filter-chips">
            {['ALL', 'VERIFIED_SIGN', 'FINGERSPELL_CANDIDATE', 'UNSUPPORTED', 'REVIEW_REQUIRED'].map((f) => (
              <button key={f} className={traceFilter === f ? 'active' : ''} onClick={() => setTraceFilter(f)}>{f === 'ALL' ? t('filterAll') : f}</button>
            ))}
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="trace-table">
              <thead>
                <tr>
                  <th>Segment</th><th>Status</th><th>Term</th><th>Concept</th><th>Educational sentence</th><th>Source span</th>
                </tr>
              </thead>
              <tbody>
                {filteredTrace.slice(0, 60).map((row: any, i: number) => (
                  <tr key={i}>
                    <td>{row.segment_stem}</td>
                    <td><StatusChip status={row.sign_decision.status} t={t} /></td>
                    <td>{row.sign_decision.term}</td>
                    <td>{row.concept}</td>
                    <td>{row.educational_sentence}</td>
                    <td style={{ maxWidth: 260 }}>"{row.source_span}"</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {filteredTrace.length > 60 && <p className="hint">Showing 60 of {filteredTrace.length} segments. Download the full report for the rest.</p>}
        </div>
      )}

      {tab === 'technical' && (
        <div>
          <h3>AI / ML</h3>
          <p><strong>Falcon-H1-7B-Instruct</strong> (local Ollama) — academic content understanding, structuring, semantic decomposition, bounded contextual terminology translation. Never generates motion/keypoints.</p>
          <p><strong>MediaPipe Holistic</strong> — body, hand and face landmark detection from verified human sign footage.</p>
          <h3 style={{ marginTop: 20 }}>Deterministic systems</h3>
          <p>Source hashing, exact source-span verification, ZHO dictionary retrieval, Arabic alphabet mapping, provenance validation, smoothing, scale/anchor normalization, motion sequencing, avatar drawing, ffmpeg assembly.</p>
          <h3 style={{ marginTop: 20 }}>Human</h3>
          <p>Academic expert (curriculum meaning). Arabic/UAE Sign Language expert (linguistic correctness) — not simulated by this prototype.</p>
          {result.stage_timings && (
            <>
              <h3 style={{ marginTop: 20 }}>Measured stage timings (this run)</h3>
              <table className="trace-table">
                <tbody>
                  {Object.entries(result.stage_timings).map(([k, v]) => (
                    <tr key={k}><td>{k}</td><td>{v}s</td></tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
          <h3 style={{ marginTop: 20 }}>Downloads</h3>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {artifacts.map((a) => (
              <a key={a.name} className="btn-secondary" href={api.jobArtifactUrl(jobId!, a.name)} download>
                {a.name}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
