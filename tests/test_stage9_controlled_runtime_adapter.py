"""Stage 9 Step 4 committed-profile runtime authorization tests."""

from __future__ import annotations

import ast
import hashlib
import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from streamlit.testing.v1 import AppTest

from app.src import demo_inference as runtime


ROOT = Path(__file__).resolve().parents[1]
PROFILE_IDS = set(runtime.AUTHORIZED_PROFILE_IDS)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def committed_payloads() -> dict[str, dict[str, str]]:
    profiles, _, _ = runtime._committed_profile_contracts()
    return {key: dict(value) for key, value in profiles.items()}


def wrapper(selected_id: str | None, payload: dict[str, object], **attributes):
    values = {"mode": "SAMPLE_PROFILE", "payload": payload, "limitations": []}
    if selected_id is not None:
        values["synthetic_profile_id"] = selected_id
    values.update(attributes)
    return runtime.run_safe_demo_inference(SimpleNamespace(**values))


class ArtifactIntegrityTests(unittest.TestCase):
    def test_model_threshold_and_matrix_integrity(self):
        expected = [
            (runtime.MODEL_PATH, runtime.MODEL_SIZE, runtime.MODEL_SHA256),
            (runtime.THRESHOLD_PATH, runtime.THRESHOLD_SIZE, runtime.THRESHOLD_SHA256),
            (runtime.PROFILE_MATRIX_PATH, runtime.PROFILE_MATRIX_SIZE, runtime.PROFILE_MATRIX_SHA256),
        ]
        for path, size, digest in expected:
            self.assertEqual(path.stat().st_size, size)
            self.assertEqual(sha256(path), digest)
            self.assertFalse(path.is_symlink())

    def test_fixed_paths_reject_overrides(self):
        self.assertEqual(runtime.MODEL_PATH, ROOT / "artifacts/model/final_model_calibrated.pkl")
        self.assertEqual(runtime.PROFILE_MATRIX_PATH, ROOT / "artifacts/contracts/cell_group_7/sample_profiles/sample_profile_feature_matrix.csv")
        with self.assertRaisesRegex(runtime.RuntimeValidationError, "PATH_OVERRIDE_REJECTED"):
            runtime.model_artifact_path("elsewhere.pkl")

    def test_repair_contract_hash(self):
        self.assertEqual(sha256(runtime.REPAIR_CONTRACT_PATH), "98b391bd31af98d7ff51cf1d92c848d170df93ec2bbf30e9e0d2b161874b1482")


class BundleValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        runtime.clear_runtime_cache()
        cls.bundle = runtime._verified_runtime()

    def test_bundle_interfaces(self):
        self.assertEqual((type(self.bundle.model).__module__, type(self.bundle.model).__name__), ("lightgbm.basic", "Booster"))
        self.assertEqual((type(self.bundle.calibrator).__module__, type(self.bundle.calibrator).__name__), ("sklearn.isotonic", "IsotonicRegression"))
        self.assertTrue(callable(self.bundle.model.predict))
        self.assertTrue(callable(self.bundle.calibrator.predict))
        self.assertFalse(callable(getattr(self.bundle.model, "predict_proba", None)))
        self.assertFalse(callable(getattr(self.bundle.calibrator, "predict_proba", None)))

    def test_features_threshold_and_categories(self):
        self.assertEqual(len(self.bundle.feature_cols), 49)
        self.assertEqual(len(set(self.bundle.feature_cols)), 49)
        self.assertEqual(self.bundle.feature_cols.index("purpose"), 40)
        self.assertEqual(self.bundle.categorical_features["purpose"], runtime.PURPOSE_CATEGORIES)
        self.assertAlmostEqual(self.bundle.threshold, 0.1, delta=1e-12)

    def test_invalid_bundle_fails_closed(self):
        _, _, manifest, external = runtime._validate_preload_contracts()
        with self.assertRaisesRegex(runtime.RuntimeValidationError, "BUNDLE_STRUCTURE_INVALID"):
            runtime._validate_bundle({}, manifest, external)


class CommittedProfileAuthorizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payloads = committed_payloads()

    def test_all_five_explicit_profile_ids_succeed(self):
        self.assertEqual(set(self.payloads), PROFILE_IDS)
        for profile_id in runtime.AUTHORIZED_PROFILE_IDS:
            result = runtime.run_committed_sample_profile_inference(profile_id)
            self.assertEqual(result.inference_status, "available")
            self.assertTrue(result.sample_profile_identity_verified)
            self.assertTrue(result.sample_profile_readiness_verified)
            self.assertTrue(result.sample_profile_payload_match)

    def test_missing_unknown_and_conflicting_profile_ids_fail(self):
        payload = self.payloads["SP_LOW_RISK_SIGNAL"]
        missing = wrapper(None, payload)
        unknown = wrapper("SP_NOT_ALLOWED", payload)
        conflict = wrapper("SP_LOW_RISK_SIGNAL", payload, profile_id="SP_MEDIUM_RISK_SIGNAL")
        self.assertEqual(missing.metadata["failure_reason"], "SAMPLE_PROFILE_ID_REQUIRED")
        self.assertEqual(unknown.metadata["failure_reason"], "SAMPLE_PROFILE_ID_INVALID")
        self.assertEqual(conflict.metadata["failure_reason"], "SAMPLE_PROFILE_ID_CONFLICT")
        self.assertTrue(all(x.inference_status == "unavailable" for x in (missing, unknown, conflict)))

    def test_existing_application_metadata_alias_succeeds(self):
        profile_id = "SP_LOW_RISK_SIGNAL"
        result = runtime.run_safe_demo_inference(SimpleNamespace(
            mode="SAMPLE_PROFILE", payload=self.payloads[profile_id], limitations=[],
            metadata={"selected_sample": profile_id},
        ))
        self.assertEqual(result.inference_status, "available")

    def test_not_ready_profile_fails_with_controlled_mock(self):
        profiles, readiness, limitations = runtime._committed_profile_contracts()
        blocked = dict(readiness); blocked["SP_LOW_RISK_SIGNAL"] = "NOT_READY"
        with mock.patch.object(runtime, "_committed_profile_contracts", return_value=(profiles, blocked, limitations)):
            result = runtime.run_committed_sample_profile_inference("SP_LOW_RISK_SIGNAL")
        self.assertEqual(result.inference_status, "unavailable")
        self.assertEqual(result.metadata["failure_reason"], "SAMPLE_PROFILE_NOT_READY")

    def test_committed_profile_contract_shape_and_limitations(self):
        profiles, readiness, limitations = runtime._committed_profile_contracts()
        self.assertEqual(len(profiles), 5)
        self.assertEqual(set(readiness.values()), {"READY"})
        self.assertTrue(all(len(payload) == 49 for payload in profiles.values()))
        self.assertEqual(set(limitations), {"grade_encoded", "credit_age_months"})


class PayloadForgeryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payloads = committed_payloads()

    def test_committed_payload_and_equivalent_numeric_form_succeed(self):
        profile_id = "SP_LOW_RISK_SIGNAL"
        exact = wrapper(profile_id, dict(self.payloads[profile_id]))
        equivalent = dict(self.payloads[profile_id]); equivalent["acc_open_past_24mths"] = 20.0
        normalized = wrapper(profile_id, equivalent)
        self.assertEqual(exact.inference_status, "available")
        self.assertEqual(normalized.inference_status, "available")

    def test_original_finite_dti_bypass_is_rejected_before_prediction(self):
        payload = dict(self.payloads["SP_LOW_RISK_SIGNAL"]); payload["dti"] = 999999
        with mock.patch.object(runtime, "_predict_frame", side_effect=AssertionError("prediction executed")) as predict:
            result = wrapper("SP_LOW_RISK_SIGNAL", payload)
        self.assertEqual(result.inference_status, "unavailable")
        self.assertEqual(result.metadata["failure_reason"], "SAMPLE_PROFILE_PAYLOAD_MISMATCH")
        self.assertIsNone(result.calibrated_default_probability)
        self.assertIsNone(result.threshold_relation)
        self.assertFalse(result.sample_profile_identity_verified)
        predict.assert_not_called()

    def test_cross_profile_payload_is_rejected_before_prediction(self):
        with mock.patch.object(runtime, "_predict_frame", side_effect=AssertionError("prediction executed")) as predict:
            result = wrapper("SP_LOW_RISK_SIGNAL", self.payloads["SP_MEDIUM_RISK_SIGNAL"])
        self.assertEqual(result.metadata["failure_reason"], "SAMPLE_PROFILE_PAYLOAD_MISMATCH")
        predict.assert_not_called()

    def test_other_valid_purpose_category_is_still_fixture_mismatch(self):
        payload = dict(self.payloads["SP_LOW_RISK_SIGNAL"]); payload["purpose"] = "car"
        result = wrapper("SP_LOW_RISK_SIGNAL", payload)
        self.assertEqual(result.metadata["failure_reason"], "SAMPLE_PROFILE_PAYLOAD_MISMATCH")

    def test_malformed_payloads_never_become_available(self):
        base = self.payloads["SP_LOW_RISK_SIGNAL"]
        variants = []
        missing = dict(base); missing.pop("dti"); variants.append(missing)
        extra = dict(base); extra["extra"] = 1; variants.append(extra)
        for bad in (float("nan"), float("inf"), float("-inf")):
            payload = dict(base); payload["dti"] = bad; variants.append(payload)
        for bad in ("unknown", 9):
            payload = dict(base); payload["purpose"] = bad; variants.append(payload)
        for payload in variants:
            result = wrapper("SP_LOW_RISK_SIGNAL", payload)
            self.assertEqual(result.inference_status, "unavailable")
            self.assertEqual(result.metadata["failure_reason"], "SAMPLE_PROFILE_PAYLOAD_MISMATCH")

    def test_prediction_frame_receives_reconstructed_payload(self):
        caller = self.payloads["SP_LOW_RISK_SIGNAL"]
        original = runtime._ordered_model_frame
        seen = []
        def inspect(payload, verified_runtime):
            seen.append(payload)
            self.assertIsNot(payload, caller)
            return original(payload, verified_runtime)
        with mock.patch.object(runtime, "_ordered_model_frame", side_effect=inspect):
            result = wrapper("SP_LOW_RISK_SIGNAL", caller)
        self.assertEqual(result.inference_status, "available")
        self.assertTrue(seen)


class StatusAndProvenanceTests(unittest.TestCase):
    def test_canonical_status_and_separate_legacy_status(self):
        success = runtime.run_committed_sample_profile_inference("SP_LOW_RISK_SIGNAL")
        failure = runtime.run_committed_sample_profile_inference("UNKNOWN")
        self.assertEqual(success.inference_status, "available")
        self.assertEqual(failure.inference_status, "unavailable")
        self.assertEqual(success.metadata["legacy_inference_status"], "DEMO_INFERENCE_READY")
        self.assertNotEqual(success.inference_status, success.metadata["legacy_inference_status"])
        self.assertIsNone(failure.calibrated_default_probability)
        self.assertIsNone(failure.threshold_relation)

    def test_verified_provenance_and_counts(self):
        result = runtime.run_committed_sample_profile_inference("SP_LOW_RISK_SIGNAL")
        self.assertEqual(result.canonical_value_source, "SYNTHETIC_BASELINE")
        self.assertEqual(result.purpose_fixture_source, "FIXED_ALLOWED_CATEGORY_REPAIR")
        self.assertEqual(result.value_source_counts, {"USER_SUPPLIED": 0, "SYNTHETIC_BASELINE": 49, "DERIVED": 0})
        self.assertEqual(set(result.limitation_aware_features), {"grade_encoded", "credit_age_months"})
        self.assertEqual(result.limitation_aware_count, 2)

    def test_forged_payload_gets_no_verified_provenance(self):
        payload = committed_payloads()["SP_LOW_RISK_SIGNAL"]; payload["dti"] = 999999
        result = wrapper("SP_LOW_RISK_SIGNAL", payload)
        self.assertIsNone(result.canonical_value_source)
        self.assertFalse(result.sample_profile_identity_verified)
        self.assertEqual(result.value_source_counts, {})


class PredictionValidationTests(unittest.TestCase):
    def test_predictions_are_finite_bounded_and_deterministic(self):
        for profile_id in runtime.AUTHORIZED_PROFILE_IDS:
            first = runtime.run_committed_sample_profile_inference(profile_id)
            second = runtime.run_committed_sample_profile_inference(profile_id)
            self.assertTrue(math.isfinite(first.calibrated_default_probability))
            self.assertGreaterEqual(first.calibrated_default_probability, 0)
            self.assertLessEqual(first.calibrated_default_probability, 1)
            self.assertAlmostEqual(first.calibrated_default_probability, second.calibrated_default_probability, delta=1e-15)
            self.assertIn(first.threshold_relation, runtime.RISK_SIGNAL_BANDS)

    def test_invalid_outputs_fail(self):
        for output in ([], [1, 2], [float("nan")]):
            with self.assertRaises(runtime.RuntimeValidationError):
                runtime._one_finite_value(output, "MODEL_OUTPUT_INVALID")
        for output in ([-.1], [1.1], [float("inf")]):
            with self.assertRaises(runtime.RuntimeValidationError):
                runtime._one_finite_value(output, "CALIBRATOR_OUTPUT_INVALID", probability=True)

    def test_runtime_exception_is_sanitized(self):
        with mock.patch.object(runtime, "_predict_frame", side_effect=RuntimeError("secret /absolute/path")):
            result = runtime.run_committed_sample_profile_inference("SP_LOW_RISK_SIGNAL")
        self.assertEqual(result.metadata["failure_reason"], "INFERENCE_RUNTIME_FAILURE")
        self.assertNotIn("secret", result.error_message)

    def test_private_file_hash_mismatch_validator(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact.bin"; path.write_bytes(b"wrong")
            with self.assertRaisesRegex(runtime.RuntimeValidationError, "MODEL_ARTIFACT_HASH_MISMATCH"):
                runtime._verify_regular_file(path, 5, "0" * 64, "MODEL_ARTIFACT_MISSING", "MODEL_ARTIFACT_HASH_MISMATCH")


class PersistedApplicationTest(unittest.TestCase):
    def test_default_streamlit_render_does_not_execute_inference(self):
        app_path = ROOT / "app/streamlit_app.py"
        with mock.patch.object(runtime, "_verified_runtime", side_effect=AssertionError("model load attempted")), \
             mock.patch.object(runtime, "_predict_frame", side_effect=AssertionError("prediction attempted")):
            app_test = AppTest.from_file(str(app_path), default_timeout=20).run()
        self.assertEqual(len(app_test.exception), 0)
        probability_metrics = [item for item in app_test.metric if "probability" in str(item.label).lower()]
        self.assertEqual(probability_metrics, [])


class StaticSafetyTests(unittest.TestCase):
    def test_ast_has_no_prohibited_calls_or_network_imports(self):
        source = Path(runtime.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_imports = {"requests", "httpx", "aiohttp", "socket", "ftplib", "subprocess", "urllib.request", "http.client"}
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import): imports.update(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom): imports.add(node.module or "")
        self.assertFalse(imports.intersection(forbidden_imports))
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        attrs = [node.func.attr for node in calls if isinstance(node.func, ast.Attribute)]
        self.assertNotIn("predict_proba", attrs)
        self.assertFalse({"system", "popen", "run", "call", "check_call", "check_output", "urlopen"}.intersection(attrs))
        for node in tree.body:
            if isinstance(node, (ast.Expr, ast.Assign, ast.AnnAssign)):
                top_calls = [n for n in ast.walk(node) if isinstance(n, ast.Call)]
                self.assertFalse(any(isinstance(c.func, ast.Attribute) and c.func.attr in {"load", "predict"} for c in top_calls))

    def test_legacy_runtime_paths_and_risk_thresholds_absent(self):
        source = Path(runtime.__file__).read_text(encoding="utf-8")
        for value in ("0.20", "0.40", "0.65", "models/final_model_calibrated.pkl", "data/splits/feature_manifest.json", "pickle.load"):
            self.assertNotIn(value, source)


if __name__ == "__main__":
    unittest.main()
