import json

from exolens.exporters import write_csv, write_json
from exolens.pipeline import AnalysisConfig, analyze_curve


def test_json_csv_exports_preserve_synthetic_test_label(tmp_path, synthetic_transit_curve):
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
    assert result.data_kind.value == "synthetic_test"
    json_path = write_json(result, tmp_path / "result.json")
    csv_path = write_csv(result, tmp_path / "result.csv")
    saved = json.loads(json_path.read_text(encoding="utf-8"))
    assert saved["provenance"]["source_type"] == "synthetic_fixture"
    assert saved["event"]["bls"]["power"] is not None
    assert saved["event"]["significance"]["snr"] is None
    assert csv_path.is_file()
    assert "synthetic_test" in csv_path.read_text(encoding="utf-8-sig")
