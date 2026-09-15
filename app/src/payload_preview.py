"""Contract-only payload preview helpers for the Streamlit demo UI."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .demo_inference import (
    DEMO_INFERENCE_READY,
    DemoInferenceResult,
    RISK_SIGNAL_BAND_NOTE,
    RISK_SIGNAL_LABEL,
    format_risk_signal,
)
from .mode_view import LIMITATION_FIELDS, normalize_mode
from .payload_builder import PayloadBuildResult, payload_result_to_json
from .ui_text import PAYLOAD_PREVIEW_NOTICE, PUBLIC_DEMO_RESULT_DISCLOSURE


PREVIEW_VALUE_NOT_AVAILABLE = "<not_available>"
PREVIEW_VALUE_CONTRACT_ONLY = "<contract_only>"


def _get_streamlit():
    try:
        import streamlit as st
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Streamlit is required to render payload-preview components. "
            "Importing app.src.payload_preview does not require Streamlit."
        ) from exc
    return st


def _is_available_frame(frame: pd.DataFrame | None) -> bool:
    return isinstance(frame, pd.DataFrame) and not frame.empty and "load_status" not in frame.columns


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


def _clean_preview_value(value: Any) -> Any:
    if pd.isna(value):
        return PREVIEW_VALUE_NOT_AVAILABLE
    if hasattr(value, "item"):
        return value.item()
    return value


def _rows_for_mode(frame: pd.DataFrame, mode: str) -> pd.DataFrame:
    safe_mode = normalize_mode(mode)
    for column_name in ["payload_mode", "schema_mode", "mode"]:
        if column_name in frame.columns:
            return frame[frame[column_name].astype(str) == safe_mode].copy()
    return frame.copy()


def _feature_column(frame: pd.DataFrame) -> str | None:
    for column_name in ["canonical_feature", "canonical_feature_name", "feature_name"]:
        if column_name in frame.columns:
            return column_name
    return None


def _payload_key(row: pd.Series, feature_column: str) -> str:
    if "payload_field_key" in row and not pd.isna(row["payload_field_key"]):
        return str(row["payload_field_key"])
    return str(row[feature_column])


def not_available_payload(mode: str, message: str) -> dict[str, Any]:
    """Return a structured not-available payload preview."""
    safe_mode = normalize_mode(mode)
    return {
        "payload_mode": safe_mode,
        "preview_status": "not_available",
        "message": message,
        "payload": {},
        "metadata": {
            "contract_only": True,
            "inference_executed": False,
            "transformation_executed": False,
            "uses_threshold": False,
        },
    }


def build_preview_payload(
    mode: str,
    payload_template_df: pd.DataFrame | None = None,
    profile_payload_map_df: pd.DataFrame | None = None,
    selected_sample: str | None = None,
    user_input: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a structural JSON preview from contract artifacts only."""
    safe_mode = normalize_mode(mode)
    if not _is_available_frame(payload_template_df):
        return not_available_payload(safe_mode, "Payload template contract table is not available.")

    template_rows = _rows_for_mode(payload_template_df, safe_mode)
    feature_column = _feature_column(template_rows)
    if template_rows.empty or feature_column is None:
        return not_available_payload(
            safe_mode,
            "No payload template rows are available for the selected mode.",
        )

    sample_values: dict[str, Any] = {}
    if (
        safe_mode == "SAMPLE_PROFILE"
        and selected_sample
        and _is_available_frame(profile_payload_map_df)
        and "profile_id" in profile_payload_map_df.columns
    ):
        profile_rows = _rows_for_mode(profile_payload_map_df, safe_mode)
        profile_rows = profile_rows[profile_rows["profile_id"].astype(str) == selected_sample]
        profile_feature_column = _feature_column(profile_rows)
        if profile_feature_column and "synthetic_value" in profile_rows.columns:
            sample_values = {
                str(row[profile_feature_column]): _clean_preview_value(row["synthetic_value"])
                for _, row in profile_rows.iterrows()
            }

    user_input = user_input or {}
    payload: dict[str, Any] = {}
    field_metadata: list[dict[str, Any]] = []

    for _, row in template_rows.iterrows():
        feature_name = str(row[feature_column])
        field_key = _payload_key(row, feature_column)
        value_allowed = _safe_bool(row.get("payload_value_allowed", False))

        if field_key in user_input:
            value = _clean_preview_value(user_input[field_key])
            value_source = "demo_input"
        elif feature_name in user_input:
            value = _clean_preview_value(user_input[feature_name])
            value_source = "demo_input"
        elif feature_name in sample_values:
            value = sample_values[feature_name]
            value_source = "sample_profile_contract"
        elif value_allowed:
            value = PREVIEW_VALUE_CONTRACT_ONLY
            value_source = str(row.get("payload_value_source", "contract_template"))
        else:
            value = PREVIEW_VALUE_NOT_AVAILABLE
            value_source = str(row.get("payload_value_source", "not_available"))

        payload[field_key] = value
        field_metadata.append(
            {
                "payload_field_key": field_key,
                "canonical_feature": feature_name,
                "value_source": value_source,
                "payload_value_allowed": value_allowed,
                "mapping_available": _safe_bool(row.get("mapping_available", False)),
                "mapping_gap": _safe_bool(row.get("mapping_gap", False)),
                "limitation_aware": _safe_bool(row.get("limitation_aware", False)),
                "disclosure_required": _safe_bool(row.get("disclosure_required", False)),
                "disclosure_complete": _safe_bool(row.get("disclosure_complete", False)),
            }
        )

    return {
        "payload_mode": safe_mode,
        "selected_sample": selected_sample,
        "preview_status": "contract_preview",
        "notice": PAYLOAD_PREVIEW_NOTICE,
        "payload": payload,
        "field_metadata": field_metadata,
        "metadata": {
            "contract_only": True,
            "field_count": len(payload),
            "inference_executed": False,
            "transformation_executed": False,
            "uses_threshold": False,
        },
    }


def compute_payload_coverage(
    preview_payload: dict[str, Any],
    payload_template_df: pd.DataFrame | None = None,
    canonical_schema_df: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Compute structural payload coverage from contract metadata."""
    payload = preview_payload.get("payload", {})
    mode = normalize_mode(str(preview_payload.get("payload_mode", "BASIC_FORM")))
    metadata_rows = preview_payload.get("field_metadata", [])

    available_values = [
        value for value in payload.values()
        if value not in {PREVIEW_VALUE_NOT_AVAILABLE, None}
    ]
    gap_rows = [
        row for row in metadata_rows
        if bool(row.get("mapping_gap")) or payload.get(str(row.get("payload_field_key"))) == PREVIEW_VALUE_NOT_AVAILABLE
    ]
    limitation_rows = [
        row for row in metadata_rows
        if bool(row.get("limitation_aware"))
        or str(row.get("canonical_feature")) in LIMITATION_FIELDS
    ]

    expected_features = 0
    if _is_available_frame(canonical_schema_df) and "schema_mode" in canonical_schema_df.columns:
        expected_features = len(_rows_for_mode(canonical_schema_df, mode))
    elif _is_available_frame(payload_template_df):
        expected_features = len(_rows_for_mode(payload_template_df, mode))

    return {
        "payload_mode": mode,
        "preview_status": preview_payload.get("preview_status", "not_available"),
        "payload_field_count": len(payload),
        "available_value_count": len(available_values),
        "expected_contract_field_count": int(expected_features),
        "gap_count": len(gap_rows),
        "limitation_field_count": len(limitation_rows),
        "contract_only": True,
        "inference_executed": False,
        "transformation_executed": False,
        "uses_threshold": False,
    }


def missing_or_gap_fields(preview_payload: dict[str, Any]) -> pd.DataFrame:
    """Return fields that are unavailable or documented as mapping gaps."""
    rows = []
    payload = preview_payload.get("payload", {})
    for row in preview_payload.get("field_metadata", []):
        field_key = str(row.get("payload_field_key"))
        if bool(row.get("mapping_gap")) or payload.get(field_key) == PREVIEW_VALUE_NOT_AVAILABLE:
            rows.append(row)
    if not rows:
        return pd.DataFrame(columns=["payload_field_key", "canonical_feature", "value_source"])
    return pd.DataFrame(rows)


def limitation_fields_table(
    limitation_disclosure_df: pd.DataFrame | None = None,
    mode: str | None = None,
) -> pd.DataFrame:
    """Return limitation disclosures for display."""
    if not _is_available_frame(limitation_disclosure_df):
        return pd.DataFrame(
            {
                "limitation_field": LIMITATION_FIELDS,
                "disclosure_status": ["not_available"] * len(LIMITATION_FIELDS),
                "disclosure_text": ["Limitation disclosure artifact is not available."] * len(LIMITATION_FIELDS),
            }
        )

    frame = limitation_disclosure_df.copy()
    if mode and "payload_mode" in frame.columns:
        safe_mode = normalize_mode(mode)
        frame = frame[frame["payload_mode"].astype(str) == safe_mode].copy()

    preferred_columns = [
        "payload_mode",
        "profile_id",
        "limitation_field",
        "included_in_template",
        "applicant_entered_input",
        "disclosure_required",
        "disclosure_complete",
        "disclosure_status",
        "disclosure_text",
    ]
    display_columns = [column for column in preferred_columns if column in frame.columns]
    return frame[display_columns].reset_index(drop=True) if display_columns else frame.reset_index(drop=True)


def render_payload_json(preview_payload: dict[str, Any]) -> None:
    """Render payload JSON preview."""
    st = _get_streamlit()
    st.info(PAYLOAD_PREVIEW_NOTICE)
    st.json(preview_payload.get("payload", {}))


def render_payload_coverage(coverage: dict[str, Any]) -> None:
    """Render payload coverage metrics."""
    st = _get_streamlit()
    cols = st.columns(4)
    cols[0].metric("Payload Fields", coverage.get("payload_field_count", 0))
    cols[1].metric("Available Values", coverage.get("available_value_count", 0))
    cols[2].metric("Gap Fields", coverage.get("mapping_gap_count", coverage.get("gap_count", 0)))
    cols[3].metric("Limitation Fields", coverage.get("limitation_field_count", 0))


def render_payload_limitations(
    limitation_disclosure_df: pd.DataFrame | None = None,
    mode: str | None = None,
) -> None:
    """Render limitation disclosures for payload preview."""
    st = _get_streamlit()
    st.warning(
        "Payload preview is contract-only. It does not run model inference, "
        "compare thresholds, or produce credit decisions."
    )
    st.dataframe(limitation_fields_table(limitation_disclosure_df, mode), use_container_width=True)


def render_missing_or_gap_fields(preview_payload: dict[str, Any]) -> None:
    """Render unavailable fields and documented mapping gaps."""
    st = _get_streamlit()
    gaps = missing_or_gap_fields(preview_payload)
    if gaps.empty:
        st.success("No unavailable payload fields are shown for this contract preview.")
        return
    st.dataframe(gaps, use_container_width=True)


def payload_field_status_frame(result: PayloadBuildResult) -> pd.DataFrame:
    """Return field-status rows from a Stage 3 payload build result."""
    preferred_columns = [
        "payload_mode",
        "canonical_feature",
        "payload_field_key",
        "field_status",
        "value_source",
        "mapping_available",
        "mapping_gap",
        "payload_value_allowed",
        "limitation_aware",
        "disclosure_required",
        "disclosure_complete",
    ]
    frame = pd.DataFrame(result.field_status)
    if frame.empty:
        return pd.DataFrame(columns=preferred_columns)
    display_columns = [column for column in preferred_columns if column in frame.columns]
    return frame[display_columns].reset_index(drop=True) if display_columns else frame.reset_index(drop=True)


def payload_validation_frame(result: PayloadBuildResult) -> pd.DataFrame:
    """Return a compact validation report table for display."""
    preferred_keys = [
        "payload_mode",
        "readiness_status",
        "canonical_feature_count",
        "canonical_feature_target",
        "payload_field_count",
        "provided_field_count",
        "available_value_count",
        "missing_required_count",
        "mapping_gap_count",
        "limitation_field_count",
        "basic_form_gap_count",
        "payload_compatible",
        "contract_schema_validation_only",
        "credit_risk_validation_executed",
        "model_validation_executed",
        "inference_executed",
        "thresholding_executed",
        "decisioning_executed",
        "guardrail_metadata_ok",
    ]
    rows = [
        {"validation_item": key, "value": result.validation.get(key)}
        for key in preferred_keys
        if key in result.validation
    ]
    return pd.DataFrame(rows)


def payload_guardrail_frame(result: PayloadBuildResult) -> pd.DataFrame:
    """Return no-inference guardrail metadata for display."""
    preferred_keys = [
        "contract_only",
        "inference_executed",
        "model_loaded",
        "threshold_used",
        "decision_generated",
        "shap_executed",
        "credit_score_generated",
        "original_mode",
        "normalized_mode",
        "mode_valid",
        "selected_sample",
    ]
    rows = [
        {"metadata_item": key, "value": result.metadata.get(key)}
        for key in preferred_keys
        if key in result.metadata
    ]
    return pd.DataFrame(rows)


def payload_result_limitations_frame(result: PayloadBuildResult) -> pd.DataFrame:
    """Return limitation rows from a Stage 3 payload build result."""
    preferred_columns = [
        "payload_mode",
        "canonical_feature",
        "payload_field_key",
        "disclosure_required",
        "disclosure_complete",
        "disclosure_text",
    ]
    frame = pd.DataFrame(result.limitations)
    if frame.empty:
        return pd.DataFrame(columns=preferred_columns)
    display_columns = [column for column in preferred_columns if column in frame.columns]
    return frame[display_columns].reset_index(drop=True) if display_columns else frame.reset_index(drop=True)


def demo_inference_metadata_frame(result: DemoInferenceResult) -> pd.DataFrame:
    """Return Stage 4 guardrail metadata for display."""
    preferred_keys = [
        "demo_inference_only",
        "model_loaded",
        "inference_executed",
        "predict_proba_executed",
        "credit_decision_generated",
        "approval_recommendation_generated",
        "rejection_recommendation_generated",
        "threshold_applied",
        "threshold_loaded_for_decisioning",
        "credit_score_generated",
        "adverse_action_generated",
        "shap_loaded",
        "shap_executed",
        "legal_compliance_claimed",
        "fairness_claimed",
        "production_ready_claimed",
        "safe_failure",
        "failure_reason",
        "model_load_status",
        "model_input_feature_count",
        "risk_signal_band_is_decision_threshold",
    ]
    rows = [
        {"metadata_item": key, "value": result.metadata.get(key)}
        for key in preferred_keys
        if key in result.metadata
    ]
    return pd.DataFrame(rows)


def demo_inference_limitations_frame(result: DemoInferenceResult) -> pd.DataFrame:
    """Return Stage 4 limitations for display."""
    preferred_columns = [
        "payload_mode",
        "canonical_feature",
        "payload_field_key",
        "disclosure_required",
        "disclosure_complete",
        "disclosure_text",
    ]
    frame = pd.DataFrame(result.limitations)
    if frame.empty:
        return pd.DataFrame(columns=preferred_columns)
    display_columns = [column for column in preferred_columns if column in frame.columns]
    return frame[display_columns].reset_index(drop=True) if display_columns else frame.reset_index(drop=True)


def demo_inference_validation_frame(result: DemoInferenceResult) -> pd.DataFrame:
    """Return compact Stage 4 validation details for display."""
    rows = [
        {"validation_item": "mode", "value": result.mode},
        {"validation_item": "inference_status", "value": result.inference_status},
        {"validation_item": "readiness_note", "value": result.readiness_note},
    ]
    for key in [
        "payload_readiness_status",
        "payload_field_count",
        "mapping_gap_count",
        "missing_required_count",
        "blocking_reasons",
    ]:
        if key in result.input_validation:
            rows.append({"validation_item": key, "value": result.input_validation.get(key)})

    compatibility = result.model_input_compatibility
    for key in [
        "status",
        "compatible",
        "expected_feature_count",
        "payload_feature_count",
        "dtype_error_count",
        "feature_order_source",
        "missing_features",
        "extra_features",
    ]:
        if key in compatibility:
            rows.append({"validation_item": f"model_input_{key}", "value": compatibility.get(key)})

    if result.error_message:
        rows.append({"validation_item": "error_message", "value": result.error_message})
    return pd.DataFrame(rows)


def render_payload_readiness(result: PayloadBuildResult) -> None:
    """Render Stage 3 payload readiness status without decision semantics."""
    st = _get_streamlit()
    status = result.readiness_status
    message = f"{status}: {result.readiness_note}"
    if status == "READY_FOR_CONTRACT_PREVIEW":
        st.success(message)
    elif status in {"PARTIAL_READY_WITH_LIMITATIONS", "BLOCKED_BY_SCHEMA_GAP"}:
        st.warning(message)
    else:
        st.error(message)


def render_payload_validation_report(result: PayloadBuildResult) -> None:
    """Render Stage 3 payload coverage and validation report."""
    st = _get_streamlit()
    render_payload_coverage(result.coverage)
    validation_frame = payload_validation_frame(result)
    if not validation_frame.empty:
        st.dataframe(validation_frame, use_container_width=True)


def render_payload_field_status(result: PayloadBuildResult) -> None:
    """Render Stage 3 field-status table."""
    st = _get_streamlit()
    frame = payload_field_status_frame(result)
    st.dataframe(frame, use_container_width=True)


def render_payload_result_limitations(result: PayloadBuildResult) -> None:
    """Render Stage 3 limitation disclosures from the builder result."""
    st = _get_streamlit()
    frame = payload_result_limitations_frame(result)
    if frame.empty:
        st.info("No limitation rows are available for this payload result.")
        return
    st.dataframe(frame, use_container_width=True)


def render_payload_guardrail_metadata(result: PayloadBuildResult) -> None:
    """Render no-inference guardrail metadata from the builder result."""
    st = _get_streamlit()
    frame = payload_guardrail_frame(result)
    st.dataframe(frame, use_container_width=True)


def render_demo_inference_guardrails(result: DemoInferenceResult) -> None:
    """Render Stage 4 guardrail metadata."""
    st = _get_streamlit()
    frame = demo_inference_metadata_frame(result)
    if frame.empty:
        st.info("Inference guardrail metadata is not available.")
        return
    st.dataframe(frame, use_container_width=True)


def render_demo_inference_limitations(result: DemoInferenceResult) -> None:
    """Render Stage 4 limitation disclosures."""
    st = _get_streamlit()
    frame = demo_inference_limitations_frame(result)
    if frame.empty:
        st.info("No limitation rows are available for this demo inference result.")
        return
    st.dataframe(frame, use_container_width=True)


def render_demo_inference_result(result: DemoInferenceResult) -> None:
    """Render a safe Stage 4 demo inference result without running inference."""
    st = _get_streamlit()
    st.subheader("Safe Demo Inference")
    st.caption(
        "Default-risk signal preview is shown only when all Stage 4 guardrails pass. "
        "Risk signal bands are descriptive demo bands, not decision thresholds."
    )

    if result.inference_status == DEMO_INFERENCE_READY:
        signal_display = format_risk_signal(result.risk_signal)
        st.success(result.readiness_note)
        cols = st.columns(3)
        cols[0].metric(RISK_SIGNAL_LABEL, signal_display["risk_signal_display"])
        cols[1].metric("Risk signal band", result.risk_signal_band or signal_display["risk_signal_band"])
        cols[2].metric("Inference status", result.inference_status)
        st.info(str(signal_display.get("risk_signal_band_note") or RISK_SIGNAL_BAND_NOTE))
    else:
        st.warning(result.readiness_note)
        blocked_reason = (
            result.metadata.get("failure_reason")
            or result.error_message
            or result.inference_status
        )
        st.info(f"Blocked reason: {blocked_reason}")

    validation_frame = demo_inference_validation_frame(result)
    if not validation_frame.empty:
        st.subheader("Stage 4 Validation")
        st.dataframe(validation_frame, use_container_width=True)

    st.subheader("Inference Guardrails")
    render_demo_inference_guardrails(result)

    st.subheader("Limitations")
    render_demo_inference_limitations(result)


def render_public_inference_result(result: DemoInferenceResult) -> None:
    """Render only disclosure-safe Step 5 result evidence."""

    st = _get_streamlit()
    st.subheader("Controlled Inference Result")
    if result.inference_status != DEMO_INFERENCE_READY:
        st.warning(result.readiness_note)
        failure_code = result.metadata.get("failure_reason") or result.inference_status
        st.info(f"Blocked reason code: {failure_code}")
        st.warning(PUBLIC_DEMO_RESULT_DISCLOSURE)
        return

    probability = result.calibrated_default_probability
    st.success(result.readiness_note)
    st.markdown(
        """
        <style>
        .st-key-safe-demo-probability-metric [data-testid="stMetricLabel"],
        .st-key-safe-demo-probability-metric [data-testid="stMetricLabel"] > div,
        .st-key-safe-demo-probability-metric [data-testid="stMetricLabel"] [data-testid="stMarkdownContainer"],
        .st-key-safe-demo-probability-metric [data-testid="stMetricLabel"] p,
        .st-key-safe-demo-model-threshold-relation [data-testid="stMetricLabel"],
        .st-key-safe-demo-canonical-feature-count [data-testid="stMetricLabel"] {
            height: auto;
            align-items: start;
            overflow: visible;
            overflow-wrap: anywhere;
            text-overflow: clip;
            white-space: normal;
        }
        .st-key-safe-demo-model-threshold-relation [data-testid="stMetricValue"],
        .st-key-safe-demo-model-threshold-relation [data-testid="stMetricValue"] > div {
            height: auto;
            min-height: 48px;
            overflow: visible;
            overflow-wrap: anywhere;
            text-overflow: clip;
            white-space: normal;
            font-size: 24px;
            line-height: 1.25;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    cols = st.columns([1, 2, 1])
    with cols[0].container(key="safe-demo-probability-metric"):
        st.metric(
            "Estimated model default-risk probability",
            f"{float(probability):.4%}" if probability is not None else "Unavailable",
        )
    with cols[1].container(key="safe-demo-model-threshold-relation"):
        st.metric("Model threshold relation", result.threshold_relation or "Unavailable")
    with cols[2].container(key="safe-demo-canonical-feature-count"):
        st.metric("Canonical feature count", result.feature_count or 0)

    metadata = result.metadata
    profile_id = (
        result.synthetic_profile_id
        or metadata.get("advanced_editor_profile_id")
        or metadata.get("selected_synthetic_profile_id")
    )
    safe_rows: list[dict[str, object]] = [
        {"result_item": "mode", "value": result.mode},
        {"result_item": "fictional_profile_id", "value": profile_id},
        {"result_item": "payload_fingerprint", "value": metadata.get("payload_fingerprint")},
        {"result_item": "edited_feature_count", "value": metadata.get("edited_feature_count", 0)},
        {"result_item": "provenance_counts", "value": result.value_source_counts},
        {"result_item": "limitation_aware_features", "value": list(result.limitation_aware_features)},
    ]
    st.dataframe(pd.DataFrame(safe_rows), use_container_width=True, hide_index=True)
    if metadata.get("edited_feature_names"):
        st.caption(
            "Edited canonical features: "
            + ", ".join(str(name) for name in metadata["edited_feature_names"])
        )
    st.warning(PUBLIC_DEMO_RESULT_DISCLOSURE)


def render_payload_result_json(result: PayloadBuildResult) -> None:
    """Render Stage 3 JSON payload preview and download control."""
    st = _get_streamlit()
    payload_json = payload_result_to_json(result)
    st.json(result.payload)
    st.download_button(
        "Download Payload JSON",
        data=payload_json,
        file_name=f"{result.mode.lower()}_contract_payload.json",
        mime="application/json",
    )


def render_payload_build_result(result: PayloadBuildResult) -> None:
    """Render the complete Stage 3 contract payload build result."""
    st = _get_streamlit()
    st.info(PAYLOAD_PREVIEW_NOTICE)

    st.subheader("Payload Readiness")
    render_payload_readiness(result)

    st.subheader("Coverage and Validation")
    render_payload_validation_report(result)

    st.subheader("Field Status")
    render_payload_field_status(result)

    st.subheader("Limitation Disclosure")
    render_payload_result_limitations(result)

    st.subheader("JSON Payload")
    render_payload_result_json(result)

    st.subheader("Guardrail Metadata")
    render_payload_guardrail_metadata(result)
