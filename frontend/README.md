# ExoLens frontend

## Windows / VS Code

From the project root, install frontend packages once and run each service in a separate VS Code terminal.

Backend terminal (project root):

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m uvicorn exolens.api:app --app-dir backend/src --host 127.0.0.1 --port 8000
```

Frontend terminal:

```powershell
cd .\frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The API is at `http://localhost:8000` and its health endpoint is `http://localhost:8000/api/v1/health`. To change the API origin, set `$env:VITE_API_URL` before starting Vite.

The API uses `data/cache` by default, first reusing a matching cached FITS product and then querying MAST via Lightkurve. It does not accept a client-supplied file path. Job state is kept in API process memory; browser result history is kept in local storage. The five existing pages are Overview, Analytics Dashboard, Target Explorer, Target Analysis, and Methods & Limitations.

Run frontend checks with `npm run typecheck`, `npm run lint`, `npm test`, and `npm run build`. Plotly renders only arrays returned by the analysis engine. Observed points and the separately styled BLS box-model line are kept distinct.
