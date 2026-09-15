"""Streamlit pages for the contract-driven portfolio demo."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from .contract_loader import load_all_contracts
from .mode_view import (
    PAYLOAD_MODES,
    get_basic_form_limitation,
    get_mode_display_name,
    render_basic_form_gap_notice,
    render_mode_field_table,
    render_mode_selector,
    render_mode_summary,
    render_public_inference_mode_selector,
)
from .demo_inference import run_safe_demo_inference, validate_payload_for_demo_inference
from .basic_form_inference import run_basic_form_inference
from .advanced_editor_inference import run_advanced_editor_inference
from .advanced_editor_runtime import advanced_editor_contract_summary
from .payload_builder import build_payload_from_mode
from .payload_preview import (
    render_demo_inference_result,
    render_payload_build_result,
    render_public_inference_result,
)
from .ui_text import (
    ADVANCED_EDITOR_INFERENCE_DISCLOSURE,
    APP_TITLE,
    BASIC_FORM_INFERENCE_DISCLOSURE,
    GOVERNANCE_LIMITATION_NOTICE,
    NO_INFERENCE_NOTICE,
    OVERVIEW_INTRO,
    PAGE_HELP_TEXT,
    PAYLOAD_BUILDER_NOTICE,
    PAYLOAD_PREVIEW_NOTICE,
    PORTFOLIO_ONLY_NOTICE,
    PROJECT_TITLE,
    PUBLIC_DEMO_RESULT_DISCLOSURE,
    REQUIRED_DISCLOSURES,
    SAFE_DEMO_INFERENCE_LIMITATION_NOTICE,
    SAFE_DEMO_INFERENCE_NOTICE,
    STAGE_BADGE,
    STAGE_LABEL,
    WHAT_THIS_APP_DEMONSTRATES,
    WHAT_THIS_APP_DOES_NOT_DO,
)
from .validation_summary import readiness_summary_to_frame


def _get_streamlit():
    try:
        import streamlit as st
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Streamlit is required to render the contract demo app pages. "
            "Install project UI dependencies before launching the app."
        ) from exc
    return st


def _load_contract_bundle() -> dict[str, Any]:
    return load_all_contracts()


def _is_available_frame(frame: pd.DataFrame | None) -> bool:
    return isinstance(frame, pd.DataFrame) and not frame.empty and "load_status" not in frame.columns


def _artifact_category_summary(manifest_df: pd.DataFrame | None) -> pd.DataFrame:
    if not _is_available_frame(manifest_df) or "artifact_category" not in manifest_df.columns:
        return pd.DataFrame(
            {
                "artifact_category": ["not_available"],
                "artifact_count": [0],
                "exported_count": [0],
                "readback_ok_count": [0],
            }
        )

    frame = manifest_df.copy()
    grouped = frame.groupby("artifact_category", dropna=False)
    summary = grouped.agg(
        artifact_count=("artifact_id", "count"),
        exported_count=("export_status", lambda values: int((values == "EXPORTED").sum())),
        readback_ok_count=("readback_status", lambda values: int((values == "READBACK_OK").sum())),
    )
    return summary.reset_index().sort_values("artifact_category")


def _safe_metric(value: Any, fallback: str = "Not Available") -> Any:
    return fallback if value is None else value


def _sample_profile_options(sample_profiles: dict[str, pd.DataFrame]) -> dict[str, str]:
    catalog = sample_profiles.get("catalog")
    if not _is_available_frame(catalog) or "profile_id" not in catalog.columns:
        return {}

    label_column = "profile_display_label" if "profile_display_label" in catalog.columns else "profile_id"
    options = {}
    for _, row in catalog.iterrows():
        profile_id = str(row["profile_id"])
        label = str(row[label_column])
        options[label] = profile_id
    return options


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASIC_FORM_CONTRACT_PATH = (
    PROJECT_ROOT / "outputs/stage9/stage9_public_input_constraint_contract.json"
)
BASIC_FORM_CONTRACT_SIZE = 20_812
BASIC_FORM_CONTRACT_SHA256 = (
    "d94e3a5de3d36e9856a2821303f00a749debc69a416f318e0dff50199b83bdae"
)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@lru_cache(maxsize=1)
def _basic_form_ui_contract() -> dict[str, Any]:
    """Load the fixed Step 4.1A constraints after integrity verification."""

    if (
        BASIC_FORM_CONTRACT_PATH.is_symlink()
        or BASIC_FORM_CONTRACT_PATH.stat().st_size != BASIC_FORM_CONTRACT_SIZE
        or _file_sha256(BASIC_FORM_CONTRACT_PATH) != BASIC_FORM_CONTRACT_SHA256
    ):
        raise ValueError("BASIC_FORM_UI_CONTRACT_INVALID")
    value = json.loads(BASIC_FORM_CONTRACT_PATH.read_text(encoding="utf-8"))
    if value.get("validation_status") != "PASS":
        raise ValueError("BASIC_FORM_UI_CONTRACT_INVALID")
    return value


def run_public_mode_inference(
    mode: str,
    *,
    sample_profile_payload_result: object | None = None,
    basic_form_source_inputs: dict[str, object] | None = None,
    basic_form_system_metadata: dict[str, object] | None = None,
    advanced_editor_request: dict[str, object] | None = None,
):
    """Route exactly one public mode to its separately authorized adapter."""

    if mode == "SAMPLE_PROFILE" and sample_profile_payload_result is not None:
        return run_safe_demo_inference(sample_profile_payload_result)
    if (
        mode == "BASIC_FORM"
        and basic_form_source_inputs is not None
        and basic_form_system_metadata is not None
    ):
        return run_basic_form_inference(
            basic_form_source_inputs,
            basic_form_system_metadata,
        )
    if mode == "ADVANCED_EDITOR" and advanced_editor_request is not None:
        return run_advanced_editor_inference(advanced_editor_request)
    from .demo_inference import blocked_demo_inference_result

    return blocked_demo_inference_result(
        mode=mode if mode in {"SAMPLE_PROFILE", "BASIC_FORM", "ADVANCED_EDITOR"} else "UNAUTHORIZED",
        failure_reason="PUBLIC_MODE_ROUTE_INVALID",
        readiness_note="The selected public input route is unavailable.",
    )


def _render_sample_profile_inference(bundle: dict[str, Any]) -> None:
    st = _get_streamlit()
    st.write("Predefined fictional examples protected by exact committed payload binding.")
    sample_options = _sample_profile_options(bundle.get("sample_profiles", {}))
    if not sample_options:
        st.error("The committed fictional profile catalog is unavailable.")
        return
    with st.form("sample_profile_inference_form"):
        selected_label = st.selectbox("Fictional sample profile", list(sample_options))
        submitted = st.form_submit_button("Run controlled inference")
    if submitted:
        payload_result = build_payload_from_mode(
            mode="SAMPLE_PROFILE",
            contract_bundle=bundle,
            selected_sample=sample_options[selected_label],
        )
        result = run_public_mode_inference(
            "SAMPLE_PROFILE",
            sample_profile_payload_result=payload_result,
        )
        render_public_inference_result(result)


def _render_basic_form_inference() -> None:
    st = _get_streamlit()
    contract = _basic_form_ui_contract()
    fields = contract["field_constraints"]
    metadata_contract = contract["system_metadata_constraints"]
    profile_ids = metadata_contract["synthetic_baseline_profile_id"]["allowed_values"]
    st.info(BASIC_FORM_INFERENCE_DISCLOSURE)
    with st.form("basic_form_inference_form"):
        annual_inc = st.number_input(
            "Fictional annual income (USD)",
            min_value=float(fields["annual_inc"]["minimum"]),
            max_value=float(fields["annual_inc"]["maximum"]),
            value=75_000.0,
        )
        dti = st.number_input(
            "Debt-to-income ratio (%)",
            min_value=float(fields["dti"]["minimum"]),
            max_value=float(fields["dti"]["maximum"]),
            value=18.27,
            help="18.27 means 18.27%; this value is not divided by 100.",
        )
        home_ownership = st.selectbox(
            "Fictional home ownership",
            fields["home_ownership"]["public_allowed_categories"],
        )
        loan_amnt = st.number_input(
            "Fictional requested loan amount (USD)",
            min_value=float(fields["loan_amnt"]["minimum"]),
            max_value=float(fields["loan_amnt"]["maximum"]),
            value=10_000.0,
        )
        purpose = st.selectbox(
            "Fictional loan purpose",
            fields["purpose"]["public_allowed_categories"],
        )
        term_months = st.selectbox(
            "Fictional term",
            fields["term_months"]["allowed_values"],
            format_func=lambda value: f"{value} months",
        )
        profile_id = st.selectbox("Synthetic completion profile", profile_ids)
        acknowledged = st.checkbox(
            "I understand that 38 features use a fictional synthetic baseline and this output is not a lending decision.",
            value=False,
            key="basic_form_acknowledgement",
        )
        submitted = st.form_submit_button("Run controlled inference")
    if submitted:
        result = run_public_mode_inference(
            "BASIC_FORM",
            basic_form_source_inputs={
                "annual_inc": annual_inc,
                "dti": dti,
                "home_ownership": home_ownership,
                "loan_amnt": loan_amnt,
                "purpose": purpose,
                "term_months": term_months,
            },
            basic_form_system_metadata={
                "synthetic_baseline_profile_id": profile_id,
                "synthetic_completion_acknowledged": acknowledged,
            },
        )
        render_public_inference_result(result)


def _advanced_editor_control(
    st: Any,
    row: dict[str, Any],
    base_value: object,
    profile_id: str,
) -> object:
    feature = row["feature_name"]
    key = f"advanced_editor_value_{profile_id}_{feature}"
    control = row["editor_control"]
    if control == "SELECT":
        options = list(row["allowed_values"])
        return st.selectbox(
            feature,
            options,
            index=options.index(base_value),
            key=key,
        )
    if control == "NUMBER_INPUT":
        return st.number_input(
            feature,
            min_value=float(row["minimum"]),
            max_value=float(row["maximum"]),
            value=float(base_value),
            key=key,
        )
    st.caption(f"{feature}: {base_value} (read-only)")
    return base_value


def _reset_advanced_editor_widget_state() -> None:
    """Clear only Advanced Editor values and acknowledgement after profile change."""

    st = _get_streamlit()
    for key in tuple(st.session_state):
        if key.startswith("advanced_editor_value_") or key.startswith("advanced_editor_acknowledgement_"):
            del st.session_state[key]


def _render_advanced_editor_inference() -> None:
    st = _get_streamlit()
    summary = advanced_editor_contract_summary()
    profile_ids = list(summary["profile_ids"])
    registry = [dict(row) for row in summary["feature_registry"]]
    projections = summary["canonical_reset_projections"]
    st.info(ADVANCED_EDITOR_INFERENCE_DISCLOSURE)
    profile_id = st.selectbox(
        "Canonical reset profile",
        profile_ids,
        key="advanced_editor_profile_id",
        on_change=_reset_advanced_editor_widget_state,
        help="Changing this selector resets all controls to that committed canonical projection.",
    )
    base = projections[profile_id]
    with st.form("advanced_editor_inference_form"):
        values: dict[str, object] = {}
        group_labels = {
            "DIRECT_USER_SUPPLIED": "Direct fictional inputs",
            "DERIVED": "Derived technical features",
            "SYNTHETIC_BASELINE_PASSTHROUGH": "Synthetic baseline passthrough features",
        }
        for partition, label in group_labels.items():
            with st.expander(label, expanded=partition == "DIRECT_USER_SUPPLIED"):
                for row in registry:
                    if row["partition_class"] != partition:
                        continue
                    feature = row["feature_name"]
                    if feature == "is_60_month":
                        continue
                    values[feature] = _advanced_editor_control(
                        st,
                        row,
                        base[feature],
                        profile_id,
                    )
        values["is_60_month"] = int(values["term_months"] == 60)
        st.caption(
            "is_60_month: "
            f"{values['is_60_month']} (read-only; derived from term_months)"
        )
        acknowledged = st.checkbox(
            "I understand that these are fictional technical model inputs and this output is not a lending decision.",
            value=False,
            key=f"advanced_editor_acknowledgement_{profile_id}",
        )
        submitted = st.form_submit_button("Run controlled inference")

    if submitted:
        order = list(summary["ordered_feature_names"])
        edited_names = [
            row["feature_name"]
            for row in registry
            if row["editable"] is True
            and values[row["feature_name"]] != base[row["feature_name"]]
        ]
        request = {
            "mode": "ADVANCED_EDITOR",
            "system_metadata": {
                "advanced_editor_profile_id": profile_id,
                "advanced_editor_acknowledged": acknowledged,
                "edited_feature_names": edited_names,
            },
            "payload_rows": [
                {"feature_index": index, "feature_name": name, "value": values[name]}
                for index, name in enumerate(order)
            ],
        }
        result = run_public_mode_inference(
            "ADVANCED_EDITOR",
            advanced_editor_request=request,
        )
        render_public_inference_result(result)


def render_overview() -> None:
    st = _get_streamlit()
    st.title(APP_TITLE)
    st.caption(f"{PROJECT_TITLE} | {STAGE_LABEL}")
    st.subheader(STAGE_BADGE)
    st.write(OVERVIEW_INTRO)
    st.info(NO_INFERENCE_NOTICE)

    try:
        bundle = _load_contract_bundle()
    except Exception as exc:
        st.error(f"Unable to read Stage 0 contract evidence: {exc}")
        return

    summary = bundle["readiness_summary"]
    cols = st.columns(5)
    cols[0].metric("Contract Artifacts", _safe_metric(summary.get("artifacts_exported")))
    cols[1].metric("Payload Modes", _safe_metric(summary.get("payload_modes")))
    cols[2].metric("Canonical Features", _safe_metric(summary.get("canonical_features")))
    cols[3].metric("Basic Form Gaps", _safe_metric(summary.get("basic_form_gap_count")))
    cols[4].metric("Read-Back", "Passed" if summary.get("readback_checks_passed") else "Requires Review")

    st.warning(PORTFOLIO_ONLY_NOTICE)
    st.dataframe(_artifact_category_summary(bundle.get("manifest_df")), use_container_width=True)


def render_contract_readiness() -> None:
    st = _get_streamlit()
    st.title("Contract Readiness")
    st.caption(PAGE_HELP_TEXT["Contract Readiness"])
    try:
        bundle = _load_contract_bundle()
    except Exception as exc:
        st.error(f"Unable to read Stage 0 contract readiness evidence: {exc}")
        return

    summary = bundle["readiness_summary"]
    st.markdown(
        """
        <style>
        .st-key-contract-readiness-stage-0-status [data-testid="stMetricValue"],
        .st-key-contract-readiness-stage-0-status [data-testid="stMetricValue"] > div {
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
    cols = st.columns([1.5, 1, 1, 1])
    with cols[0].container(key="contract-readiness-stage-0-status"):
        st.metric("Stage 0 Status", _safe_metric(summary.get("stage_0_status")))
    cols[1].metric("Exported Artifacts", _safe_metric(summary.get("artifacts_exported")))
    cols[2].metric("Payload Modes", _safe_metric(summary.get("payload_modes")))
    cols[3].metric("Canonical Features", _safe_metric(summary.get("canonical_features")))

    basic_form = get_basic_form_limitation()
    st.warning(
        f"Basic Form is {basic_form['status'].lower()} with "
        f"{basic_form['gap_count']} documented mapping gaps."
    )
    st.info(
        "Readiness is displayed from Stage 0 exported contract artifacts. "
        "The app reads contract files without mutating them."
    )
    st.dataframe(readiness_summary_to_frame(summary), use_container_width=True)
    st.subheader("Artifact Categories")
    st.dataframe(_artifact_category_summary(bundle.get("manifest_df")), use_container_width=True)


def render_demo_input_modes() -> None:
    st = _get_streamlit()
    st.title("Demo Input Modes")
    st.caption(PAGE_HELP_TEXT["Demo Input Modes"])
    st.info(
        "Explore Demo Input Modes for schema compatibility and payload readiness review. "
        "Each mode can build a contract payload object without model execution."
    )

    try:
        bundle = _load_contract_bundle()
    except Exception as exc:
        st.error(f"Unable to read demo input mode contracts: {exc}")
        return

    selected_mode = render_mode_selector(default_mode="BASIC_FORM")
    render_mode_summary(
        selected_mode,
        schema_df=bundle.get("canonical_schema"),
        mode_readiness_df=bundle.get("payload_modes"),
    )
    st.subheader("Mode Field Contract")
    render_mode_field_table(bundle.get("canonical_schema"), selected_mode)

    with st.expander("Available Demo Input Modes", expanded=False):
        mode_rows = [
            {"payload_mode": mode, "display_name": get_mode_display_name(mode)}
            for mode in PAYLOAD_MODES
        ]
        st.dataframe(pd.DataFrame(mode_rows), use_container_width=True)


def render_payload_preview() -> None:
    st = _get_streamlit()
    st.title("Payload Builder & Preview")
    st.caption(PAGE_HELP_TEXT["Payload Builder & Preview"])
    st.info(PAYLOAD_PREVIEW_NOTICE)
    st.info(PAYLOAD_BUILDER_NOTICE)

    try:
        bundle = _load_contract_bundle()
    except Exception as exc:
        st.error(f"Unable to read payload builder contracts: {exc}")
        return

    selected_mode = render_mode_selector(default_mode="SAMPLE_PROFILE")
    if selected_mode == "BASIC_FORM":
        render_basic_form_gap_notice()

    selected_sample = None
    sample_options = _sample_profile_options(bundle.get("sample_profiles", {}))
    if selected_mode == "SAMPLE_PROFILE" and sample_options:
        selected_label = st.selectbox("Sample Profile Contract", list(sample_options.keys()))
        selected_sample = sample_options[selected_label]
    elif selected_mode == "SAMPLE_PROFILE":
        st.warning("Sample profile catalog is not available. Payload builder will use template metadata only.")

    payload_result = build_payload_from_mode(
        mode=selected_mode,
        contract_bundle=bundle,
        selected_sample=selected_sample,
    )
    render_payload_build_result(payload_result)


def render_safe_demo_inference() -> None:
    st = _get_streamlit()
    st.title("Controlled Public Demo Inference")
    st.caption(PAGE_HELP_TEXT["Safe Demo Inference"])
    st.info(SAFE_DEMO_INFERENCE_NOTICE)
    st.warning(SAFE_DEMO_INFERENCE_LIMITATION_NOTICE)
    st.warning(PUBLIC_DEMO_RESULT_DISCLOSURE)

    try:
        bundle = _load_contract_bundle()
    except Exception as exc:
        st.error(f"Unable to read Safe Demo Inference contracts: {exc}")
        return

    selected_mode = render_public_inference_mode_selector(default_mode="BASIC_FORM")
    if selected_mode == "BASIC_FORM":
        _render_basic_form_inference()
    elif selected_mode == "SAMPLE_PROFILE":
        _render_sample_profile_inference(bundle)
    elif selected_mode == "ADVANCED_EDITOR":
        _render_advanced_editor_inference()
    else:
        st.error("The selected mode is not authorized.")


def render_governance_limitations() -> None:
    st = _get_streamlit()
    st.title("Governance & Limitations")
    st.caption(PAGE_HELP_TEXT["Governance & Limitations"])
    st.warning(GOVERNANCE_LIMITATION_NOTICE)
    st.info(PAYLOAD_BUILDER_NOTICE)

    cols = st.columns(2)
    with cols[0]:
        st.subheader("What This App Demonstrates")
        for item in WHAT_THIS_APP_DEMONSTRATES:
            st.write(f"- {item}")
    with cols[1]:
        st.subheader("What This App Does Not Do")
        for item in WHAT_THIS_APP_DOES_NOT_DO:
            st.write(f"- {item}")

    st.subheader("Required Disclosures")
    for disclosure in REQUIRED_DISCLOSURES:
        st.write(f"- {disclosure}")

    try:
        bundle = _load_contract_bundle()
    except Exception as exc:
        st.error(f"Unable to read limitation contract evidence: {exc}")
        return

    readiness = bundle.get("readiness", {})
    limitation_register = readiness.get("limitation_register")
    if _is_available_frame(limitation_register):
        st.subheader("Limitation Register")
        st.dataframe(limitation_register, use_container_width=True)


PAGE_RENDERERS = {
    "Overview": render_overview,
    "Contract Readiness": render_contract_readiness,
    "Demo Input Modes": render_demo_input_modes,
    "Payload Builder & Preview": render_payload_preview,
    "Safe Demo Inference": render_safe_demo_inference,
    "Governance & Limitations": render_governance_limitations,
}
