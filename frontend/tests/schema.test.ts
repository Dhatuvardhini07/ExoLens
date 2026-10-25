import { describe, expect, it } from 'vitest'
import { analysisResultSchema } from '../src/api/schema'

const syntheticFixture = {
  schema_version: '1.0', analysis_id: 'test-fixture-only', created_at_utc: '2026-01-01T00:00:00Z', data_kind: 'synthetic_test',
  target: { tic_id: null, display_name: 'Synthetic test fixture' },
  provenance: { mission: null, sector: null, data_author: null, product_id: null, archive_url: null, source_type: 'synthetic_fixture', source_filename: 'generated-in-memory-test', retrieved_at_utc: null, source_file_sha256: null, cadence_seconds: null, time_system: 'days (synthetic fixture)', time_start: 0, time_end: 10 },
  pipeline: { name: 'ExoLens', version: 'test', bls_period_range_days: [1, 5], bls_duration_range_hours: [0.5, 3], bls_n_periods: 10, bls_n_durations: 3, preprocessing: [], measurement_methods: {}, software: {} },
  data_quality: { input_points: 0, used_points: 0, removed_nan_points: 0, removed_quality_flag_points: 0, time_span_days: 10, gap_count: 0, warnings: ['Synthetic schema-test fixture only; no astronomical observation represented.'] },
  analysis_status: 'completed', event: { signal_status: 'not_evaluated', period_days: null, epoch_time: null, duration_hours: null, depth_fraction: null, depth_method: null, depth_unavailable_reason: null, bls: { power: null, best_period_days: null, best_duration_hours: null, transit_time: null, depth_fraction: null }, uncertainties: { period_days: { unit: 'days', method: 'not_calculated' }, depth_fraction: { unit: 'fraction', method: 'not_calculated' }, duration_hours: { unit: 'hours', method: 'not_calculated' }, epoch_time: { unit: 'days', method: 'not_calculated' } }, significance: { snr: null, false_alarm_probability: null, method: null } },
  validation: { status: 'unvalidated', source_name: null, source_url: null, checked_at_utc: null, notes: 'Synthetic fixture for schema test only.' }, errors: [],
}
describe('output-schema validation', () => {
  it('accepts a clearly labelled synthetic schema fixture', () => { expect(analysisResultSchema.safeParse(syntheticFixture).success).toBe(true) })
  it('rejects failed results that contain event measurements', () => { const invalid = { ...syntheticFixture, analysis_status: 'failed', errors: [{ code: 'TEST', message: 'Fixture only', retryable: false }] }; expect(analysisResultSchema.safeParse(invalid).success).toBe(false) })
  it('rejects a synthetic data record labelled as an observation', () => { const invalid = { ...syntheticFixture, data_kind: 'real_observation' }; expect(analysisResultSchema.safeParse(invalid).success).toBe(false) })
})
  it('accepts real arrays and a separately labelled fitted model in the additive chart schema', () => {
    const withCharts = { ...syntheticFixture, chart_data: { time_system: 'synthetic test time in days', observations: [{ time: 0, flux: 1 }], periodogram: [{ period_days: 2, power: 0.5 }], phase_folded: [{ phase: 0, flux: 1 }], model_curve: [{ time: 0, flux: 1 }], unavailable_reasons: {} } }
    expect(analysisResultSchema.safeParse(withCharts).success).toBe(true)
  })
