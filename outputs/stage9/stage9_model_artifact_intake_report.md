# Stage 9 Step 3 — Verified Model Artifact Intake Report

## 1. Document Control

| Field | Value |
| --- | --- |
| Project | Credit Risk Scoring + Fairness Audit |
| Stage / step | Stage 9 / Step 3 |
| Classification | `PORTFOLIO_DEMO_ONLY` |
| Target baseline | `phase8-public-demo-source` at `5cd4645af5706a71b2d95f7cc749219888cb5681` |
| Development baseline | `phase5b-demo-contracts` at `b2b4db65b2026493a336a4b9d17dc228327db380` |
| Validation | `PASS` |
| Generated at (UTC) | `2026-07-15T12:32:57Z` |

## 2. Scope

This step performs trusted model and threshold intake plus compatibility auditing only. It does not modify application code, activate model loading, execute prediction or inference, authorize public deployment, stage files, or create a commit.

## 3. Repository Preconditions

The target began clean with 45 tracked files, no staged or untracked files, and the frozen Stage 9 Step 2 contract present. The development repository was clean at the expected branch and commit. All preconditions passed before artifact inspection or copying.

## 4. Authoritative Source Artifacts

| Artifact | Source-relative path | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Calibrated bundle | `models/final_model_calibrated.pkl` | 4,881,685 | `b022b545bd7bb4294018a26a7d10af977e3c452b7f219dbdd9113adeac367cbf` |
| External threshold | `outputs/phase3/final_threshold.json` | 96 | `e45a19822f77d6b74cf5e76c0c0e6ff2f993bad4ab91e507509b3d74d410e28b` |

Both are readable tracked regular files, are not symlinks, are non-empty, and are not Git LFS pointers.

## 5. Git Lineage

The development repository HEAD is `b2b4db65b2026493a336a4b9d17dc228327db380`. Both source artifacts were last affected by commit `4e1edde3bd4d68cfc446eeae6527e054f13ba67f` (`Baseline before phase 4 continuation`). Artifact lineage is therefore distinct from current repository HEAD.

## 6. Source Integrity

Path, lineage, regular-file, symlink, size, readability, Git tracking, LFS-pointer, and SHA-256 checks passed before trusted loading. The model was loaded only from the verified local authoritative path using `joblib.load` in a one-shot metadata-only subprocess.

## 7. Trusted Bundle Inspection

The top level is `builtins.dict` with keys `model`, `calibrator`, `threshold`, `feature_cols`, and `version`. Required components are present and non-null.

| Component | Class | Module | `predict` | `predict_proba` |
| --- | --- | --- | --- | --- |
| Model | `Booster` | `lightgbm.basic` | yes | no |
| Calibrator | `IsotonicRegression` | `sklearn.isotonic` | yes | no |

No prediction or transformation method was invoked. The architecture indicates a future adapter must validate raw model `predict` followed by calibrator transformation to calibrated probability. That adapter is not implemented or authorized in this step.

Inspection used Python 3.10.12 with joblib 1.5.3, LightGBM 4.6.0, scikit-learn 1.7.2, and NumPy 1.26.4.

## 8. Threshold Validation

The bundle threshold and external `threshold` field are both finite numeric values of `0.1`, both fall strictly between 0 and 1, and differ by no more than `1e-12`. The threshold was neither recomputed nor optimized.

## 9. Feature Contract Validation

The bundle contains exactly 49 unique, non-blank ordered feature names. Its set and order exactly match `data/splits/feature_manifest.json`; its set matches the target canonical payload contract. The target schema does not declare physical CSV row order authoritative, although its first-seen canonical row order currently matches the model order.

No direct forbidden real-identity feature conflicts were found. `grade_encoded` and `credit_age_months` remain known limitation-aware features; their presence is not treated as clearance or failure.

The authoritative ordered feature names are:

`acc_open_past_24mths`, `bankruptcy_flag`, `bc_open_to_buy`, `bc_open_to_buy_missing_flag`, `bc_util`, `bc_util_missing_flag`, `credit_age_months`, `debt_to_income_revol`, `delinq_2yrs`, `delinq_flag`, `dti`, `fico_avg`, `grade_encoded`, `high_revol_util_flag`, `home_ownership_encoded`, `inq_last_6mths`, `inq_per_open_acc`, `installment`, `is_60_month`, `loan_amnt`, `loan_to_income`, `log_annual_inc`, `log_loan_amnt`, `log_revol_bal`, `log_tot_cur_bal`, `log_total_rev_hi_lim`, `mo_sin_old_rev_tl_op`, `mo_sin_old_rev_tl_op_missing_flag`, `mo_sin_rcnt_rev_tl_op`, `mo_sin_rcnt_rev_tl_op_missing_flag`, `mort_acc`, `mths_since_last_delinq`, `mths_since_last_delinq_missing_flag`, `num_actv_bc_tl`, `open_acc`, `payment_to_income`, `pct_tl_nvr_dlq`, `pub_rec`, `pub_rec_bankruptcies`, `pub_rec_flag`, `purpose`, `revol_bal`, `revol_util`, `term_months`, `tot_cur_bal`, `total_acc`, `total_rev_hi_lim`, `util_to_fico_ratio`, `verification_encoded`.

## 10. Target Copy Verification

The model was copied byte-for-byte to `artifacts/model/final_model_calibrated.pkl`, and the threshold was copied byte-for-byte to `artifacts/model/final_threshold.json`. Source and target sizes and SHA-256 hashes match for both artifacts. Both targets are regular files and not symlinks.

## 11. Runtime State After Intake

The model artifact is now present in the target repository and its integrity has been verified. Application model loading is still not activated. The application has not loaded the target artifact; `predict`, `predict_proba`, and inference have not been executed; no probability has been generated or shown; and no public deployment has occurred.

The verified model artifact is present and eligible for a later controlled runtime-adapter step, subject to independent activation and inference gates. Artifact presence alone does not make the app inference-ready.

## 12. Security and Governance Boundaries

No network access, install, retraining, recalibration, threshold optimization, reserialization, application execution, or public deployment occurred. Production approval, legal-compliance conclusion, fairness clearance, group-aware threshold activation, and current public deployment authorization remain false.

## 13. Step 3 Completion Criteria

Source lineage and integrity, trusted metadata-only inspection, threshold equivalence, 49-feature compatibility, identity-field exclusion, byte-preserving copy identity, evidence creation, and six-file repository scope must all pass. Completion authorizes human review only.

## 14. Authorization for the Next Step

Human audit and separate Git scope review are authorized. Runtime-adapter implementation, model-loading activation, prediction execution, inference execution, and public deployment remain unauthorized. Step 4 is not automatically authorized.
