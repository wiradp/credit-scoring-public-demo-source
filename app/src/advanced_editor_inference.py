"""Atomic controlled-inference adapter for frozen Advanced Editor requests.

The only public entry point accepts a raw request.  Validation is completed
against the fixed Step 4.2B authority before the unchanged Stage 4 runtime is
accessed.  No previously-created validation result is accepted as authority.
"""

from __future__ import annotations

import math
from typing import Mapping

from app.src import demo_inference as frozen_adapter
from app.src.advanced_editor_runtime import (
    AdvancedEditorValidationError,
    validate_advanced_editor_request,
)


def _blocked(
    code: str,
    *,
    runtime_loaded: bool = False,
    frame_constructed: bool = False,
    prediction_started: bool = False,
    prediction_completed: bool = False,
    validation_verified: bool = False,
) -> frozen_adapter.DemoInferenceResult:
    """Return a sanitized fail-closed result without request values."""

    metadata = frozen_adapter.guardrail_metadata(
        model_loaded=runtime_loaded,
        inference_executed=prediction_completed,
        safe_failure=True,
        failure_reason=code,
    )
    metadata.update(
        {
            "canonical_payload_logged": False,
            "raw_input_logged": False,
            "advanced_editor_validation_verified": validation_verified,
            "payload_fingerprint_verified": validation_verified,
            "runtime_loaded": runtime_loaded,
            "frame_constructed": frame_constructed,
            "prediction_started": prediction_started,
            "prediction_completed": prediction_completed,
        }
    )
    return frozen_adapter.DemoInferenceResult(
        mode="ADVANCED_EDITOR",
        inference_status=frozen_adapter.UNAVAILABLE,
        metadata=metadata,
        readiness_note="Advanced Editor demo inference is unavailable.",
        error_message="Controlled demo inference is temporarily unavailable.",
    )


def run_advanced_editor_inference(
    request: Mapping[str, object],
) -> frozen_adapter.DemoInferenceResult:
    """Validate one raw Advanced Editor request and infer atomically."""

    try:
        validated = validate_advanced_editor_request(request)
    except AdvancedEditorValidationError as exc:
        return _blocked(exc.code)
    except Exception:
        return _blocked("ADVANCED_EDITOR_VALIDATION_FAILURE")

    runtime_loaded = False
    frame_constructed = False
    prediction_started = False
    prediction_completed = False
    try:
        runtime = frozen_adapter._verified_runtime()
        runtime_loaded = True
    except frozen_adapter.RuntimeValidationError as exc:
        return _blocked(exc.code, validation_verified=True)
    except Exception:
        return _blocked("INFERENCE_RUNTIME_FAILURE", validation_verified=True)

    try:
        frame = frozen_adapter._ordered_model_frame(
            validated.validated_canonical_payload,
            runtime,
        )
        frame_constructed = True
    except frozen_adapter.RuntimeValidationError as exc:
        return _blocked(
            exc.code,
            runtime_loaded=runtime_loaded,
            validation_verified=True,
        )
    except Exception:
        return _blocked(
            "INFERENCE_RUNTIME_FAILURE",
            runtime_loaded=runtime_loaded,
            validation_verified=True,
        )

    prediction_started = True
    try:
        raw_output, probability = frozen_adapter._predict_frame(runtime, frame)
        prediction_completed = True
    except frozen_adapter.RuntimeValidationError as exc:
        return _blocked(
            exc.code,
            runtime_loaded=runtime_loaded,
            frame_constructed=frame_constructed,
            prediction_started=prediction_started,
            validation_verified=True,
        )
    except Exception:
        return _blocked(
            "INFERENCE_RUNTIME_FAILURE",
            runtime_loaded=runtime_loaded,
            frame_constructed=frame_constructed,
            prediction_started=prediction_started,
            validation_verified=True,
        )

    if not math.isfinite(float(raw_output)):
        return _blocked(
            "INFERENCE_RUNTIME_FAILURE",
            runtime_loaded=runtime_loaded,
            frame_constructed=frame_constructed,
            prediction_started=prediction_started,
            prediction_completed=prediction_completed,
            validation_verified=True,
        )
    probability = float(probability)
    if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
        return _blocked(
            "INFERENCE_RUNTIME_FAILURE",
            runtime_loaded=runtime_loaded,
            frame_constructed=frame_constructed,
            prediction_started=prediction_started,
            prediction_completed=prediction_completed,
            validation_verified=True,
        )

    relation = frozen_adapter.threshold_relation(probability, runtime.threshold)
    safe_metadata = validated.safe_metadata()
    metadata = frozen_adapter.guardrail_metadata(
        model_loaded=True,
        inference_executed=True,
    )
    metadata.update(
        {
            "advanced_editor_contract_id": "STAGE9_ADVANCED_EDITOR_VALIDATION_V1",
            "advanced_editor_validation_verified": True,
            "payload_fingerprint_verified": True,
            "payload_fingerprint": validated.payload_fingerprint,
            "advanced_editor_profile_id": validated.profile_id,
            "edited_feature_count": len(validated.edited_feature_names),
            "edited_feature_names": list(validated.edited_feature_names),
            "provenance_counts": dict(validated.provenance_counts),
            "limitation_aware_features": list(validated.limitation_aware_features),
            "canonical_payload_logged": False,
            "raw_input_logged": False,
            "credit_decision_generated": False,
            "approval_recommendation_generated": False,
            "rejection_recommendation_generated": False,
            "credit_score_generated": False,
            "fairness_claimed": False,
            "legal_compliance_claimed": False,
            "production_ready_claimed": False,
            "portfolio_demo_only": True,
            "safe_disclosure": safe_metadata["safe_disclosure"],
            "runtime_loaded": runtime_loaded,
            "frame_constructed": frame_constructed,
            "prediction_started": prediction_started,
            "prediction_completed": prediction_completed,
        }
    )
    return frozen_adapter.DemoInferenceResult(
        mode="ADVANCED_EDITOR",
        inference_status=frozen_adapter.AVAILABLE,
        risk_signal=probability,
        risk_signal_band=relation,
        calibrated_default_probability=probability,
        model_operating_threshold=runtime.threshold,
        threshold_relation=relation,
        feature_count=49,
        model_artifact_sha256=frozen_adapter.MODEL_SHA256,
        synthetic_profile_id=validated.profile_id,
        value_source_counts=dict(validated.provenance_counts),
        limitation_aware_features=validated.limitation_aware_features,
        limitation_aware_count=len(validated.limitation_aware_features),
        credit_decision=None,
        input_validation={
            "mode": "ADVANCED_EDITOR",
            "payload_field_count": 49,
            "blocking_reasons": [],
            "advanced_editor_request_validated": True,
            "edited_feature_count": len(validated.edited_feature_names),
        },
        model_input_compatibility={
            "compatible": True,
            "status": frozen_adapter.MODEL_INPUT_COMPATIBLE,
            "expected_feature_count": 49,
            "payload_feature_count": 49,
            "feature_order_source": "verified Step 4.2B contract and model bundle",
            "purpose_dtype": "category",
        },
        metadata=metadata,
        readiness_note=(
            "Controlled local inference produced an actual calibrated model "
            "probability for a validated fictional Advanced Editor scenario."
        ),
    )
