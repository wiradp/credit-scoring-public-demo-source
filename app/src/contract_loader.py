"""Read-only contract loader for the contract-driven demo UI.

This module only reads CSV/JSON artifacts under ``artifacts/contracts``. It
does not load models, explainers, thresholds, parquet data, or prediction
arrays.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .config import (
    ALLOWED_CONTRACT_SUFFIXES,
    BLOCKED_CONTRACT_SUFFIXES,
    CONTRACT_MANIFEST_CSV,
    CONTRACT_MANIFEST_JSON,
    CONTRACT_ROOT,
    STAGE_0_READINESS_REPORT,
)


ARTIFACT_SCHEMA = "schema.canonical_demo_input_schema"
ARTIFACT_WIDGETS = "widgets.widget_contract"
ARTIFACT_VALIDATION = "validation.validation_contract"
ARTIFACT_MAPPING_NORMALIZATION = "mapping.normalization_mapping_contract"
ARTIFACT_MAPPING_PAYLOAD_READINESS = "mapping.payload_readiness_matrix"
ARTIFACT_SAMPLE_CATALOG = "sample_profiles.sample_profile_catalog"
ARTIFACT_SAMPLE_FEATURE_MATRIX = "sample_profiles.sample_profile_feature_matrix"
ARTIFACT_SAMPLE_FEATURE_COVERAGE = "sample_profiles.sample_profile_feature_coverage"
ARTIFACT_SAMPLE_LIMITATIONS = "sample_profiles.sample_profile_limitation_disclosure"
ARTIFACT_SAMPLE_PAYLOAD_READINESS = "sample_profiles.sample_profile_payload_readiness"
ARTIFACT_PAYLOAD_CONTRACT = "payload.demo_payload_contract"
ARTIFACT_PAYLOAD_TEMPLATE = "payload.demo_payload_template"
ARTIFACT_PAYLOAD_FIELD_MATRIX = "payload.demo_payload_field_matrix"
ARTIFACT_PAYLOAD_MODE_READINESS = "payload.demo_payload_mode_readiness"
ARTIFACT_PAYLOAD_PROFILE_MAP = "payload.demo_payload_profile_payload_map"
ARTIFACT_PAYLOAD_LIMITATIONS = "payload.demo_payload_limitation_disclosure"
ARTIFACT_READINESS_CELLS = "readiness.cell_group_7_cell_readiness"
ARTIFACT_READINESS_MODES = "readiness.cell_group_7_mode_readiness"
ARTIFACT_LIMITATION_REGISTER = "readiness.cell_group_7_limitation_register"
ARTIFACT_BOUNDARY_CHECKS = "readiness.cell_group_7_boundary_checks"
ARTIFACT_FINAL_CHECKS = "readiness.cell_group_7_final_checks"
ARTIFACT_FINAL_REPORT = "readiness.cell_group_7_final_readiness_report"


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _project_root() -> Path:
    return CONTRACT_ROOT.parents[1]


def _empty_table(reason: str, artifact_id: str | None = None) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "artifact_id": [artifact_id or "not_available"],
            "load_status": ["not_available"],
            "load_message": [reason],
        }
    )


def load_stage_0_manifest() -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any]]:
    """Load Stage 0 manifest evidence before any contract file access."""
    if not CONTRACT_MANIFEST_CSV.exists():
        raise FileNotFoundError(f"Missing manifest CSV: {CONTRACT_MANIFEST_CSV}")
    if not CONTRACT_MANIFEST_JSON.exists():
        raise FileNotFoundError(f"Missing manifest JSON: {CONTRACT_MANIFEST_JSON}")
    if not STAGE_0_READINESS_REPORT.exists():
        raise FileNotFoundError(f"Missing readiness report: {STAGE_0_READINESS_REPORT}")

    manifest_df = pd.read_csv(CONTRACT_MANIFEST_CSV)
    manifest_json = _read_json(CONTRACT_MANIFEST_JSON)
    readiness_report = _read_json(STAGE_0_READINESS_REPORT)
    return manifest_df, manifest_json, readiness_report


def load_contract_manifest() -> dict[str, Any]:
    """Load required app-level manifest evidence."""
    manifest_df, manifest_json, readiness_report = load_stage_0_manifest()
    return {
        "manifest_df": manifest_df,
        "manifest_json": manifest_json,
        "manifest_report": manifest_json.get("report", {}),
        "readiness_report": readiness_report,
    }


def load_stage0_readiness() -> dict[str, Any]:
    """Load the required Stage 0 readiness report."""
    _, _, readiness_report = load_stage_0_manifest()
    return readiness_report


def validate_manifest_listed_path(project_root: Path, project_relative_path: str) -> Path:
    """Resolve a manifest-listed path with a fail-closed contract-root boundary."""
    candidate = (project_root / project_relative_path).resolve()
    suffix = candidate.suffix.lower()

    if suffix in BLOCKED_CONTRACT_SUFFIXES:
        raise ValueError(f"Blocked contract file suffix: {suffix}")
    if suffix not in ALLOWED_CONTRACT_SUFFIXES:
        raise ValueError(f"Unsupported contract file suffix: {suffix}")
    if not _is_under(candidate, CONTRACT_ROOT):
        raise ValueError(f"Contract path outside allowed root: {candidate}")
    if not candidate.exists():
        raise FileNotFoundError(f"Manifest-listed contract file is missing: {candidate}")

    return candidate


def _manifest_row(manifest_df: pd.DataFrame, artifact_id: str) -> pd.Series | None:
    if "artifact_id" not in manifest_df.columns:
        return None
    matches = manifest_df[manifest_df["artifact_id"].astype(str) == artifact_id]
    if matches.empty:
        return None
    return matches.iloc[0]


def _load_manifest_artifact_payload(row: pd.Series) -> pd.DataFrame | dict[str, Any]:
    project_relative_path = str(row["project_relative_path"])
    file_path = validate_manifest_listed_path(_project_root(), project_relative_path)
    suffix = file_path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(file_path)
    if suffix == ".json":
        return _read_json(file_path)
    raise ValueError(f"Unsupported contract file suffix: {suffix}")


def load_contract_table_by_artifact_id(artifact_id: str, required: bool = False) -> pd.DataFrame:
    """Load a manifest-listed CSV artifact, with optional graceful fallback."""
    manifest_df, _, _ = load_stage_0_manifest()
    row = _manifest_row(manifest_df, artifact_id)
    if row is None:
        message = f"Artifact is not listed in the Stage 0 manifest: {artifact_id}"
        if required:
            raise KeyError(message)
        return _empty_table(message, artifact_id)

    try:
        payload = _load_manifest_artifact_payload(row)
    except Exception as exc:
        if required:
            raise
        return _empty_table(str(exc), artifact_id)

    if isinstance(payload, pd.DataFrame):
        return payload

    if required:
        raise TypeError(f"Expected CSV artifact for {artifact_id}, found JSON")
    return _empty_table(f"Artifact is JSON, not a table: {artifact_id}", artifact_id)


def load_contract_json_by_artifact_id(artifact_id: str, required: bool = False) -> dict[str, Any]:
    """Load a manifest-listed JSON artifact, with optional graceful fallback."""
    manifest_df, _, _ = load_stage_0_manifest()
    row = _manifest_row(manifest_df, artifact_id)
    if row is None:
        message = f"Artifact is not listed in the Stage 0 manifest: {artifact_id}"
        if required:
            raise KeyError(message)
        return {"load_status": "not_available", "load_message": message, "artifact_id": artifact_id}

    try:
        payload = _load_manifest_artifact_payload(row)
    except Exception as exc:
        if required:
            raise
        return {"load_status": "not_available", "load_message": str(exc), "artifact_id": artifact_id}

    if isinstance(payload, dict):
        return payload

    if required:
        raise TypeError(f"Expected JSON artifact for {artifact_id}, found CSV")
    return {
        "load_status": "not_available",
        "load_message": f"Artifact is CSV, not JSON: {artifact_id}",
        "artifact_id": artifact_id,
    }


def load_manifest_listed_contracts(limit_rows: int = 25) -> dict[str, Any]:
    """Load lightweight previews for manifest-listed CSV/JSON contract files."""
    manifest_df, manifest_json, readiness_report = load_stage_0_manifest()
    project_root = _project_root()
    previews: dict[str, Any] = {}

    required_rows = manifest_df[manifest_df["required_export"].astype(bool)].copy()
    for _, row in required_rows.iterrows():
        artifact_id = str(row["artifact_id"])
        file_path = validate_manifest_listed_path(project_root, str(row["project_relative_path"]))

        if file_path.suffix.lower() == ".csv":
            preview_df = pd.read_csv(file_path, nrows=limit_rows)
            previews[artifact_id] = {
                "path": str(file_path.relative_to(project_root)),
                "file_type": "csv",
                "preview_rows": len(preview_df),
                "columns": list(preview_df.columns),
            }
        elif file_path.suffix.lower() == ".json":
            payload = _read_json(file_path)
            previews[artifact_id] = {
                "path": str(file_path.relative_to(project_root)),
                "file_type": "json",
                "top_level_keys": list(payload.keys()) if isinstance(payload, dict) else [],
            }

    return {
        "manifest_rows": len(manifest_df),
        "manifest_report": manifest_json.get("report", {}),
        "readiness_report": readiness_report,
        "contract_previews": previews,
    }


def load_canonical_schema(required: bool = False) -> pd.DataFrame:
    """Load the canonical demo input schema contract."""
    return load_contract_table_by_artifact_id(ARTIFACT_SCHEMA, required=required)


def load_widget_schema(required: bool = False) -> pd.DataFrame:
    """Load widget metadata generated from the canonical schema contract."""
    return load_contract_table_by_artifact_id(ARTIFACT_WIDGETS, required=required)


def load_payload_modes(required: bool = False) -> pd.DataFrame:
    """Load payload mode readiness metadata."""
    mode_readiness = load_contract_table_by_artifact_id(
        ARTIFACT_PAYLOAD_MODE_READINESS,
        required=required,
    )
    if "load_status" not in mode_readiness.columns:
        return mode_readiness

    fallback = load_contract_table_by_artifact_id(ARTIFACT_READINESS_MODES, required=False)
    if "load_status" not in fallback.columns:
        return fallback
    return mode_readiness


def load_mapping_summary() -> dict[str, pd.DataFrame]:
    """Load mapping contracts used for coverage and readiness display."""
    return {
        "normalization_mapping": load_contract_table_by_artifact_id(
            ARTIFACT_MAPPING_NORMALIZATION,
            required=False,
        ),
        "payload_readiness_matrix": load_contract_table_by_artifact_id(
            ARTIFACT_MAPPING_PAYLOAD_READINESS,
            required=False,
        ),
    }


def load_sample_profiles() -> dict[str, pd.DataFrame]:
    """Load sample-profile contract artifacts when available."""
    return {
        "catalog": load_contract_table_by_artifact_id(ARTIFACT_SAMPLE_CATALOG, required=False),
        "feature_matrix": load_contract_table_by_artifact_id(
            ARTIFACT_SAMPLE_FEATURE_MATRIX,
            required=False,
        ),
        "feature_coverage": load_contract_table_by_artifact_id(
            ARTIFACT_SAMPLE_FEATURE_COVERAGE,
            required=False,
        ),
        "limitation_disclosure": load_contract_table_by_artifact_id(
            ARTIFACT_SAMPLE_LIMITATIONS,
            required=False,
        ),
        "payload_readiness": load_contract_table_by_artifact_id(
            ARTIFACT_SAMPLE_PAYLOAD_READINESS,
            required=False,
        ),
    }


def load_payload_contracts() -> dict[str, pd.DataFrame]:
    """Load payload-preview contracts without executing any runtime payload logic."""
    return {
        "contract": load_contract_table_by_artifact_id(ARTIFACT_PAYLOAD_CONTRACT, required=False),
        "template": load_contract_table_by_artifact_id(ARTIFACT_PAYLOAD_TEMPLATE, required=False),
        "field_matrix": load_contract_table_by_artifact_id(
            ARTIFACT_PAYLOAD_FIELD_MATRIX,
            required=False,
        ),
        "mode_readiness": load_payload_modes(required=False),
        "profile_payload_map": load_contract_table_by_artifact_id(
            ARTIFACT_PAYLOAD_PROFILE_MAP,
            required=False,
        ),
        "limitation_disclosure": load_contract_table_by_artifact_id(
            ARTIFACT_PAYLOAD_LIMITATIONS,
            required=False,
        ),
    }


def load_validation_summary() -> pd.DataFrame:
    """Load validation contract metadata for display-only summaries."""
    return load_contract_table_by_artifact_id(ARTIFACT_VALIDATION, required=False)


def load_readiness_artifacts() -> dict[str, pd.DataFrame | dict[str, Any]]:
    """Load readiness and limitation artifacts used by governance UI pages."""
    return {
        "cell_readiness": load_contract_table_by_artifact_id(
            ARTIFACT_READINESS_CELLS,
            required=False,
        ),
        "mode_readiness": load_contract_table_by_artifact_id(
            ARTIFACT_READINESS_MODES,
            required=False,
        ),
        "limitation_register": load_contract_table_by_artifact_id(
            ARTIFACT_LIMITATION_REGISTER,
            required=False,
        ),
        "boundary_checks": load_contract_table_by_artifact_id(
            ARTIFACT_BOUNDARY_CHECKS,
            required=False,
        ),
        "final_checks": load_contract_table_by_artifact_id(ARTIFACT_FINAL_CHECKS, required=False),
        "final_report": load_contract_json_by_artifact_id(ARTIFACT_FINAL_REPORT, required=False),
    }


def load_all_contracts() -> dict[str, Any]:
    """Load contract data with page-level graceful fallbacks."""
    manifest_bundle = load_contract_manifest()
    return {
        **manifest_bundle,
        "readiness_summary": get_contract_readiness_summary(),
        "canonical_schema": load_canonical_schema(required=False),
        "widget_schema": load_widget_schema(required=False),
        "payload_modes": load_payload_modes(required=False),
        "mapping": load_mapping_summary(),
        "sample_profiles": load_sample_profiles(),
        "payload": load_payload_contracts(),
        "validation": load_validation_summary(),
        "readiness": load_readiness_artifacts(),
    }


def get_contract_readiness_summary() -> dict[str, Any]:
    """Return Stage 0 readiness fields for display in the skeleton app."""
    _, manifest_json, readiness_report = load_stage_0_manifest()
    manifest_report = manifest_json.get("report", {})

    return {
        "stage_0_status": readiness_report.get("status"),
        "stage_0_ready": readiness_report.get("ready"),
        "source_cell_group": readiness_report.get("source_cell_group"),
        "source_final_status": readiness_report.get("source_final_status"),
        "source_final_verdict": readiness_report.get("source_final_verdict"),
        "artifacts_specified": readiness_report.get("artifacts_specified"),
        "artifacts_exported": readiness_report.get("artifacts_exported"),
        "readback_checks_passed": readiness_report.get("readback_checks_passed"),
        "manifest_readback_status": manifest_report.get("readback_status"),
        "payload_modes": readiness_report.get("payload_modes"),
        "canonical_features": readiness_report.get("canonical_features"),
        "basic_form_status": readiness_report.get("basic_form_status"),
        "basic_form_gap_count": readiness_report.get("basic_form_gap_count"),
        "limitation_fields": readiness_report.get("limitation_fields", []),
        "project_blocker": readiness_report.get("project_blocker"),
    }
