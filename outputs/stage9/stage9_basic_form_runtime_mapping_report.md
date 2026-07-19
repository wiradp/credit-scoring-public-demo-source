# Stage 9 Step 4.1B — Second Revised Authoritative Basic Form Runtime Mapping Contract Report

## 1. Document Control

- Contract: `STAGE9_BASIC_FORM_RUNTIME_MAPPING_V1`
- Baseline commit: `6bbe87f99421cb837ae073cd19597763d8baed0c`
- Branch: `phase8-public-demo-source`
- Classification: `PORTFOLIO_DEMO_ONLY`
- Second-revision validation: `PASS`

## 2. Second Independent Mutation Audit Findings

This second targeted revision closes four remaining fail-closed gaps: unused registry entries, structurally unresolved operands/references, non-disjoint fingerprint classes, and row-level limitation-status drift. The seven findings closed by the first revision remain closed.

## 3. Revision Scope

Only the same six existing untracked Step 4.1B artifacts were revised. No seventh file was created. No tracked file, application source, committed contract, notebook, model, threshold, UI, runtime mapping implementation, staging area, commit, or deployment state changed.

## 4. Previous Revision Closures Preserved

Contract-driven request assembly, the 11-operation execution order, structured operation schemas, operation-parameter mutation behavior, all-48 baseline numeric validation, mapping-status validation, disclosure enforcement, derived-output validation, contract-driven fingerprint policy, direct numeric representation, fingerprint mutations, and exact 15-code failure coverage remain active.

The model order remains 49; the dependency partition remains 4 direct, 7 derived, and 38 baseline pass-through features; the authorized overwrite set remains 11; and the limitation-aware set remains two features. All seven valid request fingerprints remain unchanged.

## 5. Exact Operation Registry Closure

The operation registry is now a closed 12-operation set: exactly 11 ordered overwrite operations plus exactly one baseline pass-through operation. Extra unused operations fail closed.

The exact registry ID set equals `operation_execution_order ∪ {PRESERVE_BASELINE}`. IDs are unique, `PRESERVE_BASELINE` is the sole `BASELINE_PASSTHROUGH`, and missing, unexpected, unordered executable, second-baseline, or otherwise unused operations fail with `BASIC_FORM_MAPPING_CONTRACT_INVALID`.

## 6. Unused Operation Rejection

An in-memory `EXTRA_UNUSED_DTI` operation with a valid operation schema but absent from `operation_execution_order` is rejected during contract validation. This proves that an operation cannot be accepted merely because request assembly never reaches it. A second baseline pass-through operation and a missing ordered operation are also rejected.

## 7. Structural Operand Reference Closure

Every operation source, numerator, denominator, mapping, and allowlist reference is proven structurally resolvable before request assembly.

Validation walks operations in frozen order. It verifies each `source_fields` entry, ratio numerator, ratio denominator field, mapping reference, and allowed-values reference; verifies the target is an authorized model feature; and then exposes that target as a prior-operation target. Unknown source, numerator, denominator, mapping, and allowlist references all fail during `validate_mapping_contract` with `BASIC_FORM_MAPPING_CONTRACT_INVALID`, never as a deferred derived-value failure.

## 8. Available Context Construction

The deterministic initial context contains six public sources—`annual_inc`, `dti`, `home_ownership`, `loan_amnt`, `purpose`, and `term_months`—plus all 49 validated baseline canonical features. Profile ID and acknowledgement metadata are excluded as operands.

Every resolved reference is classified as one or more of `PUBLIC_SOURCE_FIELD`, `BASELINE_CANONICAL_FEATURE`, and `PRIOR_OPERATION_TARGET`. The contract explicitly classifies the six public fields plus baseline dependencies `installment` and `revol_bal`.

## 9. Fingerprint Representation Partition

The five fingerprint representation classes form an exact pairwise-disjoint partition of all 49 model features.

- Direct user numeric: 2 (`dti`, `loan_amnt`)
- Exact integer: 2 (`term_months`, `is_60_month`)
- Float32 derived: 6
- Category: 1 (`purpose`)
- Baseline numeric: exactly the 38 baseline pass-through features

The validator rejects duplicates within a class, class overlap, missing classification, non-model features, wrong counts, an incomplete union, or baseline-numeric drift.

## 10. Fingerprint Class Overlap Rejection

Adding `open_acc` to `direct_user_numeric` while it remains in `baseline_numeric` is rejected by `payload_fingerprint_from_contract` before record serialization. The overlap cannot be silently resolved by branch ordering. Removing `dti`, replacing it with an unexpected feature, and duplicating `purpose` are also rejected.

## 11. Row-Level Limitation Alignment

For every baseline profile, the row-level `READY_WITH_LIMITATION` feature set is exactly `{grade_encoded, credit_age_months}`.

Each of the five profiles has exactly 2 `READY_WITH_LIMITATION` rows and 47 `READY` rows. The row-level set, row-level alignment contract, and global limitation-status contract must agree exactly. Changing both required rows to `READY` and changing `open_acc` to `READY_WITH_LIMITATION` fails with `BASIC_FORM_BASELINE_NOT_READY`.

## 12. Failure Precedence

Mapping validation applies required-section, unsupported-type, registry-closure, schema, execution-order, reference, fingerprint-policy, then representation-partition precedence. Unsupported operation types retain `BASIC_FORM_OPERATION_TYPE_INVALID`; other structural failures use `BASIC_FORM_MAPPING_CONTRACT_INVALID`.

Baseline validation applies ID, allowed status, exact row-level limitation set, dependency, count, duplicate, feature set, purpose, numeric value, then payload compatibility precedence. Row-level mismatch uses `BASIC_FORM_BASELINE_NOT_READY`.

## 13. Revised Golden Vector Counts

- Request-level vectors: 7
- Operation-unit vectors: 17
- Invalid mapping vectors: 21
- Total vectors: 45

The four new invalid IDs are `INVALID_EXTRA_UNUSED_REGISTRY_OPERATION`, `INVALID_UNRESOLVED_OPERATION_REFERENCE`, `INVALID_FINGERPRINT_CLASS_OVERLAP`, and `INVALID_ROW_LEVEL_LIMITATION_STATUS_MISMATCH`. The mapping failure-code set remains exactly 15 with zero missing or unexpected codes.

## 14. Revised Unit-Test Results

The Step 4.1B standard-library suite now contains 32 tests, all passing. The required combined regression contains 27 Step 4 tests, 19 Step 4.1A tests, and 32 Step 4.1B tests: 78 passed, zero failures, zero errors.

Static validation proves that request-level golden vectors call only `assemble_from_mapping_contract`; `validate_mapping_state` and `evaluate_operation` remain isolated helpers and are not alternative request-assembly paths. The Step 4.1B suite imports no application, Streamlit, model-loader, scientific-computing, subprocess, or network module and makes no prediction call.

## 15. Post-Revision Runtime State

No application mapping or public-input UI was implemented. The executable mapping remains test-only contract validation. The Step 4.1B test did not deserialize a model, call model or calibrator prediction, generate probability, or deploy. Existing application and frozen evidence hashes remain unchanged.

## 16. Privacy, Governance, and Authorization

Vectors remain synthetic and never record a full payload, model matrix, probability, or personal data. This evidence is portfolio-demonstration governance, not lending policy, legal certification, fairness clearance, production approval, or real-underwriting authorization.

Human re-audit and Git scope review are authorized. Stage 9 Step 5 rerun, the next implementation step, staging, commit, runtime activation, public deployment, and production use remain unauthorized pending later independent gates.
