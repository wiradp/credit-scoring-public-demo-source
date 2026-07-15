"""Readiness display helpers for the Stage 1 Streamlit skeleton."""

from __future__ import annotations

from typing import Any

import pandas as pd


def readiness_summary_to_frame(summary: dict[str, Any]) -> pd.DataFrame:
    """Convert Stage 0 readiness metadata into a compact display table."""
    rows = [
        ("Stage 0 status", summary.get("stage_0_status")),
        ("Stage 0 ready", summary.get("stage_0_ready")),
        ("Source final status", summary.get("source_final_status")),
        ("Source final verdict", summary.get("source_final_verdict")),
        ("Artifacts specified", summary.get("artifacts_specified")),
        ("Artifacts exported", summary.get("artifacts_exported")),
        ("Read-back checks passed", summary.get("readback_checks_passed")),
        ("Payload modes", summary.get("payload_modes")),
        ("Canonical features", summary.get("canonical_features")),
        ("Basic Form status", summary.get("basic_form_status")),
        ("Basic Form gap count", summary.get("basic_form_gap_count")),
        ("Limitation fields", ", ".join(summary.get("limitation_fields", []))),
        ("Project blocker", summary.get("project_blocker")),
    ]
    return pd.DataFrame(rows, columns=["field", "value"])
