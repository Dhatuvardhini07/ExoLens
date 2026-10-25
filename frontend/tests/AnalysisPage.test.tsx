import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { AnalysisPage } from '../src/features/AnalysisPage'
import { ResultsProvider } from '../src/features/results-store'

afterEach(() => {
  cleanup()
  localStorage.clear()
  vi.unstubAllGlobals()
})

describe('AnalysisPage terminal job handling', () => {
  it('shows API failure details when a failed job has no result object', async () => {
    const job = {
      analysis_id: 'failed-job-123', status: 'failed',
      created_at_utc: '2026-10-25T00:00:00Z', updated_at_utc: '2026-10-25T00:00:01Z',
      result: null,
      errors: [{ code: 'NO_LIGHT_CURVE', message: 'No product for this target.', retryable: false }],
    }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => job }))
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(<QueryClientProvider client={client}><ResultsProvider><MemoryRouter initialEntries={['/analysis/failed-job-123']}><Routes><Route path="/analysis/:analysisId" element={<AnalysisPage/>}/></Routes></MemoryRouter></ResultsProvider></QueryClientProvider>)

    expect(await screen.findByText('The analysis could not be completed')).toBeTruthy()
    expect(screen.getByText(/NO_LIGHT_CURVE: No product for this target\./)).toBeTruthy()
  })
})
