from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class DataKind(str, Enum):
    REAL_OBSERVATION = "real_observation"
    SYNTHETIC_TEST = "synthetic_test"


class SourceType(str, Enum):
    MAST_PRODUCT = "mast_product"
    LOCAL_FILE = "local_file"
    SYNTHETIC_FIXTURE = "synthetic_fixture"


class AnalysisStatus(str, Enum):
    COMPLETED = "completed"
    NO_SIGNAL = "no_signal"
    FAILED = "failed"


class SignalStatus(str, Enum):
    CANDIDATE_SIGNAL = "candidate_signal"
    NO_SIGNAL = "no_signal"
    NOT_EVALUATED = "not_evaluated"


class ValidationStatus(str, Enum):
    UNVALIDATED = "unvalidated"
    CATALOG_MATCH = "catalog_match"
    INDEPENDENTLY_VALIDATED = "independently_validated"


class ErrorRecord(StrictModel):
    code: str
    message: str
    retryable: bool = False


class Target(StrictModel):
    tic_id: str | None = None
    display_name: str | None = None


class Provenance(StrictModel):
    mission: str | None = None
    sector: int | None = None
    data_author: str | None = None
    product_id: str | None = None
    archive_url: str | None = None
    source_type: SourceType
    source_filename: str | None = None
    retrieved_at_utc: datetime | None = None
    source_file_sha256: str | None = None
    cadence_seconds: float | None = None
    time_system: str | None = None
    time_start: float | None = None
    time_end: float | None = None


class PipelineInfo(StrictModel):
    name: str = "ExoLens"
    version: str
    bls_period_range_days: tuple[float, float] | None = None
    bls_duration_range_hours: tuple[float, float] | None = None
    bls_n_periods: int | None = None
    bls_n_durations: int | None = None
    preprocessing: list[dict[str, Any]] = Field(default_factory=list)
    measurement_methods: dict[str, str] = Field(default_factory=dict)
    software: dict[str, str] = Field(default_factory=dict)


class DataQuality(StrictModel):
    input_points: int | None = None
    used_points: int | None = None
    removed_nan_points: int | None = None
    removed_quality_flag_points: int | None = None
    time_span_days: float | None = None
    gap_count: int | None = None
    warnings: list[str] = Field(default_factory=list)


class TimeFluxPoint(StrictModel):
    time: float
    flux: float


class PeriodPowerPoint(StrictModel):
    period_days: float
    power: float


class PhaseFluxPoint(StrictModel):
    phase: float
    flux: float


class ChartData(StrictModel):
    time_system: str | None = None
    observations: list[TimeFluxPoint] = Field(default_factory=list)
    periodogram: list[PeriodPowerPoint] = Field(default_factory=list)
    phase_folded: list[PhaseFluxPoint] = Field(default_factory=list)
    model_curve: list[TimeFluxPoint] | None = None
    unavailable_reasons: dict[str, str] = Field(default_factory=dict)


class BLSResult(StrictModel):
    power: float | None = None
    best_period_days: float | None = None
    best_duration_hours: float | None = None
    transit_time: float | None = None
    depth_fraction: float | None = None
    # Internal array used to build chart_data; serialized only once at the top level.
    periodogram: list[PeriodPowerPoint] = Field(default_factory=list, exclude=True)


class MeasurementUncertainty(StrictModel):
    value: float | None = None
    lower: float | None = None
    upper: float | None = None
    unit: str
    method: str = "not_calculated"
    confidence_level: float | None = None


class Uncertainties(StrictModel):
    period_days: MeasurementUncertainty
    depth_fraction: MeasurementUncertainty
    duration_hours: MeasurementUncertainty
    epoch_time: MeasurementUncertainty


class Significance(StrictModel):
    snr: float | None = None
    false_alarm_probability: float | None = None
    method: str | None = None


class Event(StrictModel):
    signal_status: SignalStatus = SignalStatus.NOT_EVALUATED
    period_days: float | None = None
    epoch_time: float | None = None
    duration_hours: float | None = None
    depth_fraction: float | None = None
    depth_method: str | None = None
    depth_unavailable_reason: str | None = None
    bls: BLSResult
    uncertainties: Uncertainties
    significance: Significance = Field(default_factory=Significance)


class Validation(StrictModel):
    status: ValidationStatus = ValidationStatus.UNVALIDATED
    source_name: str | None = None
    source_url: str | None = None
    checked_at_utc: datetime | None = None
    notes: str | None = "No independent or catalog validation has been performed."


class AnalysisResult(StrictModel):
    schema_version: str = "1.1"
    analysis_id: str
    created_at_utc: datetime
    data_kind: DataKind
    target: Target
    provenance: Provenance
    pipeline: PipelineInfo
    data_quality: DataQuality
    analysis_status: AnalysisStatus
    event: Event | None = None
    validation: Validation = Field(default_factory=Validation)
    errors: list[ErrorRecord] = Field(default_factory=list)
    chart_data: ChartData | None = None

    @model_validator(mode="after")
    def check_result_consistency(self) -> "AnalysisResult":
        if self.data_kind is DataKind.SYNTHETIC_TEST and self.provenance.source_type is not SourceType.SYNTHETIC_FIXTURE:
            raise ValueError("synthetic_test data must use synthetic_fixture provenance")
        if self.data_kind is DataKind.REAL_OBSERVATION and self.provenance.source_type is SourceType.SYNTHETIC_FIXTURE:
            raise ValueError("real_observation data cannot use synthetic_fixture provenance")
        if self.analysis_status is AnalysisStatus.FAILED and not self.errors:
            raise ValueError("failed analyses must include at least one error")
        if self.analysis_status is AnalysisStatus.FAILED and self.event is not None:
            raise ValueError("failed analyses cannot contain a measured event")
        if self.analysis_status is AnalysisStatus.COMPLETED and self.event is None:
            raise ValueError("completed analyses must include the returned BLS event model")
        if self.analysis_status is not AnalysisStatus.FAILED and self.errors:
            raise ValueError("only failed analyses may contain errors")
        return self
