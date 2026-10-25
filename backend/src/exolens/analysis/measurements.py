from __future__ import annotations

import numpy as np

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
    """Estimate fractional depth from median flux inside/outside BLS transit windows."""
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
        return None, None, f"Only {n_in} point(s) fall inside fitted transit windows; at least {min_in_transit} are required."
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
