# Stage 6 - Dependency & Public Demo Packaging Cleanup

Generated: 2026-07-01

## Verdict

`STAGE6_READY_FOR_COMMIT_WITH_LIMITATIONS`

Stage 6 dependency cleanup, public-demo packaging cleanup, static validation, local launch validation, large-file audit, and curated package assembly are complete within the approved Stage 6 boundaries.

This verdict does **not** claim public live deployment, production readiness, fairness approval, legal compliance approval, deployment authorization, credit-decision readiness, or model-inference readiness.

## Completed Implementation Steps

| Step | Status | Evidence |
|---|---:|---|
| Step 1 - Create `requirements-demo.txt` | Passed | Minimal public demo dependency source created. |
| Step 2 - Clean repository `requirements.txt` | Passed | File contains only valid requirement/comment/blank lines and remains broad project/dev/notebook environment. |
| Step 3/3B - Patch Streamlit public error safety | Passed | `.streamlit/config.toml` uses `showErrorDetails = "none"`. |
| Step 4 - Static dependency/config validation | Passed | Requirements files and config passed static validation. |
| Step 5 - Active source import and legacy exposure scan | Passed | No direct active import evidence for `plotly`, `joblib`, or `pydantic`; no legacy dashboard route/import/link found. |
| Step 7B/7C - Dependency install/import validation | Passed | `streamlit`, `pandas`, `numpy`, `scikit-learn`, and `lightgbm` installed/imported with versions matching `requirements-demo.txt`. |
| Step 7D - Dependency consistency check | Passed | `python3 -m pip check` reported no broken requirements. |
| Step 8/8B/8C - Streamlit local launch/browser validation | Passed | Local server started, HTTP reachability returned `200 OK`, and server stopped cleanly. |
| Step 9/9B/9C/9D - Model artifact metadata investigation | Failed-safe / blocked | Artifact exists and has pickle protocol signature, but safe loader and direct pickle diagnosis fail with `UnpicklingError: invalid load key, '\x10'`. |
| Step 10 - Actual large-file audit | Completed | Full-repo deployment is blocked by tracked large files; curated package must exclude them. |
| Step 11/11B - Curated package manifest dry-run and validation | Passed | Include list resolved to 42 files, estimated size 1.589 MB, no included files >=10 MB. |
| Step 12 - Curated package assembly | Passed | Package assembled under `outputs/phase6/public_demo_package/`; model, data, notebooks, archive, phase1-5 outputs, and legacy dashboards excluded. |
| Step 13/13B/13C - Isolated package launch/browser validation | Passed | Package launched from isolated folder, HTTP reachability returned `200 OK`, and server stopped cleanly. |

## Readiness Dimensions

| Dimension | Status |
|---|---:|
| REQUIREMENTS_DEMO_CREATED | True |
| REQUIREMENTS_TXT_SYNTACTICALLY_CLEAN | True |
| STREAMLIT_PUBLIC_ERROR_CONFIG_PATCHED | True |
| STATIC_DEPENDENCY_CONFIG_SCAN_PASSED | True |
| ACTIVE_SOURCE_STATIC_SCAN_PASSED | True |
| DEPENDENCY_INSTALL_VALIDATED | True |
| DEPENDENCY_IMPORT_VALIDATED | True |
| PIP_CHECK_PASSED | True |
| STREAMLIT_LOCAL_LAUNCH_VALIDATED | True |
| STREAMLIT_LOCAL_BROWSER_REACHABLE | True |
| MODEL_LOAD_METADATA_VERIFIED | False |
| MODEL_LOAD_FAILED_SAFE | True |
| ARTIFACT_FORMAT_INSPECTION_COMPLETED | True |
| PICKLETOOLS_METADATA_PROBE_COMPLETED | True |
| LARGE_FILE_ACTUAL_AUDIT_RUN | True |
| FULL_REPO_DEPLOYMENT_BLOCKED | True |
| CURATED_PACKAGE_MANIFEST_VALIDATED | True |
| CURATED_PACKAGE_ASSEMBLED | True |
| CURATED_PACKAGE_LAUNCH_VALIDATED | True |
| CURATED_PACKAGE_BROWSER_REACHABLE | True |
| MODEL_ARTIFACT_EXCLUDED_FROM_PACKAGE | True |
| LEGACY_DASHBOARDS_EXCLUDED_FROM_PACKAGE | True |
| PUBLIC_LIVE_DEPLOYMENT_COMPLETED | False |

## Dependency Validation

`requirements-demo.txt` is the minimal public demo dependency source:

- `streamlit==1.51.0`
- `pandas==2.3.3`
- `numpy==1.26.4`
- `scikit-learn==1.7.2`
- `lightgbm==4.6.0`

Import validation passed after controlled install from `requirements-demo.txt`:

| Package | Detected version | Required version | Status |
|---|---:|---:|---|
| `streamlit` | `1.51.0` | `1.51.0` | Passed |
| `pandas` | `2.3.3` | `2.3.3` | Passed |
| `numpy` | `1.26.4` | `1.26.4` | Passed |
| `scikit-learn` / `sklearn` | `1.7.2` | `1.7.2` | Passed |
| `lightgbm` | `4.6.0` | `4.6.0` | Passed |

`python3 -m pip check` reported no broken requirements.

The repository-level `requirements.txt` remains a broad project/dev/notebook environment file. It is not the curated public demo deployment contract.

## Config Validation

`.streamlit/config.toml` uses public-safe error behavior:

```toml
[client]
showErrorDetails = "none"
```

Theme values were not changed.

## Streamlit Validation

Local Streamlit validation passed:

- main repo launch smoke: passed
- main repo browser reachability: `HTTP/1.1 200 OK`
- isolated curated package launch: passed
- isolated curated package browser reachability: `HTTP/1.1 200 OK`
- validation servers stopped cleanly after checks

No UI action was clicked to trigger inference.

## Model Artifact Status

Model artifact path:

```text
models/final_model_calibrated.pkl
```

Status:

- artifact exists in the main repo
- artifact header matches pickle protocol 4
- `pickletools` metadata probe found wrapper-dict and LightGBM Booster clues
- safe loader failed safely with `MODEL_ARTIFACT_LOAD_ERROR`
- direct pickle diagnosis failed with `UnpicklingError: invalid load key, '\x10'`
- model artifact is excluded from the curated public demo package

Model-load preview remains blocked. Stage 6 does not claim model inference readiness.

## Large-File Audit

Actual large-file audit completed:

- tracked large files: 25
- untracked large files: 0
- full-repo deployment blocked: True
- largest tracked blocker: `data/processed/X_train.csv` at approximately 958 MB
- all Step 10 large files are excluded from curated package

Full-repo deployment remains blocked. Curated package deployment is the recommended packaging strategy.

## Curated Package

Package path:

```text
outputs/phase6/public_demo_package/
```

Package validation:

- file count: 42
- estimated total size: 1.589 MB
- files >=10 MB: none
- deployment-target `requirements.txt` is derived from `requirements-demo.txt`
- `.streamlit/config.toml` included
- `app/streamlit_app.py` included
- required `app/src/` modules included
- required contract artifacts included
- Stage 6 public-safe report files included

Excluded from curated package:

- `models/final_model_calibrated.pkl`
- `app/dashboard_1.py`
- `app/dashboard_2.py`
- `app/utils.py`
- `data/`
- `notebooks/`
- `archive/`
- `outputs/phase1/` through `outputs/phase5/`
- cache/build artifacts

## Guardrails Preserved

Stage 6 did not:

- deploy the app
- create a public live deployment
- commit changes
- execute `predict_proba`
- apply thresholds
- run SHAP
- generate probability, score, approval, rejection, eligibility, credit-decision, or adverse-action outputs
- claim fairness approval
- claim legal compliance approval
- claim production readiness
- claim deployment authorization
- claim model-inference readiness

## Remaining Limitations / Blockers

- Model-load metadata verification remains failed-safe / blocked.
- The model artifact is excluded from the curated package.
- Full-repo deployment remains blocked by tracked large files.
- Curated package is assembled and locally validated, but not deployed.
- Browser validation was limited to local reachability and user-visible inspection boundary; no inference-triggering action was clicked.
- Streamlit runtime emitted non-blocking warnings about `use_container_width` deprecation and PyArrow dataframe auto-fixes; these should be handled in a future UI cleanup stage, not silently patched in Stage 6.

## Final Recommendation

Stage 6 is ready for commit review with limitations. Commit should include the Stage 6 dependency/config/package/report changes, while preserving the explicit blockers and non-claims above.
