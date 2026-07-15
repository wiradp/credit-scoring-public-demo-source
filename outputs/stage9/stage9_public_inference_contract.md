# Stage 9 Step 2 — Public Inference Contract

## 1. Document Control

| Field | Value |
| --- | --- |
| Project | Credit Risk Scoring + Fairness Audit |
| Contract | Public Inference Contract |
| Schema version | 1.0.0 |
| Status | `FROZEN_PENDING_IMPLEMENTATION` |
| Deployment classification | `PORTFOLIO_DEMO_ONLY` |
| Target branch | `phase8-public-demo-source` |
| Baseline commit | `6b7aae3a16650c048c802b69e1d4959f3b0a3a64` |
| Generated at (UTC) | `2026-07-15T10:48:28Z` |

This contract is authoritative for future public-inference implementation. It freezes behavior; it does not activate inference or authorize deployment.

## 2. Purpose

The planned application is a Responsible AI Credit Risk Scoring Portfolio Demo for education, portfolio demonstration, technical review, responsible-AI demonstration, and recruiter or hiring-manager review. It is not a real lending or banking decision system.

## 3. Current Baseline

The baseline contains 42 tracked deployment-source files. The Stage 8 package provides a non-inference Streamlit interface and contract artifacts. A guarded model loader and inference code path exist in source, but no model artifact is packaged, model loading is not activated, `predict_proba` has not been executed, and no public deployment has occurred.

The Cell Group 7 contracts confirm 49 canonical features. Basic Form has 45 disclosed mapping gaps and cannot independently form a complete canonical payload.

## 4. Deployment Classification

| Control | Frozen value |
| --- | --- |
| `deployment_classification` | `PORTFOLIO_DEMO_ONLY` |
| `public_inference_demo` | `planned_but_not_yet_activated` |
| `production_approval` | `false` |
| `credit_decision_authorized` | `false` |
| `legal_compliance_conclusion` | `false` |
| `fairness_clearance` | `false` |
| `public_deployment_performed` | `false` |
| `model_artifact_present` | `false` |
| `model_loading_activated` | `false` |
| `predict_proba_executed` | `false` |

Permitted purposes are education, portfolio demonstration, technical review, responsible-AI demonstration, and hiring review. Prohibited purposes are real loan applications, approval or rejection, underwriting, eligibility decisions, financial advice, legal or regulatory certification, and production banking use.

## 5. Supported Input Modes

| Mode | Public status | Contract |
| --- | --- | --- |
| Sample Profile | `PUBLICLY_SUPPORTED`; `DEFAULT_PUBLIC_MODE` | Synthetic profiles only; complete canonical features; pattern-oriented names; no real person; no hardcoded result. |
| Basic Form | `PUBLICLY_SUPPORTED_WITH_TRANSPARENT_SYNTHETIC_COMPLETION` | User selections may be combined only with a selected synthetic baseline; completion and provenance must be visible. |
| Advanced Editor | `PUBLICLY_SUPPORTED_TECHNICAL_MODE` | All canonical features; type, range, category, and required-field validation; synthetic framing; reset-to-profile and payload preview. |
| Canonical Payload | `INTERNAL_OR_TECHNICAL_VALIDATION_ONLY` | Fixture, inspection, and contract testing only; not the default; no validation or provenance bypass. |

Sample-profile names describe feature-signal patterns, never guaranteed predictions. Approved patterns include “Lower-Risk-Signal Synthetic Profile,” “Moderate-Risk-Signal Synthetic Profile,” “Higher-Risk-Signal Synthetic Profile,” “Mixed-Signal Synthetic Profile,” and “Limitation Transparency Synthetic Profile.” Names such as “Approved Applicant,” “Rejected Applicant,” “Guaranteed Safe Borrower,” and “Bad Borrower” are forbidden examples.

Raw arbitrary JSON editing is not required for the first public release.

## 6. Allowed Inputs

Only non-identifying, model-relevant synthetic-scenario fields are allowed. These may include requested loan amount, loan term, scenario annual income or income range, debt-to-income ratio, scenario credit-score range, historical account counts, utilization, delinquency history, application type, home-ownership category, loan-purpose category, employment-length category, and other approved canonical features. Every field must be presented as demo-scenario data.

## 7. Forbidden Inputs

The demo must not request, accept, upload, store, or log: full name; national ID or NIK; passport or driver-license number; full residential address; exact geolocation; phone number; email address; bank-account or credit-card number; login credentials, password, or PIN; biometric identifier or face image; identity document; complete date of birth; tax identifier; employer name tied to a real identity; real customer or loan-account ID; real credit report; financial statement or bank statement; or identity-document upload.

CSV uploads of real applicants, all document uploads, identity-bearing free text, account creation, real-applicant history storage, and user-provided model uploads are prohibited. No sensitive or real-identity field may be required.

## 8. Synthetic Completion and Input Provenance

Basic Form cannot independently populate all 49 canonical features. Missing canonical values may be completed only from a selected synthetic baseline profile. The baseline, completion, and resulting hybrid-synthetic nature must be disclosed before inference. Silent completion is prohibited.

Canonical model-feature origin, limitation status, and non-model system metadata are separate dimensions:

| Dimension | Allowed values | Cardinality and scope |
| --- | --- | --- |
| `value_source` | `USER_SUPPLIED`, `SYNTHETIC_BASELINE`, `DERIVED` | Exactly one per canonical model feature. |
| `limitation_status` | `STANDARD`, `LIMITATION_AWARE` | Exactly one per canonical model feature, independent of `value_source`. |
| System metadata | `SYSTEM_METADATA` | Non-model payload metadata only; never counted among the 49 canonical model features. |

For example, a user-entered limitation-aware field is validly represented as `value_source = USER_SUPPLIED` and `limitation_status = LIMITATION_AWARE`.

System metadata may include `input_mode`, `synthetic_baseline_profile_id`, `contract_version`, `model_artifact_identifier`, or `runtime_timestamp`. These are examples, not mandatory implementation fields in this step.

Payload preview must expose field-level `value_source` and `limitation_status`. It must separately disclose counts of `USER_SUPPLIED`, `SYNTHETIC_BASELINE`, `DERIVED`, and `LIMITATION_AWARE` canonical features. `SYSTEM_METADATA` must not enter those value-source counts or the 49-feature model matrix. A hybrid result is not an assessment of the user’s real creditworthiness.

## 9. Canonical Payload Requirements

Future inference requires a complete payload of exactly 49 canonical features; exact ordered names matching the verified model bundle; valid numeric and categorical values; no unexpected model-matrix fields; no missing required value after permitted transformation; no NaN or infinity at the runtime boundary; exactly one `value_source` and one independent `limitation_status` per canonical feature; counts of features by value source and a count of `LIMITATION_AWARE` features; system metadata outside the model matrix; and an input-mode identifier.

The 49-feature requirement is supported by the Stage 8 Cell Group 7 readiness and payload-mode contracts. Payload validation must fail closed on any disagreement with the model bundle.

## 10. Model Artifact Boundary

The only permitted model source is a trusted development-repository artifact verified in a later gate. Intake must record source repository, source-relative path, source commit, file size, SHA-256, bundle structure, model class, calibrator class, threshold, ordered feature list, feature count, and copy timestamp. Source and target SHA-256 must be identical.

The app must never download arbitrary models at runtime, accept uploaded pickle files, load a user-supplied model, use an unverified path, silently substitute another model, retrain or recalibrate, or recompute the operating threshold. This step neither copies nor loads a model.

## 11. Runtime Activation Gates

All gates must pass before inference is activated:

1. `MODEL_ARTIFACT_PRESENT`
2. `MODEL_ARTIFACT_HASH_VERIFIED`
3. `MODEL_BUNDLE_STRUCTURE_VALID`
4. `MODEL_INTERFACE_VALID`
5. `CALIBRATOR_INTERFACE_VALID`
6. `THRESHOLD_VALID`
7. `FEATURE_COUNT_VALID`
8. `FEATURE_ORDER_VALID`
9. `CANONICAL_PAYLOAD_COMPLETE`
10. `CANONICAL_VALUES_VALID`
11. `SYNTHETIC_COMPLETION_DISCLOSED`
12. `RUNTIME_SMOKE_PREDICTION_PASS`
13. `NO_FABRICATED_FALLBACK`

Inference is fail-closed. A failed gate produces no probability and no decision-like output. Documentation pages may remain available.

## 12. Output Semantics

The primary future output is a calibrated estimated default-risk probability. It must be finite, between 0.0 and 1.0 inclusive, produced by verified executable model inference, and never fabricated.

Optional accompanying information includes the verified model operating-threshold reference, relation to threshold, input mode, value-source and limitation-status counts, model version or artifact identifier, runtime limitations, and disclaimer. Approved relations are “Below the model operating threshold” and “At or above the model operating threshold.” Optional bands may use lower, moderate, or higher model-estimated default-risk signal language; bands never replace the probability.

## 13. Prohibited Output and Claim Language

The UI and model output must not issue or imply: `APPROVE`, `APPROVED`, `REJECT`, `REJECTED`, `DECLINE`, `DECLINED`, `ACCEPT`, `ACCEPTED`, `ELIGIBLE`, `NOT ELIGIBLE`, `LOAN APPROVAL`, `LOAN REJECTION`, `CREDIT APPROVAL`, `CREDIT DECISION`, `FINAL DECISION`, `GUARANTEED APPROVAL`, `SAFE BORROWER`, `BAD BORROWER`, `CREDITWORTHY`, or `NOT CREDITWORTHY`. These terms appear here only as prohibited examples.

The project must not claim that the model is fair or unbiased, removed bias, is legally compliant, satisfies ECOA or Fair Housing requirements, is approved for production, is bank-grade production ready, replaces underwriting review, or makes lending decisions. Documented audit work may be described only with its limitations and cannot become a compliance conclusion.

## 14. No-Fabricated-Prediction Policy

The app must never return a hardcoded or random probability, present a static lookup as inference, reuse an example result for a new payload, substitute a handcrafted score, show an illustrative number without clearly marking it non-inference, or return a default decision after runtime failure.

When executable inference is unavailable: `inference_status = unavailable`, `probability = null`, and `threshold_relation = null`.

## 15. Failure and Fallback Behavior

No model fallback is permitted. On initialization or gate failure, the public message must be equivalent to: “The model runtime could not be initialized. Inference is currently unavailable, but project documentation remains accessible.” Public output must not expose stack traces, local filesystem paths, or secrets.

## 16. Privacy and Logging

| Policy | Value |
| --- | --- |
| Raw input logging | `false` |
| Canonical payload logging | `false` |
| Personal-data storage | `false` |
| User-profile storage | `false` |
| File upload | `false` |
| Database required | `false` |
| External model API | `false` |
| Remote inference API | `false` |
| Account registration | `false` |

Permitted technical logs are runtime initialization status, prediction success or failure, latency, input mode, exception class, and model artifact identifier. Logs must exclude entered values, complete payloads, sensitive information, and session-identifying personal data. Transient session state may support rendering but is not persistent user storage.

## 17. Explanation-Layer Policy

Explanation is not required for the first inference release. Any later explanation must come from the verified model, must not be fabricated or described as causal, must distinguish raw model contribution from calibrated probability, must not be an adverse-action notice or legally compliant reason code, must avoid decision language, and must disclose known limitations.

Priority: (1) correct calibrated probability, (2) transparent input composition, (3) governance and limitation disclosure, and (4) optional validated explanation.

## 18. Public Disclosure Requirements

A prominent disclosure near the output must preserve this meaning: “This output is generated by a historical Lending Club portfolio model for educational demonstration. It is not a credit decision, lending recommendation, eligibility determination, or financial advice.”

Basic Form hybrid scenarios must also disclose near the output: “This is a hybrid synthetic scenario. The model result combines the values you selected with disclosed synthetic baseline values. It is not an assessment of your real creditworthiness.” These meanings may be refined but not weakened or hidden only in a footer or documentation page.

## 19. Fairness and Governance Limitations

Phase 4 completed governance documentation; it did not authorize production use. The frozen limitations are:

- annual-income-group four-fifths ratio remained below 0.80 after mitigation;
- home-ownership demographic-parity difference remained slightly above its governance threshold after mitigation;
- home-ownership four-fifths ratio remained below 0.80;
- recall decreased after mitigation;
- net predicted default-risk proxy increased;
- group-aware thresholding or second-look logic remains a governance-review candidate;
- no mitigation policy is authorized for public decision use;
- fairness diagnostics do not prove universal fairness; and
- any future deployment, once separately authorized by later independent gates, is limited to portfolio-demonstration use; current public deployment remains unauthorized.

No group-specific threshold is activated by this contract.

## 20. Explicit Non-Goals

This step does not add or inspect a model artifact, activate model loading, execute inference, execute `predict_proba`, change application behavior, add dependencies, retrain or recalibrate, activate a threshold policy, add explanations, collect identity data, create a lending decision, start a service, deploy publicly, stage files, or create a commit.

## 21. Step 2 Completion Criteria

Completion requires mutually consistent Markdown and JSON contracts, valid JSON, the exact frozen classification/modes/gates/privacy/governance rules, a two-artifact hash manifest, and repository changes limited to the three authorized untracked files. Completion freezes requirements only.

## 22. Authorization for the Next Step

Human audit and a separate Git scope review are authorized next. Model intake, runtime activation, inference execution, threshold activation, and public deployment remain unauthorized and require later independent gates.
