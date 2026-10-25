import json

from exolens.cli import main


def test_cli_writes_failure_json_and_nonzero_exit(tmp_path):
    output = tmp_path / "failed.json"
    code = main(["analyze-file", str(tmp_path / "missing.csv"), "--output", str(output)])
    assert code == 2
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["analysis_status"] == "failed"
    assert payload["errors"][0]["code"] == "NO_LIGHT_CURVE"
