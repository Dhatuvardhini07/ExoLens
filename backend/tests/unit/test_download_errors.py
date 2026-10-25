from exolens.errors import ExoLensError
from exolens.data.loaders import download_tess_target
import lightkurve as lk
import pytest


def test_tess_search_failure_is_wrapped_as_retryable(monkeypatch):
    def fail_search(*args, **kwargs):
        raise OSError("simulated network outage")
    monkeypatch.setattr(lk, "search_lightcurve", fail_search)
    with pytest.raises(ExoLensError) as caught:
        download_tess_target("123456789")
    assert caught.value.code == "DOWNLOAD_FAILED"
    assert caught.value.retryable is True
