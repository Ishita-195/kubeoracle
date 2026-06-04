# KubeOracle MLOps Layer

> **Complete MLOps infrastructure for the KubeOracle AI failure-prediction engine.**  
> Drop this folder alongside the existing `kubeoracle-updated/` project to add production-grade model lifecycle management.

---

## Architecture

```
kubeoracle-updated/
├── backend/ml/predictor.py          ← Original (kept for compatibility)
│
mlops/                               ← NEW — this folder
├── training/
│   └── train.py                     ← Experiment tracking, hyperparameter sweep, data versioning
├── model_registry/
│   ├── registry.py                  ← Version list, promote, rollback
│   └── artifacts/                   ← Versioned .pkl files + metadata JSON cards
├── serving/
│   └── predictor.py                 ← MLOps-aware drop-in for backend/ml/predictor.py
├── monitoring/
│   └── monitor.py                   ← PSI drift detection, output drift, alert log
├── pipelines/
│   └── retrain_pipeline.py          ← Orchestrates drift check → train → champion/challenger
├── data/
│   └── dataset_<timestamp>.json     ← Versioned training snapshots
└── tests/
    └── test_training.py             ← Pytest suite

.github/workflows/
└── mlops.yml                        ← GitHub Actions: lint → drift → train → build → deploy
```

---

## Quickstart

### 1. Install MLOps dependencies

```bash
# From the project root
pip install -r backend/requirements.txt
pip install -r mlops/requirements-mlops.txt
```

### 2. Train the first model

```bash
python mlops/training/train.py
# Options:
#   --n-samples 5000    larger dataset
#   --experiment my-exp custom MLflow experiment name
```

This will:
- Generate a versioned synthetic dataset in `mlops/data/`
- Run 3 hyperparameter trials tracked in MLflow
- Save the best model to `mlops/model_registry/artifacts/`
- Create a `model_latest.pkl` symlink

### 3. Inspect experiments (MLflow UI)

```bash
mlflow ui
# Open http://localhost:5000
```

### 4. Promote a model to production

```bash
# List all versions
python mlops/model_registry/registry.py list

# Promote a specific version
python mlops/model_registry/registry.py promote 20240115T093000

# Roll back if needed
python mlops/model_registry/registry.py rollback
```

### 5. Switch the backend to the MLOps predictor

In `backend/main.py`, swap the import:

```python
# Before (original)
from ml.predictor import get_model, predict_failure_probability

# After (MLOps-aware — loads from registry, hot-reloads every 5 min)
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "mlops" / "serving"))
from predictor import get_model, predict_failure_probability
```

Or set the environment variable:
```bash
export MLOPS_PREDICTOR=1   # handled by serving/predictor.py auto-detection
```

### 6. Start the model monitor

```bash
# One-shot drift report
python mlops/monitoring/monitor.py report

# Long-running monitor API on port 8001
python mlops/monitoring/monitor.py serve

# CI gate (exits 1 if critical drift)
python mlops/monitoring/monitor.py check-drift
```

### 7. Run the retraining pipeline

```bash
# Auto-check drift, retrain only if needed
python mlops/pipelines/retrain_pipeline.py

# Force retraining regardless of drift
python mlops/pipelines/retrain_pipeline.py --force

# Dry-run (check drift, do not retrain)
python mlops/pipelines/retrain_pipeline.py --dry-run
```

---

## CI/CD — GitHub Actions

The `.github/workflows/mlops.yml` workflow runs on every push to `main` and nightly:

| Job | Trigger | What it does |
|-----|---------|--------------|
| `lint-and-test` | Always | ruff + pytest with coverage gate (≥70%) |
| `drift-check` | Always | Runs `monitor.py check-drift`; sets `drift_detected` output |
| `train-and-evaluate` | Drift detected OR scheduled OR `--force` | Full training run + champion/challenger comparison |
| `build-and-push` | `main` branch after training | Builds Docker images with baked-in production model |
| `deploy-staging` | After successful build | Rolls out to staging cluster |
| `notify` | On failure | Slack notification |

**Required GitHub secrets:**

| Secret | Purpose |
|--------|---------|
| `GITHUB_TOKEN` | GHCR image push (auto-provided) |
| `SLACK_WEBHOOK_URL` | Failure notifications (optional) |
| `KUBECONFIG_STAGING` | kubectl access for staging deploy (optional) |

---

## Model Lifecycle

```
generate data → train (3 trials) → evaluate → register
      ↓                                           ↓
  monitor predictions              champion/challenger compare
      ↓                                           ↓
  drift alert                       promote to production
      ↓                                           ↓
  retrain pipeline               model_production.pkl symlink
                                        ↓
                               serving/predictor.py hot-reload
```

---

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `MODEL_TTL_SEC` | `300` | How often `serving/predictor.py` checks for a new model |
| `MLFLOW_TRACKING_URI` | `mlruns` | Local path or remote MLflow server URL |

---

## Monitoring Endpoints (port 8001)

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Liveness probe |
| `GET /drift` | Full drift report (PSI per feature + output drift) |
| `GET /alerts` | All emitted alerts (JSONL log) |
| `GET /stats` | Rolling prediction statistics |

---

## Adding Real Training Data

The current implementation uses synthetic data. To plug in real Prometheus metrics:

1. Add a `mlops/data/loader.py` that queries your Prometheus/Thanos endpoint
2. Replace the `generate_synthetic_data()` call in `train.py` with your loader
3. Call `compute_baseline(X, feature_names)` in `monitor.py` after the first real training run

---

## Running Tests

```bash
pytest mlops/tests/ -v --cov=mlops --cov-report=term-missing
```
