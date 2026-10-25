# ExoLens Python engine

This package loads local light curves or retrieves a selected TESS product, checks and normalizes observations, runs a configurable Astropy Box Least Squares (BLS) search, estimates transit-window depth when data support it, and exports a provenance-rich JSON result.

A BLS peak is a search result, not calibrated significance or confirmation. The engine does not currently classify events or estimate calibrated uncertainties. Synthetic curves are used only in tests.

## Windows setup in VS Code

Open the project folder in VS Code, choose **Terminal → New Terminal**, and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then activate again. Or skip activation and use `.\.venv\Scripts\python.exe` directly.

Run the automated tests:

```powershell
python -m pytest
```

## Analyze a local CSV

CSV files must have `time` and `flux` columns. Optional columns are `flux_err` and `quality`; non-zero quality flags are rejected. Time values are interpreted as days. State the time system when known; ExoLens does not guess it.

```powershell
exolens analyze-file .\path\to\light_curve.csv --time-system "BTJD (BJD - 2457000)" --period-min-days 0.5 --period-max-days 20 --duration-min-hours 0.5 --duration-max-hours 6 --output .\data\results\analysis.json
```

Add `--tic-id "TIC 123456789"`, `--sector 12`, `--mission TESS`, or `--cadence-seconds 1200` only when supported by the source. If output is omitted, JSON goes under `data/results/`. To analyze an explicitly synthetic local test file, add `--synthetic-test-data`; otherwise local data are treated as an observational source and its provenance remains `local_file`.

## Analyze a TESS target

Select a TIC and sector. If multiple archive products remain, provide their author (for example, `SPOC`) or an exact `--product-id`:

```powershell
exolens analyze-tic 123456789 --sector 12 --author TESS-SPOC --period-min-days 0.5 --period-max-days 20 --duration-min-hours 0.5 --duration-max-hours 6 --output .\data\results\tic-123456789.json
```

This requires network access to MAST. The command records only metadata returned by the selected product. A download may fail or selection may be ambiguous; failures are written as structured JSON and return a non-zero exit code.

## Results and current limits

This first version is tested in the available Python 3.14 environment. Dependency ranges are in `pyproject.toml`; a committed `uv.lock` is not included yet because the managed build environment denied extraction of Lightkurve’s `fbpca` source dependency during lock generation.

JSON follows `docs/output-schema.md`; CSV (`--csv`) is a flattened one-row summary. The explicit defaults are 0.5–20 days and 0.5–6 hours, with 5,000 trial periods and 10 trial durations. The depth estimate compares median flux inside repeated BLS transit windows with the median outside; it is null unless at least 3 in-window and 10 out-of-window points support it, and is withheld if the best BLS duration sits at a search boundary. The analysis returns the best BLS fit with `signal_status=not_evaluated`: no detection threshold has been calibrated. Uncertainties and SNR/false-alarm probability are not calculated, every result stays `unvalidated`, and no planet confirmation is claimed.

## Frontend

The React + TypeScript interface lives in `frontend/`. See [`frontend/README.md`](frontend/README.md) for Windows setup. FastAPI serves the `/api/v1` job and result endpoints. Completed API results and imported JSON records are saved in browser-local history; API job state is process-local.
