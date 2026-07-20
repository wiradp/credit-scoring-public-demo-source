"""Stage 9 Step 5 public-input and Streamlit integration tests."""

from __future__ import annotations

import ast
import copy
import hashlib
import inspect
import json
import math
import unittest
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from unittest import mock

from app.src import demo_inference as frozen_adapter
from app.src import pages
from app.src import advanced_editor_runtime as advanced_runtime_module
from app.src.advanced_editor_inference import run_advanced_editor_inference
from app.src.advanced_editor_runtime import (
    AdvancedEditorValidationError,
    AdvancedEditorValidationResult,
    advanced_editor_contract_summary,
    validate_advanced_editor_request,
)
from app.src.basic_form_inference import run_basic_form_inference
from app.src.ui_text import PUBLIC_DEMO_RESULT_DISCLOSURE


ROOT = Path(__file__).resolve().parents[1]
PROFILE_IDS = (
    "SP_LOW_RISK_SIGNAL",
    "SP_MEDIUM_RISK_SIGNAL",
    "SP_HIGHER_RISK_SIGNAL",
    "SP_MIXED_SIGNAL",
    "SP_LIMITATION_TRANSPARENCY",
)
RESET_PROBABILITIES = {
    "SP_LOW_RISK_SIGNAL": 0.18398918594172425,
    "SP_MEDIUM_RISK_SIGNAL": 0.35650623885918004,
    "SP_HIGHER_RISK_SIGNAL": 0.31875881523272215,
    "SP_MIXED_SIGNAL": 0.400390625,
    "SP_LIMITATION_TRANSPARENCY": 0.4418604651162791,
}
FROZEN_HASHES = {
    "app/src/demo_inference.py": "1eb8fdf3a39e4775f5817c2a4620dc7c6669d0d7ad844932f411fc25ebbc9074",
    "app/src/basic_form_runtime.py": "71bae84c24c2cc3f07a1ec02377f8065064db0551d2f77cc5727129c2bdaf50e",
    "app/src/basic_form_inference.py": "04d52edf6216d9970a4b42773596541b2a07cb4ba294eeae73eecfb68b37b728",
    "outputs/stage9/stage9_advanced_editor_validation_contract.json": "47b688fa8620a6691ac535d686912c5ca732313e16b0ee1ea4dff214f6c750ac",
    "artifacts/model/model_artifact_manifest.json": "9c49149b1a3f72fc6e0f6fe5e5efa84f5c81f65224c1bd08daded1f6231461fd",
    "artifacts/model/final_model_calibrated.pkl": "b022b545bd7bb4294018a26a7d10af977e3c452b7f219dbdd9113adeac367cbf",
    "artifacts/model/final_threshold.json": "e45a19822f77d6b74cf5e76c0c0e6ff2f993bad4ab91e507509b3d74d410e28b",
    "artifacts/contracts/cell_group_7/sample_profiles/sample_profile_feature_matrix.csv": "c16f1786900ae0ec7878aac2dbc87018c34de459ae9a36dfabf0a43ca92f1bd6",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Step5Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.summary = advanced_editor_contract_summary()
        cls.order = tuple(cls.summary["ordered_feature_names"])
        cls.registry = {row["feature_name"]: dict(row) for row in cls.summary["feature_registry"]}
        cls.projections = cls.summary["canonical_reset_projections"]
        cls.basic_vectors = json.loads(
            (ROOT / "outputs/stage9/stage9_basic_form_runtime_mapping_golden_vectors.json").read_text()
        )["request_level_vectors"]
        contract = json.loads(
            (ROOT / "outputs/stage9/stage9_advanced_editor_validation_contract.json").read_text()
        )
        cls.projection_fingerprints = {
            row["profile_id"]: row["expected_payload_fingerprint"]
            for row in contract["canonical_reset_projections"]
        }

    def request(self, profile_id: str = PROFILE_IDS[0]) -> dict[str, object]:
        base = self.projections[profile_id]
        return {
            "mode": "ADVANCED_EDITOR",
            "system_metadata": {
                "advanced_editor_profile_id": profile_id,
                "advanced_editor_acknowledged": True,
                "edited_feature_names": [],
            },
            "payload_rows": [
                {"feature_index": index, "feature_name": name, "value": base[name]}
                for index, name in enumerate(self.order)
            ],
        }

    def set_value(self, request: dict[str, object], feature: str, value: object) -> None:
        for row in request["payload_rows"]:  # type: ignore[index]
            if row["feature_name"] == feature:
                row["value"] = value
                return
        self.fail(feature)

    def assert_invalid_without_runtime(self, request: object) -> str:
        with (
            mock.patch.object(frozen_adapter, "_verified_runtime") as runtime,
            mock.patch.object(frozen_adapter, "_ordered_model_frame") as frame,
            mock.patch.object(frozen_adapter, "_predict_frame") as predict,
        ):
            result = run_advanced_editor_inference(request)  # type: ignore[arg-type]
        runtime.assert_not_called()
        frame.assert_not_called()
        predict.assert_not_called()
        self.assertEqual(result.inference_status, frozen_adapter.UNAVAILABLE)
        self.assertIsNone(result.calibrated_default_probability)
        return str(result.metadata.get("failure_reason"))


class FrozenIntegrityTests(Step5Base):
    def test_frozen_artifact_hashes(self) -> None:
        for relative_path, expected in FROZEN_HASHES.items():
            with self.subTest(path=relative_path):
                self.assertEqual(sha256(ROOT / relative_path), expected)

    def test_contract_identity_and_profile_allowlist(self) -> None:
        self.assertEqual(self.summary["contract_id"], "STAGE9_ADVANCED_EDITOR_VALIDATION_V1")
        self.assertEqual(tuple(self.summary["profile_ids"]), PROFILE_IDS)
        self.assertEqual(len(self.order), 49)


class DeepImmutableAuthorityTests(Step5Base):
    def test_internal_authority_is_recursively_immutable(self) -> None:
        contract, order, registry, projections = advanced_runtime_module._authority()
        self.assertIsInstance(contract, MappingProxyType)
        self.assertIsInstance(registry, MappingProxyType)
        self.assertIsInstance(projections, MappingProxyType)
        self.assertIsInstance(order, tuple)
        self.assertIsInstance(registry["term_months"], MappingProxyType)
        self.assertIsInstance(registry["term_months"]["allowed_values"], tuple)
        self.assertIsInstance(registry["term_months"]["reset_values_by_profile"], MappingProxyType)
        self.assertIsInstance(projections[PROFILE_IDS[0]], MappingProxyType)

    def test_public_summary_is_deeply_immutable(self) -> None:
        summary = advanced_editor_contract_summary()
        term = next(row for row in summary["feature_registry"] if row["feature_name"] == "term_months")
        with self.assertRaises(TypeError):
            summary["contract_id"] = "changed"  # type: ignore[index]
        with self.assertRaises(AttributeError):
            summary["feature_registry"].append({})  # type: ignore[union-attr]
        with self.assertRaises(TypeError):
            term["editable"] = False  # type: ignore[index]
        with self.assertRaises(AttributeError):
            term["allowed_values"].append(48)  # type: ignore[union-attr]
        with self.assertRaises(TypeError):
            term["allowed_values"][0] = 48  # type: ignore[index]
        with self.assertRaises(TypeError):
            term["reset_values_by_profile"][PROFILE_IDS[0]] = 48  # type: ignore[index]
        with self.assertRaises(TypeError):
            term["reset_projection_sources"][PROFILE_IDS[0]] = "forged"  # type: ignore[index]
        with self.assertRaises(TypeError):
            summary["canonical_reset_projections"][PROFILE_IDS[0]]["term_months"] = 48  # type: ignore[index]

    def test_separate_summary_calls_have_no_mutable_aliases(self) -> None:
        first = advanced_editor_contract_summary()
        second = advanced_editor_contract_summary()
        self.assertIsNot(first, second)
        self.assertIsNot(first["feature_registry"], second["feature_registry"])
        self.assertIsNot(first["feature_registry"][43], second["feature_registry"][43])
        self.assertIsNot(
            first["feature_registry"][43]["reset_values_by_profile"],
            second["feature_registry"][43]["reset_values_by_profile"],
        )
        self.assertIsNot(first["canonical_reset_projections"], second["canonical_reset_projections"])
        self.assertIsNot(
            first["canonical_reset_projections"][PROFILE_IDS[0]],
            second["canonical_reset_projections"][PROFILE_IDS[0]],
        )

    def test_cached_authority_cannot_be_poisoned(self) -> None:
        authority_before = advanced_runtime_module._authority()
        summary = advanced_editor_contract_summary()
        term = next(row for row in summary["feature_registry"] if row["feature_name"] == "term_months")
        purpose = next(row for row in summary["feature_registry"] if row["feature_name"] == "purpose")
        flag = next(row for row in summary["feature_registry"] if row["feature_name"] == "is_60_month")
        attempts = (
            lambda: term["allowed_values"].append(48),
            lambda: term["allowed_values"].__setitem__(0, 48),
            lambda: term["reset_values_by_profile"].__setitem__(PROFILE_IDS[0], 48),
            lambda: term["reset_projection_sources"].__setitem__(PROFILE_IDS[0], "forged"),
            lambda: summary["canonical_reset_projections"][PROFILE_IDS[0]].__setitem__("term_months", 48),
        )
        for attempt in attempts:
            with self.assertRaises((TypeError, AttributeError)):
                attempt()
        self.assertIs(advanced_runtime_module._authority(), authority_before)
        self.assertEqual(term["allowed_values"], (36, 60))
        self.assertEqual(flag["allowed_values"], (0, 1))
        self.assertNotIn("INJECTED_CATEGORY", purpose["allowed_values"])

        request = self.request(); self.set_value(request, "term_months", 48)
        request["system_metadata"]["edited_feature_names"] = ["term_months"]  # type: ignore[index]
        self.assertEqual(self.assert_invalid_without_runtime(request), "ADVANCED_EDITOR_EXACT_INTEGER_INVALID")
        request = self.request(); self.set_value(request, "purpose", "INJECTED_CATEGORY")
        request["system_metadata"]["edited_feature_names"] = ["purpose"]  # type: ignore[index]
        self.assertEqual(self.assert_invalid_without_runtime(request), "ADVANCED_EDITOR_CATEGORY_INVALID")
        request = self.request(); self.set_value(request, "is_60_month", 2)
        self.assertEqual(self.assert_invalid_without_runtime(request), "ADVANCED_EDITOR_EXACT_INTEGER_INVALID")

    def test_resets_retain_fingerprints_after_mutation_attempts(self) -> None:
        summary = advanced_editor_contract_summary()
        term = next(row for row in summary["feature_registry"] if row["feature_name"] == "term_months")
        with self.assertRaises(AttributeError):
            term["allowed_values"].append(48)  # type: ignore[union-attr]
        for profile_id in PROFILE_IDS:
            with self.subTest(profile_id=profile_id):
                validated = validate_advanced_editor_request(self.request(profile_id))
                self.assertEqual(
                    validated.payload_fingerprint,
                    self.projection_fingerprints[profile_id],
                )
                inferred = run_advanced_editor_inference(self.request(profile_id))
                self.assertEqual(inferred.calibrated_default_probability, RESET_PROBABILITIES[profile_id])


class AdvancedEditorValidationTests(Step5Base):
    def test_exact_reset_request_and_fingerprint(self) -> None:
        result = validate_advanced_editor_request(self.request())
        self.assertEqual(result.validation_status, "VALID")
        self.assertEqual(result.ordered_feature_names, self.order)
        self.assertEqual(len(result.payload_fingerprint), 64)
        self.assertEqual(dict(result.provenance_counts), {"USER_EDITED": 0, "CANONICAL_RESET_PROJECTION": 49})

    def test_result_is_sealed_immutable_and_payload_not_in_repr(self) -> None:
        result = validate_advanced_editor_request(self.request())
        self.assertNotIn("validated_canonical_payload", repr(result))
        with self.assertRaises(TypeError):
            result.validated_canonical_payload["dti"] = 0  # type: ignore[index]
        with self.assertRaises(TypeError):
            AdvancedEditorValidationResult(  # type: ignore[call-arg]
                mode="ADVANCED_EDITOR", profile_id=PROFILE_IDS[0], ordered_feature_names=(),
                validated_canonical_payload={}, payload_fingerprint="", edited_feature_names=(),
                provenance_counts={}, limitation_aware_features=(), safe_disclosure="",
                validation_status="VALID", _seal=object(),
            )

    def test_exact_request_and_metadata_shapes(self) -> None:
        for mutation in ("missing", "extra"):
            request = self.request()
            if mutation == "missing":
                request.pop("mode")
            else:
                request["extra"] = True
            with self.subTest(mutation=mutation), self.assertRaises(AdvancedEditorValidationError):
                validate_advanced_editor_request(request)
        request = self.request()
        request["system_metadata"]["extra"] = True  # type: ignore[index]
        with self.assertRaises(AdvancedEditorValidationError):
            validate_advanced_editor_request(request)

    def test_acknowledgement_and_profile_fail_closed(self) -> None:
        request = self.request()
        request["system_metadata"]["advanced_editor_acknowledged"] = False  # type: ignore[index]
        self.assertEqual(self.assert_invalid_without_runtime(request), "ADVANCED_EDITOR_ACKNOWLEDGEMENT_REQUIRED")
        request = self.request()
        request["system_metadata"]["advanced_editor_profile_id"] = "UNKNOWN"  # type: ignore[index]
        self.assertEqual(self.assert_invalid_without_runtime(request), "ADVANCED_EDITOR_PROFILE_ID_INVALID")

    def test_order_index_duplicate_and_row_shape_fail_closed(self) -> None:
        mutations = []
        wrong_order = self.request(); wrong_order["payload_rows"][0], wrong_order["payload_rows"][1] = wrong_order["payload_rows"][1], wrong_order["payload_rows"][0]  # type: ignore[index]
        mutations.append(wrong_order)
        wrong_index = self.request(); wrong_index["payload_rows"][0]["feature_index"] = 1  # type: ignore[index]
        mutations.append(wrong_index)
        duplicate = self.request(); duplicate["payload_rows"][1]["feature_name"] = duplicate["payload_rows"][0]["feature_name"]  # type: ignore[index]
        mutations.append(duplicate)
        extra = self.request(); extra["payload_rows"][0]["extra"] = 1  # type: ignore[index]
        mutations.append(extra)
        for request in mutations:
            with self.subTest(case=len(request["payload_rows"])):
                self.assert_invalid_without_runtime(request)

    def test_category_discrete_exact_integer_and_envelope_validation(self) -> None:
        bad = (("purpose", "invalid"), ("bankruptcy_flag", 99), ("term_months", 48), ("dti", -1.0))
        for feature, value in bad:
            request = self.request(); self.set_value(request, feature, value)
            request["system_metadata"]["edited_feature_names"] = [feature]  # type: ignore[index]
            with self.subTest(feature=feature):
                self.assert_invalid_without_runtime(request)

    def test_boolean_nonfinite_null_and_nested_values_fail_closed(self) -> None:
        for value in (True, float("nan"), float("inf"), None, {"nested": 1}, [1]):
            request = self.request(); self.set_value(request, "dti", value)
            request["system_metadata"]["edited_feature_names"] = ["dti"]  # type: ignore[index]
            with self.subTest(value=repr(value)):
                self.assert_invalid_without_runtime(request)

    def test_locks_and_term_flag_invariant(self) -> None:
        for feature in ("grade_encoded", "credit_age_months"):
            request = self.request(); self.set_value(request, feature, float(self.projections[PROFILE_IDS[0]][feature]) + 1)
            self.assert_invalid_without_runtime(request)
        request = self.request(); self.set_value(request, "term_months", 60)
        request["system_metadata"]["edited_feature_names"] = ["term_months"]  # type: ignore[index]
        self.assertEqual(self.assert_invalid_without_runtime(request), "ADVANCED_EDITOR_RELATIONSHIP_INVALID")
        request = self.request(); request["system_metadata"]["edited_feature_names"] = ["is_60_month"]  # type: ignore[index]
        self.assertEqual(self.assert_invalid_without_runtime(request), "ADVANCED_EDITOR_LOCKED_FEATURE_EDITED")

    def test_exact_edited_difference_set_and_provenance(self) -> None:
        request = self.request(); self.set_value(request, "dti", 12.5)
        self.assertEqual(self.assert_invalid_without_runtime(request), "ADVANCED_EDITOR_EDITED_FEATURE_SET_MISMATCH")
        request["system_metadata"]["edited_feature_names"] = ["dti"]  # type: ignore[index]
        result = validate_advanced_editor_request(request)
        self.assertEqual(result.edited_feature_names, ("dti",))
        self.assertEqual(dict(result.provenance_counts), {"USER_EDITED": 1, "CANONICAL_RESET_PROJECTION": 48})

    def test_hidden_edit_has_exact_semantics_and_failure_code(self) -> None:
        request = self.request()
        self.assertEqual(self.projections[PROFILE_IDS[0]]["dti"], 18.27)
        self.set_value(request, "dti", 12.5)
        self.assertEqual(request["system_metadata"]["edited_feature_names"], [])  # type: ignore[index]
        self.assertEqual(
            self.assert_invalid_without_runtime(request),
            "ADVANCED_EDITOR_EDITED_FEATURE_SET_MISMATCH",
        )

    def test_false_edit_declaration_has_exact_semantics_and_failure_code(self) -> None:
        request = self.request()
        self.assertEqual(
            next(row["value"] for row in request["payload_rows"] if row["feature_name"] == "dti"),  # type: ignore[index]
            18.27,
        )
        request["system_metadata"]["edited_feature_names"] = ["dti"]  # type: ignore[index]
        self.assertEqual(
            self.assert_invalid_without_runtime(request),
            "ADVANCED_EDITOR_EDITED_FEATURE_SET_MISMATCH",
        )

    def test_extra_payload_row_has_exact_semantics_and_failure_code(self) -> None:
        request = self.request()
        request["payload_rows"].append(  # type: ignore[union-attr]
            {"feature_index": 49, "feature_name": "extra", "value": 1}
        )
        self.assertEqual(
            self.assert_invalid_without_runtime(request),
            "ADVANCED_EDITOR_PAYLOAD_ROW_COUNT_INVALID",
        )

    def test_privacy_fields_fail_closed(self) -> None:
        for field in ("full_name", "national_id", "personal_narrative", "free_text_notes"):
            request = self.request(); request["system_metadata"][field] = "prohibited"  # type: ignore[index]
            with self.subTest(field=field):
                self.assert_invalid_without_runtime(request)


class AtomicInferenceTests(Step5Base):
    def test_public_api_accepts_only_raw_request(self) -> None:
        self.assertEqual(list(inspect.signature(run_advanced_editor_inference).parameters), ["request"])
        result = validate_advanced_editor_request(self.request())
        self.assert_invalid_without_runtime(result)
        with self.assertRaises(TypeError):
            run_advanced_editor_inference(self.request(), payload={})  # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            run_advanced_editor_inference(self.request(), contract_path="x")  # type: ignore[call-arg]

    def test_all_five_resets_have_exact_probability_parity_and_repeat(self) -> None:
        for profile_id, expected in RESET_PROBABILITIES.items():
            with self.subTest(profile_id=profile_id):
                first = run_advanced_editor_inference(self.request(profile_id))
                second = run_advanced_editor_inference(self.request(profile_id))
                self.assertEqual(first.inference_status, frozen_adapter.AVAILABLE)
                self.assertEqual(first.calibrated_default_probability, expected)
                self.assertEqual(second.calibrated_default_probability, expected)

    def test_representative_valid_edits_infer(self) -> None:
        cases = [
            (PROFILE_IDS[0], "dti", 12.5),
            (PROFILE_IDS[0], "purpose", "car"),
            (PROFILE_IDS[0], "bankruptcy_flag", 1),
            (PROFILE_IDS[0], "term_months", 60),
            (PROFILE_IDS[1], "term_months", 36),
        ]
        for profile_id, feature, value in cases:
            request = self.request(profile_id); self.set_value(request, feature, value)
            if feature == "term_months":
                self.set_value(request, "is_60_month", int(value == 60))
            request["system_metadata"]["edited_feature_names"] = [feature]  # type: ignore[index]
            with self.subTest(feature=feature, profile=profile_id):
                result = run_advanced_editor_inference(request)
                self.assertEqual(result.inference_status, frozen_adapter.AVAILABLE)
                self.assertTrue(math.isfinite(result.calibrated_default_probability))  # type: ignore[arg-type]
                self.assertGreaterEqual(result.calibrated_default_probability, 0)  # type: ignore[operator]
                self.assertLessEqual(result.calibrated_default_probability, 1)  # type: ignore[operator]
                self.assertEqual(result.metadata["edited_feature_names"], [feature])

    def test_seven_basic_vectors_still_infer_deterministically(self) -> None:
        for vector in self.basic_vectors:
            first = run_basic_form_inference(vector["source_inputs"], vector["system_metadata"])
            second = run_basic_form_inference(vector["source_inputs"], vector["system_metadata"])
            with self.subTest(vector=vector["vector_id"]):
                self.assertEqual(first.inference_status, frozen_adapter.AVAILABLE)
                self.assertEqual(first.calibrated_default_probability, second.calibrated_default_probability)

    def test_five_sample_profiles_still_infer(self) -> None:
        for profile_id in PROFILE_IDS:
            with self.subTest(profile_id=profile_id):
                result = frozen_adapter.run_committed_sample_profile_inference(profile_id)
                self.assertEqual(result.inference_status, frozen_adapter.AVAILABLE)

    def test_invalid_smoke_matrix_never_accesses_runtime(self) -> None:
        invalid: list[tuple[str, dict[str, object], str]] = []
        false_ack = self.request(); false_ack["system_metadata"]["advanced_editor_acknowledged"] = False  # type: ignore[index]
        invalid.append(("FALSE_ACKNOWLEDGEMENT", false_ack, "ADVANCED_EDITOR_ACKNOWLEDGEMENT_REQUIRED"))
        unknown = self.request(); unknown["system_metadata"]["advanced_editor_profile_id"] = "UNKNOWN"  # type: ignore[index]
        invalid.append(("UNKNOWN_PROFILE", unknown, "ADVANCED_EDITOR_PROFILE_ID_INVALID"))
        hidden_edit = self.request(); self.set_value(hidden_edit, "dti", 12.5)
        invalid.append(("HIDDEN_EDIT", hidden_edit, "ADVANCED_EDITOR_EDITED_FEATURE_SET_MISMATCH"))
        false_edit = self.request(); false_edit["system_metadata"]["edited_feature_names"] = ["dti"]  # type: ignore[index]
        invalid.append(("FALSE_EDIT_DECLARATION", false_edit, "ADVANCED_EDITOR_EDITED_FEATURE_SET_MISMATCH"))
        extra_row = self.request(); extra_row["payload_rows"].append({"feature_index": 49, "feature_name": "extra", "value": 1})  # type: ignore[union-attr]
        invalid.append(("EXTRA_PAYLOAD_ROW", extra_row, "ADVANCED_EDITOR_PAYLOAD_ROW_COUNT_INVALID"))
        locked_grade = self.request(); self.set_value(locked_grade, "grade_encoded", 99)
        locked_age = self.request(); self.set_value(locked_age, "credit_age_months", 99)
        flag_edit = self.request(); flag_edit["system_metadata"]["edited_feature_names"] = ["is_60_month"]  # type: ignore[index]
        invalid.extend([
            ("LOCKED_GRADE_EDIT", locked_grade, "ADVANCED_EDITOR_LOCKED_VALUE_MISMATCH"),
            ("LOCKED_CREDIT_AGE_EDIT", locked_age, "ADVANCED_EDITOR_LOCKED_VALUE_MISMATCH"),
            ("DIRECT_TERM_FLAG_EDIT", flag_edit, "ADVANCED_EDITOR_LOCKED_FEATURE_EDITED"),
        ])
        mismatch = self.request(); self.set_value(mismatch, "term_months", 60); mismatch["system_metadata"]["edited_feature_names"] = ["term_months"]  # type: ignore[index]
        invalid.append(("TERM_FLAG_MISMATCH", mismatch, "ADVANCED_EDITOR_RELATIONSHIP_INVALID"))
        value_cases = (
            ("OUT_OF_RANGE_NUMBER", "dti", -1, "ADVANCED_EDITOR_VALUE_OUT_OF_RANGE"),
            ("INVALID_CATEGORY", "purpose", "INVALID", "ADVANCED_EDITOR_CATEGORY_INVALID"),
            ("BOOLEAN_NUMERIC", "dti", True, "ADVANCED_EDITOR_BOOLEAN_VALUE_INVALID"),
            ("NAN_NUMERIC", "dti", float("nan"), "ADVANCED_EDITOR_NON_FINITE_VALUE"),
            ("INFINITY_NUMERIC", "dti", float("inf"), "ADVANCED_EDITOR_NON_FINITE_VALUE"),
        )
        for case_id, feature, value, failure_code in value_cases:
            request = self.request(); self.set_value(request, feature, value); request["system_metadata"]["edited_feature_names"] = [feature]  # type: ignore[index]
            invalid.append((case_id, request, failure_code))
        for case_id, field, failure_code in (
            ("IDENTITY_FIELD_INJECTION", "full_name", "ADVANCED_EDITOR_IDENTITY_FIELD_PROHIBITED"),
            ("FREE_TEXT_INJECTION", "free_text_notes", "ADVANCED_EDITOR_FREE_TEXT_FIELD_PROHIBITED"),
        ):
            request = self.request(); request["system_metadata"][field] = "prohibited"  # type: ignore[index]
            invalid.append((case_id, request, failure_code))
        wrong_order = self.request(); wrong_order["payload_rows"][0], wrong_order["payload_rows"][1] = wrong_order["payload_rows"][1], wrong_order["payload_rows"][0]  # type: ignore[index]
        invalid.append(("WRONG_FEATURE_ORDER", wrong_order, "ADVANCED_EDITOR_FEATURE_INDEX_INVALID"))
        self.assertEqual(len(invalid), 17)
        self.assertEqual(len({case_id for case_id, _, _ in invalid}), 17)
        for case_id, request, failure_code in invalid:
            with self.subTest(case=case_id):
                self.assertEqual(self.assert_invalid_without_runtime(request), failure_code)


class RuntimeProgressMetadataTests(Step5Base):
    def assert_progress(
        self,
        result: frozen_adapter.DemoInferenceResult,
        expected: tuple[bool, bool, bool, bool],
    ) -> None:
        keys = ("runtime_loaded", "frame_constructed", "prediction_started", "prediction_completed")
        self.assertEqual(tuple(result.metadata[key] for key in keys), expected)
        self.assertEqual(result.metadata["model_loaded"], expected[0])
        self.assertEqual(result.metadata["inference_executed"], expected[3])
        self.assertTrue(result.metadata["safe_failure"])
        self.assertIsNone(result.calibrated_default_probability)

    def test_validation_failure_progress_metadata(self) -> None:
        request = self.request()
        request["system_metadata"]["advanced_editor_acknowledged"] = False  # type: ignore[index]
        with mock.patch.object(frozen_adapter, "_verified_runtime") as runtime:
            result = run_advanced_editor_inference(request)
        runtime.assert_not_called()
        self.assert_progress(result, (False, False, False, False))

    def test_runtime_load_failure_progress_metadata(self) -> None:
        with mock.patch.object(
            frozen_adapter,
            "_verified_runtime",
            side_effect=frozen_adapter.RuntimeValidationError("MODEL_ARTIFACT_HASH_MISMATCH"),
        ):
            result = run_advanced_editor_inference(self.request())
        self.assert_progress(result, (False, False, False, False))

    def test_frame_failure_progress_metadata(self) -> None:
        runtime = SimpleNamespace(threshold=0.1)
        with (
            mock.patch.object(frozen_adapter, "_verified_runtime", return_value=runtime),
            mock.patch.object(
                frozen_adapter,
                "_ordered_model_frame",
                side_effect=frozen_adapter.RuntimeValidationError("FEATURE_ORDER_MISMATCH"),
            ),
            mock.patch.object(frozen_adapter, "_predict_frame") as predict,
        ):
            result = run_advanced_editor_inference(self.request())
        predict.assert_not_called()
        self.assert_progress(result, (True, False, False, False))

    def test_prediction_failure_progress_metadata(self) -> None:
        runtime = SimpleNamespace(threshold=0.1)
        frame = object()
        with (
            mock.patch.object(frozen_adapter, "_verified_runtime", return_value=runtime),
            mock.patch.object(frozen_adapter, "_ordered_model_frame", return_value=frame),
            mock.patch.object(
                frozen_adapter,
                "_predict_frame",
                side_effect=frozen_adapter.RuntimeValidationError("MODEL_OUTPUT_INVALID"),
            ),
        ):
            result = run_advanced_editor_inference(self.request())
        self.assert_progress(result, (True, True, True, False))

    def test_post_prediction_output_failure_progress_metadata(self) -> None:
        runtime = SimpleNamespace(threshold=0.1)
        with (
            mock.patch.object(frozen_adapter, "_verified_runtime", return_value=runtime),
            mock.patch.object(frozen_adapter, "_ordered_model_frame", return_value=object()),
            mock.patch.object(frozen_adapter, "_predict_frame", return_value=(float("nan"), 0.5)),
        ):
            result = run_advanced_editor_inference(self.request())
        self.assert_progress(result, (True, True, True, True))


class RoutingAndUiTests(Step5Base):
    def test_three_mode_routes_are_explicit_and_do_not_masquerade(self) -> None:
        sentinel = object()
        with mock.patch.object(pages, "run_safe_demo_inference", return_value=sentinel) as sample:
            self.assertIs(pages.run_public_mode_inference("SAMPLE_PROFILE", sample_profile_payload_result=object()), sentinel)
            sample.assert_called_once()
        with mock.patch.object(pages, "run_basic_form_inference", return_value=sentinel) as basic:
            self.assertIs(pages.run_public_mode_inference("BASIC_FORM", basic_form_source_inputs={}, basic_form_system_metadata={}), sentinel)
            basic.assert_called_once_with({}, {})
        with mock.patch.object(pages, "run_advanced_editor_inference", return_value=sentinel) as advanced:
            self.assertIs(pages.run_public_mode_inference("ADVANCED_EDITOR", advanced_editor_request={}), sentinel)
            advanced.assert_called_once_with({})
        blocked = pages.run_public_mode_inference("CANONICAL_PAYLOAD")
        self.assertEqual(blocked.inference_status, frozen_adapter.UNAVAILABLE)

    def test_basic_ui_uses_exact_six_field_contract_and_false_acknowledgement(self) -> None:
        contract = pages._basic_form_ui_contract()
        self.assertEqual(
            set(contract["field_constraints"]),
            {"annual_inc", "dti", "home_ownership", "loan_amnt", "purpose", "term_months"},
        )
        self.assertFalse(contract["system_metadata_constraints"]["synthetic_completion_acknowledged"]["default_value"])

    def test_ui_source_has_three_modes_explicit_submit_and_no_input_upload(self) -> None:
        source = (ROOT / "app/src/pages.py").read_text()
        for text in ("Basic Form", "Sample Profiles", "Advanced Editor — Technical Mode", "Run controlled inference"):
            self.assertIn(text, (ROOT / "app/src/mode_view.py").read_text() + source)
        self.assertIn("value=False", source)
        for forbidden in ("text_input(", "text_area(", "file_uploader(", "camera_input("):
            self.assertNotIn(forbidden, source)

    def test_required_disclosure_and_safe_result_fields_present(self) -> None:
        disclosure = (
            "This output is a fictional portfolio demonstration and is not a lending "
            "decision, approval recommendation, rejection recommendation, legal "
            "assessment, fairness conclusion, or production underwriting result."
        )
        self.assertEqual(PUBLIC_DEMO_RESULT_DISCLOSURE, disclosure)
        preview = (ROOT / "app/src/payload_preview.py").read_text()
        self.assertIn("Estimated model default-risk probability", preview)
        self.assertNotIn("st.json(result.payload)", inspect.getsource(pages.render_safe_demo_inference))

    def test_static_source_has_no_runtime_duplication_network_or_persistence(self) -> None:
        source = (ROOT / "app/src/advanced_editor_inference.py").read_text()
        tree = ast.parse(source)
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        self.assertFalse(any(isinstance(node.func, ast.Attribute) and node.func.attr == "load" and isinstance(node.func.value, ast.Name) and node.func.value.id == "joblib" for node in calls))
        imported_roots = {
            node.names[0].name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom)) and node.names
        }
        self.assertTrue({"requests", "urllib", "socket"}.isdisjoint(imported_roots))
        for forbidden in ("telemetry", "analytics", "fallback_probability", "open(", "write_text", "write_bytes"):
            self.assertNotIn(forbidden, source)
        self.assertIn("frozen_adapter._verified_runtime", source)
        self.assertIn("frozen_adapter._ordered_model_frame", source)
        self.assertIn("frozen_adapter._predict_frame", source)

    def test_streamlit_default_and_inference_page_render_without_exception(self) -> None:
        from streamlit.testing.v1 import AppTest

        app = AppTest.from_file(str(ROOT / "app/streamlit_app.py"), default_timeout=30).run()
        self.assertEqual(len(app.exception), 0)
        app.sidebar.radio[0].set_value("Safe Demo Inference").run()
        self.assertEqual(len(app.exception), 0)
        public_radios = [radio for radio in app.radio if radio.label == "Public Input Mode"]
        self.assertEqual(len(public_radios), 1)
        self.assertEqual(public_radios[0].value, "Basic Form")
        self.assertTrue(all(not checkbox.value for checkbox in app.checkbox))
        self.assertFalse(any("Controlled Inference Result" in title.value for title in app.subheader))

    def test_advanced_editor_profile_a_to_b_to_a_resets_widget_state(self) -> None:
        from streamlit.testing.v1 import AppTest

        app = AppTest.from_file(str(ROOT / "app/streamlit_app.py"), default_timeout=30).run()
        app.sidebar.radio[0].set_value("Safe Demo Inference").run()
        next(radio for radio in app.radio if radio.label == "Public Input Mode").set_value(
            "Advanced Editor — Technical Mode"
        ).run()

        def number(label: str):
            return next(widget for widget in app.number_input if widget.label == label)

        def select(label: str):
            return next(widget for widget in app.selectbox if widget.label == label)

        def result_present() -> bool:
            return any("Controlled Inference Result" in title.value for title in app.subheader)

        self.assertEqual(select("Canonical reset profile").value, PROFILE_IDS[0])
        self.assertEqual(number("dti").value, self.projections[PROFILE_IDS[0]]["dti"])
        self.assertFalse(app.checkbox[0].value)
        number("dti").set_value(15.0)
        app.checkbox[0].set_value(True)
        app.run()
        self.assertEqual(number("dti").value, 15.0)
        self.assertTrue(app.checkbox[0].value)
        self.assertFalse(result_present())

        select("Canonical reset profile").set_value(PROFILE_IDS[1]).run()
        self.assertEqual(number("dti").value, self.projections[PROFILE_IDS[1]]["dti"])
        self.assertEqual(select("term_months").value, 60)
        self.assertIn(
            "is_60_month: 1 (read-only; derived from term_months)",
            [caption.value for caption in app.caption],
        )
        self.assertFalse(app.checkbox[0].value)
        self.assertFalse(result_present())

        select("Canonical reset profile").set_value(PROFILE_IDS[0]).run()
        self.assertEqual(number("dti").value, self.projections[PROFILE_IDS[0]]["dti"])
        self.assertNotEqual(number("dti").value, 15.0)
        self.assertEqual(select("term_months").value, 36)
        self.assertIn(
            "is_60_month: 0 (read-only; derived from term_months)",
            [caption.value for caption in app.caption],
        )
        self.assertFalse(app.checkbox[0].value)
        self.assertFalse(result_present())
        self.assertEqual(len(app.exception), 0)


if __name__ == "__main__":
    unittest.main()
