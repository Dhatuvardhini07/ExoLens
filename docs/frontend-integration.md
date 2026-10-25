# Frontend integration

The React client sends versioned `/api/v1` requests and validates returned records against the Python Pydantic output model with Zod. Run the FastAPI service from the project root; the default frontend API root is `http://localhost:8000` and can be changed with `VITE_API_URL`.

The Target Explorer submits a TIC, optional sector/author selection, and BLS period/duration ranges. The API checks the configured local `data/cache` for a matching FITS product before it asks Lightkurve to query MAST. The response source type distinguishes `local_file` cached observations from a fresh `mast_product` retrieval. The client polls the job endpoint and displays terminal failures and their structured messages.

Completed API results are stored in the browser's local history for Dashboard and Explorer views. This does not synchronize across browsers. API job status and result retrieval are held in process memory and reset if the server restarts.

Schema 1.1 adds `chart_data`: retained normalized observations, the BLS periodogram, phase-folded observations, the applicable time system, and an optional separately labeled BLS box model. These arrays come from the same cleaned curve and fit as the measurement record. If an array or model cannot be generated, the UI displays an explanatory empty state; it does not invent points.

The browser still does not upload arbitrary CSV/FITS files. This would need a separate upload endpoint with size/type checks and safe server storage. The API currently exposes health, job start/status, and result endpoints; it does not provide a paginated server-wide analysis-history endpoint.
