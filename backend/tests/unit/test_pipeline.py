import numpy as np
from pydantic import ValidationError
import pytest

from exolens.models.result import (
    AnalysisResult,
    AnalysisStatus,
    DataKind,
    DataQuality,
    ErrorRecord,
    Provenance,
    SourceType,
    Target,
)
from exolens.pipeline import AnalysisConfig, analyze_curve, analyze_local_file


def test_pipeline_output_round_trips_schema(synthetic_transit_curve):
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

    validated = AnalysisResult.model_validate_json(result.model_dump_json())
    assert validated.analysis_status is AnalysisStatus.COMPLETED
    assert validated.data_kind is DataKind.SYNTHETIC_TEST
    assert validated.event is not None
    assert validated.event.signal_status.value == "not_evaluated"
    assert validated.event.significance.snr is None
    assert validated.event.significance.false_alarm_probability is None
    assert validated.event.uncertainties.period_days.method == "not_calculated"
    assert validated.validation.status.value == "unvalidated"
    assert any("no detection threshold" in warning for warning in validated.data_quality.warnings)


def test_schema_rejects_synthetic_data_with_real_source():
    with pytest.raises(ValidationError, match="synthetic_test data must use synthetic_fixture"):
        AnalysisResult(
            analysis_id="test",
            created_at_utc="2026-01-01T00:00:00Z",
            data_kind=DataKind.SYNTHETIC_TEST,
            target=Target(),
            provenance=Provenance(source_type=SourceType.LOCAL_FILE),
            pipeline={"version": "test"},
            data_quality=DataQuality(),
            analysis_status=AnalysisStatus.FAILED,
            errors=[ErrorRecord(code="NO_LIGHT_CURVE", message="test")],
        )


def test_missing_local_file_returns_structured_failure(tmp_path):
    result = analyze_local_file(tmp_path / "missing.csv")
    assert result.analysis_status is AnalysisStatus.FAILED
    assert result.event is None
    assert result.errors[0].code == "NO_LIGHT_CURVE"
    assert result.provenance.source_type is SourceType.LOCAL_FILE


def test_bad_local_csv_returns_structured_failure(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("x,y\n1,2\n", encoding="utf-8")
    result = analyze_local_file(path)
    assert result.analysis_status is AnalysisStatus.FAILED
    assert result.errors[0].code == "INVALID_LIGHT_CURVE"


def test_invalid_search_configuration_is_rejected():
    with pytest.raises(ValueError, match="duration must be shorter"):
        AnalysisConfig(period_min_days=0.1, period_max_days=1, duration_min_hours=0.5, duration_max_hours=3)


def test_failed_result_requires_error():
    with pytest.raises(ValidationError, match="failed analyses must include"):
        AnalysisResult(
            analysis_id="test",
            created_at_utc="2026-01-01T00:00:00Z",
            data_kind=DataKind.REAL_OBSERVATION,
            target=Target(),
            provenance=Provenance(source_type=SourceType.LOCAL_FILE),
            pipeline={"version": "test"},
            data_quality=DataQuality(),
            analysis_status=AnalysisStatus.FAILED,
            errors=[],
        )
