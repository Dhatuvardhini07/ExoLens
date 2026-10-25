import csv

from exolens.data.loaders import load_local_file
from exolens.errors import ExoLensError
from exolens.models.result import SourceType
import pytest


def test_csv_loader_records_local_metadata_and_hash(tmp_path):
    path = tmp_path / "synthetic_fixture.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["time", "flux", "flux_err", "quality"])
        for index in range(25):
            writer.writerow([index / 10, 1.0, 0.01, 0])

    curve = load_local_file(
        path,
        tic_id="12345",
        sector=7,
        mission="TESS",
        cadence_seconds=1200,
        time_system="synthetic test time in days",
        synthetic_test_data=True,
    )
    assert curve.target.tic_id == "TIC 12345"
    assert curve.provenance.sector == 7
    assert curve.provenance.source_filename == path.name
    assert len(curve.provenance.source_file_sha256) == 64
    assert curve.provenance.source_type is SourceType.SYNTHETIC_FIXTURE
    assert curve.data_kind == "synthetic_test"
    assert curve.time.size == 25


def test_csv_loader_rejects_non_numeric_values(tmp_path):
    path = tmp_path / "invalid.csv"
    path.write_text("time,flux\nnot-a-time,1\n", encoding="utf-8")
    with pytest.raises(ExoLensError, match="non-numeric"):
        load_local_file(path)
