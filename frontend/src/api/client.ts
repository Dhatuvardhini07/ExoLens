import { z } from 'zod'
import { analysisResultSchema, jobSchema, type AnalysisJob, type AnalysisResult } from './schema'

const API_ROOT = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')
export const apiUrl = `${API_ROOT}/api/v1`

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${apiUrl}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch {
    throw new Error(`Could not reach the ExoLens API at ${API_ROOT}. Start the backend or check VITE_API_URL.`)
  }
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body?.error?.message ?? `API request failed (${response.status})`)
  return body as T
}

export async function fetchJob(id: string): Promise<AnalysisJob> {
  return jobSchema.parse(await request(`/analyses/${encodeURIComponent(id)}`))
}

export async function startAnalysis(input: {
  tic_id: string
  sector?: number
  author?: string
  period_min_days: number
  period_max_days: number
  duration_min_hours?: number
  duration_max_hours?: number
}): Promise<{ analysis_id: string; status: 'queued'; status_url: string }> {
  const responseSchema = z.object({ analysis_id: z.string(), status: z.literal('queued'), status_url: z.string() })
  const response = await request('/analyses', {
    method: 'POST',
    body: JSON.stringify({
      target: { tic_id: input.tic_id },
      data_selection: { sector: input.sector ?? null, author: input.author ?? null, product_id: null },
      search: {
        period_min_days: input.period_min_days,
        period_max_days: input.period_max_days,
        duration_min_hours: input.duration_min_hours ?? null,
        duration_max_hours: input.duration_max_hours ?? null,
      },
    }),
  })
  return responseSchema.parse(response)
}

export function parseResult(data: unknown): AnalysisResult { return analysisResultSchema.parse(data) }
export async function healthCheck(): Promise<boolean> { try { await request('/health'); return true } catch { return false } }
