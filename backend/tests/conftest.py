import pytest

from app import ml


@pytest.fixture(autouse=True)
def isolated_experiments(tmp_path, monkeypatch):
    monkeypatch.setenv("FOREARMSENSE_OUTPUT_ROOT", str(tmp_path))
    monkeypatch.setattr(ml, "MODELS", {})
    monkeypatch.setattr(ml, "METRICS", None)
