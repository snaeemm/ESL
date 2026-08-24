const MAP: Record<string, { cls: string; icon: string; key: 'verifiedSign' | 'fingerspelled' | 'reviewRequiredStatus' | 'unsupported' | 'supplementarySign' }> = {
  VERIFIED_SIGN: { cls: 'verified', icon: '✓', key: 'verifiedSign' },
  FINGERSPELL_CANDIDATE: { cls: 'fingerspell', icon: '◇', key: 'fingerspelled' },
  REVIEW_REQUIRED: { cls: 'review', icon: '!', key: 'reviewRequiredStatus' },
  UNSUPPORTED: { cls: 'unsupported', icon: '×', key: 'unsupported' },
}

// Blocker D: a VERIFIED_SIGN whose provenance is ESL_ZAYED (observed
// Emirati educational source - supplementary, NOT independently verified)
// must NOT render as the same "✓ VERIFIED SIGN" badge as a ZHO
// institutional match. Previously the two were only distinguished by
// secondary hint text next to/below the chip, so the PRIMARY badge itself
// was indistinguishable at a glance. This gives ESL Zayed its own visually
// distinct badge (different icon/class/label), while ZHO keeps the
// existing "✓ VERIFIED SIGN" badge unchanged.
const SUPPLEMENTARY_ESL_ZAYED = { cls: 'supplementary', icon: '◐', key: 'supplementarySign' as const }

export default function StatusChip({ status, t, provenance }: { status: string; t: (k: any) => string; provenance?: 'ZHO' | 'ESL_ZAYED' | string }) {
  const m = (status === 'VERIFIED_SIGN' && provenance === 'ESL_ZAYED')
    ? SUPPLEMENTARY_ESL_ZAYED
    : MAP[status] || { cls: 'review', icon: '?', key: 'reviewRequiredStatus' as const }
  return (
    <span className={`status-chip ${m.cls}`}>
      <span aria-hidden="true">{m.icon}</span> {t(m.key)}
    </span>
  )
}
