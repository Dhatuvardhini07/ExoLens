from __future__ import annotations

import numpy as np

from exolens.models.result import BLSResult, PeriodPowerPoint
from exolens.preprocessing.clean import PreparedLightCurve


def estimate_transit_depth(
    curve: PreparedLightCurve,
    *,
    period_days: float,
    epoch_time: float,
    duration_hours: float,
    min_in_transit: int = 3,
    min_out_of_transit: int = 10,
) -> tuple[float | None, str | None, str]:
    """Estimate fractional depth from medians inside/outside repeated BLS windows."""
    if period_days <= 0 or duration_hours <= 0:
        return None, None, "BLS period or duration is not positive."
    duration_days = duration_hours / 24.0
    if duration_days >= period_days:
        return None, None, "Transit duration must be shorter than the orbital period."
    phase_offset = ((curve.time - epoch_time + 0.5 * period_days) % period_days) - 0.5 * period_days
    in_transit = np.abs(phase_offset) <= 0.5 * duration_days
    n_in = int(np.count_nonzero(in_transit))
    n_out = int(len(curve.time) - n_in)
    if n_in < min_in_transit:
        return None, None, f"Only {n_in} point(s) fall inside the fitted transit windows; at least {min_in_transit} are required."
    if n_out < min_out_of_transit:
        return None, None, f"Only {n_out} out-of-transit point(s) are available; at least {min_out_of_transit} are required."
    baseline = float(np.median(curve.flux[~in_transit]))
    in_transit_flux = float(np.median(curve.flux[in_transit]))
    if not np.isfinite(baseline) or baseline <= 0:
        return None, None, "Out-of-transit median is not finite and positive."
    depth = (baseline - in_transit_flux) / baseline
    if not np.isfinite(depth) or depth <= 0:
        return None, None, "Fitted transit window is not dimmer than the out-of-transit baseline."
    return float(depth), "median_in_transit_vs_median_out_of_transit", ""


def run_bls(
    curve: PreparedLightCurve,
    *,
    period_min_days: float,
    period_max_days: float,
    duration_min_hours: float,
    duration_max_hours: float,
    n_periods: int = 5000,
    n_durations: int = 10,
) -> BLSResult:
    """Run Astropy BLS, preserving its real periodogram and best-fit parameters."""
    from astropy.timeseries import BoxLeastSquares

    if not (0 < period_min_days < period_max_days):
        raise ValueError("period range must satisfy 0 < minimum < maximum")
    if not (0 < duration_min_hours < duration_max_hours):
        raise ValueError("duration range must satisfy 0 < minimum < maximum")
    if duration_max_hours / 24 >= period_min_days:
        raise ValueError("maximum transit duration must be shorter than minimum period")
    if n_periods < 2 or n_durations < 1:
        raise ValueError("BLS grid must contain at least 2 periods and 1 duration")

    periods = np.linspace(period_min_days, period_max_days, n_periods)
    durations = np.linspace(duration_min_hours / 24, duration_max_hours / 24, n_durations)
    bls = BoxLeastSquares(curve.time, curve.flux, dy=curve.flux_err)
    result = bls.power(periods, durations, objective="likelihood")
    power = np.asarray(result.power, dtype=float)
    if not power.size or not np.any(np.isfinite(power)):
        raise ValueError("BLS returned no finite power values")

    best_position = np.unravel_index(int(np.nanargmax(power)), power.shape)

    def fit_value(name: str) -> float:
        values = np.asarray(getattr(result, name), dtype=float)
        if values.shape == power.shape:
            return float(values[best_position])
        if values.ndim > 1:
            return float(values[best_position[0]].reshape(-1)[best_position[-1]])
        return float(values[best_position[0]])

    if power.ndim == 1:
        period_values = np.asarray(result.period, dtype=float).reshape(-1)
        period_power = power
    else:
        period_power = np.nanmax(power, axis=tuple(range(1, power.ndim)))
        returned_periods = np.asarray(result.period, dtype=float)
        period_values = returned_periods.reshape(power.shape)[:, 0] if returned_periods.size == power.size else periods

    periodogram = [
        PeriodPowerPoint(period_days=float(period), power=float(value))
        for period, value in zip(period_values, period_power, strict=True)
        if np.isfinite(period) and np.isfinite(value)
    ]
    return BLSResult(
        power=fit_value("power"),
        best_period_days=fit_value("period"),
        best_duration_hours=fit_value("duration") * 24.0,
        transit_time=fit_value("transit_time"),
        depth_fraction=fit_value("depth"),
        periodogram=periodogram,
    )
