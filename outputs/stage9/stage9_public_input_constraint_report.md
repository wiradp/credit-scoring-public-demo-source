# Stage 9 Step 4.1A — Authoritative Public Input Constraint Contract Report

## Independent Human Audit Findings

The targeted revision closes six findings: integral-float term acceptance, permissive extra system metadata, unreachable privacy-specific failure codes, incomplete exact failure-code coverage, insufficiently reproducible numeric evidence, and ambiguous DTI display scale.

## Revision Scope

Only the existing six untracked Step 4.1A files were revised. No tracked file, application source, feature mapping, Streamlit UI, model, threshold, or deployment state was changed.

## Strict Term Runtime-Type Policy

`term_months` now requires `EXACT_INTEGER_NOT_BOOLEAN`. Exact integers `36` and `60` are valid. Integral floats, numeric strings, booleans, and display-label strings fail with `PUBLIC_INPUT_TERM_INVALID`. Human-readable labels remain display-only and a future UI must construct an exact integer request before the runtime boundary.

## Exact System-Metadata Boundary

The exact metadata keys are `synthetic_baseline_profile_id` and `synthetic_completion_acknowledged`. Any other metadata key fails with `PUBLIC_INPUT_FIELD_SET_INVALID`; a missing baseline retains `PUBLIC_INPUT_BASELINE_INVALID`, while missing or false acknowledgement retains `SYNTHETIC_COMPLETION_NOT_ACKNOWLEDGED`.

## Identity and Free-Text Failure-Code Precedence

The validator checks explicit reserved identity field names first, explicit reserved free-text field names second, then other source and metadata extras. Thus `full_name` reaches `PUBLIC_INPUT_IDENTITY_FIELD_PROHIBITED`, and `personal_narrative` reaches `PUBLIC_INPUT_FREE_TEXT_PROHIBITED`. Only keys are inspected; no value heuristic or personal-data classifier is introduced.

## Exact Failure-Code Coverage

The set of failure codes exercised by invalid golden vectors is exactly equal to the 11-code frozen contract set.

## 1. Document Control

- Contract: `STAGE9_PUBLIC_INPUT_CONSTRAINT_V1`
- Baseline: `e23f00aeb34243571ed6bfe998f5ce845ae2ed12`
- Branch: `phase8-public-demo-source`
- Classification: `PORTFOLIO_DEMO_ONLY`
- Validation: `PASS`

## 2. Scope and Non-Goals

This step freezes input constraints only. No application source was modified. No UI or feature mapping was implemented. The new test does not load a model or execute inference. No probability was generated and no public deployment occurred.

## 3. Repository Preconditions

The target began clean at the required branch, HEAD, subject, parent, and 60 tracked files. The development evidence repository was clean at `b2b4db65b2026493a336a4b9d17dc228327db380`. All required frozen artifacts matched their expected sizes and SHA-256 hashes.

## 4. Previous Step 4.1 Safe-Failure Blocker

The earlier public contracts identified the six Basic Form source fields but did not freeze executable numeric ranges or explicit public allowlists. This governance freeze resolves that prerequisite without activating runtime input handling.

## 5. Authoritative Evidence Precedence

Existing public governance controls privacy and deployment scope; committed Cell Group 7 contracts establish field identity; model metadata establishes categorical compatibility; committed development cleaning and numeric summaries establish historical numeric support; this Step 4.1A prompt authorizes conservative public-demo decisions.

## 6. Existing Public Contract Limitations

Permissive legacy widget declarations and unknown-category handling were treated as known limitations, not executable policy. The new freeze does not claim those constraints previously existed.

## 7. Basic Form Source-Field Set

The exact source fields are `annual_inc`, `dti`, `home_ownership`, `loan_amnt`, `purpose`, and `term_months`. There are no duplicates, missing fields, or unexpected fields. Annual income and home ownership are transformation sources; the other four are direct model sources.

## 8. Public Constraint Governance Method

Constraints are classified as existing governance, historical support, model compatibility, conservative public-demo policy, or system-metadata policy. Validation fails closed for missing, extra, malformed, non-finite, out-of-range, and unknown values.

## 9. Numeric Historical-Support Evidence

| Field | Historical min | p01 | p99 | Historical max | Train cap lower | Train cap upper | Selected public range | Rule |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `annual_inc` | 0 | 18000 | 265152.359375 | 10999200 | 18500 | 260690.31999999564 | [18500, 260690.31999999564] | `TRAIN_FITTED_CAP_BOUND` |
| `dti` | -1 | 1.8300000429153442 | 39.369998931884766 | 999 | 2.1500000953674316 | 38.720001220703125 | [2.1500000953674316, 38.720001220703125] | `TRAIN_FITTED_CAP_BOUND` |
| `loan_amnt` | 1000 | 1500 | 36000 | 40000 | 1609.7500000000082 | 35000 | [1609.7500000000082, 35000] | `TRAIN_FITTED_CAP_BOUND` |

The bounds come from `artifacts/cleaning_artifacts.pkl`, inspected by pickle opcode analysis without deserialization, and are corroborated by `reports/numeric_describe.csv`.

## Numeric Evidence Reproduction

This revision performed a one-time read-only inspection of development evidence. The public contract now embeds a self-contained snapshot that the committed test validates without reopening the development repository.

## Cleaning Artifact Pickletools Extraction

The 1,048-byte protocol-4 pickle was read only through `pickletools.genops`. Within the `cap_bounds` dictionary opcode span, each field key (or its memo reference) is followed by two `BINFLOAT` values and `TUPLE2`. The frozen associations are:

| Field | Field opcode index/position | Lower opcode index/position | Upper opcode index/position | Extracted caps |
|---|---|---|---|---|
| `annual_inc` | 109 / 690 (`BINGET` memo 7) | 110 / 692 | 111 / 701 | 18500.0, 260690.31999999564 |
| `loan_amnt` | 114 / 712 | 116 / 724 | 117 / 733 | 1609.7500000000082, 35000.0 |
| `dti` | 148 / 891 (`BINGET` memo 8) | 149 / 893 | 150 / 902 | 2.1500000953674316, 38.720001220703125 |

The pickle was not deserialized.

## Numeric Summary Row Evidence

The exact raw CSV strings for field, minimum, p01, p99, and maximum are serialized as `field=...|min=...|p01=...|p99=...|max=...`. Their SHA-256 hashes are `83dc01b...fa03` for annual income, `32d12fb...bb98` for DTI, and `f3e2c37...bdf8` for loan amount. Full canonical rows and hashes are frozen in the JSON contract and report without loss of numeric precision.

## Cross-Source Numeric Reconciliation

For all three fields, the selected public range exactly equals the extracted train-fitted cap range, both values are finite and ordered, and the selected range lies within the numeric-summary historical minimum and maximum. All three reconciliations are `PASS`.

## 10. Annual-Income Constraint

Annual income uses a required `NUMBER_INPUT`, strict full-string numeric parsing, float64 boundary normalization, finite values, and inclusive train-cap bounds. Zero is excluded.

## 11. DTI Constraint

DTI uses the same numeric policy and inclusive train-cap bounds. The stricter positive fitted lower cap supersedes the general nonnegative minimum.

## DTI Percentage-Point Scale Semantics

DTI is a percentage-point value. The future UI label must be `Debt-to-income ratio (%)`; `18.27` means `18.27%`, not `0.1827`. Dividing or multiplying by 100 is prohibited, and Step 5 must not display or convert DTI as a fractional 0–1 ratio.

## 12. Loan-Amount Constraint

Loan amount uses the same numeric policy and inclusive train-cap bounds. Zero is excluded.

## 13. Term-Month Allowlist

The canonical integer allowlist is exactly `[36, 60]`. Display labels may say “36 months” and “60 months,” but those strings are not accepted canonical values.

## 14. Home-Ownership Historical and Public Categories

Historical categories are `OWN`, `MORTGAGE`, `RENT`, `OTHER`, `NONE`, and `ANY`. The public exact-case allowlist is `MORTGAGE`, `OWN`, `RENT`, and `OTHER`; legacy `NONE` and `ANY` fail closed. The historical encoding is not a fairness clearance or normative ranking.

## 15. Purpose Model Compatibility and Public Allowlist

The public exact-case allowlist contains all 14 model-compatible values: `car`, `credit_card`, `debt_consolidation`, `educational`, `home_improvement`, `house`, `major_purchase`, `medical`, `moving`, `other`, `renewable_energy`, `small_business`, `vacation`, and `wedding`. Free text and integer category codes are prohibited.

## 16. Synthetic-Baseline ID Constraint

The five committed profile IDs are exact allowed values. The selected ID is required system metadata, accepts no caller-provided baseline payload, and is excluded from the model matrix and provenance count.

## 17. Synthetic-Completion Acknowledgement

The acknowledgement is required boolean system metadata. Its default is false; missing or false fails closed with `SYNTHETIC_COMPLETION_NOT_ACKNOWLEDGED`.

## 18. Widget-Type Freeze

The freeze contains three `NUMBER_INPUT` fields, three source `SELECTBOX` fields, one baseline `SELECTBOX`, and one acknowledgement `CHECKBOX`. It contains no text, upload, identity-bearing, or arbitrary-JSON widget.

## 19. Privacy and Identity Boundary

Use fictional or hypothetical scenario values only. Do not enter real identity information. The result must not be used for a real lending decision. Real-person data, personal narratives, persistence, and external transmission are prohibited.

## 20. Fail-Closed Validation Policy

Expected sanitized codes are frozen for field-set, missing-value, type, finite, range, category, term, baseline, acknowledgement, identity, and free-text failures. Application implementation remains out of scope.

## 21. Revised Golden-Vector Results

All 59 synthetic vectors passed contract evaluation: 29 valid cases were accepted and 30 invalid cases were rejected with their expected codes. Five new vectors cover integral-float term, numeric-string term, extra system metadata, identity field, and free-text field rejection. The invalid-vector failure-code set exactly equals all 11 frozen codes. No vector records a payload, model matrix, or probability.

## 22. Revised Unit-Test Results

The 19 revised Step 4.1A tests passed independently. The combined mandated run passed all 46 tests: 27 existing Step 4 tests and 19 revised tests, with zero failures and zero errors. The revised test uses standard-library modules only and neither imports application runtime modules nor loads or executes the model.

## 23. Post-Revision Runtime State

No application source was modified. No feature mapping was implemented. No Streamlit UI was implemented. No model was loaded by the Step 4.1A test. No model inference was executed by the Step 4.1A test. No probability was generated. No public deployment occurred.

## 24. Limitations

These conservative portfolio-demo governance controls are not lending policy, legal certification, fairness clearance, or a recommendation for real underwriting. Transformation formulas and application wiring remain explicitly unfrozen.

## 25. Step 4.1A Completion Criteria

The exact field set, numeric ranges, categorical and discrete allowlists, two metadata controls, privacy boundary, failure codes, golden vectors, strict JSON validation, and repository scope checks pass.

## 26. Authorization for Step 4.1B

Human artifact audit and Git scope review are authorized. Step 4.1B, Step 5, public runtime activation, and public deployment remain unauthorized until human audit, scope review, staging audit, commit, and post-commit audit are complete.
