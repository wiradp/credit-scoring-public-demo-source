# Stage 9 Step 4 — Controlled Runtime Adapter Report

## 1. Document Control

- Status: `PASS`
- Generated: `2026-07-16T06:16:58Z`
- Baseline: `884318a10791a659f56ff0e12d95605bd78a5ea5`
- Classification: `PORTFOLIO_DEMO_ONLY`

## 2. Scope and Non-Goals

This step implements and tests controlled local calibrated inference for the five committed synthetic sample profiles only. A `SAMPLE_PROFILE` mode string alone is not authorization: an exact allowlisted profile ID is mandatory, readiness is verified from committed contracts, and all 49 caller values must match the selected committed fixture. It does not activate public input, alter Streamlit UI files, make lending decisions, retrain or recalibrate the model, recompute the threshold, or deploy publicly.

## 3. Repository Preconditions

The target branch was clean at the committed Step 3.1 repair baseline with 55 tracked files and no staged or untracked files. Its parent is the verified model-intake commit. The read-only development repository was on its expected clean branch and commit.

## 4. Committed Step 3.1 Repair Baseline

The committed repair hashes and contract fields passed. All five synthetic profiles contain `purpose = other`. `FIXED_ALLOWED_CATEGORY_REPAIR` is fixture lineage; canonical runtime `value_source` remains `SYNTHETIC_BASELINE`. No fourth canonical provenance label was introduced.

## 5. Frozen Runtime Contract

The runtime preserves 49 canonical features, portfolio-demo-only classification, fail-closed behavior, no fabricated probability, no approval or rejection output, no raw-input or canonical-payload logging, and no public deployment.

## 6. Model and Threshold Integrity

The fixed model and threshold are regular non-symlink files whose size and SHA-256 match their committed manifest. The frozen external and bundled thresholds both equal `0.1` within `1e-12`.

## 7. Legacy Inference Module Assessment

Executable `pickle.load`, `predict_proba`, arbitrary-path behavior, legacy fallback paths, and hard-coded descriptive risk bands were removed. Compatibility signatures reject non-null path overrides rather than using or ignoring them.

## 8. Runtime Adapter Design

The adapter validates contracts and bytes before lazy deserialization, validates the bundle and feature order after loading, and caches at most one verified immutable runtime. Only the five allowlisted, ready, identity-matched committed profiles succeed. The compatibility wrapper requires a profile ID and rejects missing, unknown, conflicting, forged, and cross-profile payloads.

## 9. Fixed-Path and Deserialization Boundary

Paths are resolved from `Path(__file__).resolve()` and remain repository-relative in result metadata. The committed bundle is loaded with `joblib.load` only inside the verified runtime function after contract, manifest, file-type, size, and hash checks.

## 10. Bundle Validation

The top-level object is a dictionary with `model`, `calibrator`, `threshold`, and `feature_cols`. The model is `lightgbm.basic.Booster`; the calibrator is `sklearn.isotonic.IsotonicRegression`. Both expose callable `predict`. Neither exposes callable `predict_proba`. The exact ordered feature list contains 49 unique, non-blank names.

## 11. Repaired Categorical Feature Handling

`purpose` is feature index 40 and uses the exact 14-category model metadata. Each repaired `other` value is built with `pandas.Categorical`; no manual ordinal code is assigned. The repaired category `other` is compatible with the model. This does not prove that `other` is risk-neutral.

## 12. Canonical Payload Boundary

The adapter requires a mapping with exactly the bundle’s 49 features and compares its strictly normalized values with the selected committed fixture. Missing, extra, nested, non-finite, non-numeric, unknown categorical, changed finite, and cross-profile values fail closed. Prediction uses a newly reconstructed authoritative committed payload, never the caller’s original mapping. No value is filled, clipped, normalized beyond strict type equivalence, derived, or substituted.

## 13. Calibrated Prediction Pipeline

The committed model was loaded locally. `LightGBM Booster.predict` was executed locally, producing exactly one finite internal value. `IsotonicRegression.predict` was executed locally, producing exactly one finite probability in `[0, 1]`. `predict_proba` was not executed. Threshold relations use only the frozen `0.1` threshold and approved neutral wording.

## 14. Fail-Closed Behavior

The adapter returns canonical `inference_status = unavailable` for unauthorized modes, missing or invalid IDs, path overrides, contract or integrity failures, fixture mismatches, invalid bundles, invalid outputs, and runtime exceptions. Success uses `inference_status = available`; legacy UI status is separate metadata. It does not expose absolute paths, stack traces, complete payloads, mismatch values, or matrices.

## 15. Unit and Static Test Results

Twenty-seven standard-library `unittest` tests passed with zero failures and zero errors. They reproduce and reject the finite-`dti` bypass, cross-profile pairing, missing and unknown IDs, not-ready profiles, categorical forgery, and malformed payloads before prediction. Static AST checks found no executable `predict_proba`, pickle load, shell, subprocess, network, or top-level model-load/predict calls. An actual persisted AppTest in the unittest file ran through the documented command; default rendering passed with zero exceptions and did not load the model, execute prediction, or generate probability.

## 16. Controlled Local Synthetic Inference Results

All five profiles were run twice through `run_committed_sample_profile_inference`, which loads fixture values internally. Their deterministic probabilities match the pre-revision evidence within `1e-15`; the finite bounded range remains `0.31875881523272215` to `0.5721649484536082`. Canonical runtime and smoke statuses both use `available`. Profile labels do not define expected probability order. Equal probabilities are permitted under isotonic calibration.

## 17. Privacy and Responsible-AI Boundaries

No personal data was used. Evidence records profile identifiers, display names, counts, internal raw outputs, calibrated probabilities, relations, and timings only. It records no raw payload, canonical payload, or model input matrix. No fairness or legal-compliance conclusion is made.

## 18. Runtime State After Step 4

The model and calibrator were loaded and executed only for verified committed profiles in controlled local tests. Forged `SAMPLE_PROFILE` payloads were rejected before either prediction method. No public user-input path was activated. No Streamlit UI file was modified. No public deployment occurred. No approval or rejection decision was produced.

## 19. Limitations

Local controlled inference success does not prove public-host build, public URL behavior, concurrent-session behavior, public form safety, or deployment-platform compatibility. Basic Form, Advanced Editor, and Canonical Payload inference remain unauthorized and untested.

## 20. Step 4 Completion Criteria

The fixed-path adapter, categorical handling, calibrated pipeline, fail-closed tests, five-profile smoke run, sanitized evidence, and exact file scope all pass. Model, threshold, repair contracts, UI files, and development repository remain unchanged.

## 21. Authorization for the Next Step

Human audit and separate Git scope review are authorized. Streamlit UI integration, public-input activation, public-host build, public deployment, staging, and commit are not authorized by this report.
