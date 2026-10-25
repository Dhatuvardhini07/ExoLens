import numpy as np

from exolens.analysis.bls import run_bls
from exolens.analysis.measurements import estimate_transit_depth


def test_bls_extracts_best_parameters_from_astropy_result(prepared_synthetic_curve):
    result = run_bls(
        prepared_synthetic_curve,
        period_min_days=2.0,
        period_max_days=2.4,
        duration_min_hours=1.5,
        duration_max_hours=2.5,
        n_periods=201,
        n_durations=5,
    )

    assert result.best_period_days is not None
    assert abs(result.best_period_days - 2.2) < 0.01
    assert abs(result.best_duration_hours - 2.0) < 0.6
    assert abs(result.transit_time - 0.37) < 0.03
    assert result.power is not None and np.isfinite(result.power)
    assert result.depth_fraction is not None and 0 < result.depth_fraction < 0.05


def test_depth_uses_repeated_transit_window_and_outside_baseline(prepared_synthetic_curve):
    estimate = estimate_transit_depth(
        prepared_synthetic_curve,
        period_days=2.2,
        epoch_time=0.37,
        duration_hours=2.0,
    )
    depth, method, reason = estimate
    assert reason == ""
    assert method == "median_in_transit_vs_median_out_of_transit"
    assert depth is not None and abs(depth - 0.02) < 0.002


def test_depth_is_null_when_transit_window_has_too_few_points(prepared_synthetic_curve):
    depth, method, reason = estimate_transit_depth(
        prepared_synthetic_curve,
        period_days=2.2,
        epoch_time=0.37,
        duration_hours=0.01,
    )
    assert depth is None
    assert method is None
    assert "Only" in reason
from exolens.models.result import BLSResult
from exolens.pipeline import AnalysisConfig, analyze_curve
import exolens.pipeline as pipeline


def test_pipeline_withholds_depth_when_best_duration_is_at_search_edge(monkeypatch, synthetic_transit_curve):
    def edge_fit(*args, **kwargs):
        return BLSResult(
            power=1.0,
            best_period_days=2.2,
            best_duration_hours=2.5,
            transit_time=0.37,
            depth_fraction=0.02,
        )
    monkeypatch.setattr(pipeline, "run_bls", edge_fit)
    result = analyze_curve(
        synthetic_transit_curve,
        AnalysisConfig(
            period_min_days=2.0,
            period_max_days=2.4,
            duration_min_hours=1.5,
            duration_max_hours=2.5,
            n_periods=201,
            n_durations=5,
        ),
    )
    assert result.event is not None
    assert result.event.duration_hours == 2.5
    assert result.event.depth_fraction is None
    assert "search boundary" in result.event.depth_unavailable_reason
    assert any("duration is at the edge" in w for w in result.data_quality.warnings)

def test_pipeline_chart_arrays_match_preprocessed_curve_and_bls_result(prepared_synthetic_curve, synthetic_transit_curve):
    from exolens.pipeline import AnalysisConfig, analyze_curve

    config = AnalysisConfig(
        period_min_days=2.0,
        period_max_days=2.4,
        duration_min_hours=1.5,
        duration_max_hours=2.5,
        n_periods=201,
        n_durations=5,
    )
    result = analyze_curve(synthetic_transit_curve, config)

    assert result.chart_data is not None
    assert result.chart_data.time_system == result.provenance.time_system
    assert len(result.chart_data.observations) == len(prepared_synthetic_curve.time)
    assert len(result.chart_data.phase_folded) == len(prepared_synthetic_curve.time)
    assert len(result.chart_data.periodogram) == config.n_periods
    assert [point.time for point in result.chart_data.observations] == prepared_synthetic_curve.time.tolist()
    assert [point.flux for point in result.chart_data.observations] == prepared_synthetic_curve.flux.tolist()
    peak = max(result.chart_data.periodogram, key=lambda point: point.power)
    assert peak.period_days == result.event.period_days
    assert peak.power == result.event.bls.power
    assert result.event.period_days == result.event.bls.best_period_days
    assert result.event.duration_hours == result.event.bls.best_duration_hours
    assert result.chart_data.model_curve is not None
    assert "periodogram" not in result.model_dump(mode="json")["event"]["bls"]
