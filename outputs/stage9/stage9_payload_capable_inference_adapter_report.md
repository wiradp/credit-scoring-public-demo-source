# Stage 9 Step 4.2A — Basic Form Payload-Capable Controlled Inference Adapter

## 1. Document Control

- Stage: 9
- Step: 4.2A
- Baseline commit: `ca056b4dcddfea315b3ee9d0a9980fb7a5212fe1`
- Branch: `phase8-public-demo-source`
- Validation status: **PASS**
- Generated at: `2026-07-19T13:10:57Z`

## 2. Scope and Non-Goals

This step closes only the Basic Form inference-adapter blocker. It creates a
contract-driven mapping runtime and a separately authorized Basic Form adapter.
It does not modify the UI, activate Advanced Editor, create lending decisions,
stage or commit files, push, or deploy.

## 3. Repository Preconditions

The repository was clean on `phase8-public-demo-source` at
`ca056b4dcddfea315b3ee9d0a9980fb7a5212fe1`. Its parent, subject, and 72-file
tracked inventory matched the required baseline. The current HEAD changed
exactly the six frozen Step 4.1B files relative to its parent.

## 4. Frozen Artifact Integrity

All required frozen sizes and SHA-256 hashes matched before implementation:
the existing controlled adapter and test, public inference contract, Step 4.1A
contract and vectors, Step 4.1B contract, vectors, and tests, model manifest,
model binary, threshold, and sample-profile matrix. The model was not
deserialized during this precondition audit.

## 5. Previous Step 5 Safe Failure

The previous Step 5 attempt correctly stopped because the frozen adapter
authorizes exact committed `SAMPLE_PROFILE` fixtures only. A Basic Form payload
has eleven authorized overwrites and must not masquerade as a committed sample
profile. Advanced Editor remains contract-preview-only pending Step 4.2B.

## 6. Adapter Architecture Decision

`app/src/basic_form_runtime.py` assembles the frozen 49-feature payload.
`app/src/basic_form_inference.py` exposes one atomic public function accepting
only source inputs and system metadata. Internal mapping evidence is rebuilt
and exactly compared before controlled inference delegates to the unchanged
Stage 4 runtime primitives.

## Independent Authorization-Boundary Finding

The independent mutation audit correctly found that frozen fields, immutable
mappings, exact type checks, and a recomputable fingerprint established only
self-consistency. They did not prove that a caller-supplied canonical payload
was derived from the frozen public inputs, selected committed profile, and
eleven-operation mapping.

## Why Frozen Dataclass Was Insufficient

`frozen=True` and `MappingProxyType` prevent ordinary assignment but do not
create a security authority boundary. A caller could previously replace or
manually construct a result, alter finite canonical values, recompute the
fingerprint, and retain plausible metadata. Authorization now depends on a
fresh authoritative rebuild, not possession of a result object.

## Atomic Public Inference API

The public API is
`run_basic_form_inference(source_inputs, system_metadata)`. It accepts only the
six Step 4.1A source fields and exact two-field system metadata. It does not
accept a mapping result, canonical payload, fingerprint, provenance,
limitation set, model path, or contract path.

## Mapping Result Non-Authority

`BasicFormMappingResult` is internal mapping evidence and is not a bearer
authorization token. Direct construction is sealed, `dataclasses.replace()`
cannot reproduce the private construction requirement, and the only helper
that accepts the type is private. A caller-supplied or self-consistently forged
payload and fingerprint cannot authorize inference.

## Retained Source Evidence

Each internally created result retains immutable, defensive, non-repr copies
of the six source inputs and two metadata fields. They are used only for the
authorization rebuild and are absent from result metadata, exceptions, smoke
evidence, and reports.

## Authoritative Rebuild Before Runtime

Immediately before model-runtime access, the private helper calls the frozen
mapping builder again with retained source and metadata evidence. It requires
exact equality for mode, both contract IDs, selected profile, acknowledgement,
feature order, payload key order and values, fingerprint, feature count,
provenance, limitation set, safe disclosure, and retained evidence. The
canonical payload is therefore rebuilt from the frozen input and mapping
contracts immediately before model-runtime access.

## Profile-to-Payload Binding

The rebuild reloads the selected allowlisted profile from the committed matrix
and reapplies the frozen registry. This structurally and cryptographically
binds the profile ID to all 38 baseline pass-through values, four direct
features, seven derived features, and the final fingerprint. Any mismatch fails
with `BASIC_FORM_AUTHORIZATION_BINDING_INVALID`.

## Self-Consistent Forgery Rejection

Matching forged fingerprints do not authorize payloads. Independent tests
changed out-of-range DTI, invalid loan amount, a derived ratio, a baseline
feature, multiple finite fields, and profile binding. Every case was rejected
before runtime access even though its forged payload and fingerprint agreed.

## Runtime Access Guard

Every authorization mutation patched the verified-runtime, ordered-frame, and
prediction primitives. All three observed aggregate call counts were zero.
The verified model runtime is not accessed for any failed authorization
mutation, and no forgery produced a probability.

## Expanded Mutation Tests

Tests also cover prohibited direct construction, prohibited
`dataclasses.replace()` forgery, removed legacy public mapping-result API,
public signature inspection, profile-ID mutation, contract and governance
metadata mutation, immutable retained evidence, and sanitized atomic input
failures.

## 7. Frozen Sample-Profile Adapter Preservation

The existing Stage 4 sample-profile adapter was not modified. Its
`AUTHORIZED_MODE` remains `SAMPLE_PROFILE`, exact committed-fixture equality
remains required, and all five committed profiles still infer successfully.
Forged, cross-profile, unknown, and missing-profile requests remain blocked.

## 8. Basic Form Runtime Mapping

The runtime strictly loads fixed repository-relative contracts and artifacts,
validates their committed integrity, enforces the exact six source fields and
two metadata fields, validates every selected baseline row, executes the frozen
closed operation registry, preserves 38 baseline values, and emits exactly 49
ordered features. All seven frozen request vectors matched impacted outputs,
float32 bit patterns, baseline preservation, and payload fingerprints.

## 9. Basic Form Authorization Envelope

`BasicFormMappingResult` has a sealed internal constructor. Its payload,
ordered names, source inputs, and system metadata are excluded from `repr`;
all retained mappings are read-only. Basic Form inference uses a separately
authorized adapter and does not masquerade as `SAMPLE_PROFILE`.

## 10. Pre-Inference Validation

Before runtime access, the adapter performs the existing structural checks and
then requires exact equality with a fresh authoritative rebuild. Raw mappings,
caller mapping results, and every tested in-memory mutation fail closed.

## 11. Reuse of Frozen Runtime Primitives

Model loading, model-frame construction, model prediction, calibration, and
threshold relation remain implemented only by the frozen Stage 4 adapter. The
new adapter calls its verified runtime, ordered-frame, prediction/calibration,
threshold-relation, metadata, result, and safe-block primitives through the
module alias. It contains no `joblib.load`, pickle loading, pandas frame
construction, or direct model/calibrator prediction.

## 12. Actual Calibrated Inference

All seven Basic Form vectors executed actual local calibrated inference. Every
probability was finite and within `[0, 1]`; no fallback or fabricated
probability exists. The returned mode is `BASIC_FORM`, feature count is 49,
credit decision is `None`, and the verified payload fingerprint is retained as
safe metadata without retaining the complete payload in evidence artifacts.

## 13. Determinism Results

Repeated mapping produced the same payload fingerprint for every vector.
Repeated controlled inference produced the same calibrated probability for
every vector. Seven distinct probabilities were observed; no monotonic risk
ordering was asserted.

## 14. Sample-Profile Regression Protection

The unchanged adapter continued to accept its five committed fixtures and to
reject forged fixture values, cross-profile payloads, unknown IDs, and missing
IDs before prediction authorization.

## 15. Advanced Editor Block

Advanced Editor remains blocked pending the executable Step 4.2B validation
contract. The explicit block returns
`ADVANCED_EDITOR_CONTRACT_NOT_FROZEN`, produces no probability, and does not
access the verified runtime or model prediction.

## 16. Privacy Boundary

No personal data was used. No complete payload is recorded in smoke results,
reports, exceptions, or result representation. No payload or raw-input logging,
network call, telemetry, persistence, or path override was added.

## 17. Governance Boundary

This remains a fictional portfolio demonstration. It creates no credit
decision, approval recommendation, rejection recommendation, credit score,
fairness clearance, legal-compliance conclusion, production authorization, or
public deployment authorization.

## 18. Revised Regression Results

The required four-suite `unittest` command passed 107 tests:

- Step 4: 27/27
- Step 4.1A: 19/19
- Step 4.1B: 32/32
- Step 4.2A: 29/29
- Failures: 0
- Errors: 0

Syntax compilation also passed for both new application modules and the new
test module, with bytecode redirected outside the repository.

## 19. Revised Smoke Results

Seven request vectors were executed successfully. All probabilities were
finite, bounded, and deterministic on repeat through the atomic public API.
No caller-supplied mapping result was used, and an authoritative rebuild was
completed for every vector. The smoke artifact records only
vector IDs, selected fictional profile IDs, fingerprints, safe counts,
limitation names, status, probabilities, threshold relations, and determinism.

## 20. Runtime State

- Basic Form mapping runtime implemented: true
- Basic Form payload inference authorized: true
- Actual Basic Form inference executed: true
- Sample-profile adapter modified: false
- Advanced Editor authorized: false
- Streamlit UI modified: false
- Public deployment performed: false

## 21. Known Limitations

The Basic Form completes 38 model values from a selected fictional synthetic
profile. `grade_encoded` and `credit_age_months` remain limitation-aware
historical compatibility features. Advanced Editor still has no executable
validation contract. This work does not establish fairness, legal compliance,
production readiness, or underwriting suitability.

## 22. Completion Criteria

All seven frozen mapping vectors matched, all seven actual inference smoke cases
passed, sample-profile protections remained intact, Advanced Editor remained
blocked, syntax and 107 regression tests passed, and only the eight authorized
new files are present.

## 23. Post-Revision Authorization State

Human artifact audit and Git scope review are authorized. Staging, commit,
Step 4.2B, a Step 5 rerun, production use, real underwriting use, and public
deployment remain unauthorized.
