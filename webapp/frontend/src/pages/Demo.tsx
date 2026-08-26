import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, type JobResult, type EnvironmentStatus, type PipelineStage, type EvaluationSummary } from '../api'
import StatusChip from '../components/StatusChip'
import { useT } from '../i18n'

// Presentation mode — assembles ONLY real data already produced by the
// pipeline (same endpoints Results.tsx uses, plus two new static/read-only
// endpoints for pipeline stage metadata and evaluation artifacts). No
// telemetry, metrics, or sign mappings are invented here — every number on
// this page traces back to a JSON file the pipeline itself wrote.
//
// Defaults to the documented hero run (job bdff1892c9da, "A Day With My
// Family Part 2") so a screen recording is deterministic; override with
// ?job=<id> to present a different completed run.
const DEFAULT_HERO_JOB = 'bdff1892c9da'

const SIX_STAGE_SUMMARY: { key: string; label: string; maps: string[] }[] = [
  { key: 'SOURCE', label: 'SOURCE', maps: ['SOURCE'] },
  { key: 'UNDERSTAND', label: 'UNDERSTAND', maps: ['UNDERSTAND'] },
  { key: 'STRUCTURE', label: 'STRUCTURE', maps: ['STRUCTURE'] },
  { key: 'GENERATE', label: 'GENERATE', maps: ['SIGN_PLAN', 'SIGN_RESOLUTION', 'DURATION_PLANNING', 'CLIP_PREP'] },
  { key: 'VALIDATE', label: 'VALIDATE', maps: ['VALIDATE'] },
  { key: 'SIGN_VIDEO', label: 'SIGN VIDEO', maps: ['RENDER', 'TRACEABILITY'] },
]

const SECTIONS = [
  { id: 'source', label: '1. Source' },
  { id: 'generate', label: '2. Generate' },
  { id: 'signvideo', label: '3. Sign Video' },
  { id: 'signplan', label: '4. Sign Plan' },
  { id: 'review', label: '5. Review' },
  { id: 'traceability', label: '6. Traceability' },
  { id: 'evaluation', label: '7. Evaluation' },
  { id: 'architecture', label: '8. Architecture' },
]

function kindBadgeClass(kind: string) {
  if (kind === 'AI') return 'kind-ai'
  if (kind === 'AI_ASSISTED') return 'kind-ai-assisted'
  return 'kind-deterministic'
}

function kindLabel(kind: string) {
  if (kind === 'AI') return 'AI'
  if (kind === 'AI_ASSISTED') return 'AI-ASSISTED'
  return 'DETERMINISTIC'
}

export default function Demo() {
  const [params] = useSearchParams()
  const jobId = params.get('job') || DEFAULT_HERO_JOB
  const t = useT()

  const [result, setResult] = useState<JobResult | null>(null)
  const [trace, setTrace] = useState<any>(null)
  const [env, setEnv] = useState<EnvironmentStatus | null>(null)
  const [stages, setStages] = useState<PipelineStage[]>([])
  const [evaluation, setEvaluation] = useState<EvaluationSummary | null>(null)
  const [activeSection, setActiveSection] = useState(0)
  const [expandedSegment, setExpandedSegment] = useState<number | null>(null)

  useEffect(() => {
    api.jobResult(jobId).then(setResult).catch(() => {})
    api.jobTraceability(jobId).then(setTrace).catch(() => {})
    api.environment().then(setEnv).catch(() => {})
    api.pipelineStages().then(setStages).catch(() => {})
    api.evaluation().then(setEvaluation).catch(() => {})
  }, [jobId])

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
        e.preventDefault()
        goTo(Math.min(activeSection + 1, SECTIONS.length - 1))
      } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
        e.preventDefault()
        goTo(Math.max(activeSection - 1, 0))
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSection])

  function goTo(i: number) {
    setActiveSection(i)
    document.getElementById(SECTIONS[i].id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const cov = result?.validation?.checks?.coverage
  const dp = result?.validation?.duration_plan
  const status = result?.validation?.overall_status
  const units = result?.episode?.units || []
  const includedUnits = units.filter((u: any) => u.included_in_episode !== false)
  const reviewUnits = includedUnits.filter(
    (u: any) => u.review_required || (u.sign_resolution || []).some((r: any) => r.review_required),
  )

  // Per-stage duration deltas — stage_timings.json stores CUMULATIVE elapsed
  // seconds since pipeline start, not per-stage durations, so we diff
  // consecutive real values rather than displaying the raw cumulative
  // numbers as if they were per-stage costs.
  const stageDeltas = useMemo(() => {
    if (!result?.stage_timings) return {}
    const order = ['ENVIRONMENT_CHECK', 'SOURCE', 'UNDERSTAND', 'STRUCTURE', 'SIGN_PLAN', 'SIGN_RESOLUTION',
      'DURATION_PLANNING', 'VALIDATE', 'CLIP_PREP', 'RENDER', 'TRACEABILITY']
    const out: Record<string, number> = {}
    let prev = 0
    for (const stage of order) {
      const v = result.stage_timings[stage]
      if (v == null) continue
      out[stage] = Math.max(0, +(v - prev).toFixed(2))
      prev = v
    }
    return out
  }, [result])

  // Approximate cumulative position of each included unit within the final
  // episode, derived from each unit's own estimated_duration_s (real field
  // already produced by the pipeline) — an honest derived estimate, clearly
  // labeled "approx.", never a fabricated exact timecode.
  const approxTimecodes = useMemo(() => {
    const out: Record<string, number> = {}
    let cursor = 0
    for (const u of includedUnits) {
      out[u.unit_id] = cursor
      cursor += u.estimated_duration_s || 0
    }
    return out
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result])

  function fmtTimecode(s: number) {
    const m = Math.floor(s / 60)
    const sec = Math.floor(s % 60)
    return `${m}:${String(sec).padStart(2, '0')}`
  }

  // Collapse consecutive segments that are genuinely identical (same term,
  // status, source, concept, unit) — the traceability.json produced by this
  // run legitimately repeats a segment once per underlying sub-unit (e.g.
  // one row per fingerspelled letter sharing the same term label). Grouping
  // them for display is a UI-only simplification — the count badge is
  // computed directly from the real duplicate rows, not fabricated — kept
  // separate from the raw data so nothing about the underlying relationships
  // is altered or hidden.
  const groupedSegments = useMemo(() => {
    const segs: any[] = trace?.segments || []
    const groups: { seg: any; count: number }[] = []
    for (const seg of segs) {
      const last = groups[groups.length - 1]
      const key = (s: any) => `${s.unit_id}|${s.sign_decision?.term}|${s.sign_decision?.status}|${s.render_source}|${s.concept}`
      if (last && key(last.seg) === key(seg)) {
        last.count += 1
      } else {
        groups.push({ seg, count: 1 })
      }
    }
    return groups
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trace])

  if (!result) {
    return <div className="demo-loading">Loading demo run {jobId}…</div>
  }

  const ch3 = evaluation?.experiments?.find((e) => e.name.startsWith('Local model selection'))
  const resQ = evaluation?.experiments?.find((e) => e.name.startsWith('MediaPipe resolution'))
  const abTest = evaluation?.experiments?.find((e) => e.name.startsWith('Vocabulary retrieval'))
  const testSuite = evaluation?.experiments?.find((e) => e.name.startsWith('Automated regression'))
  const durationNote = evaluation?.experiments?.find((e) => e.name.startsWith('Duration-planner'))

  return (
    <div className="demo-root">
      <div className="demo-sidenav" aria-label="Demo sections">
        {SECTIONS.map((s, i) => (
          <button
            key={s.id}
            className={activeSection === i ? 'active' : ''}
            onClick={() => goTo(i)}
            title={s.label}
          >
            <span className="demo-dot" />
          </button>
        ))}
      </div>

      {/* ============ 1. SOURCE ============ */}
      <section id="source" className="demo-section demo-intro">
        <p className="demo-eyebrow">MoE AI Center of Excellence — Technical Case Study</p>
        <h1 className="demo-title">AI-Powered UAE Sign Language Academic Video Generator</h1>
        <p className="demo-subtitle">Verified academic content to traceable sign-language video using local AI</p>

        <div className="demo-stage-strip">
          {SIX_STAGE_SUMMARY.map((s, i) => (
            <div className="demo-stage-strip-item" key={s.key}>
              <div className="demo-stage-strip-badge">{s.label}</div>
              {i < SIX_STAGE_SUMMARY.length - 1 && <div className="demo-stage-strip-arrow">→</div>}
            </div>
          ))}
        </div>

        <div className="demo-card-row">
          <div className="card demo-card">
            <h3>Verified source input</h3>
            <p className="hint">{result.source_manifest?.source_path}</p>
            <p className="hint">SHA-256: {result.source_manifest?.source_id}</p>
            <ul className="demo-bullets">
              <li>Source language: <strong>{(result.source_manifest?.source_language || '').toUpperCase()}</strong> (English / Arabic supported)</li>
              <li>Requested lesson duration: <strong>{dp?.requested_duration_s ?? '—'}s</strong></li>
              <li>Actual rendered duration: <strong>{dp?.actual_duration_s ?? '—'}s</strong></li>
            </ul>
          </div>
          <div className="card demo-card">
            <h3>Review mode</h3>
            <p><strong>STRICT</strong> — {'"'}Stop when expert review is required.{'"'}</p>
            <p><strong>PROTOTYPE</strong> — {'"'}Render a review-marked prototype where safe.{'"'}</p>
          </div>
        </div>
      </section>

      {/* ============ 2. GENERATE ============ */}
      <section id="generate" className="demo-section">
        <h2 className="demo-section-title">2. Generate — Pipeline Progress</h2>
        <p className="demo-section-sub">
          Real stages from this completed run. Timings below are the actual measured per-stage durations
          (diffed from stage_timings.json) — not a simulated progress animation.
        </p>
        <div className="demo-pipeline-list">
          {stages.map((s) => (
            <div className="demo-pipeline-row" key={s.stage}>
              <div className="demo-pipeline-stage">{s.stage.replace(/_/g, ' ')}</div>
              <span className={`kind-badge ${kindBadgeClass(s.kind)}`}>{kindLabel(s.kind)}</span>
              <div className="demo-pipeline-detail hint">{s.label}</div>
              <div className="demo-pipeline-time">
                {stageDeltas[s.stage] != null ? `${stageDeltas[s.stage]}s` : '—'}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ============ 3. SIGN VIDEO ============ */}
      <section id="signvideo" className="demo-section">
        <h2 className="demo-section-title">3. Sign Video</h2>

        <div className="demo-evidence-row">
          <div className="demo-evidence-item">
            <div className="demo-evidence-value">{includedUnits.filter((u: any) => u.source_span_verified).length}/{includedUnits.length}</div>
            <div className="demo-evidence-label">Source Grounded</div>
          </div>
          <div className="demo-evidence-item">
            <div className="demo-evidence-value">Local</div>
            <div className="demo-evidence-label">{(result.understanding_summary?.model || '').split('/').pop()}</div>
          </div>
          <div className="demo-evidence-item">
            <div className="demo-evidence-value">{cov?.verified_lexical_sign_coverage_pct ?? '—'}%</div>
            <div className="demo-evidence-label">Sign Coverage</div>
          </div>
          <div className="demo-evidence-item">
            <div className="demo-evidence-value">{cov?.renderable_coverage_with_fallback_pct ?? '—'}%</div>
            <div className="demo-evidence-label">Traceability (fallback-inclusive)</div>
          </div>
          <div className="demo-evidence-item">
            <div className="demo-evidence-value">{cov?.review_required_units ?? 0}</div>
            <div className="demo-evidence-label">Review Items</div>
          </div>
          <div className="demo-evidence-item">
            <div className="demo-evidence-value">{dp?.requested_duration_s ?? '—'}s / {dp?.actual_duration_s ?? '—'}s</div>
            <div className="demo-evidence-label">Target / Actual Duration</div>
          </div>
        </div>

        <h3 className="demo-video-label">Generated Sign-Language Episode</h3>
        {status !== 'PASS' && (
          <div className="status-banner warn demo-review-flag">
            <div>
              <strong>REVIEW REQUIRED</strong>
              <p style={{ margin: '4px 0 0', fontWeight: 400 }}>
                Video generated as a technical prototype. Expert sign-language review is required before educational release.
              </p>
            </div>
          </div>
        )}
        {result.has_video ? (
          <video className="lesson-video demo-video" controls src={api.jobVideoUrl(jobId)} />
        ) : (
          <div className="card">No video was rendered for this run.</div>
        )}
      </section>

      {/* ============ 4. SIGN PLAN ============ */}
      <section id="signplan" className="demo-section">
        <h2 className="demo-section-title">4. Sign Plan</h2>
        <p className="demo-section-sub">Unsupported terminology is flagged rather than silently invented.</p>
        {includedUnits.map((u: any) => (
          <div className="unit-card" key={u.unit_id}>
            <strong>{u.educational_sentence}</strong>
            <div className="demo-signplan-grid">
              {(u.sign_resolution || []).map((r: any, i: number) => {
                const provenance = r.supplementary_ref ? 'ESL_ZAYED' : r.catalog_ref ? 'ZHO' : undefined
                const source = r.catalog_ref
                  ? `ZHO catalog — ${r.catalog_ref.word_en}${r.catalog_ref.category ? ` (${r.catalog_ref.category})` : ''}`
                  : r.supplementary_ref
                    ? `ESL Zayed — ${r.supplementary_ref.source_url || r.supplementary_ref.supplementary_id}`
                    : r.terminology
                      ? `Fingerspelled: ${r.terminology.arabic_term}`
                      : '—'
                const confidence = r.supplementary_ref?.confidence || r.match_method || '—'
                return (
                  <div key={i} className="demo-signplan-item">
                    <div className="demo-signplan-term">{r.term}</div>
                    <StatusChip status={r.status} t={t} provenance={provenance} />
                    <div className="hint demo-signplan-field"><strong>Source:</strong> {source}</div>
                    <div className="hint demo-signplan-field"><strong>Confidence:</strong> {confidence}</div>
                    <div className="hint demo-signplan-field"><strong>Review:</strong> {r.review_required ? 'Required' : 'Not required'}</div>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </section>

      {/* ============ 5. REVIEW ============ */}
      <section id="review" className="demo-section">
        <h2 className="demo-section-title">5. Review — Human in the Loop</h2>
        <div className="demo-card-row">
          <div className="card demo-card">
            <h3>STRICT</h3>
            <p>Generation/render is blocked when expert review is required.</p>
          </div>
          <div className="card demo-card">
            <h3>PROTOTYPE</h3>
            <p>A clearly review-marked prototype may continue where allowed.</p>
          </div>
        </div>
        <div className="disclaimer-box">
          This prototype's developer is not a qualified Arabic Sign Language linguist. No output here is proof of linguistic correctness.
        </div>
        {reviewUnits.length === 0 && <p className="hint">No review-flagged items in this run.</p>}
        {reviewUnits.map((u: any) => (
          <div className="unit-card demo-review-card" key={u.unit_id}>
            <strong>{u.unit_id} — {u.concept}</strong>
            <p className="source-span-quote">"{u.source_span}"</p>
            {(u.sign_resolution || []).filter((r: any) => r.review_required).map((r: any, i: number) => (
              <div key={i} style={{ marginTop: 6 }}>
                <StatusChip status={r.status} t={t} provenance={r.supplementary_ref ? 'ESL_ZAYED' : r.catalog_ref ? 'ZHO' : undefined} />{' '}
                <strong>{r.term}</strong>
                <p className="hint">{r.match_reason}</p>
              </div>
            ))}
          </div>
        ))}
      </section>

      {/* ============ 6. TRACEABILITY ============ */}
      <section id="traceability" className="demo-section">
        <h2 className="demo-section-title">6. Traceability</h2>
        <p className="demo-section-sub">Click a row to expand its full provenance chain. Timecodes are approximate, derived from each unit's own estimated duration.</p>
        <div className="demo-trace-chain-list">
          {groupedSegments.slice(0, 30).map(({ seg, count }, i: number) => {
            const tc = seg.unit_id != null ? approxTimecodes[seg.unit_id] : undefined
            const expanded = expandedSegment === i
            return (
              <div className="demo-trace-chain-row" key={i}>
                <button className="demo-trace-chain-summary" onClick={() => setExpandedSegment(expanded ? null : i)}>
                  <span className="demo-chain-step">"{(seg.source_span || '').slice(0, 60)}{(seg.source_span || '').length > 60 ? '…' : ''}"</span>
                  <span className="demo-chain-arrow">→</span>
                  <span className="demo-chain-step">{seg.concept}</span>
                  <span className="demo-chain-arrow">→</span>
                  <span className="demo-chain-step">{seg.sign_decision?.term}</span>
                  <span className="demo-chain-arrow">→</span>
                  <span className="demo-chain-step">{seg.render_source || 'fallback'}</span>
                  <span className="demo-chain-arrow">→</span>
                  <span className="demo-chain-step">{tc != null ? `~${fmtTimecode(tc)}` : '—'}</span>
                  <StatusChip status={seg.sign_decision?.status} t={t} provenance={seg.render_source} />
                  {count > 1 && <span className="demo-chain-count">× {count} segments</span>}
                </button>
                {expanded && (
                  <div className="demo-trace-detail">
                    <p><strong>Selection reason:</strong> {seg.selection_reason || '—'}</p>
                    <p><strong>Match reason:</strong> {seg.sign_decision?.match_reason || '—'}</p>
                    {seg.gap_reason && <p><strong>Gap reason:</strong> {seg.gap_reason}</p>}
                    <p><strong>Source authority:</strong> {seg.source_authority || '—'}</p>
                    <p><strong>Verification status:</strong> {seg.verification_status || '—'}</p>
                    {count > 1 && <p className="hint">This term repeats across {count} underlying segments in traceability.json (e.g. one per fingerspelled letter) — shown once here for clarity.</p>}
                  </div>
                )}
              </div>
            )
          })}
        </div>
        {groupedSegments.length > 30 && (
          <p className="hint">Showing 30 of {groupedSegments.length} grouped rows ({trace?.segments?.length} raw segments) — full report in traceability.json.</p>
        )}
      </section>

      {/* ============ 7. EVALUATION ============ */}
      <section id="evaluation" className="demo-section">
        <h2 className="demo-section-title">7. Evaluation</h2>

        {ch3?.available && (
          <div className="card demo-card" style={{ marginBottom: 16 }}>
            <h3>{ch3.name}</h3>
            <p className="hint">{ch3.description}</p>
            <p className="hint">Dataset: {ch3.dataset}</p>
            <div style={{ overflowX: 'auto' }}>
              <table className="trace-table">
                <thead>
                  <tr><th>Model</th><th>Source-span match</th><th>Cosine sim.</th><th>ROUGE-1</th><th>BLEU</th></tr>
                </thead>
                <tbody>
                  {Object.entries(ch3.models || {}).map(([model, m]: [string, any]) => (
                    <tr key={model} style={model === ch3.selected_model ? { fontWeight: 700 } : undefined}>
                      <td>{model}{model === ch3.selected_model ? ' (selected)' : ''}</td>
                      <td>{m.source_span_verbatim_match_rate_pct}%</td>
                      <td>{m.cosine_similarity}</td>
                      <td>{m.rouge1_f1}</td>
                      <td>{m.bleu}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <div className="demo-card-row">
          <div className="card demo-card">
            <h3>{resQ?.name}</h3>
            <p className="hint">{resQ?.description}</p>
            <p className="hint">{resQ?.available ? `Artifact: ${resQ.artifact}` : 'Not available in this repository.'}</p>
          </div>
          <div className="card demo-card">
            <h3>{abTest?.name}</h3>
            <p className="hint">{abTest?.description}</p>
            <p className="hint">{abTest?.available ? `Artifact: ${abTest.artifact}` : 'Not available in this repository.'}</p>
          </div>
        </div>
        <div className="demo-card-row">
          <div className="card demo-card">
            <h3>{testSuite?.name}</h3>
            <p className="hint">{testSuite?.description}</p>
            {testSuite?.available ? (
              <p><strong>{testSuite.result?.passed}/{testSuite.result?.total} passing</strong> ({testSuite.result?.generated_at})</p>
            ) : (
              <p className="hint">Not yet run in this environment.</p>
            )}
          </div>
          <div className="card demo-card">
            <h3>{durationNote?.name}</h3>
            <p className="hint">{durationNote?.description}</p>
          </div>
        </div>
      </section>

      {/* ============ 8. ARCHITECTURE / LOCAL AI ============ */}
      <section id="architecture" className="demo-section">
        <h2 className="demo-section-title">8. Architecture / Local AI</h2>

        <div className="demo-arch-grid">
          <div className="demo-arch-row"><div>SOURCE</div><div className="hint">Deterministic ingestion</div></div>
          <div className="demo-arch-row"><div>UNDERSTAND</div><div className="hint">Falcon — local AI</div></div>
          <div className="demo-arch-row"><div>STRUCTURE</div><div className="hint">Falcon — local AI</div></div>
          <div className="demo-arch-row"><div>SIGN RESOLUTION</div><div className="hint">Embedding retrieval + deterministic vocabulary authority</div></div>
          <div className="demo-arch-row"><div>VALIDATE</div><div className="hint">Rules + confidence gates</div></div>
          <div className="demo-arch-row"><div>RENDER</div><div className="hint">MediaPipe motion + deterministic avatar renderer</div></div>
        </div>

        <p className="demo-statement">AI proposes. Verified data authorizes. Deterministic validation gates output.</p>

        <div className="card demo-card">
          <h3>Local model</h3>
          <p><strong>{env?.model || result.understanding_summary?.model}</strong> — served locally via Ollama.</p>
        </div>

        <p className="demo-statement demo-statement-alt">Core inference runs locally. No external generative API performs the core pipeline.</p>

        <div className="demo-card-row">
          <div className="card demo-card">
            <h3>Security / Data</h3>
            <ul className="demo-bullets">
              <li>Core AI inference runs locally (Ollama) — no external generative API in the core pipeline.</li>
              <li>Uploads limited to .txt/.md, 2MB max; filenames sanitized before use.</li>
              <li>Downloadable artifacts are restricted to an explicit allowlist — no arbitrary filesystem access.</li>
              <li>May access the public UAE ZHO government sign-language dictionary to retrieve sign clips not already cached locally.</li>
            </ul>
          </div>
          <div className="card demo-card">
            <h3>Production Path</h3>
            <div className="demo-roadmap">
              {['Prototype Today', 'Interpreter Review', 'Vocabulary Expansion', 'Evaluation Dataset', 'Fine-tuning / Improved Motion Model', 'Controlled Production Deployment'].map((step, i, arr) => (
                <span key={step} className="demo-roadmap-step">
                  {step}{i < arr.length - 1 ? ' →' : ''}
                </span>
              ))}
            </div>
            <p className="hint" style={{ marginTop: 10 }}>Roadmap — not functionality implemented today.</p>
          </div>
        </div>
      </section>
    </div>
  )
}
