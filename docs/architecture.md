# ExoLens project architecture

## Goal

ExoLens is a scientific analysis workspace for inspecting transit-like signals in TESS light curves. Its first version reports reproducible measurements and evidence. It does not claim a signal is a planet, and it does not use machine-learning classification until suitable labelled data and an evaluation plan exist.

## Repository layout

```text
exolens/
├── README.md
├── .gitignore
├── pyproject.toml                 # Python dependencies, linting, test configuration
├── pnpm-workspace.yaml            # Frontend package workspace
├── backend/
│   ├── src/exolens/
│   │   ├── api/                   # FastAPI routes and API models
│   │   ├── analysis/              # BLS search and transit measurements
│   │   ├── data/                  # Lightkurve/MAST and local-file adapters
│   │   ├── preprocessing/         # Quality masks, cleaning, normalization
│   │   ├── models/                # Shared Python result models
│   │   ├── jobs/                  # Analysis job lifecycle and persistence
│   │   └── export/                # JSON/CSV serialization
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── fixtures/              # Small synthetic test curves, clearly marked
├── frontend/
│   ├── src/{app,components,features,charts,api,styles}/
│   └── tests/
├── docs/
│   ├── architecture.md
│   ├── output-schema.md
│   ├── api-contract.md
│   └── roadmap.md
├── reference/original_submission/ # Optional local, read-only reference copies
└── data/cache/                    # Download cache; ignored by Git
```

The current workspace is not a Git repository and does not yet contain this application structure. This is the intended layout, not a claim that code exists. Start with one root `pyproject.toml`; split Python configuration only if dependency isolation becomes useful.

## Main technology choices

- **Python engine:** Astropy, Lightkurve, NumPy, and Pydantic. Astropy provides Box Least Squares (BLS); Lightkurve helps retrieve and work with TESS curves; Pydantic checks result fields and types.
- **API:** FastAPI with versioned JSON endpoints. It keeps scientific calculations out of the browser and gives the frontend a stable interface.
- **Frontend:** React + TypeScript using Vite. This is a compact setup for an interactive dashboard; TypeScript catches many data-shape mistakes during development.
- **Charts:** Plotly.js through its React wrapper for interactive curves, BLS periodograms, and phase-folded plots. It supports scientific axes, hover details, zoom, and range selection. Its larger download size is acceptable initially; revisit if performance measurements show a problem.
- **Frontend data handling:** TanStack Query for fetching/caching/job polling and Zod for runtime API validation. TypeScript alone cannot guarantee that external JSON is valid.
- **Tests:** pytest for Python calculations/API behavior; Vitest + React Testing Library for components; Playwright for a few end-to-end user flows.
- **Dependencies:** `uv` for Python environments/lockfiles and `pnpm` for frontend packages. Pin versions so a later run can recreate the environment.

## Data flow

```text
TIC/sector request → FastAPI validates and creates a job
→ Lightkurve/MAST retrieves a real curve (or a local adapter loads an explicitly selected file)
→ preprocessing records accepted/rejected points and warnings
→ BLS search returns its best-fit parameters and statistic
→ measurement step estimates transit properties/uncertainty only when supported
→ versioned result is saved/exported as JSON
→ React dashboard polls status and renders result and provenance
```

For local development, begin with a small SQLite job store and a single-process worker. This is simple to run, but is not a durable multi-worker deployment design. Deployment preparation should select a managed database/job queue if real workloads require them.

## Visual direction

Use near-black navy surfaces, subtle low-contrast star fields, restrained cyan/violet accents, and legible typography. Scientific charts take visual priority. Provide responsive layouts, clear loading/empty/error states, keyboard-accessible controls, and restrained transitions. Motion should explain state changes without competing with the data. Charts need readable labels, units, and hover details.

## GitHub and original-file policy

Keep code, docs, tests, lockfiles, and a concise README in Git. Ignore downloaded light curves, caches, credentials, and environment files. Original BAH materials remain unchanged; local reference copies may live under `reference/original_submission/`, but should be excluded from a public repository by default until publication rights and user preference are clear. Never replace originals with cleaned or reformatted versions.

## Scientific safeguards

A result describes an analysis of a light curve. A BLS peak is evidence for a periodic box-shaped signal under the configured search, not planet confirmation. A confirmed-planet label must come from a linked authoritative source and be shown as catalog metadata, separate from ExoLens's analysis status. Synthetic curves are for software tests or clearly labelled demonstrations; never present them as real TESS observations.
