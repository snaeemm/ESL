const MAP: Record<string, { cls: string; icon: string; key: 'verifiedSign' | 'fingerspelled' | 'reviewRequiredStatus' | 'unsupported' }> = {
  VERIFIED_SIGN: { cls: 'verified', icon: '✓', key: 'verifiedSign' },
  FINGERSPELL_CANDIDATE: { cls: 'fingerspell', icon: '◇', key: 'fingerspelled' },
  REVIEW_REQUIRED: { cls: 'review', icon: '!', key: 'reviewRequiredStatus' },
  UNSUPPORTED: { cls: 'unsupported', icon: '×', key: 'unsupported' },
}

export default function StatusChip({ status, t }: { status: string; t: (k: any) => string }) {
  const m = MAP[status] || { cls: 'review', icon: '?', key: 'reviewRequiredStatus' as const }
  return (
    <span className={`status-chip ${m.cls}`}>
      <span aria-hidden="true">{m.icon}</span> {t(m.key)}
    </span>
  )
}
