import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api, type JobEvent, type JobSnapshot } from '../api'
import { useT } from '../i18n'

const STAGE_ORDER = [
  'ENVIRONMENT_CHECK', 'SOURCE', 'UNDERSTAND', 'STRUCTURE', 'SIGN_PLAN',
  'SIGN_RESOLUTION', 'DURATION_PLANNING', 'VALIDATE', 'CLIP_PREP', 'RENDER',
  'TRACEABILITY', 'DONE',
]

export default function Progress() {
  const { jobId } = useParams()
  const navigate = useNavigate()
  const t = useT()
  const [events, setEvents] = useState<JobEvent[]>([])
  const [snapshot, setSnapshot] = useState<JobSnapshot | null>(null)
  const startRef = useRef<number>(Date.now())
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (!jobId) return
    let stop = false
    async function poll() {
      try {
        const [ev, snap] = await Promise.all([api.jobEvents(jobId!), api.jobStatus(jobId!)])
        if (stop) return
        setEvents(ev)
        setSnapshot(snap)
        if (snap.status === 'done') {
          navigate(`/jobs/${jobId}/results`)
          return
        }
        if (snap.status === 'blocked' || snap.status === 'error') return
      } catch {
        // backend not reachable yet — keep polling
      }
      if (!stop) setTimeout(poll, 1500)
    }
    poll()
    const timer = setInterval(() => setElapsed(Math.round((Date.now() - startRef.current) / 1000)), 1000)
    return () => { stop = true; clearInterval(timer) }
  }, [jobId, navigate])

  const latestByStage: Record<string, JobEvent> = {}
  for (const e of events) latestByStage[e.stage] = e

  const blocked = snapshot?.status === 'blocked' || snapshot?.status === 'error'
  const allDone = latestByStage['DONE']?.status === 'done'

  const mm = Math.floor(elapsed / 60)
  const ss = elapsed % 60
  const elapsedLabel = mm > 0 ? `${mm}m ${ss}s` : `${ss}s`

  return (
    <div style={{ maxWidth: 620, margin: '0 auto' }}>
      <h2 className="page-title" style={{ fontSize: 26 }}>{allDone ? t('stage_DONE') : t('generating')}</h2>
      <p className="hint" style={{ marginTop: -8, marginBottom: 18 }}>{t('elapsed')}: {elapsedLabel}</p>

      {blocked && (
        <div className="status-banner error">
          <div>
            <strong>{snapshot?.status === 'blocked' ? 'Stopped — expert review required or provenance failure' : 'An error occurred'}</strong>
            <p style={{ margin: '4px 0 0' }}>{snapshot?.error}</p>
          </div>
        </div>
      )}

      <div className="card stage-tracker">
        {STAGE_ORDER.map((stage, i) => {
          const ev = latestByStage[stage]
          const isDone = ev?.status === 'done'
          const isBlocked = ev?.status === 'blocked' || ev?.status === 'error'
          const isActive = (ev?.status === 'running' || isBlocked) && !isDone
          const state = isDone ? 'done' : isActive ? 'active' : 'pending'
          const isLast = i === STAGE_ORDER.length - 1
          return (
            <div key={stage} className="stage-row">
              <div className="stage-dot-col">
                <span className={`stage-dot ${state}`} />
                {!isLast && <span className={`stage-connector ${isDone ? 'done' : ''}`} />}
              </div>
              <div className="stage-text">
                <div className={`stage-title ${state}`}>{t(`stage_${stage}` as any)}</div>
                {(state === 'active' || state === 'done') && ev?.message && (
                  <div className={`stage-detail ${state}`}>{ev.message}</div>
                )}
                {state === 'active' && !isBlocked && (
                  <div className="stage-progress-track">
                    <div className="stage-progress-fill" />
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      <p className="footnote">Technical prototype — not an officially deployed Ministry service.</p>

      {blocked && (
        <button className="btn-secondary" style={{ marginTop: 16 }} onClick={() => navigate('/')}>
          Back to Create Lesson
        </button>
      )}
    </div>
  )
}
