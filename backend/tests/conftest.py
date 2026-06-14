"""
Shared fixtures for the backend test suite.

The backend is designed to run with `backend/` as the working directory
(uvicorn main:app), so its modules import each other by bare name
(`from mock_generator import ...`). We replicate that here by putting the
backend root on sys.path before any backend module is imported.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture(scope="session")
def client():
    """A FastAPI TestClient bound to the real application."""
    from main import app
    return TestClient(app)
