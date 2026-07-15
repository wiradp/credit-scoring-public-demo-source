"""Safe UI copy for the contract-driven Streamlit demo."""

APP_TITLE = "Responsible AI Credit Risk Contract Demo"
PROJECT_TITLE = "Credit Risk Scoring + Fairness Audit"
STAGE_LABEL = "Stage 4 — Safe Demo Inference"
STAGE_BADGE = "Safe Demo Inference"

OVERVIEW_INTRO = (
    "This app demonstrates a governance-aware credit risk workflow using "
    "contract artifacts. It previews demo input modes, schema compatibility, "
    "payload readiness, and governance limitations."
)

NO_INFERENCE_NOTICE = (
    "This demo does not perform lending decisioning, thresholding, or scoring. "
    "Stage 4 may run a guarded model behavior preview only after contract "
    "payload and model-input checks pass."
)

PORTFOLIO_ONLY_NOTICE = (
    "This project is a portfolio demonstration of a governance-aware machine "
    "learning workflow. It is not a production credit decisioning system."
)

BASIC_FORM_LIMITATION_NOTICE = (
    "Basic Form is a simplified demo input mode. It cannot construct all "
    "canonical model features and is suitable only for safe contract preview, "
    "not for scoring or decisioning."
)

PAYLOAD_PREVIEW_NOTICE = (
    "The payload shown here is a contract/schema preview only. It is not sent "
    "to a model and is not used for credit decisioning."
)

PAYLOAD_BUILDER_NOTICE = (
    "Stage 3 builds a contract-only canonical payload object for schema "
    "compatibility review. It does not perform credit risk validation, model "
    "validation, inference, thresholding, or decisioning."
)

SAFE_DEMO_INFERENCE_NOTICE = (
    "Stage 4 consumes the Stage 3 payload builder result and may produce a "
    "default-risk signal preview only when all payload, model-input, and "
    "guardrail checks pass."
)

SAFE_DEMO_INFERENCE_LIMITATION_NOTICE = (
    "Default-risk signal bands are descriptive demo bands for portfolio model "
    "behavior review. They are not decision thresholds."
)

GOVERNANCE_LIMITATION_NOTICE = (
    "Fairness audit findings are carried forward as limitations and governance "
    "review inputs, not as proof of fairness, legal compliance, or deployment "
    "authorization."
)

ALLOWED_TERMS = [
    "portfolio demo",
    "contract preview",
    "demo input mode",
    "schema compatibility",
    "payload readiness",
    "mapping coverage",
    "contract readiness",
    "governance limitation",
    "limitation disclosure",
    "contract artifact",
    "sample profile",
    "synthetic profile",
    "validation contract",
    "payload preview",
    "payload builder",
    "contract payload builder",
    "fairness-audit transparency",
    "responsible AI demo",
    "not for credit decisioning",
    "no unguarded model inference",
    "guarded model behavior preview",
    "guarded default-risk signal preview",
]

SAFE_ACTION_LABELS = [
    "Preview Contract Payload",
    "Validate Against Contract",
    "Show Canonical Mapping",
    "Reset Demo Input",
    "View Schema Compatibility",
    "Review Payload Readiness",
]

REQUIRED_DISCLOSURES = [
    "This Streamlit app is a portfolio demo and contract preview interface.",
    "This app does not make lending outcome recommendations.",
    "No legal, compliance, fairness, or deployment approval is claimed.",
    "Stage 3 builds contract payloads for schema compatibility review only.",
    "Stage 4 preview is guarded and does not apply thresholding or recommendation logic.",
    "Basic Form remains partial with 45 documented mapping gaps from the Stage 0 contract.",
    "Limitation-aware fields, including credit_age_months and grade_encoded, remain disclosed.",
    "Sample profiles are demo contract artifacts and are not real borrower recommendations.",
]

WHAT_THIS_APP_DEMONSTRATES = [
    "Contract-driven demo design",
    "Feature governance awareness",
    "Payload transparency",
    "Schema compatibility review",
    "Payload readiness review",
    "Contract payload building",
    "Default-risk signal preview",
    "Model behavior preview",
    "Inference guardrail transparency",
    "Limitation disclosure",
    "Responsible AI portfolio framing",
]

WHAT_THIS_APP_DOES_NOT_DO = [
    "Does not make lending outcome recommendations",
    "Does not apply threshold-based outcome rules",
    "Does not run unguarded model execution",
    "Does not produce scoring outputs for real use",
    "Does not prove fairness compliance",
    "Does not replace legal or compliance review",
    "Does not authorize deployment",
]

MODE_DESCRIPTIONS = {
    "BASIC_FORM": (
        "Simplified recruiter-friendly demo input mode. It is partial and keeps "
        "the 45 documented mapping gaps visible."
    ),
    "SAMPLE_PROFILE": (
        "Sample-profile mode uses contract artifacts for safe payload preview "
        "and guarded model behavior preview."
    ),
    "ADVANCED_EDITOR": (
        "Contract-aware technical editor for broader schema compatibility "
        "inspection. Stage 4 blocks preview if payload or model-input checks fail."
    ),
    "CANONICAL_PAYLOAD": (
        "Full canonical payload inspection mode for technical review. It is a "
        "contract and model-behavior preview, not a decisioning workflow."
    ),
}

MODE_DISPLAY_NAMES = {
    "BASIC_FORM": "Basic Form",
    "SAMPLE_PROFILE": "Sample Profile",
    "ADVANCED_EDITOR": "Advanced Editor",
    "CANONICAL_PAYLOAD": "Canonical Payload",
}

PAGE_HELP_TEXT = {
    "Overview": "Portfolio demo scope, current stage, and governance boundary.",
    "Contract Readiness": "Stage 0 contract export and read-back evidence.",
    "Demo Input Modes": "Mode-level schema compatibility and limitation review.",
    "Payload Builder & Preview": "Contract-only payload builder and schema compatibility preview.",
    "Safe Demo Inference": "Guarded default-risk signal preview and inference guardrail metadata.",
    "Governance & Limitations": "Non-production boundaries and limitation disclosures.",
}

FORBIDDEN_POSITIVE_CLAIMS = [
    "approve",
    "approved",
    "reject",
    "rejected",
    "decline",
    "declined",
    "eligible",
    "not eligible",
    "loan decision",
    "credit decision",
    "assess risk",
    "run model",
    "check approval",
    "application result",
    "assessment result",
    "threshold decision",
    "SHAP explanation",
    "adverse action",
    "production-ready",
    "fair model",
    "bias removed",
    "legally compliant",
    "ECOA compliant",
    "Fair Housing compliant",
    "deployment approved",
]

ALLOWED_NEGATIVE_CONTEXTS = [
    "not a credit decision system",
    "does not make lending, approval, eligibility, or credit decisions",
    "no legal, compliance, fairness, or deployment approval is claimed",
    "not a production credit decisioning system",
    "not a real lending system",
    "does not run unguarded inference",
    "does not run scoring",
    "does not run unguarded model inference",
    "does not use inference for lending decisions",
    "does not apply thresholding or recommendation logic",
    "does not make recommendations",
    "does not approve or reject loan applications",
    "does not produce credit decisions",
    "does not prove fairness compliance",
    "does not authorize deployment",
]

GLOBAL_DISCLAIMER = (
    "This Streamlit app is a portfolio demo and contract preview interface. "
    "It does not make lending, approval, eligibility, or credit decisions. "
    "No legal, compliance, fairness, or deployment approval is claimed. "
    "Any model execution is limited to a guarded default-risk signal preview."
)

STATUS_LABELS = {
    "READY_WITH_WARNINGS": "Available with limitations",
    "READY": "Available",
    "EXPORTED": "Loaded",
    "READBACK_OK": "Read-back passed",
    "BASIC_FORM_PARTIAL_READY_WITH_GAPS": "Partial with documented gaps",
    "NOT_READY": "Requires review",
}
