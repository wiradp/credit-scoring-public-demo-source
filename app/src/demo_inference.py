"""Safe demo inference skeleton for Stage 4.

This module defines the guarded result shape for portfolio-demo inference. It
does not load models, execute ``predict_proba``, apply thresholds, load SHAP,
or import Streamlit.
"""

from __future__ import annotations

import pickle
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


DEMO_INFERENCE_READY = "DEMO_INFERENCE_READY"
DEMO_INFERENCE_BLOCKED_BY_PAYLOAD_GAP = "DEMO_INFERENCE_BLOCKED_BY_PAYLOAD_GAP"
DEMO_INFERENCE_BLOCKED_BY_SCHEMA_ERROR = "DEMO_INFERENCE_BLOCKED_BY_SCHEMA_ERROR"
DEMO_INFERENCE_BLOCKED_BY_MODEL_ARTIFACT_MISSING = (
    "DEMO_INFERENCE_BLOCKED_BY_MODEL_ARTIFACT_MISSING"
)
DEMO_INFERENCE_FAILED_SAFE = "DEMO_INFERENCE_FAILED_SAFE"

DEMO_INFERENCE_STATUSES = [
    DEMO_INFERENCE_READY,
    DEMO_INFERENCE_BLOCKED_BY_PAYLOAD_GAP,
    DEMO_INFERENCE_BLOCKED_BY_SCHEMA_ERROR,
    DEMO_INFERENCE_BLOCKED_BY_MODEL_ARTIFACT_MISSING,
    DEMO_INFERENCE_FAILED_SAFE,
]

MODEL_INPUT_COMPATIBLE = "MODEL_INPUT_COMPATIBLE"
MODEL_INPUT_BLOCKED_MISSING_FEATURES = "MODEL_INPUT_BLOCKED_MISSING_FEATURES"
MODEL_INPUT_BLOCKED_EXTRA_FEATURES = "MODEL_INPUT_BLOCKED_EXTRA_FEATURES"
MODEL_INPUT_BLOCKED_ORDER_UNKNOWN = "MODEL_INPUT_BLOCKED_ORDER_UNKNOWN"
MODEL_INPUT_BLOCKED_DTYPE_ERROR = "MODEL_INPUT_BLOCKED_DTYPE_ERROR"
MODEL_INPUT_BLOCKED_REFERENCE_UNAVAILABLE = "MODEL_INPUT_BLOCKED_REFERENCE_UNAVAILABLE"

MODEL_INPUT_STATUSES = [
    MODEL_INPUT_COMPATIBLE,
    MODEL_INPUT_BLOCKED_MISSING_FEATURES,
    MODEL_INPUT_BLOCKED_EXTRA_FEATURES,
    MODEL_INPUT_BLOCKED_ORDER_UNKNOWN,
    MODEL_INPUT_BLOCKED_DTYPE_ERROR,
    MODEL_INPUT_BLOCKED_REFERENCE_UNAVAILABLE,
]

RISK_SIGNAL_LABEL = "Default-risk signal"
RISK_SIGNAL_BANDS = [
    "LOW_SIGNAL",
    "MEDIUM_SIGNAL",
    "HIGH_SIGNAL",
    "VERY_HIGH_SIGNAL",
]
RISK_SIGNAL_BAND_NOTE = (
    "Risk signal bands are descriptive demo bands for model behavior preview only. "
    "They are not decision thresholds."
)

SAFE_INFERENCE_LABELS = {
    "page_title": "Safe Demo Inference",
    "signal_preview": "Default-Risk Signal Preview",
    "probability_preview": "Demo Probability Preview",
    "behavior_preview": "Model Behavior Preview",
    "guardrails": "Inference Guardrails",
    "limitations": "Limitations",
    "blocked_reason": "Why inference may be blocked",
}

REQUIRED_PAYLOAD_FIELD_COUNT = 49
REQUIRED_PAYLOAD_READINESS_STATUS = "READY_FOR_CONTRACT_PREVIEW"
DEFAULT_MODEL_ARTIFACT_PATH = Path(__file__).resolve().parents[2] / "models" / "final_model_calibrated.pkl"
DEFAULT_FEATURE_MANIFEST_PATH = Path(__file__).resolve().parents[2] / "data" / "splits" / "feature_manifest.json"
PAYLOAD_MODE_BASIC_FORM = "BASIC_FORM"


GUARDRAIL_METADATA_DEFAULTS = {
    "demo_inference_only": True,
    "model_loaded": False,
    "inference_executed": False,
    "predict_proba_executed": False,
    "credit_decision_generated": False,
    "approval_recommendation_generated": False,
    "rejection_recommendation_generated": False,
    "threshold_applied": False,
    "threshold_loaded_for_decisioning": False,
    "credit_score_generated": False,
    "adverse_action_generated": False,
    "shap_loaded": False,
    "shap_executed": False,
    "legal_compliance_claimed": False,
    "fairness_claimed": False,
    "production_ready_claimed": False,
    "safe_failure": False,
    "failure_reason": None,
}


@dataclass(frozen=True)
class DemoInferenceResult:
    """Stage 4 guarded result object for safe demo inference previews."""

    mode: str
    inference_status: str = DEMO_INFERENCE_FAILED_SAFE
    risk_signal: float | None = None
    risk_signal_band: str | None = None
    risk_signal_label: str = RISK_SIGNAL_LABEL
    input_validation: dict[str, Any] = field(default_factory=dict)
    model_input_compatibility: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    limitations: list[dict[str, Any]] = field(default_factory=list)
    readiness_note: str = "Safe demo inference has not been executed."
    error_message: str | None = None


@dataclass(frozen=True)
class ModelArtifactLoadResult:
    """Read-only model artifact load result with fail-safe metadata."""

    model: Any | None = None
    model_path: str | None = None
    model_loaded: bool = False
    model_available: bool = False
    has_predict_proba: bool = False
    load_status: str = DEMO_INFERENCE_BLOCKED_BY_MODEL_ARTIFACT_MISSING
    metadata: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None


@dataclass(frozen=True)
class FeatureManifestLoadResult:
    """Read-only feature manifest load result for model input validation."""

    feature_names: list[str] = field(default_factory=list)
    manifest_path: str | None = None
    manifest_loaded: bool = False
    manifest_valid: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None


def guardrail_metadata(
    *,
    model_loaded: bool = False,
    inference_executed: bool = False,
    predict_proba_executed: bool = False,
    safe_failure: bool = False,
    failure_reason: str | None = None,
) -> dict[str, Any]:
    """Return fresh Stage 4 guardrail metadata with no decisioning claims."""
    metadata = dict(GUARDRAIL_METADATA_DEFAULTS)
    metadata.update(
        {
            "model_loaded": bool(model_loaded),
            "inference_executed": bool(inference_executed),
            "predict_proba_executed": bool(predict_proba_executed),
            "safe_failure": bool(safe_failure),
            "failure_reason": failure_reason,
        }
    )
    return metadata


def _model_loader_metadata(
    *,
    model_path: Path,
    model_loaded: bool = False,
    model_available: bool = False,
    has_predict_proba: bool = False,
    load_status: str = DEMO_INFERENCE_BLOCKED_BY_MODEL_ARTIFACT_MISSING,
    failure_reason: str | None = None,
    model_class: str | None = None,
) -> dict[str, Any]:
    """Return model-loader metadata while preserving no-inference guardrails."""
    metadata = guardrail_metadata(
        model_loaded=model_loaded,
        inference_executed=False,
        predict_proba_executed=False,
        safe_failure=not model_loaded,
        failure_reason=failure_reason,
    )
    metadata.update(
        {
            "model_artifact_path": str(model_path),
            "model_artifact_available": bool(model_available),
            "has_predict_proba": bool(has_predict_proba),
            "model_class": model_class,
            "model_load_status": load_status,
            "threshold_loaded_for_decisioning": False,
            "shap_loaded": False,
            "shap_executed": False,
        }
    )
    return metadata


def model_artifact_path(path: str | Path | None = None) -> Path:
    """Resolve the configured read-only model artifact path."""
    return Path(path).expanduser().resolve() if path is not None else DEFAULT_MODEL_ARTIFACT_PATH


def feature_manifest_path(path: str | Path | None = None) -> Path:
    """Resolve the configured read-only feature manifest path."""
    return Path(path).expanduser().resolve() if path is not None else DEFAULT_FEATURE_MANIFEST_PATH


def load_model_artifact(path: str | Path | None = None) -> ModelArtifactLoadResult:
    """Load the demo model artifact read-only without executing inference.

    The loader intentionally does not import SHAP, read threshold artifacts, or
    call prediction methods. Dependency and pickle failures are converted into
    safe blocked results for UI display.
    """
    resolved_path = model_artifact_path(path)

    if not resolved_path.exists() or not resolved_path.is_file():
        error_message = f"Model artifact is not available: {resolved_path}"
        metadata = _model_loader_metadata(
            model_path=resolved_path,
            model_available=False,
            load_status=DEMO_INFERENCE_BLOCKED_BY_MODEL_ARTIFACT_MISSING,
            failure_reason="MODEL_ARTIFACT_MISSING",
        )
        return ModelArtifactLoadResult(
            model_path=str(resolved_path),
            load_status=DEMO_INFERENCE_BLOCKED_BY_MODEL_ARTIFACT_MISSING,
            metadata=metadata,
            error_message=error_message,
        )

    try:
        with resolved_path.open("rb") as file:
            model = pickle.load(file)
    except (ModuleNotFoundError, ImportError) as exc:
        error_message = f"Model artifact dependency is unavailable: {exc}"
        metadata = _model_loader_metadata(
            model_path=resolved_path,
            model_available=True,
            load_status=DEMO_INFERENCE_FAILED_SAFE,
            failure_reason="MODEL_ARTIFACT_IMPORT_ERROR",
        )
        return ModelArtifactLoadResult(
            model_path=str(resolved_path),
            model_available=True,
            load_status=DEMO_INFERENCE_FAILED_SAFE,
            metadata=metadata,
            error_message=error_message,
        )
    except (pickle.PickleError, EOFError, AttributeError, ValueError, TypeError, OSError) as exc:
        error_message = f"Model artifact could not be loaded safely: {exc}"
        metadata = _model_loader_metadata(
            model_path=resolved_path,
            model_available=True,
            load_status=DEMO_INFERENCE_FAILED_SAFE,
            failure_reason="MODEL_ARTIFACT_LOAD_ERROR",
        )
        return ModelArtifactLoadResult(
            model_path=str(resolved_path),
            model_available=True,
            load_status=DEMO_INFERENCE_FAILED_SAFE,
            metadata=metadata,
            error_message=error_message,
        )

    has_predict_proba = callable(getattr(model, "predict_proba", None))
    model_class = type(model).__name__
    if not has_predict_proba:
        error_message = (
            "Loaded model object is unsupported for demo inference because it "
            "does not expose a callable predict_proba method."
        )
        metadata = _model_loader_metadata(
            model_path=resolved_path,
            model_available=True,
            model_loaded=False,
            has_predict_proba=False,
            load_status=DEMO_INFERENCE_FAILED_SAFE,
            failure_reason="UNSUPPORTED_MODEL_OBJECT_WITHOUT_PREDICT_PROBA",
            model_class=model_class,
        )
        return ModelArtifactLoadResult(
            model_path=str(resolved_path),
            model_available=True,
            has_predict_proba=False,
            load_status=DEMO_INFERENCE_FAILED_SAFE,
            metadata=metadata,
            error_message=error_message,
        )

    metadata = _model_loader_metadata(
        model_path=resolved_path,
        model_available=True,
        model_loaded=True,
        has_predict_proba=True,
        load_status=DEMO_INFERENCE_READY,
        failure_reason=None,
        model_class=model_class,
    )
    return ModelArtifactLoadResult(
        model=model,
        model_path=str(resolved_path),
        model_loaded=True,
        model_available=True,
        has_predict_proba=True,
        load_status=DEMO_INFERENCE_READY,
        metadata=metadata,
    )


def load_feature_manifest(path: str | Path | None = None) -> FeatureManifestLoadResult:
    """Load expected model feature names from the read-only feature manifest."""
    resolved_path = feature_manifest_path(path)
    base_metadata = {
        "feature_manifest_path": str(resolved_path),
        "feature_manifest_loaded": False,
        "feature_manifest_valid": False,
        "expected_feature_count": 0,
        "expected_feature_names_unique": False,
    }

    if not resolved_path.exists() or not resolved_path.is_file():
        return FeatureManifestLoadResult(
            manifest_path=str(resolved_path),
            metadata=base_metadata,
            error_message=f"Feature manifest is not available: {resolved_path}",
        )

    try:
        with resolved_path.open("r", encoding="utf-8") as file:
            manifest = json.load(file)
    except (json.JSONDecodeError, OSError) as exc:
        return FeatureManifestLoadResult(
            manifest_path=str(resolved_path),
            manifest_loaded=False,
            metadata=base_metadata,
            error_message=f"Feature manifest could not be loaded safely: {exc}",
        )

    feature_names = manifest.get("feature_cols")
    n_features = manifest.get("n_features")
    valid_list = isinstance(feature_names, list) and all(
        isinstance(feature_name, str) and bool(feature_name)
        for feature_name in feature_names
    )
    unique_names = valid_list and len(set(feature_names)) == len(feature_names)
    count_matches = valid_list and len(feature_names) == REQUIRED_PAYLOAD_FIELD_COUNT
    declared_count_matches = n_features in {None, REQUIRED_PAYLOAD_FIELD_COUNT}
    manifest_valid = bool(valid_list and unique_names and count_matches and declared_count_matches)

    metadata = {
        **base_metadata,
        "feature_manifest_loaded": True,
        "feature_manifest_valid": manifest_valid,
        "expected_feature_count": len(feature_names) if isinstance(feature_names, list) else 0,
        "declared_n_features": n_features,
        "expected_feature_names_unique": unique_names,
        "feature_count_matches_required": count_matches,
        "declared_count_matches_required": declared_count_matches,
    }
    if not manifest_valid:
        return FeatureManifestLoadResult(
            manifest_path=str(resolved_path),
            manifest_loaded=True,
            manifest_valid=False,
            metadata=metadata,
            error_message=(
                "Feature manifest must provide unique feature_cols with "
                f"{REQUIRED_PAYLOAD_FIELD_COUNT} items."
            ),
        )

    return FeatureManifestLoadResult(
        feature_names=list(feature_names),
        manifest_path=str(resolved_path),
        manifest_loaded=True,
        manifest_valid=True,
        metadata=metadata,
    )


def _sequence_from_model_feature_metadata(value: Any) -> list[str] | None:
    """Return a string sequence from model feature metadata, if available."""
    if value is None:
        return None
    if isinstance(value, str):
        return [value]
    try:
        return [str(item) for item in list(value)]
    except TypeError:
        return None


def extract_model_feature_metadata(model: Any) -> dict[str, list[str]]:
    """Extract model feature-name metadata without executing prediction."""
    sources: dict[str, list[str]] = {}

    feature_names_in = _sequence_from_model_feature_metadata(
        getattr(model, "feature_names_in_", None)
    )
    if feature_names_in:
        sources["model.feature_names_in_"] = feature_names_in

    feature_name_attr = _sequence_from_model_feature_metadata(
        getattr(model, "feature_name_", None)
    )
    if feature_name_attr:
        sources["model.feature_name_"] = feature_name_attr

    if hasattr(model, "get_booster"):
        try:
            booster = model.get_booster()
            booster_features = _sequence_from_model_feature_metadata(
                getattr(booster, "feature_names", None)
            )
            if booster_features:
                sources["model.get_booster().feature_names"] = booster_features
        except Exception:
            pass

    booster_attr = getattr(model, "booster_", None)
    if booster_attr is not None and hasattr(booster_attr, "feature_name"):
        try:
            booster_attr_features = _sequence_from_model_feature_metadata(
                booster_attr.feature_name()
            )
            if booster_attr_features:
                sources["model.booster_.feature_name()"] = booster_attr_features
        except Exception:
            pass

    for attr_name in ["estimator", "base_estimator"]:
        nested_model = getattr(model, attr_name, None)
        nested_features = _sequence_from_model_feature_metadata(
            getattr(nested_model, "feature_names_in_", None)
        )
        if nested_features:
            sources[f"model.{attr_name}.feature_names_in_"] = nested_features

    return sources


def compare_model_feature_metadata(
    *,
    expected_features: list[str],
    model: Any | None = None,
) -> dict[str, Any]:
    """Compare model feature metadata against manifest features when available."""
    if model is None:
        return {
            "model_feature_metadata_available": False,
            "model_feature_metadata_conflict": False,
            "model_feature_metadata_sources": [],
            "model_feature_metadata_note": "Model object is not loaded for metadata comparison.",
        }

    sources = extract_model_feature_metadata(model)
    comparisons = []
    conflict_sources = []
    for source_name, feature_names in sources.items():
        same_names = set(feature_names) == set(expected_features)
        same_order = feature_names == expected_features
        comparison = {
            "source": source_name,
            "feature_count": len(feature_names),
            "matches_manifest_names": same_names,
            "matches_manifest_order": same_order,
            "missing_expected_count": len([name for name in expected_features if name not in feature_names]),
            "extra_model_feature_count": len([name for name in feature_names if name not in expected_features]),
        }
        comparisons.append(comparison)
        if not same_names or not same_order:
            conflict_sources.append(source_name)

    return {
        "model_feature_metadata_available": bool(sources),
        "model_feature_metadata_conflict": bool(conflict_sources),
        "model_feature_metadata_sources": list(sources.keys()),
        "model_feature_metadata_comparisons": comparisons,
        "conflict_sources": conflict_sources,
    }


def _is_missing_payload_value(value: Any) -> bool:
    """Return whether a payload value is unsafe for model input validation."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() in {
            "",
            "<missing>",
            "<mapping_gap>",
            "<contract_placeholder>",
            "<not_available>",
            "<contract_only>",
        }
    try:
        return bool(value != value)
    except Exception:
        return False


def _safe_numeric_value(value: Any) -> tuple[bool, float | int | None]:
    """Return whether a payload value can be safely converted for model input."""
    if isinstance(value, bool):
        return True, int(value)
    if isinstance(value, int):
        return True, value
    if isinstance(value, float):
        if _is_missing_payload_value(value):
            return False, None
        return True, value
    if isinstance(value, str):
        stripped = value.strip()
        if _is_missing_payload_value(stripped):
            return False, None
        try:
            return True, float(stripped)
        except ValueError:
            return False, None
    if hasattr(value, "item"):
        try:
            return _safe_numeric_value(value.item())
        except Exception:
            return False, None
    return False, None


def validate_model_input_compatibility(
    *,
    payload: dict[str, Any],
    feature_manifest_path_override: str | Path | None = None,
    model: Any | None = None,
) -> dict[str, Any]:
    """Validate payload keys, order, and dtypes against the feature manifest."""
    manifest_result = load_feature_manifest(feature_manifest_path_override)
    if not manifest_result.manifest_valid:
        return {
            "status": MODEL_INPUT_BLOCKED_REFERENCE_UNAVAILABLE,
            "compatible": False,
            "feature_manifest": manifest_result.metadata,
            "error_message": manifest_result.error_message,
        }

    expected_features = manifest_result.feature_names
    payload_keys = list(payload.keys())
    missing_features = [feature for feature in expected_features if feature not in payload]
    extra_features = [feature for feature in payload_keys if feature not in set(expected_features)]

    if missing_features:
        return {
            "status": MODEL_INPUT_BLOCKED_MISSING_FEATURES,
            "compatible": False,
            "feature_manifest": manifest_result.metadata,
            "expected_feature_count": len(expected_features),
            "payload_feature_count": len(payload_keys),
            "missing_features": missing_features,
            "extra_features": extra_features,
            "error_message": "Payload is missing required model features.",
        }

    if extra_features:
        return {
            "status": MODEL_INPUT_BLOCKED_EXTRA_FEATURES,
            "compatible": False,
            "feature_manifest": manifest_result.metadata,
            "expected_feature_count": len(expected_features),
            "payload_feature_count": len(payload_keys),
            "missing_features": missing_features,
            "extra_features": extra_features,
            "error_message": "Payload includes unsafe extra model-input fields.",
        }

    dtype_errors = []
    ordered_values: list[float | int] = []
    for feature_name in expected_features:
        value = payload.get(feature_name)
        ok, converted = _safe_numeric_value(value)
        if not ok:
            dtype_errors.append({"feature": feature_name, "value_type": type(value).__name__})
            continue
        ordered_values.append(converted)

    if dtype_errors:
        return {
            "status": MODEL_INPUT_BLOCKED_DTYPE_ERROR,
            "compatible": False,
            "feature_manifest": manifest_result.metadata,
            "expected_feature_count": len(expected_features),
            "payload_feature_count": len(payload_keys),
            "missing_features": [],
            "extra_features": [],
            "dtype_error_count": len(dtype_errors),
            "dtype_errors": dtype_errors[:10],
            "error_message": "Payload values are not safely numeric-convertible.",
        }

    model_metadata = compare_model_feature_metadata(
        expected_features=expected_features,
        model=model,
    )
    if model_metadata.get("model_feature_metadata_conflict"):
        return {
            "status": MODEL_INPUT_BLOCKED_ORDER_UNKNOWN,
            "compatible": False,
            "feature_manifest": manifest_result.metadata,
            "expected_feature_count": len(expected_features),
            "payload_feature_count": len(payload_keys),
            "missing_features": [],
            "extra_features": [],
            "model_feature_metadata": model_metadata,
            "error_message": "Model feature metadata conflicts with feature_manifest.",
        }

    return {
        "status": MODEL_INPUT_COMPATIBLE,
        "compatible": True,
        "feature_manifest": manifest_result.metadata,
        "expected_feature_count": len(expected_features),
        "payload_feature_count": len(payload_keys),
        "missing_features": [],
        "extra_features": [],
        "dtype_error_count": 0,
        "feature_order_source": "feature_manifest.feature_cols",
        "ordered_features": list(expected_features),
        "ordered_values": ordered_values,
        "model_feature_metadata": model_metadata,
    }


def blocked_demo_inference_result(
    *,
    mode: str,
    inference_status: str,
    readiness_note: str,
    error_message: str | None = None,
    input_validation: dict[str, Any] | None = None,
    model_input_compatibility: dict[str, Any] | None = None,
    limitations: list[dict[str, Any]] | None = None,
    failure_reason: str | None = None,
) -> DemoInferenceResult:
    """Return a fail-safe blocked result without executing inference."""
    return DemoInferenceResult(
        mode=mode,
        inference_status=inference_status,
        input_validation=input_validation or {},
        model_input_compatibility=model_input_compatibility or {},
        metadata=guardrail_metadata(
            safe_failure=True,
            failure_reason=failure_reason or error_message or inference_status,
        ),
        limitations=limitations or [],
        readiness_note=readiness_note,
        error_message=error_message,
    )


def validate_payload_for_demo_inference(
    payload_result: Any,
    *,
    feature_manifest_path_override: str | Path | None = None,
    model: Any | None = None,
) -> DemoInferenceResult:
    """Validate a Stage 3 payload result before demo inference."""
    mode = str(getattr(payload_result, "mode", "UNKNOWN"))
    payload = getattr(payload_result, "payload", {}) or {}
    coverage = getattr(payload_result, "coverage", {}) or {}
    readiness_status = str(getattr(payload_result, "readiness_status", "UNKNOWN"))

    payload_field_count = int(coverage.get("payload_field_count", len(payload)) or 0)
    mapping_gap_count = int(coverage.get("mapping_gap_count", 0) or 0)
    missing_required_count = int(coverage.get("missing_required_count", 0) or 0)
    input_validation = {
        "mode": mode,
        "payload_readiness_status": readiness_status,
        "payload_field_count": payload_field_count,
        "required_payload_field_count": REQUIRED_PAYLOAD_FIELD_COUNT,
        "mapping_gap_count": mapping_gap_count,
        "missing_required_count": missing_required_count,
        "payload_readiness_required": REQUIRED_PAYLOAD_READINESS_STATUS,
    }

    if mode == PAYLOAD_MODE_BASIC_FORM:
        input_validation["blocked_reason"] = "BASIC_FORM_PARTIAL_SOURCE_INPUT_WITH_MAPPING_GAPS"
        return blocked_demo_inference_result(
            mode=mode,
            inference_status=DEMO_INFERENCE_BLOCKED_BY_PAYLOAD_GAP,
            readiness_note="BASIC_FORM is blocked from demo inference because it has documented mapping gaps.",
            input_validation=input_validation,
            limitations=list(getattr(payload_result, "limitations", []) or []),
            failure_reason="BASIC_FORM_MAPPING_GAP_BLOCK",
        )

    blocking_reasons = []
    if readiness_status != REQUIRED_PAYLOAD_READINESS_STATUS:
        blocking_reasons.append("PAYLOAD_READINESS_NOT_READY_FOR_CONTRACT_PREVIEW")
    if payload_field_count != REQUIRED_PAYLOAD_FIELD_COUNT:
        blocking_reasons.append("PAYLOAD_FIELD_COUNT_MISMATCH")
    if mapping_gap_count != 0:
        blocking_reasons.append("MAPPING_GAP_COUNT_NONZERO")
    if missing_required_count != 0:
        blocking_reasons.append("MISSING_REQUIRED_COUNT_NONZERO")

    if blocking_reasons:
        input_validation["blocking_reasons"] = blocking_reasons
        return blocked_demo_inference_result(
            mode=mode,
            inference_status=DEMO_INFERENCE_BLOCKED_BY_SCHEMA_ERROR,
            readiness_note="Payload is not ready for safe demo inference.",
            input_validation=input_validation,
            limitations=list(getattr(payload_result, "limitations", []) or []),
            failure_reason="PAYLOAD_SCHEMA_VALIDATION_BLOCK",
        )

    model_input_compatibility = validate_model_input_compatibility(
        payload=payload,
        feature_manifest_path_override=feature_manifest_path_override,
        model=model,
    )
    if not model_input_compatibility.get("compatible"):
        return blocked_demo_inference_result(
            mode=mode,
            inference_status=DEMO_INFERENCE_BLOCKED_BY_SCHEMA_ERROR,
            readiness_note="Payload is blocked because model input compatibility was not proven.",
            input_validation=input_validation,
            model_input_compatibility=model_input_compatibility,
            limitations=list(getattr(payload_result, "limitations", []) or []),
            error_message=str(model_input_compatibility.get("error_message")),
            failure_reason=str(model_input_compatibility.get("status")),
        )

    return DemoInferenceResult(
        mode=mode,
        inference_status=DEMO_INFERENCE_READY,
        input_validation={**input_validation, "blocking_reasons": []},
        model_input_compatibility=model_input_compatibility,
        metadata=guardrail_metadata(),
        limitations=list(getattr(payload_result, "limitations", []) or []),
        readiness_note="Payload passed Stage 4 validation for safe demo inference.",
    )


def _has_blocking_model_input_issue(model_input_compatibility: dict[str, Any]) -> bool:
    """Return whether compatibility metadata contains any blocking issue."""
    return bool(
        model_input_compatibility.get("status") != MODEL_INPUT_COMPATIBLE
        or not model_input_compatibility.get("compatible")
        or model_input_compatibility.get("dtype_error_count", 0) != 0
        or model_input_compatibility.get("missing_features")
        or model_input_compatibility.get("extra_features")
    )


def _is_ready_for_predict_proba(validation_result: DemoInferenceResult) -> bool:
    """Return whether every Stage 4 precondition for predict_proba is satisfied."""
    compatibility = validation_result.model_input_compatibility
    ordered_features = compatibility.get("ordered_features")
    ordered_values = compatibility.get("ordered_values")
    return bool(
        validation_result.inference_status == DEMO_INFERENCE_READY
        and compatibility.get("status") == MODEL_INPUT_COMPATIBLE
        and isinstance(ordered_features, list)
        and isinstance(ordered_values, list)
        and len(ordered_features) == REQUIRED_PAYLOAD_FIELD_COUNT
        and len(ordered_values) == REQUIRED_PAYLOAD_FIELD_COUNT
        and not _has_blocking_model_input_issue(compatibility)
    )


def _model_input_frame(
    *,
    ordered_features: list[str],
    ordered_values: list[float | int],
) -> Any:
    """Return a one-row model input frame if pandas is available, else a matrix.

    pandas preserves column names for models that validate feature names. The
    fallback matrix is only used when pandas is unavailable and the loaded model
    accepts array-like input.
    """
    try:
        import pandas as pd
    except ModuleNotFoundError:
        return [ordered_values]
    except ImportError:
        return [ordered_values]
    return pd.DataFrame([ordered_values], columns=ordered_features)


def _extract_default_risk_signal(probability_output: Any) -> float:
    """Extract the positive-class probability from a predict_proba output."""
    try:
        rows = probability_output.tolist()
    except AttributeError:
        rows = probability_output

    if not rows:
        raise ValueError("predict_proba returned an empty output.")
    first_row = rows[0]
    try:
        row_values = list(first_row)
    except TypeError as exc:
        raise ValueError("predict_proba output is not row-like.") from exc

    if len(row_values) < 2:
        raise ValueError("predict_proba output does not include a positive-class column.")

    signal = float(row_values[1])
    if signal < 0.0 or signal > 1.0:
        raise ValueError("predict_proba output is outside the expected probability range.")
    return signal


def _blocked_model_result(
    *,
    mode: str,
    model_load_result: ModelArtifactLoadResult,
    input_validation: dict[str, Any] | None = None,
    model_input_compatibility: dict[str, Any] | None = None,
    limitations: list[dict[str, Any]] | None = None,
) -> DemoInferenceResult:
    """Return a safe blocked result for model artifact failures."""
    failure_reason = str(model_load_result.metadata.get("failure_reason") or model_load_result.load_status)
    inference_status = (
        DEMO_INFERENCE_BLOCKED_BY_MODEL_ARTIFACT_MISSING
        if model_load_result.load_status == DEMO_INFERENCE_BLOCKED_BY_MODEL_ARTIFACT_MISSING
        else DEMO_INFERENCE_FAILED_SAFE
    )
    return blocked_demo_inference_result(
        mode=mode,
        inference_status=inference_status,
        readiness_note="Model artifact is not available for safe demo inference.",
        input_validation=input_validation,
        model_input_compatibility=model_input_compatibility,
        limitations=limitations,
        error_message=model_load_result.error_message,
        failure_reason=failure_reason,
    )


def assign_risk_signal_band(risk_signal: float | int) -> str:
    """Assign a descriptive demo band without applying a decision threshold."""
    signal = float(risk_signal)
    if signal < 0.0 or signal > 1.0:
        raise ValueError("Risk signal must be within the 0.0 to 1.0 preview range.")
    if signal < 0.20:
        return "LOW_SIGNAL"
    if signal < 0.40:
        return "MEDIUM_SIGNAL"
    if signal < 0.65:
        return "HIGH_SIGNAL"
    return "VERY_HIGH_SIGNAL"


def format_risk_signal(risk_signal: float | int | None) -> dict[str, Any]:
    """Return safe display metadata for a default-risk signal preview."""
    if risk_signal is None:
        return {
            "risk_signal": None,
            "risk_signal_display": "Not available",
            "risk_signal_band": None,
            "risk_signal_label": RISK_SIGNAL_LABEL,
            "risk_signal_band_note": RISK_SIGNAL_BAND_NOTE,
            "band_is_decision_threshold": False,
        }

    signal = float(risk_signal)
    band = assign_risk_signal_band(signal)
    return {
        "risk_signal": signal,
        "risk_signal_display": f"{signal:.3f}",
        "risk_signal_band": band,
        "risk_signal_label": RISK_SIGNAL_LABEL,
        "risk_signal_band_note": RISK_SIGNAL_BAND_NOTE,
        "band_is_decision_threshold": False,
    }


def run_safe_demo_inference(
    payload_result: Any,
    *,
    model_path: str | Path | None = None,
    feature_manifest_path_override: str | Path | None = None,
) -> DemoInferenceResult:
    """Run guarded demo predict_proba only after all Stage 4 checks pass.

    This function does not apply thresholds, generate decisions, load SHAP, or
    produce explanations. It only returns a default-risk signal preview when all
    input, model, and guardrail checks pass.
    """
    mode = str(getattr(payload_result, "mode", "UNKNOWN"))
    model_load_result = load_model_artifact(model_path)
    if not (
        model_load_result.model_loaded
        and model_load_result.has_predict_proba
        and model_load_result.model is not None
    ):
        return _blocked_model_result(
            mode=mode,
            model_load_result=model_load_result,
            limitations=list(getattr(payload_result, "limitations", []) or []),
        )

    validation_result = validate_payload_for_demo_inference(
        payload_result,
        feature_manifest_path_override=feature_manifest_path_override,
        model=model_load_result.model,
    )
    if not _is_ready_for_predict_proba(validation_result):
        return validation_result

    compatibility = validation_result.model_input_compatibility
    ordered_features = compatibility["ordered_features"]
    ordered_values = compatibility["ordered_values"]
    model_input = _model_input_frame(
        ordered_features=ordered_features,
        ordered_values=ordered_values,
    )

    try:
        probability_output = model_load_result.model.predict_proba(model_input)
        risk_signal = _extract_default_risk_signal(probability_output)
    except Exception as exc:
        return blocked_demo_inference_result(
            mode=mode,
            inference_status=DEMO_INFERENCE_FAILED_SAFE,
            readiness_note="Safe demo inference failed before producing a preview.",
            input_validation=validation_result.input_validation,
            model_input_compatibility=compatibility,
            limitations=validation_result.limitations,
            error_message=f"predict_proba failed safely: {exc}",
            failure_reason="PREDICT_PROBA_FAILED_SAFE",
        )

    metadata = guardrail_metadata(
        model_loaded=True,
        inference_executed=True,
        predict_proba_executed=True,
        safe_failure=False,
        failure_reason=None,
    )
    metadata.update(
        {
            "model_artifact_path": model_load_result.model_path,
            "model_load_status": model_load_result.load_status,
            "feature_order_source": compatibility.get("feature_order_source"),
            "model_input_feature_count": len(ordered_features),
            "risk_signal_band_note": RISK_SIGNAL_BAND_NOTE,
            "risk_signal_band_is_decision_threshold": False,
        }
    )
    risk_signal_display = format_risk_signal(risk_signal)
    return DemoInferenceResult(
        mode=mode,
        inference_status=DEMO_INFERENCE_READY,
        risk_signal=risk_signal,
        risk_signal_band=str(risk_signal_display["risk_signal_band"]),
        risk_signal_label=RISK_SIGNAL_LABEL,
        input_validation=validation_result.input_validation,
        model_input_compatibility=compatibility,
        metadata=metadata,
        limitations=validation_result.limitations,
        readiness_note="Safe demo inference produced a default-risk signal preview.",
    )


def demo_inference_result_to_dict(result: DemoInferenceResult) -> dict[str, Any]:
    """Return a JSON-friendly dictionary for UI rendering and tests."""
    return asdict(result)
