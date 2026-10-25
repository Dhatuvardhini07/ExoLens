from __future__ import annotations

import logging
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from exolens import __version__
from exolens.models.result import AnalysisResult, AnalysisStatus, ErrorRecord
from exolens.pipeline import AnalysisConfig, analyze_local_file, analyze_tess_target

logger = logging.getLogger("exolens.api")


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TargetRequest(StrictRequest):
    tic_id: str = Field(min_length=1, max_length=32)

    @field_validator("tic_id")
    @classmethod
    def valid_tic(cls, value: str) -> str:
        cleaned = value.strip().upper().removeprefix("TIC").strip()
        if not cleaned.isdigit():
            raise ValueError("TIC ID must contain a numeric identifier.")
        return f"TIC {cleaned}"


class DataSelectionRequest(StrictRequest):
    sector: int | None = Field(default=None, ge=1)
    author: str | None = Field(default=None, min_length=1, max_length=80)
    product_id: str | None = Field(default=None, min_length=1, max_length=200)


class SearchRequest(StrictRequest):
    period_min_days: float = Field(default=0.5, gt=0)
    period_max_days: float = Field(default=20.0, gt=0)
    duration_min_hours: float | None = Field(default=None, gt=0)
    duration_max_hours: float | None = Field(default=None, gt=0)
    n_periods: int = Field(default=5000, ge=2, le=50000)
    n_durations: int = Field(default=10, ge=1, le=100)

    @model_validator(mode="after")
    def validate_ranges(self) -> "SearchRequest":
        if self.period_max_days <= self.period_min_days:
            raise ValueError("period_max_days must be greater than period_min_days.")
        duration_min = self.duration_min_hours if self.duration_min_hours is not None else 0.5
        duration_max = self.duration_max_hours if self.duration_max_hours is not None else 6.0
        if duration_max <= duration_min:
            raise ValueError("duration_max_hours must be greater than duration_min_hours.")
        if duration_max / 24 >= self.period_min_days:
            raise ValueError("maximum duration must be shorter than the minimum period.")
        return self

    def to_config(self) -> AnalysisConfig:
        return AnalysisConfig(
            period_min_days=self.period_min_days,
            period_max_days=self.period_max_days,
            duration_min_hours=self.duration_min_hours if self.duration_min_hours is not None else 0.5,
            duration_max_hours=self.duration_max_hours if self.duration_max_hours is not None else 6.0,
            n_periods=self.n_periods,
            n_durations=self.n_durations,
        )


class AnalysisRequest(StrictRequest):
    target: TargetRequest
    data_selection: DataSelectionRequest = Field(default_factory=DataSelectionRequest)
    search: SearchRequest = Field(default_factory=SearchRequest)


class JobRecord(BaseModel):
    analysis_id: str
    status: str
    created_at_utc: datetime
    updated_at_utc: datetime
    result: AnalysisResult | None = None
    errors: list[ErrorRecord] = Field(default_factory=list)


class JobStore:
    """Process-local job store; results last until this API process stops."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._lock = RLock()

    def put(self, job: JobRecord) -> None:
        with self._lock:
            self._jobs[job.analysis_id] = job

    def get(self, analysis_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(analysis_id)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _normalized_digits(tic_id: str) -> str:
    return re.sub(r"\D", "", tic_id)


def _infer_cached_author(path: Path) -> str | None:
    name = path.name.lower()
    if "tess-spoc" in name:
        return "TESS-SPOC"
    if "tess-qlp" in name:
        return "QLP"
    return None


def find_cached_tess_file(
    cache_dir: Path,
    *,
    tic_id: str,
    sector: int | None,
    author: str | None,
) -> Path | None:
    """Find a matching FITS only inside ExoLens' configured cache directory."""
    if not cache_dir.is_dir():
        return None
    digits = _normalized_digits(tic_id)
    padded_id = digits.zfill(16)
    wanted_author = re.sub(r"[^a-z0-9]", "", author.lower()) if author else None
    matches: list[Path] = []
    for path in cache_dir.rglob("*_lc.fits"):
        name = path.name.lower()
        if padded_id not in name and not re.search(rf"(?<!\d)0*{re.escape(digits)}(?!\d)", name):
            continue
        if sector is not None and not re.search(rf"s0*{sector}(?:_|\b)", name):
            continue
        if wanted_author:
            normalized_name = re.sub(r"[^a-z0-9]", "", name)
            if wanted_author not in normalized_name:
                continue
        matches.append(path)
    if len(matches) > 1:
        names = ", ".join(path.name for path in matches[:3])
        raise ValueError(f"Multiple cached light curves match this target selection ({names}); choose a sector and author.")
    return matches[0] if matches else None


def _execute_analysis(
    request: AnalysisRequest,
    *,
    cache_dir: Path,
    config: AnalysisConfig,
) -> AnalysisResult:
    selection = request.data_selection
    if selection.product_id is None:
        cached_file = find_cached_tess_file(
            cache_dir,
            tic_id=request.target.tic_id,
            sector=selection.sector,
            author=selection.author,
        )
    else:
        cached_file = None

    if cached_file is not None:
        author = selection.author or _infer_cached_author(cached_file)
        return analyze_local_file(
            cached_file,
            config=config,
            tic_id=request.target.tic_id,
            sector=selection.sector,
            mission="TESS",
            author=author,
            time_system="BTJD (BJD - 2457000)",
        )

    return analyze_tess_target(
        request.target.tic_id,
        config=config,
        sector=selection.sector,
        author=selection.author,
        product_id=selection.product_id,
        cache_dir=cache_dir,
    )


def create_app(*, cache_dir: str | Path | None = None) -> FastAPI:
    root = Path(cache_dir) if cache_dir is not None else Path(os.getenv("EXOLENS_CACHE_DIR", "data/cache"))
    if not root.is_absolute():
        root = Path.cwd() / root
    store = JobStore()

    app = FastAPI(title="ExoLens API", version=__version__)
    origins = [item.strip() for item in os.getenv("EXOLENS_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if item.strip()]
    app.state.job_store = store
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(RequestValidationError)
    async def request_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": {"code": "INVALID_REQUEST", "message": "The analysis request is invalid.", "retryable": False, "details": jsonable_encoder(exc.errors())}},
        )

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, dict) else {"code": "HTTP_ERROR", "message": str(exc.detail), "retryable": False, "details": {}}
        return JSONResponse(status_code=exc.status_code, content={"error": detail}, headers=exc.headers)

    def run_job(analysis_id: str, payload: AnalysisRequest) -> None:
        now = _utc_now()
        store.put(JobRecord(analysis_id=analysis_id, status="running", created_at_utc=now, updated_at_utc=now))
        try:
            result = _execute_analysis(payload, cache_dir=root, config=payload.search.to_config())
            result.analysis_id = analysis_id
            state = "failed" if result.analysis_status is AnalysisStatus.FAILED else result.analysis_status.value
            store.put(JobRecord(
                analysis_id=analysis_id,
                status=state,
                created_at_utc=now,
                updated_at_utc=_utc_now(),
                result=result,
                errors=result.errors,
            ))
        except ValueError as exc:
            error = ErrorRecord(code="AMBIGUOUS_PRODUCT", message=str(exc), retryable=False)
            store.put(JobRecord(analysis_id=analysis_id, status="failed", created_at_utc=now, updated_at_utc=_utc_now(), errors=[error]))
        except Exception:
            logger.exception("Unexpected analysis job failure (%s)", analysis_id)
            error = ErrorRecord(code="ANALYSIS_FAILED", message="The analysis could not be completed due to an internal error.", retryable=True)
            store.put(JobRecord(analysis_id=analysis_id, status="failed", created_at_utc=now, updated_at_utc=_utc_now(), errors=[error]))

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "ExoLens API", "version": __version__}

    @app.post("/api/v1/analyses", status_code=status.HTTP_202_ACCEPTED)
    def start_analysis(payload: AnalysisRequest, background: BackgroundTasks) -> dict[str, str]:
        analysis_id = str(uuid4())
        now = _utc_now()
        store.put(JobRecord(analysis_id=analysis_id, status="queued", created_at_utc=now, updated_at_utc=now))
        background.add_task(run_job, analysis_id, payload)
        return {"analysis_id": analysis_id, "status": "queued", "status_url": f"/api/v1/analyses/{analysis_id}"}

    @app.get("/api/v1/analyses/{analysis_id}")
    def get_analysis(analysis_id: str) -> dict[str, object]:
        job = store.get(analysis_id)
        if job is None:
            raise HTTPException(status_code=404, detail={"code": "ANALYSIS_NOT_FOUND", "message": "No analysis job exists with that ID.", "retryable": False, "details": {}})
        return jsonable_encoder(job.model_dump(mode="json"))

    @app.get("/api/v1/analyses/{analysis_id}/result")
    def get_result(analysis_id: str) -> object:
        job = store.get(analysis_id)
        if job is None:
            raise HTTPException(status_code=404, detail={"code": "ANALYSIS_NOT_FOUND", "message": "No analysis job exists with that ID.", "retryable": False, "details": {}})
        if job.result is None:
            if job.status == "failed":
                raise HTTPException(status_code=422, detail={"code": job.errors[0].code if job.errors else "ANALYSIS_FAILED", "message": job.errors[0].message if job.errors else "Analysis failed.", "retryable": bool(job.errors and job.errors[0].retryable), "details": {}})
            raise HTTPException(status_code=409, detail={"code": "ANALYSIS_NOT_READY", "message": "The analysis result is not ready yet.", "retryable": True, "details": {}})
        return jsonable_encoder(job.result.model_dump(mode="json"))

    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("exolens.api:app", host=os.getenv("EXOLENS_API_HOST", "127.0.0.1"), port=int(os.getenv("EXOLENS_API_PORT", "8000")), reload=False)
