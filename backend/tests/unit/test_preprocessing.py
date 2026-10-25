from dataclasses import replace

import numpy as np
import pytest

from exolens.data.loaders import LightCurveData
from exolens.errors import ExoLensError
from exolens.preprocessing.clean import prepare_light_curve


def test_preprocessing_rejects_bad_quality_and_nonfinite_rows(synthetic_transit_curve):
    data = synthetic_transit_curve
    time = data.time.copy()
    flux = data.flux.copy()
    error = data.flux_err.copy()
    quality = data.quality.copy()
    quality[2] = 1
    flux[3] = np.nan
    error[4] = 0.0
    updated = replace(data, time=time, flux=flux, flux_err=error, quality=quality)

    prepared = prepare_light_curve(updated)

    assert prepared.quality.input_points == len(time)
    assert prepared.quality.removed_quality_flag_points == 1
    assert prepared.quality.removed_nan_points == 2
    assert prepared.quality.used_points == len(time) - 3
    assert np.all(np.diff(prepared.time) > 0)
    assert np.isclose(np.median(prepared.flux), 1.0, atol=0.002)
    assert np.all(prepared.flux_err > 0)


def test_preprocessing_rejects_duplicate_timestamps(synthetic_transit_curve):
    data = synthetic_transit_curve
    time = data.time.copy()
    time[1] = time[0]
    with pytest.raises(ExoLensError, match="duplicate timestamps"):
        prepare_light_curve(replace(data, time=time))


def test_preprocessing_reports_insufficient_data(synthetic_transit_curve):
    data = synthetic_transit_curve
    short = replace(data, time=data.time[:10], flux=data.flux[:10], flux_err=data.flux_err[:10], quality=data.quality[:10])
    with pytest.raises(ExoLensError, match="at least 20"):
        prepare_light_curve(short)


def test_preprocessing_rejects_bad_array_lengths(synthetic_transit_curve):
    data = synthetic_transit_curve
    with pytest.raises(ExoLensError, match="same number of rows"):
        prepare_light_curve(replace(data, flux_err=data.flux_err[:-1]))
