from __future__ import annotations

import numpy as np
import pytest

from exolens.data.loaders import LightCurveData
from exolens.models.result import Provenance, SourceType, Target
from exolens.preprocessing.clean import prepare_light_curve


@pytest.fixture
def synthetic_transit_curve() -> LightCurveData:
    """Synthetic test fixture only; it is not real TESS data or a discovery."""
    rng = np.random.default_rng(271828)
    cadence_days = 20 / 1440
    time = np.arange(0.0, 12.0, cadence_days)
    true_period = 2.2
    true_epoch = 0.37
    duration_days = 2.0 / 24
    phase_offset = ((time - true_epoch + 0.5 * true_period) % true_period) - 0.5 * true_period
    transit = np.abs(phase_offset) <= duration_days / 2
    flux = 1.0 - 0.02 * transit + rng.normal(0.0, 0.0004, size=time.size)
    flux_err = np.full(time.size, 0.0005)
    provenance = Provenance(
        mission=None,
        time_system="synthetic test time in days",
        source_type=SourceType.SYNTHETIC_FIXTURE,
        source_filename="in-memory synthetic test fixture",
        time_start=float(time[0]),
        time_end=float(time[-1]),
        cadence_seconds=20 * 60,
    )
    return LightCurveData(
        time=time,
        flux=flux,
        flux_err=flux_err,
        quality=np.zeros(time.size),
        target=Target(display_name="Synthetic test fixture only"),
        provenance=provenance,
        data_kind="synthetic_test",
    )


@pytest.fixture
def prepared_synthetic_curve(synthetic_transit_curve: LightCurveData):
    """Preprocessed synthetic fixture for unit tests only."""
    return prepare_light_curve(synthetic_transit_curve)
