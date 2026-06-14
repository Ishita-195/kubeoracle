"""
Shared fixtures for the mlops test suite.

The mlops modules import each other by bare module name and resolve paths
relative to the repo root, so we put each package directory on sys.path.

We also neutralise os-level symlinks: train.py and registry.py create
`model_latest.pkl` / `model_production.pkl` via Path.symlink_to, which requires
elevated privileges on Windows. Replacing it with a file copy keeps the exact
same code paths executing and behaves identically for the readers downstream.
"""
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for _sub in ["training", "model_registry", "monitoring", "serving", "pipelines"]:
    _p = str(ROOT / "mlops" / _sub)
    if _p not in sys.path:
        sys.path.insert(0, _p)


@pytest.fixture(autouse=True)
def symlink_as_copy(monkeypatch):
    """Make Path.symlink_to copy the target instead, for cross-platform tests."""
    def _copy(self, target, target_is_directory=False):
        src = self.parent / target          # registry/train pass a bare filename
        if self.exists() or self.is_symlink():
            self.unlink()
        shutil.copy(src, self)

    monkeypatch.setattr(Path, "symlink_to", _copy, raising=True)
    yield
