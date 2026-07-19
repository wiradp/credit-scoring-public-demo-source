"""Stage 9 Step 4.2A Basic Form controlled-inference tests."""

from __future__ import annotations

import copy
import csv
import hashlib
import inspect
import json
import math
import struct
import unittest
from dataclasses import fields, replace
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from unittest import mock

from app.src import demo_inference as frozen_adapter
from app.src import basic_form_inference as basic_inference_module
from app.src.basic_form_inference import (
    ADVANCED_EDITOR_FAILURE_CODE,
    _run_authoritative_mapping_inference,
    block_advanced_editor_inference,
    run_basic_form_inference,
)
from app.src.basic_form_runtime import (
    BasicFormMappingResult,
    BasicFormRuntimeError,
    EXPECTED_LIMITATION_AWARE_FEATURES,
    EXPECTED_VALUE_SOURCE_COUNTS,
    _payload_fingerprint,
    _validate_baseline_profile,
    _validate_mapping_contract,
    build_basic_form_mapping_result,
    recompute_payload_fingerprint,
)


ROOT = Path(__file__).resolve().parents[1]
VECTORS_PATH = ROOT / "outputs/stage9/stage9_basic_form_runtime_mapping_golden_vectors.json"
MAPPING_PATH = ROOT / "outputs/stage9/stage9_basic_form_runtime_mapping_contract.json"
MATRIX_PATH = ROOT / "artifacts/contracts/cell_group_7/sample_profiles/sample_profile_feature_matrix.csv"
DEMO_INFERENCE_PATH = ROOT / "app/src/demo_inference.py"
PROFILE_IDS = (
    "SP_LOW_RISK_SIGNAL",
    "SP_MEDIUM_RISK_SIGNAL",
    "SP_HIGHER_RISK_SIGNAL",
    "SP_MIXED_SIGNAL",
    "SP_LIMITATION_TRANSPARENCY",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_profiles() -> dict[str, list[dict[str, str]]]:
    with MATRIX_PATH.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    profiles: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        profiles.setdefault(row["profile_id"], []).append(row)
    return profiles


def _profile_payload(rows: list[dict[str, str]]) -> dict[str, object]:
    return {
        row["canonical_feature"]: (
            row["synthetic_value"]
            if row["canonical_feature"] == "purpose"
            else float(row["synthetic_value"])
        )
        for row in rows
    }


def _unsafe_clone(
    result: BasicFormMappingResult,
    **changes: object,
) -> BasicFormMappingResult:
    """Simulate hostile object mutation without invoking the sealed constructor."""

    forged = object.__new__(BasicFormMappingResult)
    for item in fields(BasicFormMappingResult):
        object.__setattr__(
            forged,
            item.name,
            changes.get(item.name, getattr(result, item.name)),
        )
    return forged


class Step42ABase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.vectors = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))["request_level_vectors"]
        cls.mapping_contract = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
        cls.profiles = _load_profiles()

    def mapping(self, index: int = 0) -> BasicFormMappingResult:
        vector = self.vectors[index]
        return build_basic_form_mapping_result(vector["source_inputs"], vector["system_metadata"])

    @staticmethod
    def failure_code(result: frozen_adapter.DemoInferenceResult) -> str | None:
        return result.metadata.get("failure_reason")


class FrozenAdapterPreservationTests(Step42ABase):
    def test_frozen_adapter_size_hash_and_mode(self) -> None:
        self.assertEqual(DEMO_INFERENCE_PATH.stat().st_size, 38_299)
        self.assertEqual(_sha256(DEMO_INFERENCE_PATH), "1eb8fdf3a39e4775f5817c2a4620dc7c6669d0d7ad844932f411fc25ebbc9074")
        self.assertEqual(frozen_adapter.AUTHORIZED_MODE, "SAMPLE_PROFILE")

    def test_existing_five_profiles_still_infer(self) -> None:
        for profile_id in PROFILE_IDS:
            with self.subTest(profile_id=profile_id):
                result = frozen_adapter.run_committed_sample_profile_inference(profile_id)
                self.assertEqual(result.inference_status, frozen_adapter.AVAILABLE)
                self.assertIsNotNone(result.calibrated_default_probability)

    def test_forged_sample_profile_payload_rejected(self) -> None:
        payload = _profile_payload(self.profiles[PROFILE_IDS[0]])
        payload["dti"] = float(payload["dti"]) + 1.0
        request = SimpleNamespace(mode="SAMPLE_PROFILE", synthetic_profile_id=PROFILE_IDS[0], payload=payload, limitations=[])
        result = frozen_adapter.run_safe_demo_inference(request)
        self.assertEqual(self.failure_code(result), "SAMPLE_PROFILE_PAYLOAD_MISMATCH")

    def test_cross_profile_payload_rejected(self) -> None:
        request = SimpleNamespace(
            mode="SAMPLE_PROFILE",
            synthetic_profile_id=PROFILE_IDS[0],
            payload=_profile_payload(self.profiles[PROFILE_IDS[1]]),
            limitations=[],
        )
        result = frozen_adapter.run_safe_demo_inference(request)
        self.assertEqual(self.failure_code(result), "SAMPLE_PROFILE_PAYLOAD_MISMATCH")

    def test_unknown_and_missing_profile_rejected(self) -> None:
        unknown = SimpleNamespace(mode="SAMPLE_PROFILE", synthetic_profile_id="UNKNOWN", limitations=[])
        missing = SimpleNamespace(mode="SAMPLE_PROFILE", limitations=[])
        self.assertEqual(self.failure_code(frozen_adapter.run_safe_demo_inference(unknown)), "SAMPLE_PROFILE_ID_INVALID")
        self.assertEqual(self.failure_code(frozen_adapter.run_safe_demo_inference(missing)), "SAMPLE_PROFILE_ID_REQUIRED")


class BasicFormGoldenParityTests(Step42ABase):
    def test_all_seven_vectors_match_frozen_outputs(self) -> None:
        passthrough = set(self.mapping_contract["dependency_partition"]["synthetic_baseline_passthrough"])
        for vector in self.vectors:
            with self.subTest(vector=vector["vector_id"]):
                result = build_basic_form_mapping_result(vector["source_inputs"], vector["system_metadata"])
                self.assertEqual(result.feature_count, 49)
                self.assertEqual(tuple(result.payload), result.ordered_feature_names)
                self.assertEqual(result.payload_fingerprint, vector["expected_ordered_payload_sha256"])
                self.assertEqual(dict(result.value_source_counts), vector["expected_value_source_counts"])
                self.assertEqual(result.limitation_aware_features, tuple(vector["expected_limitation_aware_features"]))
                for name, expected in vector["expected_impacted_feature_outputs"].items():
                    self.assertEqual(result.payload[name], expected)
                for name, expected in vector["expected_float32_bits"].items():
                    bits = struct.unpack(">I", struct.pack(">f", float(result.payload[name])))[0]
                    self.assertEqual(bits, expected)
                baseline = _profile_payload(self.profiles[result.selected_synthetic_profile_id])
                self.assertEqual(sum(result.payload[name] == baseline[name] for name in passthrough), 38)
                self.assertEqual(recompute_payload_fingerprint(result), result.payload_fingerprint)

    def test_mapping_result_repr_omits_payload(self) -> None:
        result = self.mapping()
        rendered = repr(result)
        self.assertNotIn("payload=", rendered)
        self.assertNotIn("source_inputs=", rendered)
        self.assertNotIn("system_metadata=", rendered)
        self.assertNotIn(str(result.source_inputs["annual_inc"]), rendered)
        self.assertNotIn("acc_open_past_24mths", rendered)
        with self.assertRaises(TypeError):
            result.payload["dti"] = 0.0  # type: ignore[index]
        with self.assertRaises(TypeError):
            result.source_inputs["dti"] = 0.0  # type: ignore[index]
        with self.assertRaises(TypeError):
            result.system_metadata["synthetic_completion_acknowledged"] = False  # type: ignore[index]

    def test_identical_inputs_are_mapping_deterministic(self) -> None:
        for vector in self.vectors:
            first = build_basic_form_mapping_result(vector["source_inputs"], vector["system_metadata"])
            second = build_basic_form_mapping_result(vector["source_inputs"], vector["system_metadata"])
            self.assertEqual(first.payload_fingerprint, second.payload_fingerprint)
            self.assertEqual(dict(first.payload), dict(second.payload))

    def test_contract_registry_and_baseline_mutations_fail_closed(self) -> None:
        extra = copy.deepcopy(self.mapping_contract)
        extra["operation_registry"].append(copy.deepcopy(extra["operation_registry"][0]))
        with self.assertRaises(BasicFormRuntimeError):
            _validate_mapping_contract(extra)
        missing = copy.deepcopy(self.mapping_contract)
        missing["operation_registry"].pop(0)
        with self.assertRaises(BasicFormRuntimeError):
            _validate_mapping_contract(missing)
        unresolved = copy.deepcopy(self.mapping_contract)
        unresolved["operation_registry"][0]["source_fields"] = ["unresolved_operand"]
        with self.assertRaises(BasicFormRuntimeError):
            _validate_mapping_contract(unresolved)
        overlap = copy.deepcopy(self.mapping_contract)
        overlap["payload_fingerprint_contract"]["feature_representation_classes"]["category"].append("dti")
        with self.assertRaises(BasicFormRuntimeError):
            _validate_mapping_contract(overlap)

        rows = copy.deepcopy(self.profiles[PROFILE_IDS[0]])
        next(row for row in rows if row["canonical_feature"] == "grade_encoded")["mapping_status"] = "READY"
        with self.assertRaises(BasicFormRuntimeError):
            _validate_baseline_profile(self.mapping_contract, PROFILE_IDS[0], rows)
        rows = copy.deepcopy(self.profiles[PROFILE_IDS[0]])
        next(row for row in rows if row["canonical_feature"] == "installment")["synthetic_value"] = "NaN"
        with self.assertRaises(BasicFormRuntimeError):
            _validate_baseline_profile(self.mapping_contract, PROFILE_IDS[0], rows)


class BasicFormActualInferenceTests(Step42ABase):
    def test_all_seven_vectors_use_atomic_api_for_actual_probabilities(self) -> None:
        for vector in self.vectors:
            with self.subTest(vector=vector["vector_id"]):
                result = run_basic_form_inference(vector["source_inputs"], vector["system_metadata"])
                probability = result.calibrated_default_probability
                self.assertEqual(result.mode, "BASIC_FORM")
                self.assertEqual(result.inference_status, frozen_adapter.AVAILABLE)
                self.assertEqual(result.feature_count, 49)
                self.assertIsNotNone(probability)
                self.assertTrue(math.isfinite(probability))
                self.assertGreaterEqual(probability, 0.0)
                self.assertLessEqual(probability, 1.0)
                self.assertIsNone(result.credit_decision)
                self.assertTrue(result.metadata["payload_fingerprint_verified"])
                self.assertTrue(result.metadata["authoritative_rebuild_verified"])
                self.assertTrue(result.metadata["profile_payload_binding_verified"])
                self.assertEqual(result.metadata["payload_fingerprint"], vector["expected_ordered_payload_sha256"])
                self.assertFalse(result.sample_profile_identity_verified)
                self.assertFalse(result.sample_profile_payload_match)

    def test_all_seven_atomic_requests_are_probability_deterministic(self) -> None:
        for vector in self.vectors:
            first = run_basic_form_inference(vector["source_inputs"], vector["system_metadata"])
            second = run_basic_form_inference(vector["source_inputs"], vector["system_metadata"])
            self.assertEqual(first.metadata["payload_fingerprint"], second.metadata["payload_fingerprint"])
            self.assertEqual(first.calibrated_default_probability, second.calibrated_default_probability)


class BasicFormAuthorizationBoundaryTests(Step42ABase):
    def forge_payload(
        self,
        changes: dict[str, object],
        *,
        index: int = 0,
        profile_id: str | None = None,
    ) -> BasicFormMappingResult:
        original = self.mapping(index)
        payload = dict(original.payload)
        payload.update(changes)
        fingerprint = _payload_fingerprint(self.mapping_contract, payload)
        return _unsafe_clone(
            original,
            payload=MappingProxyType(payload),
            payload_fingerprint=fingerprint,
            selected_synthetic_profile_id=(profile_id or original.selected_synthetic_profile_id),
        )

    def assertForgeryBlocked(self, forged: BasicFormMappingResult) -> None:  # noqa: N802
        with (
            mock.patch.object(frozen_adapter, "_verified_runtime") as verified_runtime,
            mock.patch.object(frozen_adapter, "_ordered_model_frame") as ordered_frame,
            mock.patch.object(frozen_adapter, "_predict_frame") as predict_frame,
        ):
            result = _run_authoritative_mapping_inference(forged)
        self.assertEqual(result.inference_status, frozen_adapter.UNAVAILABLE)
        self.assertIsNone(result.calibrated_default_probability)
        self.assertIsNone(result.risk_signal)
        self.assertEqual(self.failure_code(result), "BASIC_FORM_AUTHORIZATION_BINDING_INVALID")
        verified_runtime.assert_not_called()
        ordered_frame.assert_not_called()
        predict_frame.assert_not_called()

    def test_public_api_accepts_only_source_inputs_and_metadata(self) -> None:
        signature = inspect.signature(run_basic_form_inference)
        self.assertEqual(list(signature.parameters), ["source_inputs", "system_metadata"])
        forbidden = {"mapping_result", "payload", "canonical_payload", "fingerprint", "provenance", "limitation_set", "model_path", "contract_path"}
        self.assertFalse(forbidden & set(signature.parameters))

    def test_mapping_result_is_not_public_authorization_input(self) -> None:
        self.assertFalse(hasattr(basic_inference_module, "run_validated_basic_form_inference"))
        public_functions = {
            name: value for name, value in inspect.getmembers(basic_inference_module, inspect.isfunction)
            if not name.startswith("_")
        }
        for name, function in public_functions.items():
            annotation = inspect.signature(function).parameters
            with self.subTest(function=name):
                self.assertNotIn("mapping_result", annotation)
        with mock.patch.object(frozen_adapter, "_verified_runtime") as runtime:
            result = run_basic_form_inference(self.mapping(), {})  # type: ignore[arg-type]
        runtime.assert_not_called()
        self.assertEqual(result.inference_status, frozen_adapter.UNAVAILABLE)

    def test_direct_mapping_result_construction_is_prohibited(self) -> None:
        with self.assertRaises(TypeError):
            BasicFormMappingResult()  # type: ignore[call-arg]

    def test_dataclasses_replace_forgery_is_prohibited(self) -> None:
        result = self.mapping()
        payload = dict(result.payload)
        payload["open_acc"] = float(payload["open_acc"]) + 1.0
        with self.assertRaises(TypeError):
            replace(result, payload=MappingProxyType(payload), payload_fingerprint=_payload_fingerprint(self.mapping_contract, payload))

    def test_self_consistent_forged_payload_is_rejected(self) -> None:
        self.assertForgeryBlocked(self.forge_payload({"open_acc": 123.0}))

    def test_out_of_range_dti_with_matching_fingerprint_is_rejected(self) -> None:
        self.assertForgeryBlocked(self.forge_payload({"dti": 9999.0}))

    def test_invalid_loan_amount_with_matching_fingerprint_is_rejected(self) -> None:
        self.assertForgeryBlocked(self.forge_payload({"loan_amnt": -123.0}))

    def test_altered_derived_value_with_matching_fingerprint_is_rejected(self) -> None:
        result = self.mapping()
        changed = float(result.payload["payment_to_income"]) + 0.125
        self.assertForgeryBlocked(self.forge_payload({"payment_to_income": changed}))

    def test_altered_baseline_value_with_matching_fingerprint_is_rejected(self) -> None:
        result = self.mapping()
        changed = float(result.payload["open_acc"]) + 1.0
        self.assertForgeryBlocked(self.forge_payload({"open_acc": changed}))

    def test_multiple_finite_mutations_with_matching_fingerprint_are_rejected(self) -> None:
        result = self.mapping()
        self.assertForgeryBlocked(self.forge_payload({
            "dti": 9999.0,
            "loan_amnt": -123.0,
            "payment_to_income": float(result.payload["payment_to_income"]) + 0.125,
            "open_acc": float(result.payload["open_acc"]) + 1.0,
        }))

    def test_profile_payload_binding_mismatch_is_rejected(self) -> None:
        original = self.mapping(0)
        medium = _profile_payload(self.profiles[PROFILE_IDS[1]])
        passthrough = self.mapping_contract["dependency_partition"]["synthetic_baseline_passthrough"]
        changes = {name: medium[name] for name in passthrough}
        forged = self.forge_payload(changes, profile_id=original.selected_synthetic_profile_id)
        self.assertForgeryBlocked(forged)

    def test_profile_id_changed_with_payload_retained_is_rejected(self) -> None:
        original = self.mapping(0)
        forged = _unsafe_clone(original, selected_synthetic_profile_id=PROFILE_IDS[1])
        self.assertForgeryBlocked(forged)

    def test_mode_acknowledgement_and_evidence_mutations_never_access_runtime(self) -> None:
        original = self.mapping()
        cases = (
            _unsafe_clone(original, mode="SAMPLE_PROFILE"),
            _unsafe_clone(original, synthetic_completion_acknowledged=False),
            _unsafe_clone(original, mapping_contract_id="WRONG"),
            _unsafe_clone(original, input_contract_id="WRONG"),
            _unsafe_clone(original, value_source_counts=MappingProxyType({"USER_SUPPLIED": 5, "DERIVED": 6, "SYNTHETIC_BASELINE": 38})),
            _unsafe_clone(original, limitation_aware_features=("grade_encoded",)),
        )
        for forged in cases:
            with (
                mock.patch.object(frozen_adapter, "_verified_runtime") as runtime,
                mock.patch.object(frozen_adapter, "_ordered_model_frame") as frame,
                mock.patch.object(frozen_adapter, "_predict_frame") as predict,
            ):
                result = _run_authoritative_mapping_inference(forged)
            self.assertEqual(result.inference_status, frozen_adapter.UNAVAILABLE)
            runtime.assert_not_called()
            frame.assert_not_called()
            predict.assert_not_called()

    def test_atomic_validation_failures_are_sanitized_and_skip_runtime(self) -> None:
        vector = self.vectors[0]
        source = dict(vector["source_inputs"])
        metadata = dict(vector["system_metadata"])
        cases = [
            ({**source, "email": "fictional@example.invalid"}, metadata),
            ({**source, "personal_narrative": "fictional"}, metadata),
            ({**source, "dti": float("inf")}, metadata),
            ({**source, "term_months": 36.0}, metadata),
            ({**source, "purpose": "unknown"}, metadata),
            (source, {**metadata, "synthetic_completion_acknowledged": False}),
        ]
        for bad_source, bad_metadata in cases:
            with self.subTest(keys=tuple(bad_source)):
                with mock.patch.object(frozen_adapter, "_verified_runtime") as runtime:
                    result = run_basic_form_inference(bad_source, bad_metadata)
                runtime.assert_not_called()
                self.assertEqual(result.inference_status, frozen_adapter.UNAVAILABLE)
                self.assertIsNone(result.calibrated_default_probability)
                self.assertIsNone(result.risk_signal)
                self.assertNotIn(str(bad_source.get("annual_inc")), result.error_message or "")
                self.assertNotIn(str(ROOT), result.error_message or "")


class AdvancedEditorAndStaticBoundaryTests(Step42ABase):
    def test_advanced_editor_block_never_accesses_runtime(self) -> None:
        with mock.patch.object(frozen_adapter, "_verified_runtime") as runtime:
            result = block_advanced_editor_inference()
        runtime.assert_not_called()
        self.assertEqual(self.failure_code(result), ADVANCED_EDITOR_FAILURE_CODE)
        self.assertIsNone(result.calibrated_default_probability)
        self.assertFalse(result.metadata["inference_executed"])

    def test_model_runtime_implementation_is_not_duplicated(self) -> None:
        runtime_source = (ROOT / "app/src/basic_form_runtime.py").read_text(encoding="utf-8")
        inference_source = (ROOT / "app/src/basic_form_inference.py").read_text(encoding="utf-8")
        combined = runtime_source + inference_source
        for forbidden in (
            "joblib.load", "pickle.load", "model.predict(", "calibrator.predict(",
            "pd.DataFrame(", "pd.Categorical(",
        ):
            self.assertNotIn(forbidden, combined)
        self.assertNotIn("frozen_adapter._verified_runtime", runtime_source)
        self.assertNotIn("frozen_adapter._ordered_model_frame", runtime_source)
        self.assertNotIn("frozen_adapter._predict_frame", runtime_source)
        self.assertIn("frozen_adapter._verified_runtime", inference_source)
        self.assertIn("frozen_adapter._ordered_model_frame", inference_source)
        self.assertIn("frozen_adapter._predict_frame", inference_source)

    def test_no_fallback_probability_or_network_telemetry(self) -> None:
        combined = "\n".join(
            (ROOT / relative).read_text(encoding="utf-8")
            for relative in ("app/src/basic_form_runtime.py", "app/src/basic_form_inference.py")
        )
        for forbidden in ("requests", "urllib", "http.client", "socket", "telemetry", "fallback_probability"):
            self.assertNotIn(forbidden, combined)

    def test_smoke_and_reports_do_not_record_complete_payload(self) -> None:
        evidence_paths = (
            ROOT / "outputs/stage9/stage9_basic_form_inference_smoke_results.json",
            ROOT / "outputs/stage9/stage9_payload_capable_inference_adapter_report.json",
            ROOT / "outputs/stage9/stage9_payload_capable_inference_adapter_report.md",
        )
        feature_names = self.mapping_contract["model_feature_contract"]["ordered_feature_names"]
        for path in evidence_paths:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertNotIn('"payload": {', text)
                self.assertLess(sum(name in text for name in feature_names), 49)


if __name__ == "__main__":
    unittest.main()
