from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from uuid import uuid4

import numpy as np

from exolens import __version__
from exolens.analysis.bls import run_bls
from exolens.analysis.measurements import estimate_transit_depth
from exolens.data.loaders import LightCurveData, download_tess_target, load_local_file
from exolens.errors import ExoLensError
from exolens.models.result import (
    AnalysisResult,
    AnalysisStatus,
    ChartData,
    PhaseFluxPoint,
    TimeFluxPoint,
    DataKind,
    DataQuality,
    ErrorRecord,
    Event,
    MeasurementUncertainty,
    PipelineInfo,
    Provenance,
    SignalStatus,
    Significance,
    SourceType,
    Target,
    Uncertainties,
    Validation,
)
from exolens.preprocessing.clean import prepare_light_curve


@dataclass(frozen=True)
class AnalysisConfig:
    period_min_days: float = 0.5
    period_max_days: float = 20.0
    duration_min_hours: float = 0.5
    duration_max_hours: float = 6.0
    n_periods: int = 5000
    n_durations: int = 10
    min_points: int = 20

    def __post_init__(self) -> None:
        if not (0 < self.period_min_days < self.period_max_days):
            raise ValueError("period range must satisfy 0 < minimum < maximum")
        if not (0 < self.duration_min_hours < self.duration_max_hours):
            raise ValueError("duration range must satisfy 0 < minimum < maximum")
        if self.duration_max_hours / 24 >= self.period_min_days:
            raise ValueError("maximum duration must be shorter than minimum period")
        if self.n_periods < 2 or self.n_durations < 1:
            raise ValueError("BLS grid needs at least 2 periods and 1 duration")
        if self.min_points < 3:
            raise ValueError("min_points must be at least 3")


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "unknown"


def _pipeline_info(config: AnalysisConfig) -> PipelineInfo:
    return PipelineInfo(
        version=__version__,
        bls_period_range_days=(config.period_min_days, config.period_max_days),
        bls_duration_range_hours=(config.duration_min_hours, config.duration_max_hours),
        bls_n_periods=config.n_periods,
        bls_n_durations=config.n_durations,
        preprocessing=[
            {"name": "quality_mask", "rule": "exclude non-zero quality flags"},
            {"name": "finite_value_filter", "rule": "require finite time and flux; finite positive flux_err when supplied"},
            {"name": "time_sort", "rule": "sort ascending and reject duplicate timestamps"},
            {"name": "normalization", "rule": "divide flux and flux_err by median retained flux"},
            {"name": "gap_count", "rule": "count time differences greater than max(5 times median cadence, 0.5 day)"},
        ],
        measurement_methods={
            "period": "Astropy BoxLeastSquares.power; maximum returned likelihood objective",
            "epoch": "transit_time returned by Astropy BoxLeastSquares at maximum power",
            "duration": "duration returned by Astropy BoxLeastSquares at maximum power",
            "depth": "median in repeated BLS transit windows versus median outside; requires at least 3 in-transit and 10 out-of-transit points",
            "uncertainties": "not_calculated",
            "significance": "not_calculated; BLS power is not a probability or SNR",
        },
        software={
            "python": f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}.{__import__('sys').version_info.micro}",
            "astropy": _package_version("astropy"),
            "lightkurve": _package_version("lightkurve"),
            "numpy": _package_version("numpy"),
            "pydantic": _package_version("pydantic"),
            "exolens": __version__,
        },
    )


def _uncertainties() -> Uncertainties:
    return Uncertainties(
        period_days=MeasurementUncertainty(unit="days"),
        depth_fraction=MeasurementUncertainty(unit="fraction"),
        duration_hours=MeasurementUncertainty(unit="hours"),
        epoch_time=MeasurementUncertainty(unit="same as epoch time"),
    )


def _chart_data(curve, bls) -> ChartData:
    """Build plotted arrays only from the cleaned observations and this BLS fit."""
    time = np.asarray(curve.time, dtype=float)
    flux = np.asarray(curve.flux, dtype=float)
    observations = [TimeFluxPoint(time=float(t), flux=float(f)) for t, f in zip(time, flux, strict=True)]

    period = float(bls.best_period_days)
    epoch = float(bls.transit_time)
    duration_days = float(bls.best_duration_hours) / 24.0
    phase = ((time - epoch) / period + 0.5) % 1.0 - 0.5
    phase_order = np.argsort(phase, kind="stable")
    phase_folded = [
        PhaseFluxPoint(phase=float(phase[index]), flux=float(flux[index]))
        for index in phase_order
    ]

    reasons: dict[str, str] = {}
    model_curve = None
    depth = bls.depth_fraction
    if not (np.isfinite(period) and period > 0 and np.isfinite(duration_days) and 0 < duration_days < period and np.isfinite(epoch)):
        reasons["model_curve"] = "The BLS fit did not return a valid period, epoch, and duration for a model curve."
    elif depth is None or not np.isfinite(depth) or depth <= 0:
        reasons["model_curve"] = "The BLS fit did not return a finite positive box depth."
    else:
        observed_in = np.abs(((time - epoch + 0.5 * period) % period) - 0.5 * period) <= duration_days / 2
        outside = flux[~observed_in]
        baseline = float(np.median(outside)) if outside.size else float("nan")
        if not np.isfinite(baseline) or baseline <= float(depth):
            reasons["model_curve"] = "A positive out-of-transit baseline could not be estimated for the BLS model."
        else:
            model_time = np.linspace(float(time[0]), float(time[-1]), min(max(1000, len(time) * 2), 5000))
            model_phase = np.abs(((model_time - epoch + 0.5 * period) % period) - 0.5 * period)
            model_flux = np.where(model_phase <= duration_days / 2, baseline - float(depth), baseline)
            model_curve = [TimeFluxPoint(time=float(t), flux=float(f)) for t, f in zip(model_time, model_flux, strict=True)]

    return ChartData(
        time_system=curve.time_system,
        observations=observations,
        periodogram=bls.periodogram,
        phase_folded=phase_folded,
        model_curve=model_curve,
        unavailable_reasons=reasons,
    )


def _failed_result(
    *,
    target: Target,
    provenance: Provenance,
    config: AnalysisConfig,
    error: ExoLensError,
    input_points: int | None = None,
    data_kind: DataKind = DataKind.REAL_OBSERVATION,
) -> AnalysisResult:
    return AnalysisResult(
        analysis_id=str(uuid4()),
        created_at_utc=datetime.now(UTC),
        data_kind=data_kind,
        target=target,
        provenance=provenance,
        pipeline=_pipeline_info(config),
        data_quality=DataQuality(input_points=input_points),
        analysis_status=AnalysisStatus.FAILED,
        event=None,
        validation=Validation(),
        errors=[ErrorRecord(code=error.code, message=error.message, retryable=error.retryable)],
    )


def analyze_curve(data: LightCurveData, config: AnalysisConfig | None = None) -> AnalysisResult:
    """Preprocess, run BLS, measure depth when supported, and return schema result."""
    config = config or AnalysisConfig()
    if data.data_kind not in (DataKind.REAL_OBSERVATION.value, DataKind.SYNTHETIC_TEST.value):
        raise ValueError("unsupported data_kind")
    kind = DataKind(data.data_kind)
    try:
        curve = prepare_light_curve(data, min_points=config.min_points)
        warnings = list(curve.quality.warnings)
        if curve.quality.time_span_days is not None and config.period_max_days >= curve.quality.time_span_days:
            warnings.append("Search includes periods as long as or longer than the observed baseline; recurrence is not established.")
        if curve.quality.time_span_days is not None and curve.quality.time_span_days < 2 * config.period_max_days:
            warnings.append("Observed baseline is shorter than two times the maximum searched period.")
        if data.provenance.time_system is None:
            warnings.append("Period search assumes input times are measured in days; provide the correct time system for interpretation.")
        quality = curve.quality.model_copy(update={"warnings": warnings})
        bls = run_bls(
            curve,
            period_min_days=config.period_min_days,
            period_max_days=config.period_max_days,
            duration_min_hours=config.duration_min_hours,
            duration_max_hours=config.duration_max_hours,
            n_periods=config.n_periods,
            n_durations=config.n_durations,
        )
        duration_step = (config.duration_max_hours - config.duration_min_hours) / max(config.n_durations - 1, 1)
        at_duration_edge = (
            bls.best_duration_hours is not None
            and (
                abs(bls.best_duration_hours - config.duration_min_hours) <= max(duration_step * 0.51, 1e-8)
                or abs(bls.best_duration_hours - config.duration_max_hours) <= max(duration_step * 0.51, 1e-8)
            )
        )
        period_step = (config.period_max_days - config.period_min_days) / (config.n_periods - 1)
        at_period_edge = (
            bls.best_period_days is not None
            and (
                abs(bls.best_period_days - config.period_min_days) <= period_step * 0.51
                or abs(bls.best_period_days - config.period_max_days) <= period_step * 0.51
            )
        )
        if at_period_edge:
            quality.warnings.append("Best BLS period is at the edge of the searched range; widen the period range before interpreting it.")
        if at_duration_edge:
            quality.warnings.append("Best BLS duration is at the edge of the searched range; widen the duration range before interpreting it.")
            depth, depth_method, depth_reason = None, None, "Best BLS duration is at the search boundary, so the transit window is not sufficiently constrained for a depth estimate."
        else:
            depth, depth_method, depth_reason = estimate_transit_depth(
                curve,
                period_days=float(bls.best_period_days),
                epoch_time=float(bls.transit_time),
                duration_hours=float(bls.best_duration_hours),
            )
        if depth_reason:
            quality.warnings.append(f"Transit depth was not estimated: {depth_reason}")
        quality.warnings.append("BLS selected a best-fit box model; no detection threshold or independent validation was applied.")
        event = Event(
            signal_status=SignalStatus.NOT_EVALUATED,
            period_days=bls.best_period_days,
            epoch_time=bls.transit_time,
            duration_hours=bls.best_duration_hours,
            depth_fraction=depth,
            depth_method=depth_method,
            depth_unavailable_reason=depth_reason or None,
            bls=bls,
            uncertainties=_uncertainties(),
            significance=Significance(),
        )
        return AnalysisResult(
            analysis_id=str(uuid4()),
            created_at_utc=datetime.now(UTC),
            data_kind=kind,
            target=data.target,
            provenance=data.provenance,
            pipeline=_pipeline_info(config),
            data_quality=quality,
            analysis_status=AnalysisStatus.COMPLETED,
            event=event,
            validation=Validation(),
            errors=[],
            chart_data=_chart_data(curve, bls),
        )
    except ExoLensError as exc:
        return _failed_result(
            target=data.target,
            provenance=data.provenance,
            config=config,
            error=exc,
            input_points=len(data.time),
            data_kind=kind,
        )
    except Exception as exc:
        error = ExoLensError("BLS_FAILED", f"Analysis failed: {exc}")
        return _failed_result(
            target=data.target,
            provenance=data.provenance,
            config=config,
            error=error,
            input_points=len(data.time),
            data_kind=kind,
        )


def analyze_local_file(
    filename: str | Path,
    *,
    config: AnalysisConfig | None = None,
    tic_id: str | None = None,
    sector: int | None = None,
    mission: str | None = None,
    author: str | None = None,
    cadence_seconds: float | None = None,
    time_system: str | None = None,
    synthetic_test_data: bool = False,
) -> AnalysisResult:
    config = config or AnalysisConfig()
    try:
        data = load_local_file(
            filename,
            tic_id=tic_id,
            sector=sector,
            mission=mission,
            author=author,
            cadence_seconds=cadence_seconds,
            time_system=time_system,
            synthetic_test_data=synthetic_test_data,
        )
    except ExoLensError as exc:
        path = Path(filename)
        provenance = Provenance(
            mission=mission,
            sector=sector,
            data_author=author,
            source_type=SourceType.SYNTHETIC_FIXTURE if synthetic_test_data else SourceType.LOCAL_FILE,
            source_filename=path.name,
            cadence_seconds=cadence_seconds,
            time_system=time_system,
        )
        try:
            target = Target(tic_id=tic_id)
        except Exception:
            target = Target()
        return _failed_result(
            target=target, provenance=provenance, config=config, error=exc,
            data_kind=DataKind.SYNTHETIC_TEST if synthetic_test_data else DataKind.REAL_OBSERVATION,
        )
    return analyze_curve(data, config)


def analyze_tess_target(
    tic_id: str,
    *,
    config: AnalysisConfig | None = None,
    sector: int | None = None,
    author: str | None = None,
    product_id: str | None = None,
    cache_dir: str | Path = "data/cache",
) -> AnalysisResult:
    config = config or AnalysisConfig()
    try:
        data = download_tess_target(
            tic_id, sector=sector, author=author, product_id=product_id, cache_dir=cache_dir
        )
    except ExoLensError as exc:
        try:
            target = Target(tic_id=f"TIC {tic_id.removeprefix('TIC ').strip()}")
        except Exception:
            target = Target()
        provenance = Provenance(
            mission="TESS",
            sector=sector,
            data_author=author,
            product_id=product_id,
            source_type=SourceType.MAST_PRODUCT,
        )
        return _failed_result(target=target, provenance=provenance, config=config, error=exc)
    return analyze_curve(data, config)
