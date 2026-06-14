"""
Unit tests for mlops/model_registry/registry.py.

ARTIFACTS_DIR and REGISTRY_FILE are redirected to a tmp dir so the real
registry is never touched. The autouse symlink->copy fixture (conftest)
makes promote() work on Windows.
"""
import json
import pickle

import pytest


@pytest.fixture
def reg_env(monkeypatch, tmp_path):
    import registry as reg
    monkeypatch.setattr(reg, "ARTIFACTS_DIR", tmp_path)
    monkeypatch.setattr(reg, "REGISTRY_FILE", tmp_path / "registry.json")
    return reg, tmp_path


def _register(reg, tmp, version, auc=0.90):
    meta = {
        "version": version,
        "mlflow_run_id": f"run-{version}",
        "params": {"n_estimators": 80},
        "metrics": {"roc_auc": auc, "f1": 0.85},
        "features": ["cpu", "mem"],
        "registered_at": f"2026-01-0{version[-1]}T00:00:00",
    }
    meta_path = tmp / f"model_{version}_meta.json"
    meta_path.write_text(json.dumps(meta))
    reg.register_from_meta(meta_path)
    # accompanying artifact so promote() can find it
    with open(tmp / f"model_{version}.pkl", "wb") as f:
        pickle.dump({"version": version}, f)


def test_empty_registry_defaults(reg_env):
    reg, _ = reg_env
    assert reg.list_versions() == []
    assert reg._load_registry()["production"] is None


def test_register_and_list(reg_env):
    reg, tmp = reg_env
    _register(reg, tmp, "v1")
    versions = reg.list_versions()
    assert len(versions) == 1
    assert versions[0]["version"] == "v1"
    assert versions[0]["is_production"] is False


def test_info(reg_env):
    reg, tmp = reg_env
    _register(reg, tmp, "v1")
    data = reg.info("v1")
    assert data["version"] == "v1"
    assert data["metrics"]["roc_auc"] == 0.90


def test_info_unknown_version_raises(reg_env):
    reg, _ = reg_env
    with pytest.raises(ValueError):
        reg.info("nope")


def test_promote_and_get_production_model(reg_env):
    reg, tmp = reg_env
    _register(reg, tmp, "v1")
    reg.promote("v1")
    stored = json.loads((tmp / "registry.json").read_text())
    assert stored["production"] == "v1"
    assert reg.get_production_model() == {"version": "v1"}
    assert reg.list_versions()[0]["is_production"] is True


def test_promote_unknown_version_raises(reg_env):
    reg, _ = reg_env
    with pytest.raises(ValueError):
        reg.promote("ghost")


def test_promote_missing_artifact_raises(reg_env):
    reg, tmp = reg_env
    meta = {"version": "v9", "metrics": {}, "params": {}, "features": [],
            "registered_at": "2026-01-09T00:00:00", "mlflow_run_id": "x"}
    mp = tmp / "model_v9_meta.json"
    mp.write_text(json.dumps(meta))
    reg.register_from_meta(mp)   # registered, but no model_v9.pkl artifact
    with pytest.raises(FileNotFoundError):
        reg.promote("v9")


def test_rollback(reg_env):
    reg, tmp = reg_env
    _register(reg, tmp, "v1")
    _register(reg, tmp, "v2")
    reg.promote("v1")
    reg.promote("v2")
    reg.rollback()
    stored = json.loads((tmp / "registry.json").read_text())
    assert stored["production"] == "v1"


def test_rollback_without_history(reg_env, capsys):
    reg, _ = reg_env
    reg.rollback()   # nothing to roll back to
    assert "No previous production" in capsys.readouterr().out


def test_get_production_falls_back_to_latest(reg_env):
    reg, tmp = reg_env
    with open(tmp / "model_latest.pkl", "wb") as f:
        pickle.dump({"latest": True}, f)
    assert reg.get_production_model() == {"latest": True}


def test_get_production_raises_when_nothing(reg_env):
    reg, _ = reg_env
    with pytest.raises(RuntimeError):
        reg.get_production_model()


def test_cli_list_and_promote_and_info(reg_env, monkeypatch, capsys):
    reg, tmp = reg_env
    monkeypatch.setattr("sys.argv", ["registry.py", "list"])
    reg._cli()
    assert "No registered models" in capsys.readouterr().out

    _register(reg, tmp, "v1")
    monkeypatch.setattr("sys.argv", ["registry.py", "promote", "v1"])
    reg._cli()
    monkeypatch.setattr("sys.argv", ["registry.py", "list"])
    reg._cli()
    assert "v1" in capsys.readouterr().out

    monkeypatch.setattr("sys.argv", ["registry.py", "info", "v1"])
    reg._cli()
    assert "v1" in capsys.readouterr().out


def test_cli_unknown_command_exits(reg_env, monkeypatch):
    reg, _ = reg_env
    monkeypatch.setattr("sys.argv", ["registry.py", "frobnicate"])
    with pytest.raises(SystemExit):
        reg._cli()
