import { z } from 'zod'

const nullableNumber = z.number().nullable().optional()
const uncertainty = z.object({
  value: nullableNumber,
  lower: nullableNumber,
  upper: nullableNumber,
  unit: z.string(),
  method: z.string().optional(),
  confidence_level: nullableNumber,
})
const chartPoint = z.object({ time: z.number(), flux: z.number() })
const resultShape = z.object({
  schema_version: z.string(), analysis_id: z.string(), created_at_utc: z.string(), data_kind: z.enum(['real_observation', 'synthetic_test']),
  target: z.object({ tic_id: z.string().nullable(), display_name: z.string().nullable().optional() }),
  provenance: z.object({ mission: z.string().nullable(), sector: z.number().nullable(), data_author: z.string().nullable(), product_id: z.string().nullable(), archive_url: z.string().nullable().optional(), source_type: z.enum(['mast_product', 'local_file', 'synthetic_fixture']), source_filename: z.string().nullable(), retrieved_at_utc: z.string().nullable(), source_file_sha256: z.string().nullable().optional(), cadence_seconds: nullableNumber, time_system: z.string().nullable(), time_start: nullableNumber, time_end: nullableNumber }),
  pipeline: z.object({ name: z.string(), version: z.string(), bls_period_range_days: z.tuple([z.number(), z.number()]).nullable().optional(), bls_duration_range_hours: z.tuple([z.number(), z.number()]).nullable().optional(), bls_n_periods: z.number().nullable().optional(), bls_n_durations: z.number().nullable().optional(), preprocessing: z.array(z.unknown()).optional(), measurement_methods: z.record(z.string(), z.string()).optional(), software: z.record(z.string(), z.string()).optional() }),
  data_quality: z.object({ input_points: z.number().nullable(), used_points: z.number().nullable(), removed_nan_points: z.number().nullable(), removed_quality_flag_points: z.number().nullable(), time_span_days: nullableNumber, gap_count: z.number().nullable(), warnings: z.array(z.string()) }),
  analysis_status: z.enum(['completed', 'no_signal', 'failed']),
  event: z.object({ signal_status: z.enum(['candidate_signal', 'no_signal', 'not_evaluated']), period_days: nullableNumber, epoch_time: nullableNumber, duration_hours: nullableNumber, depth_fraction: nullableNumber, depth_method: z.string().nullable().optional(), depth_unavailable_reason: z.string().nullable().optional(), bls: z.object({ power: nullableNumber, best_period_days: nullableNumber, best_duration_hours: nullableNumber, transit_time: nullableNumber, depth_fraction: nullableNumber }), uncertainties: z.object({ period_days: uncertainty, depth_fraction: uncertainty, duration_hours: uncertainty, epoch_time: uncertainty }), significance: z.object({ snr: nullableNumber, false_alarm_probability: nullableNumber, method: z.string().nullable().optional() }).optional() }).nullable(),
  validation: z.object({ status: z.enum(['unvalidated', 'catalog_match', 'independently_validated']), source_name: z.string().nullable().optional(), source_url: z.string().nullable().optional(), checked_at_utc: z.string().nullable().optional(), notes: z.string().nullable().optional() }),
  errors: z.array(z.object({ code: z.string(), message: z.string(), retryable: z.boolean() })),
  chart_data: z.object({
    time_system: z.string().nullable().optional(),
    observations: z.array(z.object({ time: z.number(), flux: z.number() })).optional(),
    periodogram: z.array(z.object({ period_days: z.number(), power: z.number() })).optional(),
    phase_folded: z.array(z.object({ phase: z.number(), flux: z.number() })).optional(),
    model_curve: z.array(chartPoint).nullable().optional(),
    unavailable_reasons: z.record(z.string(), z.string()).optional(),
  }).nullable().optional(),
})
export const analysisResultSchema = resultShape.superRefine((record, ctx) => {
  if (record.data_kind === 'synthetic_test' && record.provenance.source_type !== 'synthetic_fixture') ctx.addIssue({ code: 'custom', message: 'Synthetic test data must use synthetic_fixture provenance.', path: ['provenance', 'source_type'] })
  if (record.data_kind === 'real_observation' && record.provenance.source_type === 'synthetic_fixture') ctx.addIssue({ code: 'custom', message: 'Real observations cannot use synthetic_fixture provenance.', path: ['provenance', 'source_type'] })
  if (record.analysis_status === 'failed' && (!record.errors.length || record.event !== null)) ctx.addIssue({ code: 'custom', message: 'Failed results require errors and cannot contain event measurements.', path: ['analysis_status'] })
  if (record.analysis_status === 'completed' && record.event === null) ctx.addIssue({ code: 'custom', message: 'Completed results must include the returned BLS event model.', path: ['event'] })
  if (record.analysis_status !== 'failed' && record.errors.length) ctx.addIssue({ code: 'custom', message: 'Only failed results may contain errors.', path: ['errors'] })
})
export type AnalysisResult = z.infer<typeof analysisResultSchema>
export const jobSchema = z.object({ analysis_id: z.string(), status: z.enum(['queued', 'running', 'completed', 'no_signal', 'failed']), created_at_utc: z.string().optional(), updated_at_utc: z.string().optional(), result: analysisResultSchema.nullable(), errors: z.array(z.object({ code: z.string(), message: z.string(), retryable: z.boolean() })).default([]) })
export type AnalysisJob = z.infer<typeof jobSchema>
