"""Fail-closed controlled local inference adapter for the portfolio demo.

Only committed SAMPLE_PROFILE fixtures are authorized in Stage 9 Step 4. Model
loading is fixed-path, integrity-gated, lazy, and limited to one cached runtime.
"""

from __future__ import annotations

import hashlib
import csv
import json
import math
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

import joblib
import numpy as np
import pandas as pd


AVAILABLE = "available"
UNAVAILABLE = "unavailable"
DEMO_INFERENCE_READY = AVAILABLE
DEMO_INFERENCE_BLOCKED_BY_PAYLOAD_GAP = UNAVAILABLE
DEMO_INFERENCE_BLOCKED_BY_SCHEMA_ERROR = UNAVAILABLE
DEMO_INFERENCE_BLOCKED_BY_MODEL_ARTIFACT_MISSING = UNAVAILABLE
DEMO_INFERENCE_FAILED_SAFE = UNAVAILABLE
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

RISK_SIGNAL_LABEL = "Estimated default-risk probability"
RISK_SIGNAL_BANDS = [
    "Below the model operating threshold",
    "At or above the model operating threshold",
]
RISK_SIGNAL_BAND_NOTE = "This is a model operating-threshold relation, not a lending decision or risk band."
SAFE_INFERENCE_LABELS = {
    "page_title": "Safe Demo Inference",
    "signal_preview": "Default-Risk Signal Preview",
    "probability_preview": "Calibrated Probability Preview",
    "behavior_preview": "Model Behavior Preview",
    "guardrails": "Inference Guardrails",
    "limitations": "Limitations",
    "blocked_reason": "Why inference may be blocked",
}

REQUIRED_PAYLOAD_FIELD_COUNT = 49
REQUIRED_PAYLOAD_READINESS_STATUS = "READY_FOR_CONTRACT_PREVIEW"
PAYLOAD_MODE_BASIC_FORM = "BASIC_FORM"
AUTHORIZED_MODE = "SAMPLE_PROFILE"
MODEL_SHA256 = "b022b545bd7bb4294018a26a7d10af977e3c452b7f219dbdd9113adeac367cbf"
MODEL_SIZE = 4_881_685
THRESHOLD_SHA256 = "e45a19822f77d6b74cf5e76c0c0e6ff2f993bad4ab91e507509b3d74d410e28b"
THRESHOLD_SIZE = 96
EXPECTED_THRESHOLD = 0.1
THRESHOLD_TOLERANCE = 1e-12
PURPOSE_FEATURE = "purpose"
PURPOSE_CATEGORIES = (
    "car", "credit_card", "debt_consolidation", "educational", "home_improvement",
    "house", "major_purchase", "medical", "moving", "other", "renewable_energy",
    "small_business", "vacation", "wedding",
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "artifacts/model/final_model_calibrated.pkl"
THRESHOLD_PATH = PROJECT_ROOT / "artifacts/model/final_threshold.json"
MODEL_MANIFEST_PATH = PROJECT_ROOT / "artifacts/model/model_artifact_manifest.json"
PUBLIC_CONTRACT_PATH = PROJECT_ROOT / "outputs/stage9/stage9_public_inference_contract.json"
REPAIR_CONTRACT_PATH = PROJECT_ROOT / "outputs/stage9/stage9_sample_profile_categorical_repair_contract.json"
PROFILE_MATRIX_PATH = PROJECT_ROOT / "artifacts/contracts/cell_group_7/sample_profiles/sample_profile_feature_matrix.csv"
PROFILE_CATALOG_PATH = PROJECT_ROOT / "artifacts/contracts/cell_group_7/sample_profiles/sample_profile_catalog.csv"
PROFILE_READINESS_PATH = PROJECT_ROOT / "artifacts/contracts/cell_group_7/sample_profiles/sample_profile_payload_readiness.csv"
PROFILE_COVERAGE_PATH = PROJECT_ROOT / "artifacts/contracts/cell_group_7/sample_profiles/sample_profile_feature_coverage.csv"
PROFILE_MATRIX_SIZE = 89_769
PROFILE_MATRIX_SHA256 = "c16f1786900ae0ec7878aac2dbc87018c34de459ae9a36dfabf0a43ca92f1bd6"
AUTHORIZED_PROFILE_IDS = (
    "SP_LOW_RISK_SIGNAL",
    "SP_MEDIUM_RISK_SIGNAL",
    "SP_HIGHER_RISK_SIGNAL",
    "SP_MIXED_SIGNAL",
    "SP_LIMITATION_TRANSPARENCY",
)
LIMITATION_AWARE_FEATURES = ("grade_encoded", "credit_age_months")
DEFAULT_MODEL_ARTIFACT_PATH = MODEL_PATH
DEFAULT_FEATURE_MANIFEST_PATH = MODEL_MANIFEST_PATH

FAILURE_MESSAGES = {
    "MODE_NOT_AUTHORIZED_FOR_STEP4": "This input mode is not authorized for controlled Stage 4 inference.",
    "PATH_OVERRIDE_REJECTED": "Runtime path overrides are not permitted.",
    "SAMPLE_PROFILE_ID_REQUIRED": "A committed synthetic profile identifier is required.",
    "SAMPLE_PROFILE_ID_INVALID": "The synthetic profile identifier is not authorized.",
    "SAMPLE_PROFILE_ID_CONFLICT": "Conflicting synthetic profile identifiers were supplied.",
    "SAMPLE_PROFILE_NOT_READY": "The committed synthetic profile is not ready for controlled inference.",
    "SAMPLE_PROFILE_CONTRACT_INVALID": "The committed synthetic profile contract could not be verified.",
    "SAMPLE_PROFILE_PAYLOAD_MISMATCH": "The supplied payload does not match the committed synthetic profile.",
    "CONTRACT_INVALID": "The frozen inference contract could not be verified.",
    "REPAIR_CONTRACT_INVALID": "The categorical repair contract could not be verified.",
    "MODEL_MANIFEST_INVALID": "The model manifest could not be verified.",
    "MODEL_ARTIFACT_MISSING": "The verified model artifact is unavailable.",
    "MODEL_ARTIFACT_SYMLINK": "The model artifact failed its file-safety check.",
    "MODEL_ARTIFACT_HASH_MISMATCH": "The model artifact failed its integrity check.",
    "THRESHOLD_ARTIFACT_MISSING": "The frozen threshold artifact is unavailable.",
    "THRESHOLD_ARTIFACT_HASH_MISMATCH": "The threshold artifact failed its integrity check.",
    "BUNDLE_STRUCTURE_INVALID": "The verified runtime bundle has an invalid structure.",
    "MODEL_INTERFACE_INVALID": "The model interface is incompatible.",
    "CALIBRATOR_INTERFACE_INVALID": "The calibrator interface is incompatible.",
    "THRESHOLD_MISMATCH": "The runtime threshold does not match the frozen threshold.",
    "FEATURE_COUNT_INVALID": "The canonical feature count is invalid.",
    "FEATURE_SET_MISMATCH": "The canonical feature set is invalid.",
    "FEATURE_ORDER_MISMATCH": "The canonical feature order is invalid.",
    "FEATURE_VALUE_INVALID": "A canonical feature value is invalid.",
    "CATEGORICAL_METADATA_INVALID": "Categorical metadata is incompatible.",
    "UNKNOWN_CATEGORY": "A categorical value is not authorized by the model metadata.",
    "MODEL_OUTPUT_INVALID": "The model returned an invalid internal value.",
    "CALIBRATOR_OUTPUT_INVALID": "The calibrator returned an invalid probability.",
    "INFERENCE_RUNTIME_FAILURE": "Controlled local inference is unavailable.",
}

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
    "portfolio_demo_only": True,
}


class RuntimeValidationError(ValueError):
    """Internal exception carrying a sanitized failure code."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class DemoInferenceResult:
    mode: str
    inference_status: str = DEMO_INFERENCE_FAILED_SAFE
    risk_signal: float | None = None
    risk_signal_band: str | None = None
    risk_signal_label: str = RISK_SIGNAL_LABEL
    calibrated_default_probability: float | None = None
    model_operating_threshold: float | None = None
    threshold_relation: str | None = None
    feature_count: int | None = None
    model_artifact_sha256: str | None = None
    raw_model_output_internal: float | None = None
    canonical_value_source: str | None = None
    purpose_fixture_source: str | None = None
    synthetic_profile_id: str | None = None
    sample_profile_identity_verified: bool = False
    sample_profile_readiness_verified: bool = False
    sample_profile_payload_match: bool = False
    value_source_counts: dict[str, int] = field(default_factory=dict)
    limitation_aware_features: tuple[str, ...] = ()
    limitation_aware_count: int = 0
    credit_decision: None = None
    input_validation: dict[str, Any] = field(default_factory=dict)
    model_input_compatibility: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    limitations: list[dict[str, Any]] = field(default_factory=list)
    readiness_note: str = "Controlled local inference has not been executed."
    error_message: str | None = None


@dataclass(frozen=True)
class ModelArtifactLoadResult:
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
    feature_names: list[str] = field(default_factory=list)
    manifest_path: str | None = None
    manifest_loaded: bool = False
    manifest_valid: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None


@dataclass(frozen=True)
class VerifiedRuntime:
    model: Any
    calibrator: Any
    threshold: float
    feature_cols: tuple[str, ...]
    categorical_features: dict[str, tuple[str, ...]]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _strict_json(path: Path) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError(value)
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)


def _verify_regular_file(path: Path, size: int, digest: str, missing_code: str, hash_code: str) -> None:
    if not path.exists() or not path.is_file():
        raise RuntimeValidationError(missing_code)
    if path.is_symlink():
        raise RuntimeValidationError("MODEL_ARTIFACT_SYMLINK" if path == MODEL_PATH else hash_code)
    if path.stat().st_size != size or _sha256(path) != digest:
        raise RuntimeValidationError(hash_code)


def _validate_preload_contracts() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], float]:
    try:
        contract = _strict_json(PUBLIC_CONTRACT_PATH)
    except (OSError, ValueError, TypeError):
        raise RuntimeValidationError("CONTRACT_INVALID") from None
    deployment = contract.get("deployment_classification", {})
    payload_contract = contract.get("canonical_payload_contract", {})
    output_contract = contract.get("output_contract", {})
    privacy = contract.get("privacy_and_logging", {})
    if not (
        deployment.get("classification") == "PORTFOLIO_DEMO_ONLY"
        and deployment.get("public_deployment_performed") is False
        and payload_contract.get("expected_canonical_feature_count") == REQUIRED_PAYLOAD_FIELD_COUNT
        and output_contract.get("approval_rejection_output_allowed") is False
        and output_contract.get("fabricated_probability_allowed") is False
        and privacy.get("RAW_INPUT_LOGGING") is False
        and privacy.get("CANONICAL_PAYLOAD_LOGGING") is False
    ):
        raise RuntimeValidationError("CONTRACT_INVALID")
    try:
        repair = _strict_json(REPAIR_CONTRACT_PATH)
    except (OSError, ValueError, TypeError):
        raise RuntimeValidationError("REPAIR_CONTRACT_INVALID") from None
    policy = repair.get("repair_policy", {})
    model_contract = repair.get("model_contract", {})
    if not (
        repair.get("blocked_feature") == PURPOSE_FEATURE
        and model_contract.get("feature_index") == 40
        and model_contract.get("allowed_categories") == list(PURPOSE_CATEGORIES)
        and policy.get("policy_id") == "PURPOSE_FIXED_ALLOWED_CATEGORY_V1"
        and policy.get("replacement_category") == "other"
        and policy.get("fixture_source") == "FIXED_ALLOWED_CATEGORY_REPAIR"
        and policy.get("canonical_value_source") == "SYNTHETIC_BASELINE"
        and policy.get("fixture_source_is_canonical_value_source") is False
        and policy.get("canonical_provenance_taxonomy_preserved") is True
    ):
        raise RuntimeValidationError("REPAIR_CONTRACT_INVALID")
    try:
        manifest = _strict_json(MODEL_MANIFEST_PATH)
    except (OSError, ValueError, TypeError):
        raise RuntimeValidationError("MODEL_MANIFEST_INVALID") from None
    artifact = manifest.get("model_artifact", {})
    threshold_meta = manifest.get("threshold", {})
    features = manifest.get("features", {})
    if not (
        manifest.get("validation_status") == "PASS"
        and artifact.get("source_target_identity") is True
        and artifact.get("target_regular_file") is True
        and artifact.get("target_symlink") is False
        and artifact.get("target_size_bytes") == MODEL_SIZE
        and artifact.get("target_sha256") == MODEL_SHA256
        and threshold_meta.get("source_target_identity") is True
        and features.get("expected_count") == REQUIRED_PAYLOAD_FIELD_COUNT
    ):
        raise RuntimeValidationError("MODEL_MANIFEST_INVALID")
    _verify_regular_file(MODEL_PATH, MODEL_SIZE, MODEL_SHA256, "MODEL_ARTIFACT_MISSING", "MODEL_ARTIFACT_HASH_MISMATCH")
    _verify_regular_file(THRESHOLD_PATH, THRESHOLD_SIZE, THRESHOLD_SHA256, "THRESHOLD_ARTIFACT_MISSING", "THRESHOLD_ARTIFACT_HASH_MISMATCH")
    try:
        threshold_json = _strict_json(THRESHOLD_PATH)
        external = float(threshold_json["threshold"])
    except (OSError, ValueError, TypeError, KeyError):
        raise RuntimeValidationError("THRESHOLD_MISMATCH") from None
    if not math.isfinite(external) or not 0 < external < 1 or abs(external - EXPECTED_THRESHOLD) > THRESHOLD_TOLERANCE:
        raise RuntimeValidationError("THRESHOLD_MISMATCH")
    return contract, repair, manifest, external


def _validate_bundle(bundle: Any, manifest: Mapping[str, Any], external_threshold: float) -> VerifiedRuntime:
    if type(bundle) is not dict or not {"model", "calibrator", "threshold", "feature_cols"}.issubset(bundle):
        raise RuntimeValidationError("BUNDLE_STRUCTURE_INVALID")
    model, calibrator = bundle["model"], bundle["calibrator"]
    if type(model).__module__ != "lightgbm.basic" or type(model).__name__ != "Booster" or not callable(getattr(model, "predict", None)):
        raise RuntimeValidationError("MODEL_INTERFACE_INVALID")
    if type(calibrator).__module__ != "sklearn.isotonic" or type(calibrator).__name__ != "IsotonicRegression" or not callable(getattr(calibrator, "predict", None)):
        raise RuntimeValidationError("CALIBRATOR_INTERFACE_INVALID")
    cols = bundle["feature_cols"]
    if isinstance(cols, (str, bytes)) or not isinstance(cols, Sequence):
        raise RuntimeValidationError("BUNDLE_STRUCTURE_INVALID")
    feature_cols = tuple(cols)
    if len(feature_cols) != REQUIRED_PAYLOAD_FIELD_COUNT:
        raise RuntimeValidationError("FEATURE_COUNT_INVALID")
    if any(not isinstance(x, str) or not x.strip() for x in feature_cols) or len(set(feature_cols)) != len(feature_cols):
        raise RuntimeValidationError("FEATURE_SET_MISMATCH")
    expected = tuple(manifest.get("features", {}).get("ordered_feature_names", []))
    if feature_cols != expected:
        raise RuntimeValidationError("FEATURE_ORDER_MISMATCH")
    try:
        bundle_threshold = float(bundle["threshold"])
    except (TypeError, ValueError):
        raise RuntimeValidationError("THRESHOLD_MISMATCH") from None
    if not math.isfinite(bundle_threshold) or abs(bundle_threshold - external_threshold) > THRESHOLD_TOLERANCE:
        raise RuntimeValidationError("THRESHOLD_MISMATCH")
    categories = getattr(model, "pandas_categorical", None)
    if not isinstance(categories, list) or len(categories) != 1 or tuple(categories[0]) != PURPOSE_CATEGORIES:
        raise RuntimeValidationError("CATEGORICAL_METADATA_INVALID")
    if feature_cols.index(PURPOSE_FEATURE) != 40:
        raise RuntimeValidationError("FEATURE_ORDER_MISMATCH")
    return VerifiedRuntime(model, calibrator, bundle_threshold, feature_cols, {PURPOSE_FEATURE: PURPOSE_CATEGORIES})


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists() or not path.is_file() or path.is_symlink():
        raise RuntimeValidationError("SAMPLE_PROFILE_CONTRACT_INVALID")
    try:
        with path.open(newline="", encoding="utf-8-sig") as stream:
            return list(csv.DictReader(stream))
    except (OSError, csv.Error, UnicodeError):
        raise RuntimeValidationError("SAMPLE_PROFILE_CONTRACT_INVALID") from None


@lru_cache(maxsize=1)
def _committed_profile_contracts() -> tuple[dict[str, dict[str, str]], dict[str, str], tuple[str, ...]]:
    _verify_regular_file(
        PROFILE_MATRIX_PATH,
        PROFILE_MATRIX_SIZE,
        PROFILE_MATRIX_SHA256,
        "SAMPLE_PROFILE_CONTRACT_INVALID",
        "SAMPLE_PROFILE_CONTRACT_INVALID",
    )
    rows = _read_csv_rows(PROFILE_MATRIX_PATH)
    readiness_rows = _read_csv_rows(PROFILE_READINESS_PATH)
    if len(rows) != 245:
        raise RuntimeValidationError("SAMPLE_PROFILE_CONTRACT_INVALID")
    profile_ids = {row.get("profile_id", "") for row in rows}
    if profile_ids != set(AUTHORIZED_PROFILE_IDS):
        raise RuntimeValidationError("SAMPLE_PROFILE_CONTRACT_INVALID")
    profiles: dict[str, dict[str, str]] = {}
    limitation_features: set[str] = set()
    seen: set[tuple[str, str]] = set()
    for row in rows:
        profile_id = row.get("profile_id", "")
        feature = row.get("canonical_feature", "")
        key = (profile_id, feature)
        if not feature or key in seen:
            raise RuntimeValidationError("SAMPLE_PROFILE_CONTRACT_INVALID")
        seen.add(key)
        profiles.setdefault(profile_id, {})[feature] = row.get("synthetic_value", "")
        if str(row.get("limitation_aware", "")).strip().lower() == "true":
            limitation_features.add(feature)
    if any(len(payload) != 49 for payload in profiles.values()):
        raise RuntimeValidationError("SAMPLE_PROFILE_CONTRACT_INVALID")
    readiness: dict[str, str] = {}
    for row in readiness_rows:
        profile_id = row.get("profile_id", "")
        if profile_id in readiness:
            raise RuntimeValidationError("SAMPLE_PROFILE_CONTRACT_INVALID")
        ready = str(row.get("profile_ready", "")).strip().lower() == "true"
        count_ok = row.get("canonical_feature_count") == "49" and row.get("expected_canonical_feature_count") == "49"
        handoff = str(row.get("handoff_ready_for_cell_7_9", "")).strip().lower() == "true"
        readiness[profile_id] = "READY" if ready and count_ok and handoff else "NOT_READY"
    if set(readiness) != set(AUTHORIZED_PROFILE_IDS) or limitation_features != set(LIMITATION_AWARE_FEATURES):
        raise RuntimeValidationError("SAMPLE_PROFILE_CONTRACT_INVALID")
    return profiles, readiness, tuple(sorted(limitation_features))


@lru_cache(maxsize=1)
def _verified_runtime() -> VerifiedRuntime:
    _, _, manifest, external = _validate_preload_contracts()
    try:
        bundle = joblib.load(MODEL_PATH)
    except Exception:
        raise RuntimeValidationError("BUNDLE_STRUCTURE_INVALID") from None
    return _validate_bundle(bundle, manifest, external)


def clear_runtime_cache() -> None:
    _verified_runtime.cache_clear()
    _committed_profile_contracts.cache_clear()


def guardrail_metadata(*, model_loaded: bool = False, inference_executed: bool = False,
                       predict_proba_executed: bool = False, safe_failure: bool = False,
                       failure_reason: str | None = None) -> dict[str, Any]:
    metadata = dict(GUARDRAIL_METADATA_DEFAULTS)
    metadata.update({
        "model_loaded": bool(model_loaded), "inference_executed": bool(inference_executed),
        "predict_proba_executed": bool(predict_proba_executed), "safe_failure": bool(safe_failure),
        "failure_reason": failure_reason,
    })
    return metadata


def model_artifact_path(path: str | Path | None = None) -> Path:
    if path is not None:
        raise RuntimeValidationError("PATH_OVERRIDE_REJECTED")
    return MODEL_PATH


def feature_manifest_path(path: str | Path | None = None) -> Path:
    if path is not None:
        raise RuntimeValidationError("PATH_OVERRIDE_REJECTED")
    return MODEL_MANIFEST_PATH


def load_model_artifact(path: str | Path | None = None) -> ModelArtifactLoadResult:
    if path is not None:
        return ModelArtifactLoadResult(load_status=DEMO_INFERENCE_FAILED_SAFE, error_message=FAILURE_MESSAGES["PATH_OVERRIDE_REJECTED"], metadata=guardrail_metadata(safe_failure=True, failure_reason="PATH_OVERRIDE_REJECTED"))
    try:
        runtime = _verified_runtime()
    except RuntimeValidationError as exc:
        return ModelArtifactLoadResult(load_status=DEMO_INFERENCE_FAILED_SAFE, error_message=FAILURE_MESSAGES.get(exc.code, FAILURE_MESSAGES["INFERENCE_RUNTIME_FAILURE"]), metadata=guardrail_metadata(safe_failure=True, failure_reason=exc.code))
    return ModelArtifactLoadResult(model=runtime, model_path="artifacts/model/final_model_calibrated.pkl", model_loaded=True, model_available=True, has_predict_proba=False, load_status=DEMO_INFERENCE_READY, metadata=guardrail_metadata(model_loaded=True))


def load_feature_manifest(path: str | Path | None = None) -> FeatureManifestLoadResult:
    if path is not None:
        return FeatureManifestLoadResult(error_message=FAILURE_MESSAGES["PATH_OVERRIDE_REJECTED"], metadata={"failure_reason": "PATH_OVERRIDE_REJECTED"})
    try:
        manifest = _strict_json(MODEL_MANIFEST_PATH)
        names = list(manifest["features"]["ordered_feature_names"])
    except (OSError, ValueError, TypeError, KeyError):
        return FeatureManifestLoadResult(error_message=FAILURE_MESSAGES["MODEL_MANIFEST_INVALID"])
    return FeatureManifestLoadResult(names, "artifacts/model/model_artifact_manifest.json", True, len(names) == 49)


def _finite_numeric(value: Any) -> float | int:
    if isinstance(value, bool) or value is None or isinstance(value, (dict, list, set, tuple)):
        raise RuntimeValidationError("FEATURE_VALUE_INVALID")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise RuntimeValidationError("FEATURE_VALUE_INVALID") from None
    if not math.isfinite(number):
        raise RuntimeValidationError("FEATURE_VALUE_INVALID")
    return int(number) if number.is_integer() else number


def _normalize_payload(payload: Mapping[str, Any], runtime: VerifiedRuntime) -> dict[str, float | int | str]:
    if not isinstance(payload, Mapping):
        raise RuntimeValidationError("FEATURE_VALUE_INVALID")
    if len(payload) != REQUIRED_PAYLOAD_FIELD_COUNT:
        raise RuntimeValidationError("FEATURE_COUNT_INVALID")
    if set(payload) != set(runtime.feature_cols):
        raise RuntimeValidationError("FEATURE_SET_MISMATCH")
    normalized: dict[str, float | int | str] = {}
    for feature in runtime.feature_cols:
        value = payload[feature]
        if feature == PURPOSE_FEATURE:
            if not isinstance(value, str) or value not in PURPOSE_CATEGORIES:
                raise RuntimeValidationError("UNKNOWN_CATEGORY")
            normalized[feature] = value
        else:
            normalized[feature] = _finite_numeric(value)
    return normalized


def _ordered_model_frame(payload: Mapping[str, Any], runtime: VerifiedRuntime) -> pd.DataFrame:
    normalized = _normalize_payload(payload, runtime)
    purpose = normalized[PURPOSE_FEATURE]
    data: dict[str, Any] = {}
    for feature in runtime.feature_cols:
        if feature == PURPOSE_FEATURE:
            data[feature] = pd.Categorical([purpose], categories=list(PURPOSE_CATEGORIES))
        else:
            data[feature] = [normalized[feature]]
    frame = pd.DataFrame(data, columns=list(runtime.feature_cols))
    if str(frame[PURPOSE_FEATURE].dtype) != "category" or frame[PURPOSE_FEATURE].isna().any():
        raise RuntimeValidationError("CATEGORICAL_METADATA_INVALID")
    return frame


def validate_model_input_compatibility(*, payload: Mapping[str, Any], feature_manifest_path_override: str | Path | None = None, model: Any | None = None) -> dict[str, Any]:
    if feature_manifest_path_override is not None:
        return {"compatible": False, "status": MODEL_INPUT_BLOCKED_REFERENCE_UNAVAILABLE, "error_code": "PATH_OVERRIDE_REJECTED", "error_message": FAILURE_MESSAGES["PATH_OVERRIDE_REJECTED"]}
    try:
        runtime = model if isinstance(model, VerifiedRuntime) else _verified_runtime()
        frame = _ordered_model_frame(payload, runtime)
    except RuntimeValidationError as exc:
        return {"compatible": False, "status": MODEL_INPUT_BLOCKED_DTYPE_ERROR, "error_code": exc.code, "error_message": FAILURE_MESSAGES.get(exc.code, FAILURE_MESSAGES["INFERENCE_RUNTIME_FAILURE"])}
    return {"compatible": True, "status": MODEL_INPUT_COMPATIBLE, "expected_feature_count": 49, "payload_feature_count": len(payload), "missing_features": [], "extra_features": [], "dtype_error_count": 0, "feature_order_source": "verified bundle feature_cols", "ordered_features": list(runtime.feature_cols), "purpose_dtype": str(frame[PURPOSE_FEATURE].dtype)}


def blocked_demo_inference_result(*, mode: str, inference_status: str = DEMO_INFERENCE_FAILED_SAFE,
                                  readiness_note: str | None = None, error_message: str | None = None,
                                  input_validation: dict[str, Any] | None = None,
                                  model_input_compatibility: dict[str, Any] | None = None,
                                  limitations: list[dict[str, Any]] | None = None,
                                  failure_reason: str | None = None) -> DemoInferenceResult:
    code = failure_reason or inference_status
    return DemoInferenceResult(mode=mode, inference_status=UNAVAILABLE,
        input_validation=input_validation or {}, model_input_compatibility=model_input_compatibility or {},
        metadata={**guardrail_metadata(safe_failure=True, failure_reason=code), "legacy_inference_status": inference_status}, limitations=limitations or [],
        readiness_note=readiness_note or "Controlled local inference is unavailable.",
        error_message=error_message or FAILURE_MESSAGES.get(code, FAILURE_MESSAGES["INFERENCE_RUNTIME_FAILURE"]))


def _resolve_profile_id(payload_result: Any) -> str:
    candidates: list[str] = []
    for name in ("synthetic_profile_id", "profile_id"):
        value = getattr(payload_result, name, None)
        if value is not None:
            candidates.append(str(value))
    metadata = getattr(payload_result, "metadata", None)
    if isinstance(metadata, Mapping) and metadata.get("selected_sample") is not None:
        candidates.append(str(metadata["selected_sample"]))
    if not candidates:
        raise RuntimeValidationError("SAMPLE_PROFILE_ID_REQUIRED")
    if len(set(candidates)) != 1:
        raise RuntimeValidationError("SAMPLE_PROFILE_ID_CONFLICT")
    profile_id = candidates[0]
    if profile_id not in AUTHORIZED_PROFILE_IDS:
        raise RuntimeValidationError("SAMPLE_PROFILE_ID_INVALID")
    return profile_id


def _authorize_committed_profile(
    profile_id: str,
    runtime: VerifiedRuntime,
    caller_payload: Mapping[str, Any] | None = None,
) -> tuple[dict[str, float | int | str], tuple[str, ...]]:
    if profile_id not in AUTHORIZED_PROFILE_IDS:
        raise RuntimeValidationError("SAMPLE_PROFILE_ID_INVALID")
    profiles, readiness, limitation_features = _committed_profile_contracts()
    if readiness.get(profile_id) != "READY":
        raise RuntimeValidationError("SAMPLE_PROFILE_NOT_READY")
    try:
        authoritative = _normalize_payload(profiles[profile_id], runtime)
    except (KeyError, RuntimeValidationError):
        raise RuntimeValidationError("SAMPLE_PROFILE_CONTRACT_INVALID") from None
    if set(authoritative) != set(runtime.feature_cols) or authoritative.get(PURPOSE_FEATURE) != "other":
        raise RuntimeValidationError("SAMPLE_PROFILE_CONTRACT_INVALID")
    if caller_payload is not None:
        try:
            caller_normalized = _normalize_payload(caller_payload, runtime)
        except RuntimeValidationError as exc:
            if exc.code in {"FEATURE_COUNT_INVALID", "FEATURE_SET_MISMATCH", "FEATURE_VALUE_INVALID", "UNKNOWN_CATEGORY"}:
                raise RuntimeValidationError("SAMPLE_PROFILE_PAYLOAD_MISMATCH") from None
            raise
        if caller_normalized != authoritative:
            raise RuntimeValidationError("SAMPLE_PROFILE_PAYLOAD_MISMATCH")
    return authoritative, limitation_features


def validate_payload_for_demo_inference(payload_result: Any, *, feature_manifest_path_override: str | Path | None = None, model: Any | None = None) -> DemoInferenceResult:
    mode = str(getattr(payload_result, "mode", "UNKNOWN"))
    if feature_manifest_path_override is not None:
        return blocked_demo_inference_result(mode=mode, failure_reason="PATH_OVERRIDE_REJECTED")
    if mode != AUTHORIZED_MODE:
        return blocked_demo_inference_result(mode=mode, failure_reason="MODE_NOT_AUTHORIZED_FOR_STEP4")
    try:
        profile_id = _resolve_profile_id(payload_result)
        runtime = model if isinstance(model, VerifiedRuntime) else _verified_runtime()
        authoritative, limitation_features = _authorize_committed_profile(
            profile_id, runtime, getattr(payload_result, "payload", None)
        )
        compatibility = validate_model_input_compatibility(payload=authoritative, model=runtime)
    except RuntimeValidationError as exc:
        return blocked_demo_inference_result(mode=mode, inference_status="DEMO_INFERENCE_BLOCKED_BY_SCHEMA_ERROR", failure_reason=exc.code)
    return DemoInferenceResult(mode=mode, inference_status=DEMO_INFERENCE_READY,
        synthetic_profile_id=profile_id, sample_profile_identity_verified=True,
        sample_profile_readiness_verified=True, sample_profile_payload_match=True,
        value_source_counts={"USER_SUPPLIED": 0, "SYNTHETIC_BASELINE": 49, "DERIVED": 0},
        limitation_aware_features=limitation_features, limitation_aware_count=len(limitation_features),
        canonical_value_source="SYNTHETIC_BASELINE", purpose_fixture_source="FIXED_ALLOWED_CATEGORY_REPAIR",
        input_validation={"mode": mode, "payload_field_count": len(authoritative), "blocking_reasons": []},
        model_input_compatibility=compatibility, metadata={**guardrail_metadata(), "legacy_inference_status": "DEMO_INFERENCE_READY"},
        limitations=list(getattr(payload_result, "limitations", []) or []),
        readiness_note="The synthetic sample profile passed controlled Stage 4 validation.")


def _one_finite_value(output: Any, code: str, probability: bool = False) -> float:
    try:
        vector = np.asarray(output).reshape(-1)
        if vector.size != 1:
            raise ValueError
        value = float(vector[0])
    except (TypeError, ValueError, IndexError):
        raise RuntimeValidationError(code) from None
    if not math.isfinite(value) or (probability and not 0 <= value <= 1):
        raise RuntimeValidationError(code)
    return value


def _predict_frame(runtime: VerifiedRuntime, frame: pd.DataFrame) -> tuple[float, float]:
    raw_vector = np.asarray(runtime.model.predict(frame)).reshape(-1)
    raw = _one_finite_value(raw_vector, "MODEL_OUTPUT_INVALID")
    calibrated_vector = np.asarray(runtime.calibrator.predict(raw_vector)).reshape(-1)
    probability = _one_finite_value(calibrated_vector, "CALIBRATOR_OUTPUT_INVALID", probability=True)
    return raw, probability


def _execute_committed_profile(
    profile_id: str,
    runtime: VerifiedRuntime,
    authoritative: Mapping[str, Any],
    limitation_features: tuple[str, ...],
    limitations: list[dict[str, Any]] | None = None,
) -> DemoInferenceResult:
    frame = _ordered_model_frame(authoritative, runtime)
    raw, probability = _predict_frame(runtime, frame)
    relation = threshold_relation(probability, runtime.threshold)
    metadata = guardrail_metadata(model_loaded=True, inference_executed=True)
    metadata.update({
        "legacy_inference_status": "DEMO_INFERENCE_READY",
        "model_load_status": AVAILABLE,
        "model_input_feature_count": 49,
        "risk_signal_band_is_decision_threshold": False,
        "threshold_applied": True,
        "canonical_value_source": "SYNTHETIC_BASELINE",
        "purpose_fixture_source": "FIXED_ALLOWED_CATEGORY_REPAIR",
    })
    return DemoInferenceResult(
        mode=AUTHORIZED_MODE,
        inference_status=AVAILABLE,
        risk_signal=probability,
        risk_signal_band=relation,
        calibrated_default_probability=probability,
        model_operating_threshold=runtime.threshold,
        threshold_relation=relation,
        feature_count=49,
        model_artifact_sha256=MODEL_SHA256,
        raw_model_output_internal=raw,
        canonical_value_source="SYNTHETIC_BASELINE",
        purpose_fixture_source="FIXED_ALLOWED_CATEGORY_REPAIR",
        synthetic_profile_id=profile_id,
        sample_profile_identity_verified=True,
        sample_profile_readiness_verified=True,
        sample_profile_payload_match=True,
        value_source_counts={"USER_SUPPLIED": 0, "SYNTHETIC_BASELINE": 49, "DERIVED": 0},
        limitation_aware_features=limitation_features,
        limitation_aware_count=len(limitation_features),
        input_validation={"mode": AUTHORIZED_MODE, "payload_field_count": 49, "blocking_reasons": []},
        model_input_compatibility={
            "compatible": True,
            "status": MODEL_INPUT_COMPATIBLE,
            "expected_feature_count": 49,
            "payload_feature_count": 49,
            "feature_order_source": "verified bundle feature_cols",
            "purpose_dtype": "category",
        },
        metadata=metadata,
        limitations=limitations or [],
        readiness_note="Controlled local inference produced a calibrated default-risk probability for a verified committed synthetic profile.",
    )


def run_committed_sample_profile_inference(profile_id: str) -> DemoInferenceResult:
    """Infer one allowlisted ready profile using only its committed fixture values."""
    try:
        runtime = _verified_runtime()
        authoritative, limitation_features = _authorize_committed_profile(str(profile_id), runtime)
        return _execute_committed_profile(str(profile_id), runtime, authoritative, limitation_features)
    except RuntimeValidationError as exc:
        return blocked_demo_inference_result(mode=AUTHORIZED_MODE, failure_reason=exc.code)
    except Exception:
        return blocked_demo_inference_result(mode=AUTHORIZED_MODE, failure_reason="INFERENCE_RUNTIME_FAILURE")


def threshold_relation(probability: float, threshold: float = EXPECTED_THRESHOLD) -> str:
    return "Below the model operating threshold" if probability < threshold else "At or above the model operating threshold"


def assign_risk_signal_band(risk_signal: float | int) -> str:
    signal = float(risk_signal)
    if not math.isfinite(signal) or not 0 <= signal <= 1:
        raise ValueError("Probability must be finite and within [0, 1].")
    return threshold_relation(signal)


def format_risk_signal(risk_signal: float | int | None) -> dict[str, Any]:
    if risk_signal is None:
        return {"risk_signal": None, "risk_signal_display": "Not available", "risk_signal_band": None,
                "risk_signal_label": RISK_SIGNAL_LABEL, "risk_signal_band_note": RISK_SIGNAL_BAND_NOTE,
                "band_is_decision_threshold": False}
    signal = float(risk_signal)
    relation = assign_risk_signal_band(signal)
    return {"risk_signal": signal, "risk_signal_display": f"{signal:.3f}", "risk_signal_band": relation,
            "risk_signal_label": RISK_SIGNAL_LABEL, "risk_signal_band_note": RISK_SIGNAL_BAND_NOTE,
            "band_is_decision_threshold": False}


def run_safe_demo_inference(payload_result: Any, *, model_path: str | Path | None = None,
                            feature_manifest_path_override: str | Path | None = None) -> DemoInferenceResult:
    mode = str(getattr(payload_result, "mode", "UNKNOWN"))
    limitations = list(getattr(payload_result, "limitations", []) or [])
    if model_path is not None or feature_manifest_path_override is not None:
        return blocked_demo_inference_result(mode=mode, limitations=limitations, failure_reason="PATH_OVERRIDE_REJECTED")
    if mode != AUTHORIZED_MODE:
        return blocked_demo_inference_result(mode=mode, limitations=limitations, failure_reason="MODE_NOT_AUTHORIZED_FOR_STEP4")
    try:
        runtime = _verified_runtime()
        profile_id = _resolve_profile_id(payload_result)
        authoritative, limitation_features = _authorize_committed_profile(
            profile_id, runtime, getattr(payload_result, "payload", None)
        )
        return _execute_committed_profile(profile_id, runtime, authoritative, limitation_features, limitations)
    except RuntimeValidationError as exc:
        return blocked_demo_inference_result(mode=mode, limitations=limitations, failure_reason=exc.code)
    except Exception:
        return blocked_demo_inference_result(mode=mode, limitations=limitations, failure_reason="INFERENCE_RUNTIME_FAILURE")


def demo_inference_result_to_dict(result: DemoInferenceResult) -> dict[str, Any]:
    return asdict(result)
