import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type HistoryRow } from '../api'
import { useT } from '../i18n'

export default function History() {
  const t = useT()
  const [rows, setRows] = useState<HistoryRow[]>([])

  useEffect(() => {
    api.listJobs().then(setRows).catch(() => {})
  }, [])

  if (rows.length === 0) return <p>{t('historyEmpty')}</p>

  return (
    <div className="history-grid">
      {rows.map((r) => (
        <Link key={r.job_id} to={r.status === 'done' ? `/jobs/${r.job_id}/results` : `/jobs/${r.job_id}/progress`} className="card" style={{ textDecoration: 'none', color: 'inherit' }}>
          <p className="hint">{new Date(r.created_at * 1000).toLocaleString()}</p>
          <p style={{ fontWeight: 600, fontSize: '0.85rem', wordBreak: 'break-all' }}>{r.source_path?.split('/').pop() || r.job_id}</p>
          <p className="hint">{r.status.toUpperCase()} · {r.validation_status || '—'}</p>
          <p className="hint">Requested {r.requested_duration_s ?? '—'}s · Actual {r.actual_duration_s ?? '—'}s</p>
          <p className="hint">Lexical coverage: {r.verified_lexical_sign_coverage_pct ?? '—'}%</p>
        </Link>
      ))}
    </div>
  )
}
