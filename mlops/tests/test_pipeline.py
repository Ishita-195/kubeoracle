"""
Unit tests for mlops/pipelines/retrain_pipeline.py.

Training is real but sandboxed: train/registry output dirs and the MLflow
tracking URI all point inside tmp_path, and n_samples is kept small.
"""
import json

import pytest


@pytest.fixture
def sandbox(monkeypatch, tmp_path):
    import mlflow
    import registry
    import retrain_pipeline as rp
    import train
    import monitor

    art = tmp_path / "artifacts"
    data = tmp_path / "data"
    rep = tmp_path / "reports"
    for d in (art, data, rep):
        d.mkdir()

    monkeypatch.setattr(train, "DATA_DIR", data)
    monkeypatch.setattr(train, "MODEL_DIR", art)
    monkeypatch.setattr(train, "REPORT_DIR", rep)
    monkeypatch.setattr(registry, "ARTIFACTS_DIR", art)
    monkeypatch.setattr(registry, "REGISTRY_FILE", tmp_path / "registry.json")
    monkeypatch.setattr(rp, "PIPELINE_LOG", tmp_path / "pipeline_runs.jsonl")
    monkeypatch.setattr(rp, "ROOT", tmp_path)
    # keep drift checks deterministic (no prediction log => no drift)
    monkeypatch.setattr(monitor, "LOG_PATH", tmp_path / "preds.jsonl")
    monkeypatch.setattr(monitor, "BASELINE_PATH", tmp_path / "baseline.json")
    # mlflow >=3 puts the local file store in maintenance mode; opt back in so
    # the test works on both the pinned CI version (2.13) and newer locals.
    monkeypatch.setenv("MLFLOW_ALLOW_FILE_STORE", "true")
    mlflow.set_tracking_uri((tmp_path / "mlruns").as_uri())
    return rp, registry, tmp_path


def test_log_run_writes_jsonl(sandbox):
    rp, _, tmp = sandbox
    rp._log_run({"retrained": False})
    lines = (tmp / "pipeline_runs.jsonl").read_text().splitlines()
    assert len(lines) == 1
    assert "ts" in json.loads(lines[0])


def test_current_production_auc_none_when_no_registry(sandbox):
    rp, _, _ = sandbox
    assert rp._current_production_auc() is None


def test_current_production_auc_reads_value(sandbox):
    rp, _, tmp = sandbox
    reg_dir = tmp / "mlops" / "model_registry"
    reg_dir.mkdir(parents=True)
    (reg_dir / "registry.json").write_text(json.dumps({
        "production": "v1",
        "versions": {"v1": {"metrics": {"roc_auc": 0.93}}},
    }))
    assert rp._current_production_auc() == 0.93


def test_check_drift_needed_no_drift(sandbox):
    rp, _, _ = sandbox
    should, reasons = rp._check_drift_needed()
    assert should is False
    assert reasons == []


def test_run_pipeline_skips_without_drift(sandbox):
    rp, _, _ = sandbox
    outcome = rp.run_pipeline(force=False, dry_run=False)
    assert outcome["retrained"] is False
    assert "No critical drift" in outcome["skipped_reason"]


def test_run_pipeline_dry_run(sandbox):
    rp, _, _ = sandbox
    outcome = rp.run_pipeline(force=True, dry_run=True)
    assert outcome["skipped_reason"] == "dry-run"
    assert outcome["retrained"] is False


def test_run_pipeline_force_trains_and_promotes(sandbox):
    rp, registry, tmp = sandbox
    # pre-register a version with an artifact so the promote() path runs
    import pickle
    meta = {"version": "seed", "metrics": {"roc_auc": 0.5}, "params": {},
            "features": [], "registered_at": "2026-01-01T00:00:00", "mlflow_run_id": "x"}
    mp = tmp / "artifacts" / "model_seed_meta.json"
    mp.write_text(json.dumps(meta))
    registry.register_from_meta(mp)
    with open(tmp / "artifacts" / "model_seed.pkl", "wb") as f:
        pickle.dump({"seed": True}, f)

    outcome = rp.run_pipeline(force=True, dry_run=False, n_samples=250)
    assert outcome["retrained"] is True
    assert outcome["promoted"] is True


def test_run_pipeline_retains_champion(sandbox):
    rp, _, tmp = sandbox
    # production model already has a very high AUC the challenger can't beat
    reg_dir = tmp / "mlops" / "model_registry"
    reg_dir.mkdir(parents=True)
    (reg_dir / "registry.json").write_text(json.dumps({
        "production": "v1",
        "versions": {"v1": {"metrics": {"roc_auc": 0.999}}},
    }))
    outcome = rp.run_pipeline(force=True, dry_run=False, n_samples=250)
    assert outcome["retrained"] is True
    assert outcome["promoted"] is False
