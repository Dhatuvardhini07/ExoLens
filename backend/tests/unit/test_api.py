from fastapi.testclient import TestClient

import exolens.api as api
from exolens.pipeline import AnalysisConfig, analyze_curve, analyze_local_file


def _request(tic="TIC 39728879"):
    return {
        "target": {"tic_id": tic},
        "data_selection": {"sector": 6, "author": "TESS-SPOC", "product_id": None},
        "search": {
            "period_min_days": 2.0,
            "period_max_days": 2.4,
            "duration_min_hours": 1.5,
            "duration_max_hours": 2.5,
            "n_periods": 201,
            "n_durations": 5,
        },
    }


def test_health_endpoint_returns_ready_status(tmp_path):
    client = TestClient(api.create_app(cache_dir=tmp_path))
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analysis_job_returns_chart_arrays_from_same_pipeline_result(monkeypatch, tmp_path, synthetic_transit_curve):
    def synthetic_analysis(tic_id, *, config, **kwargs):
        return analyze_curve(synthetic_transit_curve, config)

    monkeypatch.setattr(api, "analyze_tess_target", synthetic_analysis)
    client = TestClient(api.create_app(cache_dir=tmp_path))
    started = client.post("/api/v1/analyses", json=_request())
    assert started.status_code == 202
    job_id = started.json()["analysis_id"]
    job = client.get(started.json()["status_url"]).json()

    assert job["status"] == "completed"
    result = job["result"]
    assert result["analysis_id"] == job_id
    assert result["data_kind"] == "synthetic_test"
    assert result["provenance"]["source_type"] == "synthetic_fixture"
    assert len(result["chart_data"]["observations"]) == result["data_quality"]["used_points"]
    assert len(result["chart_data"]["phase_folded"]) == result["data_quality"]["used_points"]
    assert len(result["chart_data"]["periodogram"]) == result["pipeline"]["bls_n_periods"]
    assert result["chart_data"]["time_system"] == result["provenance"]["time_system"]
    assert "periodogram" not in result["event"]["bls"]
    assert result["event"]["period_days"] == result["event"]["bls"]["best_period_days"]
    assert result["event"]["duration_hours"] == result["event"]["bls"]["best_duration_hours"]
    assert result["validation"]["status"] == "unvalidated"
    assert client.get(f"/api/v1/analyses/{job_id}/result").json() == result


def test_invalid_tic_and_search_ranges_have_structured_errors(tmp_path):
    client = TestClient(api.create_app(cache_dir=tmp_path))
    invalid_tic = client.post("/api/v1/analyses", json=_request("TIC nope"))
    assert invalid_tic.status_code == 422
    assert invalid_tic.json()["error"]["code"] == "INVALID_REQUEST"

    invalid_search = _request()
    invalid_search["search"]["period_max_days"] = 1.0
    response = client.post("/api/v1/analyses", json=invalid_search)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_cached_fits_is_selected_without_mast_call(monkeypatch, tmp_path, synthetic_transit_curve):
    cache = tmp_path / "mastDownload"
    product = cache / "hlsp_tess-spoc_tess_phot_0000000039728879-s0006_tess_v1_lc.fits"
    product.parent.mkdir(parents=True)
    product.touch()
    seen = {}

    def local_analysis(filename, **kwargs):
        seen["filename"] = filename
        seen.update(kwargs)
        return analyze_curve(synthetic_transit_curve, kwargs["config"])

    def unexpected_archive(*args, **kwargs):
        raise AssertionError("MAST should not be used when a matching cached FITS exists")

    monkeypatch.setattr(api, "analyze_local_file", local_analysis)
    monkeypatch.setattr(api, "analyze_tess_target", unexpected_archive)
    client = TestClient(api.create_app(cache_dir=cache))
    response = client.post("/api/v1/analyses", json=_request())
    job = client.get(response.json()["status_url"]).json()

    assert response.status_code == 202
    assert job["status"] == "completed"
    assert seen["filename"] == product
    assert seen["tic_id"] == "TIC 39728879"
    assert seen["sector"] == 6


def test_failed_pipeline_job_is_terminal_and_exposes_structured_reason(monkeypatch, tmp_path):
    def no_local_product(tic_id, *, config, **kwargs):
        return analyze_local_file(tmp_path / "missing.csv", config=config, tic_id=tic_id)

    monkeypatch.setattr(api, "analyze_tess_target", no_local_product)
    client = TestClient(api.create_app(cache_dir=tmp_path))
    response = client.post("/api/v1/analyses", json=_request())
    job = client.get(response.json()["status_url"]).json()

    assert job["status"] == "failed"
    assert job["result"]["analysis_status"] == "failed"
    assert job["errors"][0]["code"] == "NO_LIGHT_CURVE"


def test_internal_failure_without_result_is_terminal_and_result_endpoint_is_structured(monkeypatch, tmp_path):
    def crash(*args, **kwargs):
        raise RuntimeError("private internal detail")

    monkeypatch.setattr(api, "_execute_analysis", crash)
    client = TestClient(api.create_app(cache_dir=tmp_path))
    started = client.post("/api/v1/analyses", json=_request())
    job_id = started.json()["analysis_id"]
    job = client.get(started.json()["status_url"]).json()

    assert job["status"] == "failed"
    assert job["result"] is None
    assert job["errors"][0]["code"] == "ANALYSIS_FAILED"
    assert "private internal detail" not in job["errors"][0]["message"]
    error = client.get(f"/api/v1/analyses/{job_id}/result")
    assert error.status_code == 422
    assert error.json()["error"]["code"] == "ANALYSIS_FAILED"


def test_unknown_analysis_returns_structured_not_found(tmp_path):
    client = TestClient(api.create_app(cache_dir=tmp_path))
    response = client.get("/api/v1/analyses/unknown")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ANALYSIS_NOT_FOUND"
