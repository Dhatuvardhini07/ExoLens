# ExoLens analysis output schema

This JSON record represents one target and one analysis run. Python, the API, exports, and the frontend share the same names and meanings. Unmeasured values are `null`, not guessed. Schema 1.1 adds optional plotted arrays derived from the same cleaned observations and BLS result; schema 1.0 records remain readable.

## Conventions

- Field names use `snake_case`; top-level `schema_version` starts at `1.0`.
- `null` means unavailable or not calculated; it does not mean zero.
- Periods use days, durations hours, depth a fractional decrease in normalized flux, and BLS power is unitless.
- Time values must name their system. TESS data often use BTJD (`BJD - 2457000`), but use the source product's actual time system.
- Record provenance, pipeline version/settings, and quality information for every result.

## Top-level fields

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `schema_version` | string | yes | Contract version, initially `1.0`; `1.1` adds chart arrays. |
| `analysis_id` | string | yes | Unique analysis run identifier. |
| `created_at_utc` | ISO 8601 string | yes | Result creation time in UTC. |
| `data_kind` | enum | yes | `real_observation` or `synthetic_test`. |
| `target` | object | yes | TIC and optional display name. |
| `provenance` | object | yes | Mission, sector, product, source, and time metadata. |
| `pipeline` | object | yes | Software, search settings, preprocessing, and measurement methods. |
| `data_quality` | object | yes | Counts, coverage, gaps, and warnings. |
| `analysis_status` | enum | yes | `completed`, `no_signal`, or `failed`. |
| `event` | object or null | yes | Measurements if a signal is returned; otherwise null. |
| `validation` | object | yes | Validation state and optional external catalog evidence. |
| `errors` | array | yes | Structured errors; empty if none. |
| `chart_data` | object or null | schema 1.1 | Chart arrays from this same cleaned curve and BLS fit. |

## `target`

| Field | Type | Meaning |
|---|---|---|
| `tic_id` | string or null | TIC identifier, for example `TIC 123456789`; null for synthetic data without a real target. |
| `display_name` | string or null | Optional display name; does not replace TIC ID. |

## `provenance`

| Field | Type | Meaning |
|---|---|---|
| `mission` | string or null | Mission, expected to be `TESS` for the first release. |
| `sector` | integer or null | Sector stated by the selected product. |
| `data_author` | string or null | Archive-reported product pipeline/author. |
| `product_id` | string or null | Archive product identifier. |
| `archive_url` | string or null | Link to the actual product/archive record. |
| `source_type` | enum | `mast_product`, `local_file`, or `synthetic_fixture`. |
| `source_filename` | string or null | Local basename only (never a server path); archive product name if available. |
| `retrieved_at_utc` | ISO 8601 string or null | Retrieval time; null if unknown/not applicable. |
| `source_file_sha256` | string or null | Optional hash of exact source file. |
| `cadence_seconds` | number or null | Observation cadence in seconds. |
| `time_system` | string or null | Explicit system, e.g. `BTJD (BJD - 2457000)`. |
| `time_start`, `time_end` | number or null | Time bounds in `time_system`. |

For a local file, record its filename without exposing a server path, source type, and hash when practical. Do not infer sector or product unless metadata supports it. A local synthetic test file must use `data_kind=synthetic_test` and `source_type=synthetic_fixture`.

## `pipeline`

| Field | Type | Meaning |
|---|---|---|
| `name` | string | `ExoLens`. |
| `version` | string | Release version or Git commit. |
| `bls_period_range_days` | two-number array or null | Searched period range in days. |
| `bls_duration_range_hours` | two-number array or null | Searched duration range in hours. |
| `bls_n_periods` | integer or null | Number of trial periods in the BLS grid. |
| `bls_n_durations` | integer or null | Number of trial durations in the BLS grid. |
| `preprocessing` | array | Ordered operations and settings, such as quality masking, NaN removal, and normalization. |
| `measurement_methods` | object | Method names/versions for period, depth, duration, and uncertainty estimates. |
| `software` | object | Names and versions of Python, Astropy, Lightkurve, NumPy, and ExoLens. |

## `data_quality`

| Field | Type/unit | Meaning |
|---|---|---|
| `input_points` | integer or null | Number of source observations. |
| `used_points` | integer or null | Points passed to analysis after documented filters. |
| `removed_nan_points` | integer or null | Points removed for invalid/non-finite values. |
| `removed_quality_flag_points` | integer or null | Points rejected by selected quality mask. |
| `time_span_days` | number or null | Span of usable observation times. |
| `gap_count` | integer or null | Count using a documented time-gap threshold; null until defined. |
| `warnings` | string array | Short coverage, gaps, sparse sampling, or other limitations. |

Document whether rejection counts overlap. Do not imply counts sum to all removed observations if one point can have multiple reasons.

## `event`

| Field | Type/unit | Meaning |
|---|---|---|
| `signal_status` | enum | `candidate_signal`, `no_signal`, or `not_evaluated`; an analysis outcome, not a planet verdict. |
| `period_days` | number or null | Best-fit BLS period in days. |
| `epoch_time` | number or null | Best-fit transit epoch in `provenance.time_system`. |
| `duration_hours` | number or null | Event duration in hours, only if searched/measured. |
| `depth_fraction` | number or null | Flux decrease relative to estimated out-of-transit baseline; `0.01` means 1%. |
| `depth_method` | string or null | Method used for the displayed depth estimate. |
| `depth_unavailable_reason` | string or null | Why a transit-window estimate could not be supported. |
| `bls` | object | Search outputs below. |
| `uncertainties` | object | Uncertainties below. |
| `significance` | object | Optional SNR or false-alarm estimate with method. |

### `event.bls`

| Field | Type | Meaning |
|---|---|---|
| `power` | number or null | Configured BLS statistic. Unitless; **not** probability or confidence. |
| `best_period_days` | number or null | Period at selected BLS peak. |
| `best_duration_hours` | number or null | Duration at selected BLS solution. |
| `transit_time` | number or null | BLS reference time in the declared time system. |
| `depth_fraction` | number or null | BLS-returned depth, distinct from a later refit depth. |

### `event.uncertainties`

Each measurement uncertainty uses the same object structure:

```json
{"value": null, "lower": null, "upper": null, "unit": "days", "method": "not_calculated", "confidence_level": null}
```

Use keys `period_days`, `depth_fraction`, `duration_hours`, and `epoch_time`. `value` is a symmetric one-sigma uncertainty only where the method supports that interpretation. `lower`/`upper` are asymmetric bounds in the measurement's unit. `confidence_level` (such as `0.95`) is allowed only for an interval with a defensible coverage interpretation. Until calculated, keep numbers null and method `not_calculated`.

Name the method (for example, a documented bootstrap or fit covariance). Coarse search-grid spacing is not a measured error bar.

### `event.significance`

| Field | Type | Meaning |
|---|---|---|
| `snr` | number or null | Signal-to-noise only after a specified noise/signal model is applied. |
| `false_alarm_probability` | number or null | Probability only when computed using a documented method. |
| `method` | string or null | Calculation method; required if either value is non-null. |

Never convert raw BLS power to probability, confidence percentage, or SNR.

## `validation`

| Field | Type | Meaning |
|---|---|---|
| `status` | enum | `unvalidated`, `catalog_match`, or `independently_validated`; initial engine emits `unvalidated`. |
| `source_name` | string or null | External catalog/source with a verified match. |
| `source_url` | string or null | Direct supporting record link. |
| `checked_at_utc` | ISO 8601 string or null | Time the source was checked. |
| `notes` | string or null | Distinguishes an external catalog label from ExoLens analysis. |

`catalog_match` means a record was found; it is not ExoLens validation. Do not emit `independently_validated` until a documented scientific validation process exists. A BLS-only result must never be described as a confirmed planet.

## `errors`

Each item has `code`, user-safe `message`, and `retryable`. Suggested codes: `TARGET_NOT_FOUND`, `NO_LIGHT_CURVE`, `DOWNLOAD_FAILED`, `INVALID_LIGHT_CURVE`, `INSUFFICIENT_DATA`, `BLS_FAILED`. Do not expose credentials or server paths.

## Allowed statuses

| Field | Allowed values |
|---|---|
| `analysis_status` | `completed`, `no_signal`, `failed` |
| `event.signal_status` | `candidate_signal`, `no_signal`, `not_evaluated` |
| `validation.status` | `unvalidated`, `catalog_match`, `independently_validated` |
| `data_kind` | `real_observation`, `synthetic_test` |
| `provenance.source_type` | `mast_product`, `local_file`, `synthetic_fixture` |

## Example (schema illustration only)

Null measurements and absent TIC make clear this is not an observation or analysis result.

```json
{
  "schema_version": "1.0",
  "analysis_id": "example-only",
  "created_at_utc": "2026-01-01T00:00:00Z",
  "data_kind": "synthetic_test",
  "target": {"tic_id": null, "display_name": "Schema illustration only"},
  "provenance": {
    "mission": null, "sector": null, "data_author": null, "product_id": null,
    "archive_url": null, "source_type": "synthetic_fixture", "source_filename": "synthetic fixture only", "retrieved_at_utc": null,
    "source_file_sha256": null, "cadence_seconds": null, "time_system": null,
    "time_start": null, "time_end": null
  },
  "pipeline": {
    "name": "ExoLens", "version": "not-yet-implemented",
    "bls_period_range_days": null, "bls_duration_range_hours": null,
    "bls_n_periods": null, "bls_n_durations": null,
    "preprocessing": [], "measurement_methods": {}, "software": {}
  },
  "data_quality": {
    "input_points": null, "used_points": null, "removed_nan_points": null,
    "removed_quality_flag_points": null, "time_span_days": null,
    "gap_count": null, "warnings": ["Schema illustration; no curve analyzed."]
  },
  "analysis_status": "failed",
  "event": null,
  "validation": {
    "status": "unvalidated", "source_name": null, "source_url": null,
    "checked_at_utc": null, "notes": "No target or observation is represented."
  },
  "errors": [{"code": "NO_LIGHT_CURVE", "message": "Schema illustration only; no analysis was run.", "retryable": false}]
}
```

## `chart_data` (schema 1.1, optional)

Successful analyses include these arrays when they can be calculated from the same preprocessed light curve and BLS result used for the measurement fields. They are `null` on analysis failure or omitted only when a chart cannot be built; no points are synthesized to fill gaps.

| Field | Point fields | Meaning |
|---|---|---|
| `time_system` | string or null | Same time system as `provenance.time_system`. `time` values are in that system and in days. |
| `observations` | `time`, `flux` | Every retained, quality-filtered observation. Flux is the median-normalized flux used by BLS. These are data, not model points. |
| `periodogram` | `period_days`, `power` | Astropy BLS power for each searched trial period, maximizing over the configured duration grid. Power is a search statistic, never a probability. |
| `phase_folded` | `phase`, `flux` | The same retained observations folded at the selected BLS period. Phase is in cycles in `[-0.5, 0.5)`, with the fitted epoch at phase zero. |
| `model_curve` | `time`, `flux` or null | Optional fitted box model evaluated over a display grid. It is explicitly a model, not observed data. Built from the selected BLS period, epoch, duration, BLS box depth, and the observed out-of-transit median. |
| `unavailable_reasons` | string map | A short reason when the optional model curve cannot be responsibly created. |

The periodogram trial grid is the same grid recorded in `pipeline.bls_period_range_days` and `pipeline.bls_n_periods`. Observation and phase-folded arrays have the same number of entries as `data_quality.used_points`. The model curve may have a different number of points because it is evaluated on a separate display grid.
