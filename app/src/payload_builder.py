"""Contract-only payload builder skeleton for Stage 3.

This module is intentionally Streamlit-free and does not load models,
explainers, thresholds, parquet files, or prediction assets. Stage 3 payload
building is limited to contract/schema validation and JSON preview support.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


PAYLOAD_MODES = [
    "BASIC_FORM",
    "SAMPLE_PROFILE",
    "ADVANCED_EDITOR",
    "CANONICAL_PAYLOAD",
]

LIMITATION_FIELDS = ["credit_age_months", "grade_encoded"]
BASIC_FORM_GAP_COUNT = 45
EXPECTED_CANONICAL_FEATURE_COUNT = 49

MISSING_VALUE_MARKER = "<missing>"
MAPPING_GAP_MARKER = "<mapping_gap>"
CONTRACT_PLACEHOLDER_MARKER = "<contract_placeholder>"

FIELD_STATUS_PROVIDED = "PROVIDED"
FIELD_STATUS_DEFAULTED = "DEFAULTED"
FIELD_STATUS_DERIVED_PLACEHOLDER = "DERIVED_PLACEHOLDER"
FIELD_STATUS_MISSING_REQUIRED = "MISSING_REQUIRED"
FIELD_STATUS_MAPPING_GAP = "MAPPING_GAP"
FIELD_STATUS_LIMITATION_FIELD = "LIMITATION_FIELD"
FIELD_STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"

FIELD_STATUSES = [
    FIELD_STATUS_PROVIDED,
    FIELD_STATUS_DEFAULTED,
    FIELD_STATUS_DERIVED_PLACEHOLDER,
    FIELD_STATUS_MISSING_REQUIRED,
    FIELD_STATUS_MAPPING_GAP,
    FIELD_STATUS_LIMITATION_FIELD,
    FIELD_STATUS_NOT_APPLICABLE,
]

READINESS_READY_FOR_CONTRACT_PREVIEW = "READY_FOR_CONTRACT_PREVIEW"
READINESS_PARTIAL_READY_WITH_LIMITATIONS = "PARTIAL_READY_WITH_LIMITATIONS"
READINESS_BLOCKED_BY_SCHEMA_GAP = "BLOCKED_BY_SCHEMA_GAP"
READINESS_INVALID_INPUT = "INVALID_INPUT"

READINESS_STATUSES = [
    READINESS_READY_FOR_CONTRACT_PREVIEW,
    READINESS_PARTIAL_READY_WITH_LIMITATIONS,
    READINESS_BLOCKED_BY_SCHEMA_GAP,
    READINESS_INVALID_INPUT,
]

PAYLOAD_SOURCE_PRIORITY = [
    "editor_or_user_values",
    "sample_profile_values",
    "contract_placeholder_or_default",
    "missing_or_gap_marker",
]

GUARDRAIL_METADATA = {
    "contract_only": True,
    "inference_executed": False,
    "model_loaded": False,
    "threshold_used": False,
    "decision_generated": False,
    "shap_executed": False,
    "credit_score_generated": False,
}


@dataclass(frozen=True)
class PayloadBuildResult:
    """Stable Stage 3 payload build result consumed by UI renderers."""

    mode: str
    payload: dict[str, Any] = field(default_factory=dict)
    field_status: list[dict[str, Any]] = field(default_factory=list)
    coverage: dict[str, Any] = field(default_factory=dict)
    limitations: list[dict[str, Any]] = field(default_factory=list)
    validation: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    readiness_status: str = READINESS_BLOCKED_BY_SCHEMA_GAP
    readiness_note: str = "Payload builder logic has not been implemented yet."


def guardrail_metadata() -> dict[str, bool]:
    """Return a fresh copy of required no-inference guardrail metadata."""
    return dict(GUARDRAIL_METADATA)


def normalize_mode(mode: str | None) -> str:
    """Return a supported payload mode, defaulting to BASIC_FORM."""
    if mode in PAYLOAD_MODES:
        return str(mode)
    return "BASIC_FORM"


def safe_bool(value: Any) -> bool:
    """Normalize contract boolean-like values without importing pandas."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    try:
        return bool(value)
    except Exception:
        return False


def is_missing_value(value: Any) -> bool:
    """Return whether a value should be treated as absent for payload coverage."""
    if value is None:
        return True
    if isinstance(value, str):
        return value in {MISSING_VALUE_MARKER, MAPPING_GAP_MARKER, ""}
    try:
        return bool(value != value)
    except Exception:
        return False


def _row_value(row: Any, key: str, default: Any = None) -> Any:
    """Read a value from a dict-like or pandas Series-like row."""
    if row is None:
        return default
    if isinstance(row, dict):
        return row.get(key, default)
    if hasattr(row, "get"):
        try:
            return row.get(key, default)
        except Exception:
            return default
    return default


def _iter_records(frame: Any) -> list[dict[str, Any]]:
    """Return records from a pandas-like frame or list of dictionaries."""
    if frame is None:
        return []
    if isinstance(frame, list):
        return [row for row in frame if isinstance(row, dict)]
    if hasattr(frame, "to_dict"):
        try:
            records = frame.to_dict("records")
            return records if isinstance(records, list) else []
        except Exception:
            return []
    return []


def _available_frame(frame: Any) -> bool:
    """Return whether a contract table is available for metadata reads."""
    if frame is None:
        return False
    if hasattr(frame, "empty") and bool(getattr(frame, "empty")):
        return False
    if hasattr(frame, "columns") and "load_status" in list(getattr(frame, "columns")):
        return False
    return bool(_iter_records(frame))


def _filter_rows_for_mode(rows: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    """Filter contract rows by payload/schema mode when a mode column exists."""
    safe_mode = normalize_mode(mode)
    mode_columns = ["payload_mode", "schema_mode", "mode"]
    filtered = []
    mode_column_found = False
    for row in rows:
        for column in mode_columns:
            if column in row:
                mode_column_found = True
                if str(row.get(column)) == safe_mode:
                    filtered.append(row)
                break
    return filtered if mode_column_found else rows


def get_canonical_feature_key(row: Any) -> str | None:
    """Return the best canonical feature identifier from a contract row."""
    for column in ["canonical_feature", "canonical_feature_name", "feature_name"]:
        value = _row_value(row, column)
        if value is not None and not is_missing_value(value):
            return str(value)
    return None


def is_limitation_field(feature_name: str | None) -> bool:
    """Return whether a canonical feature is limitation-aware in Stage 3."""
    if not feature_name:
        return False
    return str(feature_name) in set(LIMITATION_FIELDS)


def get_unique_canonical_features(
    *,
    mode: str = "CANONICAL_PAYLOAD",
    contract_bundle: dict[str, Any] | None = None,
    payload_template_df: Any = None,
    canonical_schema_df: Any = None,
) -> list[str]:
    """Return unique canonical features for a mode, targeting 49 features.

    Payload contracts are preferred because schema contracts contain repeated
    mode rows. Schema rows are only a fallback and are still deduplicated.
    """
    safe_mode = normalize_mode(mode)
    if contract_bundle:
        payload_bundle = contract_bundle.get("payload", {})
        payload_template_df = payload_template_df or payload_bundle.get("template")
        canonical_schema_df = canonical_schema_df or contract_bundle.get("canonical_schema")

    source_rows: list[dict[str, Any]] = []
    if _available_frame(payload_template_df):
        source_rows = _filter_rows_for_mode(_iter_records(payload_template_df), safe_mode)
    elif _available_frame(canonical_schema_df):
        source_rows = _filter_rows_for_mode(_iter_records(canonical_schema_df), safe_mode)

    features: list[str] = []
    seen: set[str] = set()
    for row in source_rows:
        feature_name = get_canonical_feature_key(row)
        if not feature_name or feature_name in seen:
            continue
        seen.add(feature_name)
        features.append(feature_name)

    return features


def classify_field_status(
    *,
    value: Any = None,
    value_source: str | None = None,
    canonical_feature: str | None = None,
    is_required: bool = False,
    mapping_gap: bool = False,
    mapping_available: bool = True,
    payload_value_allowed: bool = True,
    limitation_aware: bool = False,
    defaulted: bool = False,
    placeholder: bool = False,
) -> str:
    """Classify one payload field status.

    This function classifies contract/schema payload state only. It does not
    evaluate credit risk, run inference, compare thresholds, or generate a
    decision.
    """
    if limitation_aware or is_limitation_field(canonical_feature):
        return FIELD_STATUS_LIMITATION_FIELD
    if safe_bool(mapping_gap) or not safe_bool(mapping_available):
        return FIELD_STATUS_MAPPING_GAP
    if value_source == "editor_or_user_values" and not is_missing_value(value):
        return FIELD_STATUS_PROVIDED
    if value_source == "sample_profile_values" and not is_missing_value(value):
        return FIELD_STATUS_PROVIDED
    if defaulted:
        return FIELD_STATUS_DEFAULTED
    if placeholder or value == CONTRACT_PLACEHOLDER_MARKER:
        return FIELD_STATUS_DERIVED_PLACEHOLDER
    if not safe_bool(payload_value_allowed):
        return FIELD_STATUS_NOT_APPLICABLE
    if is_missing_value(value):
        if is_required:
            return FIELD_STATUS_MISSING_REQUIRED
        return FIELD_STATUS_NOT_APPLICABLE
    if value_source in {"contract_placeholder_or_default", "default"}:
        return FIELD_STATUS_DEFAULTED
    return FIELD_STATUS_PROVIDED


def compute_payload_coverage(
    *,
    mode: str,
    payload: dict[str, Any] | None = None,
    field_status: list[dict[str, Any]] | None = None,
    contract_bundle: dict[str, Any] | None = None,
    payload_template_df: Any = None,
    canonical_schema_df: Any = None,
) -> dict[str, Any]:
    """Compute contract payload coverage metrics.

    The canonical target is the unique canonical feature count, not the number
    of schema rows. For the current Stage 0 contracts this should be 49.
    """
    safe_mode = normalize_mode(mode)
    payload = payload or {}
    field_status = field_status or []
    canonical_features = get_unique_canonical_features(
        mode=safe_mode,
        contract_bundle=contract_bundle,
        payload_template_df=payload_template_df,
        canonical_schema_df=canonical_schema_df,
    )
    target_count = len(canonical_features) or EXPECTED_CANONICAL_FEATURE_COUNT

    status_counts = {status: 0 for status in FIELD_STATUSES}
    for row in field_status:
        status = str(row.get("field_status", FIELD_STATUS_NOT_APPLICABLE))
        if status not in status_counts:
            status_counts[status] = 0
        status_counts[status] += 1

    provided_count = status_counts.get(FIELD_STATUS_PROVIDED, 0)
    defaulted_count = status_counts.get(FIELD_STATUS_DEFAULTED, 0)
    placeholder_count = status_counts.get(FIELD_STATUS_DERIVED_PLACEHOLDER, 0)
    missing_required_count = status_counts.get(FIELD_STATUS_MISSING_REQUIRED, 0)
    mapping_gap_count = status_counts.get(FIELD_STATUS_MAPPING_GAP, 0)
    limitation_field_count = status_counts.get(FIELD_STATUS_LIMITATION_FIELD, 0)
    not_applicable_count = status_counts.get(FIELD_STATUS_NOT_APPLICABLE, 0)

    if not field_status:
        provided_count = sum(1 for value in payload.values() if not is_missing_value(value))

    if safe_mode == "BASIC_FORM":
        mapping_gap_count = max(mapping_gap_count, BASIC_FORM_GAP_COUNT)

    available_count = provided_count + defaulted_count + placeholder_count + limitation_field_count
    coverage_ratio = round(available_count / target_count, 4) if target_count else 0.0

    return {
        "payload_mode": safe_mode,
        "canonical_feature_count": target_count,
        "expected_canonical_feature_count": EXPECTED_CANONICAL_FEATURE_COUNT,
        "uses_unique_canonical_features": True,
        "schema_row_count_is_payload_target": False,
        "payload_field_count": len(payload),
        "available_value_count": available_count,
        "provided_field_count": provided_count,
        "defaulted_field_count": defaulted_count,
        "placeholder_field_count": placeholder_count,
        "missing_required_count": missing_required_count,
        "mapping_gap_count": mapping_gap_count,
        "limitation_field_count": limitation_field_count,
        "not_applicable_count": not_applicable_count,
        "basic_form_gap_count": BASIC_FORM_GAP_COUNT if safe_mode == "BASIC_FORM" else 0,
        "coverage_ratio": coverage_ratio,
        **guardrail_metadata(),
    }


def _clean_payload_value(value: Any) -> Any:
    """Return a JSON-friendly payload value or None for missing contract values."""
    if is_missing_value(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return value
    return value


def _contract_tables(contract_bundle: dict[str, Any] | None) -> dict[str, Any]:
    """Extract Stage 3 contract tables from a loaded contract bundle."""
    contract_bundle = contract_bundle or {}
    payload_bundle = contract_bundle.get("payload", {})
    return {
        "canonical_schema": contract_bundle.get("canonical_schema"),
        "payload_template": payload_bundle.get("template"),
        "profile_payload_map": payload_bundle.get("profile_payload_map"),
        "limitation_disclosure": payload_bundle.get("limitation_disclosure"),
    }


def _mode_template_rows(
    *,
    mode: str,
    contract_bundle: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Return unique payload template rows for the selected mode."""
    tables = _contract_tables(contract_bundle)
    rows = _filter_rows_for_mode(_iter_records(tables.get("payload_template")), mode)
    if not rows:
        rows = _filter_rows_for_mode(_iter_records(tables.get("canonical_schema")), mode)

    unique_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        feature_name = get_canonical_feature_key(row)
        if not feature_name or feature_name in seen:
            continue
        seen.add(feature_name)
        unique_rows.append(row)
    return unique_rows


def _sample_profile_values(
    *,
    mode: str,
    contract_bundle: dict[str, Any] | None,
    selected_sample: str | None,
) -> tuple[dict[str, Any], str | None]:
    """Return sample-profile values keyed by canonical feature."""
    if normalize_mode(mode) != "SAMPLE_PROFILE":
        return {}, selected_sample

    tables = _contract_tables(contract_bundle)
    rows = _filter_rows_for_mode(_iter_records(tables.get("profile_payload_map")), mode)
    if not rows:
        return {}, selected_sample

    sample_id = selected_sample
    if not sample_id:
        first_profile = _row_value(rows[0], "profile_id")
        sample_id = str(first_profile) if not is_missing_value(first_profile) else None

    values: dict[str, Any] = {}
    for row in rows:
        if sample_id and str(_row_value(row, "profile_id")) != sample_id:
            continue
        feature_name = get_canonical_feature_key(row)
        value = _clean_payload_value(_row_value(row, "synthetic_value"))
        if feature_name and value is not None:
            values[feature_name] = value
    return values, sample_id


def _lookup_user_value(
    *,
    canonical_feature: str,
    payload_field_key: str,
    user_input: dict[str, Any],
) -> tuple[bool, Any]:
    """Return a user/editor value by canonical feature or payload field key."""
    for key in [canonical_feature, payload_field_key]:
        if key in user_input and not is_missing_value(user_input[key]):
            return True, _clean_payload_value(user_input[key])
    return False, None


def _contract_placeholder_value(row: dict[str, Any]) -> tuple[bool, Any, bool]:
    """Return contract default/placeholder availability for a template row."""
    for key in ["default_value", "synthetic_value"]:
        value = _clean_payload_value(_row_value(row, key))
        if value is not None:
            return True, value, False
    if safe_bool(_row_value(row, "placeholder_value_allowed", False)):
        return True, CONTRACT_PLACEHOLDER_MARKER, True
    return False, None, False


def build_payload_from_mode(
    *,
    mode: str,
    contract_bundle: dict[str, Any],
    user_input: dict[str, Any] | None = None,
    editor_values: dict[str, Any] | None = None,
    selected_sample: str | None = None,
) -> PayloadBuildResult:
    """Build a canonical payload from the selected contract mode.

    This assembles contract payload structure only. It does not compute model
    validation, credit risk validation, inference, thresholding, or decisions.
    """
    original_mode = mode
    safe_mode = normalize_mode(mode)
    mode_valid = original_mode == safe_mode
    combined_user_values = {
        **(user_input or {}),
        **(editor_values or {}),
    }

    template_rows = _mode_template_rows(mode=safe_mode, contract_bundle=contract_bundle)
    sample_values, resolved_selected_sample = _sample_profile_values(
        mode=safe_mode,
        contract_bundle=contract_bundle,
        selected_sample=selected_sample,
    )

    payload: dict[str, Any] = {}
    field_status_rows: list[dict[str, Any]] = []
    limitation_rows: list[dict[str, Any]] = []

    for row in template_rows:
        canonical_feature = get_canonical_feature_key(row)
        if not canonical_feature:
            continue

        payload_field_key = str(
            _row_value(row, "payload_field_key", canonical_feature)
            or canonical_feature
        )
        mapping_gap = safe_bool(_row_value(row, "mapping_gap", False))
        mapping_available = safe_bool(_row_value(row, "mapping_available", True))
        payload_value_allowed = safe_bool(_row_value(row, "payload_value_allowed", True))
        limitation_aware = (
            safe_bool(_row_value(row, "limitation_aware", False))
            or is_limitation_field(canonical_feature)
        )
        is_required = safe_bool(_row_value(row, "is_required", False))

        has_value, value = _lookup_user_value(
            canonical_feature=canonical_feature,
            payload_field_key=payload_field_key,
            user_input=combined_user_values,
        )
        value_source = "editor_or_user_values" if has_value else None
        placeholder = False
        defaulted = False

        if not has_value and canonical_feature in sample_values:
            has_value = True
            value = sample_values[canonical_feature]
            value_source = "sample_profile_values"

        if not has_value:
            has_contract_value, contract_value, placeholder = _contract_placeholder_value(row)
            if has_contract_value:
                has_value = True
                value = contract_value
                value_source = "contract_placeholder_or_default"
                defaulted = not placeholder

        if not has_value:
            value = MAPPING_GAP_MARKER if mapping_gap or not mapping_available else MISSING_VALUE_MARKER
            value_source = "missing_or_gap_marker"

        field_status = classify_field_status(
            value=value,
            value_source=value_source,
            canonical_feature=canonical_feature,
            is_required=is_required,
            mapping_gap=mapping_gap,
            mapping_available=mapping_available,
            payload_value_allowed=payload_value_allowed,
            limitation_aware=limitation_aware,
            defaulted=defaulted,
            placeholder=placeholder,
        )

        payload[canonical_feature] = value
        status_row = {
            "payload_mode": safe_mode,
            "canonical_feature": canonical_feature,
            "payload_field_key": payload_field_key,
            "field_status": field_status,
            "value_source": value_source,
            "mapping_available": mapping_available,
            "mapping_gap": mapping_gap,
            "payload_value_allowed": payload_value_allowed,
            "limitation_aware": limitation_aware,
            "disclosure_required": safe_bool(_row_value(row, "disclosure_required", False)),
            "disclosure_complete": safe_bool(_row_value(row, "disclosure_complete", False)),
        }
        field_status_rows.append(status_row)

        if limitation_aware:
            limitation_rows.append(
                {
                    "payload_mode": safe_mode,
                    "canonical_feature": canonical_feature,
                    "payload_field_key": payload_field_key,
                    "disclosure_required": status_row["disclosure_required"],
                    "disclosure_complete": status_row["disclosure_complete"],
                    "disclosure_text": _clean_payload_value(_row_value(row, "disclosure_text")),
                }
            )

    coverage = compute_payload_coverage(
        mode=safe_mode,
        payload=payload,
        field_status=field_status_rows,
        contract_bundle=contract_bundle,
    )

    metadata = {
        **guardrail_metadata(),
        "original_mode": original_mode,
        "normalized_mode": safe_mode,
        "mode_valid": mode_valid,
        "source_priority": list(PAYLOAD_SOURCE_PRIORITY),
        "selected_sample": resolved_selected_sample,
    }
    validation = generate_payload_validation_report(
        mode=safe_mode,
        original_mode=original_mode,
        mode_valid=mode_valid,
        payload=payload,
        field_status=field_status_rows,
        coverage=coverage,
        metadata=metadata,
        limitations=limitation_rows,
    )
    readiness_status, readiness_note = compute_payload_readiness(
        mode=safe_mode,
        mode_valid=mode_valid,
        coverage=coverage,
        validation=validation,
    )
    validation["readiness_status"] = readiness_status
    validation["readiness_note"] = readiness_note

    return PayloadBuildResult(
        mode=safe_mode,
        payload=payload,
        field_status=field_status_rows,
        coverage=coverage,
        limitations=limitation_rows,
        validation=validation,
        metadata=metadata,
        readiness_status=readiness_status,
        readiness_note=readiness_note,
    )


def compute_payload_readiness(
    *,
    mode: str,
    mode_valid: bool = True,
    coverage: dict[str, Any] | None = None,
    validation: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Compute conservative contract/schema payload readiness.

    Readiness here is only about contract payload structure. It is not credit
    risk validation, model validation, inference, thresholding, or decisioning.
    """
    safe_mode = normalize_mode(mode)
    coverage = coverage or {}
    validation = validation or {}

    canonical_feature_count = int(
        coverage.get("canonical_feature_count")
        or validation.get("canonical_feature_count")
        or 0
    )
    missing_required_count = int(coverage.get("missing_required_count") or 0)
    mapping_gap_count = int(coverage.get("mapping_gap_count") or 0)

    if not mode_valid:
        return (
            READINESS_INVALID_INPUT,
            "Invalid payload mode. The payload was normalized for inspection but is not valid.",
        )

    if canonical_feature_count != EXPECTED_CANONICAL_FEATURE_COUNT:
        return (
            READINESS_BLOCKED_BY_SCHEMA_GAP,
            "Canonical payload target does not match the expected 49 unique features.",
        )

    if safe_mode == "BASIC_FORM":
        return (
            READINESS_PARTIAL_READY_WITH_LIMITATIONS,
            "Basic Form remains partial with 45 documented mapping gaps and disclosed limitations.",
        )

    if missing_required_count > 0:
        if safe_mode == "ADVANCED_EDITOR":
            return (
                READINESS_INVALID_INPUT,
                "Advanced Editor has missing required contract fields.",
            )
        return (
            READINESS_PARTIAL_READY_WITH_LIMITATIONS,
            "Payload has missing required contract fields and is limited to review.",
        )

    if mapping_gap_count > 0:
        return (
            READINESS_PARTIAL_READY_WITH_LIMITATIONS,
            "Payload has mapping gaps and is limited to contract review.",
        )

    return (
        READINESS_READY_FOR_CONTRACT_PREVIEW,
        "Payload structure is ready for contract/schema preview only.",
    )


def generate_payload_validation_report(
    *,
    mode: str,
    original_mode: str | None = None,
    mode_valid: bool = True,
    payload: dict[str, Any] | None = None,
    field_status: list[dict[str, Any]] | None = None,
    coverage: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    limitations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Generate a contract/schema validation report for a payload build."""
    safe_mode = normalize_mode(mode)
    payload = payload or {}
    field_status = field_status or []
    coverage = coverage or {}
    metadata = {**guardrail_metadata(), **(metadata or {})}
    limitations = limitations or []

    canonical_feature_count = int(coverage.get("canonical_feature_count") or 0)
    payload_field_count = int(coverage.get("payload_field_count") or len(payload))
    mapping_gap_count = int(coverage.get("mapping_gap_count") or 0)
    missing_required_count = int(coverage.get("missing_required_count") or 0)
    limitation_field_count = int(coverage.get("limitation_field_count") or len(limitations))

    guardrail_ok = all(
        metadata.get(key) == expected
        for key, expected in guardrail_metadata().items()
    )

    status_counts = {status: 0 for status in FIELD_STATUSES}
    for row in field_status:
        status = str(row.get("field_status", FIELD_STATUS_NOT_APPLICABLE))
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "payload_mode": safe_mode,
        "original_mode": original_mode if original_mode is not None else safe_mode,
        "normalized_mode": safe_mode,
        "mode_valid": mode_valid,
        "canonical_feature_target": EXPECTED_CANONICAL_FEATURE_COUNT,
        "canonical_feature_count": canonical_feature_count,
        "payload_field_count": payload_field_count,
        "provided_field_count": int(coverage.get("provided_field_count") or 0),
        "available_value_count": int(coverage.get("available_value_count") or 0),
        "missing_required_count": missing_required_count,
        "mapping_gap_count": mapping_gap_count,
        "limitation_field_count": limitation_field_count,
        "basic_form_gap_count": (
            BASIC_FORM_GAP_COUNT if safe_mode == "BASIC_FORM" else int(coverage.get("basic_form_gap_count") or 0)
        ),
        "field_status_counts": status_counts,
        "payload_compatible": (
            mode_valid
            and canonical_feature_count == EXPECTED_CANONICAL_FEATURE_COUNT
            and missing_required_count == 0
            and mapping_gap_count == 0
        ),
        "contract_schema_validation_only": True,
        "credit_risk_validation_executed": False,
        "model_validation_executed": False,
        "inference_executed": False,
        "thresholding_executed": False,
        "decisioning_executed": False,
        "guardrail_metadata_ok": guardrail_ok,
        "schema_row_count_is_payload_target": False,
        **guardrail_metadata(),
    }


def _json_safe(value: Any) -> Any:
    """Convert common scalar/container values into JSON-safe structures."""
    if isinstance(value, PayloadBuildResult):
        return _json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if is_missing_value(value):
        return None
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except Exception:
            return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def payload_result_to_json(
    result: PayloadBuildResult,
    *,
    indent: int = 2,
) -> str:
    """Serialize a payload build result for preview/download.

    The serialized result contains only contract payload structure, validation
    metadata, and guardrail flags. It does not contain model or inference output.
    """
    payload = {
        "mode": result.mode,
        "readiness_status": result.readiness_status,
        "readiness_note": result.readiness_note,
        "payload": result.payload,
        "field_status": result.field_status,
        "coverage": result.coverage,
        "limitations": result.limitations,
        "validation": result.validation,
        "metadata": {
            **guardrail_metadata(),
            **result.metadata,
        },
    }
    return json.dumps(_json_safe(payload), indent=indent, sort_keys=True)
