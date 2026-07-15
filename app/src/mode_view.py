"""Mode-view helpers for the contract-driven Streamlit UI."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .ui_text import (
    BASIC_FORM_LIMITATION_NOTICE,
    MODE_DESCRIPTIONS,
    MODE_DISPLAY_NAMES,
)


PAYLOAD_MODES = [
    "BASIC_FORM",
    "SAMPLE_PROFILE",
    "ADVANCED_EDITOR",
    "CANONICAL_PAYLOAD",
]

BASIC_FORM_GAP_COUNT = 45
LIMITATION_FIELDS = ["credit_age_months", "grade_encoded"]


def _get_streamlit():
    try:
        import streamlit as st
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Streamlit is required to render mode-view components. "
            "Importing app.src.mode_view does not require Streamlit."
        ) from exc
    return st


def _is_available_frame(frame: pd.DataFrame | None) -> bool:
    return isinstance(frame, pd.DataFrame) and not frame.empty and "load_status" not in frame.columns


def normalize_mode(mode: str | None) -> str:
    """Return a valid payload mode, defaulting to BASIC_FORM."""
    if mode in PAYLOAD_MODES:
        return str(mode)
    return "BASIC_FORM"


def get_mode_display_name(mode: str | None) -> str:
    """Return human-readable mode text."""
    safe_mode = normalize_mode(mode)
    return MODE_DISPLAY_NAMES.get(safe_mode, safe_mode.replace("_", " ").title())


def get_mode_description(mode: str | None) -> str:
    """Return safe copy for a payload mode."""
    safe_mode = normalize_mode(mode)
    return MODE_DESCRIPTIONS.get(safe_mode, "Contract-aware demo input mode.")


def get_basic_form_limitation() -> dict[str, Any]:
    """Return the required Basic Form limitation disclosure."""
    return {
        "mode": "BASIC_FORM",
        "status": "Partial with documented gaps",
        "gap_count": BASIC_FORM_GAP_COUNT,
        "limitation_fields": LIMITATION_FIELDS,
        "notice": BASIC_FORM_LIMITATION_NOTICE,
    }


def summarize_mode_fields(schema_df: pd.DataFrame | None, mode: str) -> dict[str, Any]:
    """Summarize schema rows for a mode without executing validation or inference."""
    safe_mode = normalize_mode(mode)
    summary: dict[str, Any] = {
        "mode": safe_mode,
        "mode_display": get_mode_display_name(safe_mode),
        "field_count": 0,
        "visible_fields": 0,
        "editable_fields": 0,
        "payload_compatible_fields": 0,
        "required_fields": 0,
        "limitation_fields_present": [],
        "schema_available": False,
    }

    if not _is_available_frame(schema_df) or "schema_mode" not in schema_df.columns:
        return summary

    mode_rows = schema_df[schema_df["schema_mode"].astype(str) == safe_mode].copy()
    summary["schema_available"] = True
    summary["field_count"] = int(len(mode_rows))

    boolean_columns = {
        "visible_fields": "is_visible",
        "editable_fields": "is_editable",
        "payload_compatible_fields": "payload_compatible",
        "required_fields": "is_required",
    }
    for output_key, column_name in boolean_columns.items():
        if column_name in mode_rows.columns:
            summary[output_key] = int(mode_rows[column_name].fillna(False).astype(bool).sum())

    if "canonical_feature_name" in mode_rows.columns:
        present_features = set(mode_rows["canonical_feature_name"].dropna().astype(str))
        summary["limitation_fields_present"] = [
            field for field in LIMITATION_FIELDS if field in present_features
        ]

    return summary


def mode_field_table(schema_df: pd.DataFrame | None, mode: str) -> pd.DataFrame:
    """Return a compact display table for fields in one mode."""
    safe_mode = normalize_mode(mode)
    if not _is_available_frame(schema_df) or "schema_mode" not in schema_df.columns:
        return pd.DataFrame(
            {
                "mode": [safe_mode],
                "status": ["not_available"],
                "message": ["Schema contract table is not available."],
            }
        )

    mode_rows = schema_df[schema_df["schema_mode"].astype(str) == safe_mode].copy()
    preferred_columns = [
        "schema_mode",
        "feature_name",
        "canonical_feature_name",
        "entity_type",
        "demo_role",
        "feature_family",
        "governance_tag",
        "acquisition_type",
        "is_required",
        "is_editable",
        "is_visible",
        "payload_compatible",
    ]
    display_columns = [column for column in preferred_columns if column in mode_rows.columns]
    if not display_columns:
        return mode_rows
    return mode_rows[display_columns].reset_index(drop=True)


def mode_readiness_table(mode_readiness_df: pd.DataFrame | None, mode: str) -> pd.DataFrame:
    """Return readiness rows for the selected mode, if the artifact is available."""
    safe_mode = normalize_mode(mode)
    if not _is_available_frame(mode_readiness_df):
        return pd.DataFrame(
            {
                "mode": [safe_mode],
                "status": ["not_available"],
                "message": ["Mode readiness contract table is not available."],
            }
        )

    mode_column = None
    for candidate in ["payload_mode", "schema_mode", "mode"]:
        if candidate in mode_readiness_df.columns:
            mode_column = candidate
            break

    if mode_column is None:
        return mode_readiness_df.copy()

    return mode_readiness_df[
        mode_readiness_df[mode_column].astype(str) == safe_mode
    ].reset_index(drop=True)


def render_mode_selector(default_mode: str = "BASIC_FORM") -> str:
    """Render and return a selected payload mode."""
    st = _get_streamlit()
    safe_default = normalize_mode(default_mode)
    labels = [get_mode_display_name(mode) for mode in PAYLOAD_MODES]
    selected_label = st.radio(
        "Demo Input Mode",
        labels,
        index=PAYLOAD_MODES.index(safe_default),
        horizontal=True,
    )
    label_to_mode = {
        get_mode_display_name(mode): mode
        for mode in PAYLOAD_MODES
    }
    return label_to_mode[selected_label]


def render_basic_form_gap_notice() -> None:
    """Render the required Basic Form limitation notice."""
    st = _get_streamlit()
    limitation = get_basic_form_limitation()
    st.warning(limitation["notice"])
    st.caption(
        "Basic Form status: "
        f"{limitation['status']} | Mapping gaps: {limitation['gap_count']} | "
        f"Limitation fields: {', '.join(limitation['limitation_fields'])}"
    )


def render_mode_summary(
    mode: str,
    schema_df: pd.DataFrame | None = None,
    mode_readiness_df: pd.DataFrame | None = None,
) -> None:
    """Render a safe mode summary without model or decision semantics."""
    st = _get_streamlit()
    safe_mode = normalize_mode(mode)
    summary = summarize_mode_fields(schema_df, safe_mode)

    st.subheader(get_mode_display_name(safe_mode))
    st.write(get_mode_description(safe_mode))

    cols = st.columns(4)
    cols[0].metric("Contract Fields", summary["field_count"])
    cols[1].metric("Visible Fields", summary["visible_fields"])
    cols[2].metric("Editable Fields", summary["editable_fields"])
    cols[3].metric("Payload-Compatible Fields", summary["payload_compatible_fields"])

    if safe_mode == "BASIC_FORM":
        render_basic_form_gap_notice()

    readiness = mode_readiness_table(mode_readiness_df, safe_mode)
    if _is_available_frame(readiness):
        st.dataframe(readiness, use_container_width=True)


def render_mode_field_table(schema_df: pd.DataFrame | None, mode: str) -> None:
    """Render compact schema fields for the selected mode."""
    st = _get_streamlit()
    st.dataframe(mode_field_table(schema_df, mode), use_container_width=True)


def render_mode_limitations(mode: str) -> None:
    """Render mode-level limitations with required Basic Form handling."""
    st = _get_streamlit()
    safe_mode = normalize_mode(mode)
    if safe_mode == "BASIC_FORM":
        render_basic_form_gap_notice()
        return

    st.info(
        "This mode is for contract preview and schema compatibility review only. "
        "It does not run model inference or produce credit decisions."
    )
