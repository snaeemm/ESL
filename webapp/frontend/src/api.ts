// Thin client over the FastAPI backend (webapp/backend). No business
// logic here — every number shown in the UI comes from these responses,
// which are themselves the pipeline's own JSON artifacts (episode.json,
// validation.json, traceability.json, ...). Nothing is hard-coded.

export interface EnvironmentStatus {
  ok: boolean
  problems: string[]
  model: string
}

export interface JobEvent {
  stage: string
  status: 'running' | 'done' | 'blocked' | 'error'
  message: string
  data: Record<string, any>
  timestamp: string
  elapsed_s?: number
}

export interface JobSnapshot {
  job_id: string
  status: 'queued' | 'running' | 'done' | 'blocked' | 'error'
  created_at: number
  error: string
  params: Record<string, any>
  num_events: number
  last_event: JobEvent | null
}

export interface JobResult {
  job_id: string
  status: string
  error: string
  source_manifest: any
  understanding_summary: { model: string; num_concepts_extracted: number; num_verified: number } | null
  episode: any
  validation: any
  stage_timings: Record<string, number> | null
  has_video: boolean
}

export interface HistoryRow {
  job_id: string
  status: string
  created_at: number
  source_path: string | null
  source_language: string | null
  requested_duration_s: number | null
  actual_duration_s: number | null
  validation_status: string | null
  verified_lexical_sign_coverage_pct: number | null
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(body.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  environment: () => fetch('/api/environment').then((r) => json<EnvironmentStatus>(r)),

  createJob: (form: FormData) =>
    fetch('/api/jobs', { method: 'POST', body: form }).then((r) => json<{ job_id: string; status: string }>(r)),

  jobStatus: (id: string) => fetch(`/api/jobs/${id}`).then((r) => json<JobSnapshot>(r)),
  jobEvents: (id: string) => fetch(`/api/jobs/${id}/events`).then((r) => json<JobEvent[]>(r)),
  jobResult: (id: string) => fetch(`/api/jobs/${id}/result`).then((r) => json<JobResult>(r)),
  jobTraceability: (id: string) => fetch(`/api/jobs/${id}/traceability`).then((r) => json<any>(r)),
  jobReview: (id: string) => fetch(`/api/jobs/${id}/review`).then((r) => json<any>(r)),
  jobArtifacts: (id: string) => fetch(`/api/jobs/${id}/artifacts`).then((r) => json<{ name: string; size_bytes: number }[]>(r)),
  jobVideoUrl: (id: string) => `/api/jobs/${id}/video`,
  jobArtifactUrl: (id: string, name: string) => `/api/jobs/${id}/artifacts/${name}`,

  listJobs: () => fetch('/api/jobs').then((r) => json<HistoryRow[]>(r)),
}
