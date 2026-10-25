from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from exolens.data.loaders import LightCurveData
from exolens.errors import ExoLensError
from exolens.models.result import DataQuality


@dataclass(frozen=True)
class PreparedLightCurve:
    time: np.ndarray
    flux: np.ndarray
    flux_err: np.ndarray | None
    quality: DataQuality
    time_system: str | None


def prepare_light_curve(data: LightCurveData, *, min_points: int = 20) -> PreparedLightCurve:
    """Apply quality/finite masks, sort in time, and normalize by median flux."""
    time = np.asarray(data.time, dtype=float).reshape(-1)
    flux = np.asarray(data.flux, dtype=float).reshape(-1)
    flux_err = None if data.flux_err is None else np.asarray(data.flux_err, dtype=float).reshape(-1)
    quality_flags = None if data.quality is None else np.asarray(data.quality, dtype=float).reshape(-1)
    n = len(time)
    if n == 0 or len(flux) != n:
        raise ExoLensError("INVALID_LIGHT_CURVE", "Time and flux arrays must be non-empty and have equal lengths.")
    if flux_err is not None and len(flux_err) != n:
        raise ExoLensError("INVALID_LIGHT_CURVE", "flux_err must have the same number of rows as time and flux.")
    if quality_flags is not None and len(quality_flags) != n:
        raise ExoLensError("INVALID_LIGHT_CURVE", "quality flags must have the same number of rows as time and flux.")

    bad_quality = np.zeros(n, dtype=bool)
    if quality_flags is not None:
        bad_quality = np.isfinite(quality_flags) & (quality_flags != 0)
    valid = np.isfinite(time) & np.isfinite(flux)
    if flux_err is not None:
        valid &= np.isfinite(flux_err) & (flux_err > 0)
    if quality_flags is not None:
        valid &= np.isfinite(quality_flags)
    invalid = ~valid
    removed_nan = int(np.count_nonzero(invalid & ~bad_quality))
    removed_quality = int(np.count_nonzero(bad_quality))
    keep = valid & ~bad_quality

    time = time[keep]
    flux = flux[keep]
    flux_err = flux_err[keep] if flux_err is not None else None
    if len(time) < min_points:
        raise ExoLensError(
            "INSUFFICIENT_DATA",
            f"Only {len(time)} usable observations remain; at least {min_points} are required.",
        )

    order = np.argsort(time, kind="stable")
    time, flux = time[order], flux[order]
    if flux_err is not None:
        flux_err = flux_err[order]
    if np.any(np.diff(time) <= 0):
        raise ExoLensError("INVALID_LIGHT_CURVE", "Time values must be unique; duplicate timestamps were found.")

    baseline = float(np.median(flux))
    if not np.isfinite(baseline) or baseline <= 0:
        raise ExoLensError("INVALID_LIGHT_CURVE", "Median flux must be finite and positive to normalize this light curve.")
    flux = flux / baseline
    if flux_err is not None:
        flux_err = flux_err / baseline

    gaps = 0
    if len(time) > 1:
        differences = np.diff(time)
        cadence = float(np.median(differences))
        gap_threshold_days = max(5.0 * cadence, 0.5)
        gaps = int(np.count_nonzero(differences > gap_threshold_days))
    warnings: list[str] = []
    if removed_nan:
        warnings.append(f"Removed {removed_nan} observation(s) with non-finite/invalid measurements.")
    if removed_quality:
        warnings.append(f"Removed {removed_quality} observation(s) with non-zero quality flags.")
    if gaps:
        warnings.append(f"Found {gaps} time gap(s) longer than the documented gap threshold.")
    if data.provenance.time_system is None:
        warnings.append("Time system was not supplied or present in source metadata; period units assume input time is in days.")

    quality = DataQuality(
        input_points=n,
        used_points=len(time),
        removed_nan_points=removed_nan,
        removed_quality_flag_points=removed_quality,
        time_span_days=float(time[-1] - time[0]),
        gap_count=gaps,
        warnings=warnings,
    )
    return PreparedLightCurve(time, flux, flux_err, quality, data.provenance.time_system)
