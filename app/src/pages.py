"""Streamlit pages for the contract-driven portfolio demo."""

from __future__ import annotations

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
)
from .demo_inference import run_safe_demo_inference, validate_payload_for_demo_inference
from .payload_builder import build_payload_from_mode
from .payload_preview import render_demo_inference_result, render_payload_build_result
from .ui_text import (
    APP_TITLE,
    GOVERNANCE_LIMITATION_NOTICE,
    NO_INFERENCE_NOTICE,
    OVERVIEW_INTRO,
    PAGE_HELP_TEXT,
    PAYLOAD_BUILDER_NOTICE,
    PAYLOAD_PREVIEW_NOTICE,
    PORTFOLIO_ONLY_NOTICE,
    PROJECT_TITLE,
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
    cols = st.columns(4)
    cols[0].metric("Stage 0 Status", _safe_metric(summary.get("stage_0_status")))
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
    st.title("Safe Demo Inference")
    st.caption(PAGE_HELP_TEXT["Safe Demo Inference"])
    st.info(SAFE_DEMO_INFERENCE_NOTICE)
    st.warning(SAFE_DEMO_INFERENCE_LIMITATION_NOTICE)

    try:
        bundle = _load_contract_bundle()
    except Exception as exc:
        st.error(f"Unable to read Safe Demo Inference contracts: {exc}")
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
        st.warning("Sample profile catalog is not available. Preview will use template metadata only.")

    payload_result = build_payload_from_mode(
        mode=selected_mode,
        contract_bundle=bundle,
        selected_sample=selected_sample,
    )

    st.subheader("Stage 3 Payload Builder Result")
    render_payload_build_result(payload_result)

    st.subheader("Default-Risk Signal Preview")
    if selected_mode == "BASIC_FORM":
        demo_inference_result = validate_payload_for_demo_inference(payload_result)
    else:
        demo_inference_result = run_safe_demo_inference(payload_result)
    render_demo_inference_result(demo_inference_result)


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
