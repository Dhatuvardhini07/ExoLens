# ExoLens API contract

The FastAPI service connects the Python engine to the React frontend using versioned JSON under `/api/v1`. Jobs are asynchronous in the API process and are lost when it restarts.

## Endpoints

### `POST /api/v1/analyses`

Start an analysis for a TIC ID. The API checks the configured local cache first and labels a cache hit `local_file`; only when no cached product matches does it use the existing Lightkurve/MAST retrieval path. The client cannot pass arbitrary server paths or arbitrary URLs.

Request:

```json
{
  "target": {"tic_id": "TIC 123456789"},
  "data_selection": {"sector": null, "author": null, "product_id": null},
  "search": {
    "period_min_days": 0.5,
    "period_max_days": 20.0,
    "duration_min_hours": null,
    "duration_max_hours": null
  }
}
```

Sector/author/product ID are optional constraints, not claims a matching product exists. The API first checks the configured local `data/cache` for a matching cached FITS file; that result is labeled `local_file`. If none matches, it calls the existing Lightkurve/MAST loader. Ambiguous cached products fail with an explicit selection error. Search defaults are documented and echoed in the result. The numeric range above is an illustrative request example, not an experimental result.

Response: `202 Accepted`

```json
{
  "analysis_id": "opaque-id",
  "status": "queued",
  "status_url": "/api/v1/analyses/opaque-id"
}
```

### `GET /api/v1/analyses/{analysis_id}`

Poll job status. Return `queued` or `running` while working; on completion return `completed`, `no_signal`, or `failed`, and include the result from `docs/output-schema.md` when available.

```json
{
  "analysis_id": "opaque-id",
  "status": "running",
  "created_at_utc": "2026-01-01T00:00:00Z",
  "updated_at_utc": "2026-01-01T00:00:00Z",
  "result": null,
  "errors": []
}
```

IDs/timestamps are illustrative placeholders. The API must not return fabricated measurements.

### `GET /api/v1/analyses/{analysis_id}/result`

Return the completed record following `docs/output-schema.md`. Return `409 Conflict` while running and a structured error if failed.

### `GET /api/v1/health`

Return a minimal readiness response. Do not expose secrets or host details.

## Error format

```json
{
  "error": {
    "code": "NO_LIGHT_CURVE",
    "message": "No light curve was found for the selected target and data options.",
    "retryable": false,
    "details": {}
  }
}
```

Suggested HTTP behavior: `400` invalid input, `404` unknown analysis ID/target, `409` result requested before completion, `422` insufficient usable data, `502` upstream archive/download failure, and `500` unexpected internal error. Keep stack traces and local paths in server logs, not responses.

Jobs and result history are held in process memory. Restarting the API clears them; browser-imported results remain browser-local. The API does not accept filesystem paths from the client.



## API rules

- Validate TIC identifier format; use stable string IDs.
- Include units in field names where possible; the output schema is the shared source of truth.
- Echo the selected data product and BLS settings for reproducibility.
- Represent unavailable values as JSON `null`, with an explanatory warning or error.
- Keep BLS power separate from probabilities and confidence labels.
- Return `data_kind` and provenance to distinguish real observations from synthetic tests.
- Do not return guessed ML classifications. Future classification fields need labelled data, evaluation evidence, and a schema change.
- Never accept client filesystem paths. A later upload feature needs a separate endpoint with size/type checks and a generated server-side identifier.
- Restrict CORS to the known frontend origin in deployment; avoid wildcard origins with credentials.

## Compatibility

Represent API models in Python with Pydantic and validate frontend responses with Zod. Additive optional fields are generally compatible. Renaming fields, changing units/status meanings, or changing uncertainty representation requires a migration or a new API/schema version.
