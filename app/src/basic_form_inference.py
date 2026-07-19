"""Separately authorized Basic Form controlled-inference adapter.

This module revalidates the immutable mapping envelope, then delegates model
runtime verification, frame construction, prediction, calibration, and
threshold relation to the unchanged Stage 4 adapter.
"""

from __future__ import annotations

import math
from typing import Mapping

from app.src import demo_inference as frozen_adapter
from app.src.basic_form_runtime import (
    BasicFormMappingResult,
    BasicFormRuntimeError,
    _mapping_results_exactly_match,
    build_basic_form_mapping_result as _build_basic_form_mapping_result,
    revalidate_basic_form_mapping_result as _revalidate_basic_form_mapping_result,
)


ADVANCED_EDITOR_FAILURE_CODE = "ADVANCED_EDITOR_CONTRACT_NOT_FROZEN"


def _blocked(code: str, *, execution_started: bool = False) -> frozen_adapter.DemoInferenceResult:
    if not execution_started:
        return frozen_adapter.blocked_demo_inference_result(
            mode="BASIC_FORM",
            failure_reason=code,
            readiness_note="Basic Form demo inference is unavailable.",
        )
    metadata = frozen_adapter.guardrail_metadata(
        model_loaded=True,
        inference_executed=True,
        safe_failure=True,
        failure_reason=code,
    )
    metadata.update({
        "canonical_payload_logged": False,
        "raw_input_logged": False,
        "basic_form_mapping_verified": True,
        "payload_fingerprint_verified": True,
    })
    return frozen_adapter.DemoInferenceResult(
        mode="BASIC_FORM",
        inference_status=frozen_adapter.UNAVAILABLE,
        metadata=metadata,
        readiness_note="Basic Form demo inference is unavailable.",
        error_message="Demo inference is temporarily unavailable.",
    )


def _run_authoritative_mapping_inference(
    mapping_result: BasicFormMappingResult,
) -> frozen_adapter.DemoInferenceResult:
    """Infer only after an exact authoritative rebuild of internal evidence."""

    if type(mapping_result) is not BasicFormMappingResult:
        return _blocked("BASIC_FORM_RESULT_TYPE_INVALID")
    try:
        _revalidate_basic_form_mapping_result(mapping_result)
        rebuilt = _build_basic_form_mapping_result(
            mapping_result.source_inputs,
            mapping_result.system_metadata,
        )
        if not _mapping_results_exactly_match(mapping_result, rebuilt):
            raise BasicFormRuntimeError("BASIC_FORM_AUTHORIZATION_BINDING_INVALID")
        runtime = frozen_adapter._verified_runtime()
        frame = frozen_adapter._ordered_model_frame(rebuilt.payload, runtime)
        raw_output, probability = frozen_adapter._predict_frame(runtime, frame)
    except BasicFormRuntimeError as exc:
        return _blocked(exc.code)
    except frozen_adapter.RuntimeValidationError as exc:
        return _blocked(exc.code)
    except Exception:
        return _blocked("INFERENCE_RUNTIME_FAILURE")

    if not math.isfinite(float(raw_output)):
        return _blocked("INFERENCE_RUNTIME_FAILURE", execution_started=True)
    probability = float(probability)
    if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
        return _blocked("INFERENCE_RUNTIME_FAILURE", execution_started=True)
    relation = frozen_adapter.threshold_relation(probability, runtime.threshold)
    metadata = frozen_adapter.guardrail_metadata(model_loaded=True, inference_executed=True)
    metadata.update({
        "payload_fingerprint": mapping_result.payload_fingerprint,
        "selected_synthetic_profile_id": mapping_result.selected_synthetic_profile_id,
        "basic_form_mapping_verified": True,
        "payload_fingerprint_verified": True,
        "authoritative_rebuild_verified": True,
        "profile_payload_binding_verified": True,
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
    })
    return frozen_adapter.DemoInferenceResult(
        mode="BASIC_FORM",
        inference_status=frozen_adapter.AVAILABLE,
        risk_signal=probability,
        risk_signal_band=relation,
        calibrated_default_probability=probability,
        model_operating_threshold=runtime.threshold,
        threshold_relation=relation,
        feature_count=49,
        model_artifact_sha256=frozen_adapter.MODEL_SHA256,
        synthetic_profile_id=mapping_result.selected_synthetic_profile_id,
        sample_profile_identity_verified=False,
        sample_profile_readiness_verified=False,
        sample_profile_payload_match=False,
        value_source_counts=dict(mapping_result.value_source_counts),
        limitation_aware_features=mapping_result.limitation_aware_features,
        limitation_aware_count=len(mapping_result.limitation_aware_features),
        credit_decision=None,
        input_validation={
            "mode": "BASIC_FORM",
            "payload_field_count": 49,
            "blocking_reasons": [],
            "mapping_result_revalidated": True,
            "authoritative_rebuild_completed": True,
        },
        model_input_compatibility={
            "compatible": True,
            "status": frozen_adapter.MODEL_INPUT_COMPATIBLE,
            "expected_feature_count": 49,
            "payload_feature_count": 49,
            "feature_order_source": "verified bundle feature_cols",
            "purpose_dtype": "category",
        },
        metadata=metadata,
        readiness_note=(
            "Controlled local inference produced an actual calibrated model "
            "probability for a validated fictional Basic Form scenario."
        ),
    )


def run_basic_form_inference(
    source_inputs: Mapping[str, object],
    system_metadata: Mapping[str, object],
) -> frozen_adapter.DemoInferenceResult:
    """Atomically map validated public inputs and run controlled inference."""

    try:
        mapping_result = _build_basic_form_mapping_result(source_inputs, system_metadata)
    except BasicFormRuntimeError as exc:
        return _blocked(exc.code)
    except Exception:
        return _blocked("INFERENCE_RUNTIME_FAILURE")
    return _run_authoritative_mapping_inference(mapping_result)


def block_advanced_editor_inference() -> frozen_adapter.DemoInferenceResult:
    """Return the explicit Step 4.2A Advanced Editor authorization block."""

    return frozen_adapter.blocked_demo_inference_result(
        mode="ADVANCED_EDITOR",
        failure_reason=ADVANCED_EDITOR_FAILURE_CODE,
        readiness_note="Advanced Editor inference is not authorized.",
    )
