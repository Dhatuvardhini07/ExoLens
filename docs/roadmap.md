# ExoLens implementation roadmap

Every stage preserves scientific provenance. Synthetic fixtures are test-only; BLS search statistics are not planet confirmations.

## Completed

### Project foundation

Architecture, output schema, API contract, scientific safeguards, and project structure are documented. Original BAH report and notebook remain reference-only.

### Python analysis engine

Local CSV/FITS and Lightkurve/MAST loading, preprocessing, BLS, supported depth estimates, structured failures, JSON/CSV exports, and CLI are implemented. Schema 1.1 also includes real observation, periodogram, phase-folded, and optional separate model-curve arrays.

### React frontend

The five existing pages remain in place. The interface imports validated JSON, presents local history, and renders only arrays returned by the engine.

### FastAPI integration

The API validates requests, checks the local TESS cache before MAST, starts/polls in-process jobs, returns structured failures/results, and serves health and result endpoints. The frontend submits jobs, polls status, stores completed results locally, and shows terminal failures.

## Next: deployment preparation

- Decide on durable job/result storage before multi-worker or public deployment; current jobs live only in the API process.
- Configure deployment-specific CORS, request limits, logging, and monitoring.
- Add CI and supported-version dependency lockfiles.
- Prepare portfolio documentation, screenshots, setup instructions, and a reproducible demo based only on genuine observations or clearly marked synthetic fixtures.

## Scientific work deferred until supported by evidence

- Calibrated uncertainties, SNR, false-alarm probabilities, and detection thresholds.
- Classifier training until labeled data and an evaluation plan are available.
- Any independent validation or planet-confirmation claim.
- Bulk processing of tens of thousands of targets before single-target performance and resource limits are measured.
