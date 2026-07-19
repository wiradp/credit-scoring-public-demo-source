"""Static Stage 9 Step 4.1A public-input constraint contract tests.

These tests validate JSON governance artifacts only. They do not import the
application, deserialize the model, or execute inference.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "outputs/stage9/stage9_public_input_constraint_contract.json"
VECTORS_PATH = ROOT / "outputs/stage9/stage9_public_input_constraint_golden_vectors.json"

EXPECTED_SOURCE_FIELDS = {
    "annual_inc", "dti", "home_ownership", "loan_amnt", "purpose", "term_months"
}
EXPECTED_METADATA_FIELDS = {
    "synthetic_baseline_profile_id", "synthetic_completion_acknowledged"
}
PROHIBITED_IDENTITY_FIELDS = {
    "full_name", "name", "nik", "national_id", "date_of_birth", "address",
    "phone", "email", "account_number", "employer_identity", "customer_id",
    "loan_account_id", "identity_document",
}
PROHIBITED_FREE_TEXT_FIELDS = {
    "personal_narrative", "narrative", "notes", "comments", "description",
    "story", "free_text",
}
EXPECTED_PURPOSES = {
    "car", "credit_card", "debt_consolidation", "educational",
    "home_improvement", "house", "major_purchase", "medical", "moving",
    "other", "renewable_energy", "small_business", "vacation", "wedding",
}
EXPECTED_BASELINES = {
    "SP_LOW_RISK_SIGNAL", "SP_MEDIUM_RISK_SIGNAL", "SP_HIGHER_RISK_SIGNAL",
    "SP_MIXED_SIGNAL", "SP_LIMITATION_TRANSPARENCY",
}
BASE_INPUTS = {
    "annual_inc": 65000.0,
    "dti": 18.27,
    "home_ownership": "MORTGAGE",
    "loan_amnt": 12000.0,
    "purpose": "other",
    "term_months": 36,
}
BASE_METADATA = {
    "synthetic_baseline_profile_id": "SP_LOW_RISK_SIGNAL",
    "synthetic_completion_acknowledged": True,
}


def _reject_constant(value: str) -> None:
    raise ValueError(f"Non-standard JSON constant: {value}")


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(
            handle,
            parse_constant=_reject_constant,
            object_pairs_hook=_reject_duplicate_keys,
        )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _numeric(value: object) -> tuple[float | None, str | None]:
    if isinstance(value, bool) or value is None or isinstance(value, (list, dict)):
        return None, "PUBLIC_INPUT_TYPE_INVALID"
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None, "PUBLIC_INPUT_TYPE_INVALID"
    if not math.isfinite(parsed):
        return None, "PUBLIC_INPUT_NON_FINITE"
    return parsed, None


def validate_vector(contract: dict, vector: dict) -> tuple[str, dict]:
    shape = vector.get("sanitized_input_shape", {})
    inputs = deepcopy(shape.get("source_inputs", BASE_INPUTS))
    metadata = deepcopy(shape.get("system_metadata", BASE_METADATA))
    target = vector.get("target_field")
    if target in EXPECTED_SOURCE_FIELDS:
        inputs[target] = vector["input_value"]
    elif target:
        metadata[target] = vector["input_value"]

    all_request_fields = set(inputs) | set(metadata)
    if all_request_fields & PROHIBITED_IDENTITY_FIELDS:
        return "PUBLIC_INPUT_IDENTITY_FIELD_PROHIBITED", {}
    if all_request_fields & PROHIBITED_FREE_TEXT_FIELDS:
        return "PUBLIC_INPUT_FREE_TEXT_PROHIBITED", {}

    actual_fields = set(inputs)
    if actual_fields - EXPECTED_SOURCE_FIELDS:
        return "PUBLIC_INPUT_FIELD_SET_INVALID", {}
    if set(metadata) - EXPECTED_METADATA_FIELDS:
        return "PUBLIC_INPUT_FIELD_SET_INVALID", {}
    if EXPECTED_SOURCE_FIELDS - actual_fields:
        return "PUBLIC_INPUT_VALUE_MISSING", {}

    normalized = {}
    for field in ("annual_inc", "dti", "loan_amnt"):
        value, error = _numeric(inputs[field])
        if error:
            return error, normalized
        limits = contract["field_constraints"][field]
        if value < limits["minimum"] or value > limits["maximum"]:
            return "PUBLIC_INPUT_OUT_OF_RANGE", normalized
        normalized[field] = value

    if inputs["home_ownership"] not in contract["field_constraints"]["home_ownership"]["public_allowed_categories"]:
        return "PUBLIC_INPUT_CATEGORY_INVALID", normalized
    if inputs["purpose"] not in contract["field_constraints"]["purpose"]["public_allowed_categories"]:
        return "PUBLIC_INPUT_CATEGORY_INVALID", normalized
    term = inputs["term_months"]
    if type(term) is not int:
        return "PUBLIC_INPUT_TERM_INVALID", normalized
    if term not in contract["field_constraints"]["term_months"]["allowed_values"]:
        return "PUBLIC_INPUT_TERM_INVALID", normalized
    if metadata.get("synthetic_baseline_profile_id") not in EXPECTED_BASELINES:
        return "PUBLIC_INPUT_BASELINE_INVALID", normalized
    if metadata.get("synthetic_completion_acknowledged") is not True:
        return "SYNTHETIC_COMPLETION_NOT_ACKNOWLEDGED", normalized
    if target in inputs and target not in normalized:
        normalized[target] = inputs[target]
    if target in metadata:
        normalized[target] = metadata[target]
    return "valid", normalized


class PublicInputConstraintContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_json(CONTRACT_PATH)
        cls.vectors = load_json(VECTORS_PATH)

    def test_json_contract_identity(self) -> None:
        self.assertEqual(self.contract["contract_id"], "STAGE9_PUBLIC_INPUT_CONSTRAINT_V1")
        self.assertEqual(self.contract["deployment_classification"], "PORTFOLIO_DEMO_ONLY")
        self.assertEqual(self.contract["validation_status"], "PASS")

    def test_exact_source_field_set_and_roles(self) -> None:
        source = self.contract["source_field_contract"]
        self.assertEqual(source["count"], 6)
        self.assertEqual(set(source["fields"]), EXPECTED_SOURCE_FIELDS)
        self.assertEqual(set(source["roles"]), EXPECTED_SOURCE_FIELDS)
        self.assertEqual(source["extra_source_field_policy"], "FAIL_CLOSED")

    def test_numeric_bounds_are_exact_train_caps(self) -> None:
        expected = {
            "annual_inc": (18500.0, 260690.31999999564),
            "dti": (2.1500000953674316, 38.720001220703125),
            "loan_amnt": (1609.7500000000082, 35000.0),
        }
        for field, bounds in expected.items():
            item = self.contract["field_constraints"][field]
            self.assertEqual((item["minimum"], item["maximum"]), bounds)
            self.assertTrue(item["minimum_inclusive"])
            self.assertTrue(item["maximum_inclusive"])
            self.assertEqual(item["selection_rule"], "TRAIN_FITTED_CAP_BOUND")
            self.assertTrue(item["finite_required"])
            self.assertFalse(item["boolean_allowed"])

    def test_categorical_and_term_allowlists(self) -> None:
        fields = self.contract["field_constraints"]
        self.assertEqual(set(fields["purpose"]["public_allowed_categories"]), EXPECTED_PURPOSES)
        self.assertEqual(fields["term_months"]["allowed_values"], [36, 60])
        self.assertEqual(fields["home_ownership"]["public_allowed_categories"], ["MORTGAGE", "OWN", "RENT", "OTHER"])
        self.assertEqual(fields["home_ownership"]["public_blocked_legacy_categories"], ["NONE", "ANY"])

    def test_strict_integer_term_policy(self) -> None:
        term = self.contract["field_constraints"]["term_months"]
        self.assertEqual(term["runtime_type_policy"], "EXACT_INTEGER_NOT_BOOLEAN")
        self.assertEqual(term["accepted_json_types"], ["integer"])
        self.assertFalse(term["integral_float_allowed"])
        self.assertFalse(term["numeric_string_allowed"])
        self.assertFalse(term["display_label_string_allowed_at_runtime_boundary"])
        for value in (36, 60):
            result, _ = validate_vector(self.contract, {"target_field": "term_months", "input_value": value})
            self.assertEqual(result, "valid")
        for value in (36.0, 60.0, "36", "60", True, False):
            result, _ = validate_vector(self.contract, {"target_field": "term_months", "input_value": value})
            self.assertEqual(result, "PUBLIC_INPUT_TERM_INVALID")

    def test_system_metadata_controls(self) -> None:
        metadata = self.contract["system_metadata_constraints"]
        self.assertEqual(set(metadata["synthetic_baseline_profile_id"]["allowed_values"]), EXPECTED_BASELINES)
        self.assertFalse(metadata["synthetic_baseline_profile_id"]["included_in_model_matrix"])
        self.assertIs(metadata["synthetic_completion_acknowledged"]["required_value"], True)
        self.assertIs(metadata["synthetic_completion_acknowledged"]["default_value"], False)

    def test_exact_system_metadata_field_set(self) -> None:
        policy = self.contract["system_metadata_field_set_policy"]
        self.assertEqual(set(policy["exact_fields"]), EXPECTED_METADATA_FIELDS)
        self.assertEqual(policy["extra_field_policy"], "FAIL_CLOSED")
        shape = {
            "source_inputs": deepcopy(BASE_INPUTS),
            "system_metadata": {**BASE_METADATA, "unexpected_metadata": "synthetic"},
        }
        result, _ = validate_vector(self.contract, {"sanitized_input_shape": shape})
        self.assertEqual(result, "PUBLIC_INPUT_FIELD_SET_INVALID")

    def test_privacy_field_precedence(self) -> None:
        registry = self.contract["privacy_and_identity_boundary"]["prohibited_field_registry"]
        self.assertEqual(set(registry["identity_field_names"]), PROHIBITED_IDENTITY_FIELDS)
        self.assertEqual(set(registry["free_text_field_names"]), PROHIBITED_FREE_TEXT_FIELDS)
        for field, code in (
            ("full_name", "PUBLIC_INPUT_IDENTITY_FIELD_PROHIBITED"),
            ("personal_narrative", "PUBLIC_INPUT_FREE_TEXT_PROHIBITED"),
        ):
            shape = {
                "source_inputs": {**BASE_INPUTS, field: "synthetic"},
                "system_metadata": deepcopy(BASE_METADATA),
            }
            result, _ = validate_vector(self.contract, {"sanitized_input_shape": shape})
            self.assertEqual(result, code)

    def test_widget_and_privacy_boundary(self) -> None:
        widgets = self.contract["widget_policy"]
        self.assertEqual(len(widgets["NUMBER_INPUT"]), 3)
        self.assertEqual(len(widgets["SELECTBOX"]), 4)
        self.assertEqual(len(widgets["CHECKBOX"]), 1)
        self.assertEqual(widgets["free_text_widget_count"], 0)
        privacy = self.contract["privacy_and_identity_boundary"]
        self.assertFalse(privacy["real_person_data_allowed"])
        self.assertFalse(privacy["persistent_storage_allowed"])
        self.assertFalse(privacy["external_transmission_allowed"])

    def test_golden_vector_summary(self) -> None:
        summary = self.vectors["summary"]
        self.assertEqual(summary, {"vector_count": 59, "valid_count": 29, "invalid_count": 30})
        self.assertEqual(len(self.vectors["vectors"]), 59)

    def test_exact_failure_code_set_coverage(self) -> None:
        expected_failure_codes = set(self.contract["expected_failure_codes"])
        vector_failure_codes = {
            vector["expected_failure_code"]
            for vector in self.vectors["vectors"]
            if vector["expected_status"] == "invalid"
        }
        self.assertEqual(len(expected_failure_codes), 11)
        self.assertEqual(vector_failure_codes, expected_failure_codes)

    def test_all_golden_vectors(self) -> None:
        for vector in self.vectors["vectors"]:
            with self.subTest(vector_id=vector["vector_id"]):
                result, normalized = validate_vector(self.contract, vector)
                expected = "valid" if vector["expected_status"] == "valid" else vector["expected_failure_code"]
                self.assertEqual(result, expected)
                expected_normalized = vector.get("expected_normalized_value")
                if isinstance(expected_normalized, dict):
                    for field, value in expected_normalized.items():
                        self.assertEqual(normalized[field], value)
                elif expected_normalized is not None:
                    self.assertEqual(normalized[vector["target_field"]], expected_normalized)

    def test_vectors_are_synthetic_and_do_not_record_outputs(self) -> None:
        privacy = self.vectors["privacy"]
        self.assertFalse(privacy["personal_data_used"])
        self.assertTrue(privacy["synthetic_vectors_only"])
        self.assertFalse(privacy["model_payload_recorded"])
        self.assertFalse(privacy["probability_recorded"])
        self.assertFalse(self.vectors["model_inference_executed"])

    def test_numeric_evidence_field_to_cap_associations(self) -> None:
        evidence = self.contract["numeric_evidence_reproduction"]
        cleaning = evidence["cleaning_artifact_extraction"]
        self.assertEqual(cleaning["source_relative_path"], "artifacts/cleaning_artifacts.pkl")
        self.assertEqual(cleaning["source_size_bytes"], 1048)
        self.assertEqual(cleaning["source_sha256"], "27030ab2de846e97360e9549836847bfa45b48ecd81c9ec1af76c8658dd453bd")
        self.assertFalse(cleaning["pickle_deserialized"])
        associations = cleaning["field_cap_associations"]
        self.assertEqual({row["field"] for row in associations}, {"annual_inc", "dti", "loan_amnt"})
        self.assertEqual(len(associations), 3)
        expected = {
            "annual_inc": (18500.0, 260690.31999999564),
            "dti": (2.1500000953674316, 38.720001220703125),
            "loan_amnt": (1609.7500000000082, 35000.0),
        }
        for row in associations:
            self.assertEqual((row["lower_cap"], row["upper_cap"]), expected[row["field"]])
            self.assertTrue(math.isfinite(row["lower_cap"]))
            self.assertTrue(math.isfinite(row["upper_cap"]))
            field_contract = self.contract["field_constraints"][row["field"]]
            self.assertEqual((field_contract["minimum"], field_contract["maximum"]), expected[row["field"]])

    def test_numeric_summary_snapshot_and_reconciliation(self) -> None:
        evidence = self.contract["numeric_evidence_reproduction"]
        summary = evidence["numeric_summary_extraction"]
        self.assertEqual(summary["source_relative_path"], "reports/numeric_describe.csv")
        self.assertEqual(summary["source_size_bytes"], 3768)
        self.assertEqual(summary["source_sha256"], "0a856b761a5cf4e3a2aa80d334ea52cd8dc1138ecc434f927f9d67da663347b8")
        self.assertEqual({row["field"] for row in summary["rows"]}, {"annual_inc", "dti", "loan_amnt"})
        self.assertEqual(len(summary["rows"]), 3)
        for row in summary["rows"]:
            self.assertEqual(hashlib.sha256(row["canonical_serialized_row"].encode()).hexdigest(), row["canonical_row_sha256"])
            self.assertEqual(len(row["canonical_row_sha256"]), 64)
        for row in evidence["cross_source_reconciliation"]:
            lower, upper = row["train_fitted_cap_range"]
            historical_min, historical_max = row["numeric_summary_range"]
            self.assertTrue(historical_min <= lower <= upper <= historical_max)
            self.assertEqual(row["selected_public_range"], row["train_fitted_cap_range"])
            self.assertTrue(row["selected_equals_cap_range"])
            self.assertEqual(row["reconciliation_status"], "PASS")

    def test_dti_percentage_point_scale(self) -> None:
        dti = self.contract["field_constraints"]["dti"]
        self.assertEqual(dti["scale_semantics"], "PERCENTAGE_POINTS")
        self.assertEqual(dti["display_label_guidance"], "Debt-to-income ratio (%)")
        self.assertEqual(dti["runtime_value_expected"], "18.27-style percentage-point value")
        self.assertEqual(dti["fractional_unit_conversion"], "PROHIBITED")

    def test_no_runtime_or_model_imports(self) -> None:
        tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        prohibited = {
            "app", "joblib", "pickle", "streamlit", "numpy", "pandas",
            "sklearn", "subprocess", "socket", "http", "urllib", "requests",
        }
        self.assertTrue(imported.isdisjoint(prohibited))

    def test_frozen_application_and_step4_test_hashes(self) -> None:
        expected = {
            "app/src/demo_inference.py": "1eb8fdf3a39e4775f5817c2a4620dc7c6669d0d7ad844932f411fc25ebbc9074",
            "tests/test_stage9_controlled_runtime_adapter.py": "fa277e2a3fc323739e1e86e9e2b51ea779cbc836f7a43980189ffef449cac2b8",
            "outputs/stage9/stage9_public_inference_contract.json": "8fb783382577d73ed6d329baa8d82432c538d16a91b224a2f30987a8c795ea47",
            "outputs/stage9/stage9_sample_profile_categorical_repair_contract.json": "98b391bd31af98d7ff51cf1d92c848d170df93ec2bbf30e9e0d2b161874b1482",
            "artifacts/contracts/cell_group_7/sample_profiles/sample_profile_feature_matrix.csv": "c16f1786900ae0ec7878aac2dbc87018c34de459ae9a36dfabf0a43ca92f1bd6",
            "artifacts/contracts/manifest/cell_group_7_contract_export_manifest.json": "626c5369dfe9a70ed2b37bd3aa43fb90abc0c2466f2b0635e41b4728e7adfbf9",
        }
        for relative_path, digest in expected.items():
            self.assertEqual(sha256(ROOT / relative_path), digest)

    def test_non_goals_and_authorization_remain_closed(self) -> None:
        non_goals = self.contract["non_goals"]
        self.assertFalse(non_goals["application_source_modified"])
        self.assertFalse(non_goals["model_inference_executed"])
        self.assertFalse(non_goals["public_deployment_performed"])
        authorization = self.contract["next_step_authorization"]
        self.assertFalse(authorization["stage9_step4_1b_authorized"])
        self.assertFalse(authorization["stage9_step5_rerun_authorized"])
        self.assertFalse(authorization["public_deployment_authorized"])


if __name__ == "__main__":
    unittest.main()
