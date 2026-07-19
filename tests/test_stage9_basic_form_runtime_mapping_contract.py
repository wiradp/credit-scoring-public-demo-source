"""Self-contained Stage 9 Step 4.1B mapping-contract tests.

The suite reads committed JSON/CSV fixtures only. It does not import the
application, deserialize the model, execute prediction, or generate a
probability.
"""

from __future__ import annotations

import ast
import copy
import csv
import hashlib
import json
import math
import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "outputs/stage9/stage9_basic_form_runtime_mapping_contract.json"
VECTORS_PATH = ROOT / "outputs/stage9/stage9_basic_form_runtime_mapping_golden_vectors.json"
INPUT_CONTRACT_PATH = ROOT / "outputs/stage9/stage9_public_input_constraint_contract.json"
MODEL_MANIFEST_PATH = ROOT / "artifacts/model/model_artifact_manifest.json"
MATRIX_PATH = ROOT / "artifacts/contracts/cell_group_7/sample_profiles/sample_profile_feature_matrix.csv"


def _reject_constant(value: str) -> None:
    raise ValueError(f"Non-standard JSON constant: {value}")


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle, parse_constant=_reject_constant, object_pairs_hook=_unique_object)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def float32(value: float) -> float:
    return struct.unpack(">f", struct.pack(">f", float(value)))[0]


def float32_bits(value: float) -> int:
    return struct.unpack(">I", struct.pack(">f", float(value)))[0]


def load_profiles() -> dict[str, list[dict]]:
    with MATRIX_PATH.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    profiles: dict[str, list[dict]] = {}
    for row in rows:
        profiles.setdefault(row["profile_id"], []).append(row)
    return profiles


def profile_payload(rows: list[dict]) -> dict[str, object]:
    payload = {}
    for row in rows:
        feature = row["canonical_feature"]
        value = row["synthetic_value"]
        payload[feature] = value if feature == "purpose" else float(value)
    return payload


def operation_by_target(contract: dict) -> dict[str, dict]:
    return {
        item["target_feature"]: item
        for item in contract["operation_registry"]
        if "target_feature" in item
    }


class MappingFailure(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def resolve_contract_reference(contract: dict, reference: str) -> object:
    value: object = contract
    for part in reference.split("."):
        if not isinstance(value, dict) or part not in value:
            raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        value = value[part]
    return value


def validate_fingerprint_contract(contract: dict) -> tuple[dict[str, set[str]], list[str], dict[str, str]]:
    try:
        policy = contract["payload_fingerprint_contract"]
        partition = contract["fingerprint_representation_partition_contract"]
        classes = policy["feature_representation_classes"]
    except (KeyError, TypeError) as error:
        raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID") from error
    supported = {
        "algorithm": "SHA-256",
        "input_encoding": "UTF-8",
        "record_format": "feature_index|feature_name|logical_type_tag|canonical_value_representation",
        "record_separator": "LF",
        "float32_derived_representation": "UNSIGNED_32_BIT_IEEE754_BITS_BASE10",
        "direct_user_numeric_representation": "PYTHON_FORMAT_DOT_17G_FLOAT64",
        "baseline_numeric_representation": "PYTHON_FORMAT_DOT_17G_FLOAT64",
        "exact_integer_representation": "BASE10_INTEGER_TEXT",
        "purpose_representation": "EXACT_UTF8_CATEGORY",
    }
    if any(policy.get(key) != value for key, value in supported.items()):
        raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    tags = policy.get("type_tags")
    if tags != {"category": "CATEGORY", "exact_integer": "INT8", "numeric": "NUMERIC"}:
        raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    expected_names = ["direct_user_numeric", "exact_integer", "float32_derived", "category", "baseline_numeric"]
    expected_counts = {"direct_user_numeric": 2, "exact_integer": 2, "float32_derived": 6, "category": 1, "baseline_numeric": 38, "total": 49}
    if partition.get("class_names") != expected_names or partition.get("class_counts") != expected_counts:
        raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    try:
        raw_classes = {
            "direct_user_numeric": classes["direct_user_numeric"],
            "exact_integer": classes["exact_integer"],
            "float32_derived": classes["float32_derived"],
            "category": classes["category"],
            "baseline_numeric": resolve_contract_reference(contract, classes["baseline_numeric_reference"]),
        }
        ordered = resolve_contract_reference(contract, policy["canonical_feature_order_reference"])
    except (KeyError, TypeError) as error:
        raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID") from error
    if not isinstance(ordered, list) or any(not isinstance(value, list) for value in raw_classes.values()):
        raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    for name, values in raw_classes.items():
        if len(values) != expected_counts[name] or len(set(values)) != len(values):
            raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    class_sets = {name: set(values) for name, values in raw_classes.items()}
    union = set().union(*class_sets.values())
    if sum(len(values) for values in class_sets.values()) != len(union):
        raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    if len(union) != expected_counts["total"] or union != set(ordered):
        raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    if class_sets["baseline_numeric"] != set(contract["dependency_partition"]["synthetic_baseline_passthrough"]):
        raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    if not all(partition.get(field) is expected for field, expected in (
        ("classes_pairwise_disjoint", True),
        ("union_equals_exact_model_feature_set", True),
        ("duplicates_within_class_allowed", False),
        ("unclassified_features_allowed", False),
        ("non_model_features_allowed", False),
        ("baseline_numeric_must_equal_baseline_passthrough_set", True),
    )):
        raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    return class_sets, ordered, tags


def validate_mapping_contract(contract: dict) -> None:
    required_sections = {
        "operation_type_allowlist", "operation_registry", "operation_parameter_contract",
        "operation_execution_order", "exact_operation_registry_contract", "assembly_algorithm",
        "dependency_partition", "model_feature_contract", "source_field_contract",
        "available_context_contract", "operand_reference_contract", "provenance_contract",
        "payload_fingerprint_contract", "fingerprint_representation_partition_contract",
    }
    if not isinstance(contract, dict) or not required_sections <= set(contract):
        raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    allowed = set(contract["operation_type_allowlist"])
    registry = contract["operation_registry"]
    schemas = contract["operation_parameter_contract"]
    order = contract["operation_execution_order"]
    closure = contract["exact_operation_registry_contract"]
    if not isinstance(registry, list) or not isinstance(order, list) or not isinstance(schemas, dict):
        raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")

    for operation in registry:
        if not isinstance(operation, dict):
            raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        operation_type = operation.get("operation_type")
        if operation_type is not None and operation_type not in allowed:
            raise MappingFailure("BASIC_FORM_OPERATION_TYPE_INVALID")

    registry_ids = [operation.get("operation_id") for operation in registry]
    expected_registry_ids = set(order) | {"PRESERVE_BASELINE"}
    baseline_operations = [operation for operation in registry if operation.get("operation_type") == "BASELINE_PASSTHROUGH"]
    if (
        len(registry) != 12
        or len(registry_ids) != len(set(registry_ids))
        or set(registry_ids) != expected_registry_ids
        or len(baseline_operations) != 1
        or baseline_operations[0].get("operation_id") != "PRESERVE_BASELINE"
        or closure.get("expected_registry_count") != 12
        or closure.get("expected_executable_operation_count") != 11
        or closure.get("expected_baseline_passthrough_operation_count") != 1
        or closure.get("baseline_passthrough_operation_id") != "PRESERVE_BASELINE"
        or set(closure.get("expected_registry_operation_ids", [])) != expected_registry_ids
        or closure.get("registry_identity_rule") != "SET_EQUALS_OPERATION_EXECUTION_ORDER_UNION_PRESERVE_BASELINE"
        or closure.get("operation_ids_unique") is not True
        or closure.get("unused_operations_allowed") is not False
        or closure.get("unexpected_operations_allowed") is not False
        or closure.get("missing_operations_allowed") is not False
    ):
        raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")

    assembly = contract["assembly_algorithm"]
    if (
        assembly.get("baseline_passthrough_precedes_operation_sequence") is not True
        or assembly.get("request_assembly_uses_operation_registry") is not True
        or assembly.get("hardcoded_derived_formula_path_allowed") is not False
    ):
        raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    allowed_sources = set(contract["provenance_contract"]["allowed_value_sources"])
    for operation in registry:
        operation_type = operation.get("operation_type")
        schema = schemas.get(operation_type)
        if not schema or any(field not in operation for field in schema["required_fields"]):
            raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        if not isinstance(operation["operation_id"], str) or not operation["operation_id"] or operation["value_source"] not in allowed_sources:
            raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        if "source_field_count" in schema and (not isinstance(operation["source_fields"], list) or len(operation["source_fields"]) != schema["source_field_count"]):
            raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        if operation_type != "BASELINE_PASSTHROUGH" and (
            not isinstance(operation["target_feature"], str)
            or not isinstance(operation["source_fields"], list)
            or not all(isinstance(field, str) and field for field in operation["source_fields"])
        ):
            raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        if operation_type == "IDENTITY_NUMERIC":
            if operation["logical_type"] != "finite numeric" or operation["value_source"] != "USER_SUPPLIED":
                raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        elif operation_type == "IDENTITY_EXACT_INTEGER":
            values = operation["allowed_values"]
            if operation["runtime_type_policy"] != "EXACT_INTEGER_NOT_BOOLEAN" or not isinstance(values, list) or not values or any(type(value) is not int for value in values) or len(set(values)) != len(values) or operation["value_source"] != "USER_SUPPLIED":
                raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        elif operation_type == "IDENTITY_CATEGORICAL":
            if not isinstance(operation["allowed_values_reference"], str) or operation["value_source"] != "USER_SUPPLIED":
                raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        elif operation_type == "LOG1P_FLOAT32":
            if operation["function"] != schema["supported_function"] or operation["positive_finite_input_required"] is not True or operation["output_dtype"] != "float32" or operation["cast_count"] != 1 or operation["value_source"] != "DERIVED":
                raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        elif operation_type == "ORDINAL_MAP_FLOAT32":
            if operation["validate_allowlist_first"] is not True or operation["unknown_fallback_used"] is not False or operation["output_dtype"] != "float32" or operation["cast_count"] != 1 or not isinstance(operation["mapping_reference"], str) or operation["value_source"] != "DERIVED":
                raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        elif operation_type == "RATIO_CLIP_FLOAT32":
            denominator = operation["denominator"]
            if not isinstance(denominator, dict) or any(field not in denominator for field in schema["denominator_required_fields"]):
                raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
            try:
                divide_by = float(denominator["divide_by"])
                lower, upper = float(operation["clip_lower"]), float(operation["clip_upper"])
            except (TypeError, ValueError) as error:
                raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID") from error
            if isinstance(denominator["divide_by"], bool) or not math.isfinite(divide_by) or divide_by <= 0 or not all(math.isfinite(value) for value in (lower, upper)) or lower > upper:
                raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
            if operation["numerator"] not in operation["source_fields"] or denominator["field"] not in operation["source_fields"] or operation["output_dtype"] != "float32" or operation["cast_count"] != 1 or operation["value_source"] != "DERIVED":
                raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        elif operation_type == "EQUALS_FLAG_INT8":
            if operation["output_dtype"] != "int8" or {operation["true_output"], operation["false_output"]} != {0, 1} or operation["value_source"] != "DERIVED":
                raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        elif operation_type == "BASELINE_PASSTHROUGH":
            if operation["exact_identity_required"] is not True or operation["value_source"] != "SYNTHETIC_BASELINE" or not isinstance(operation["target_features_reference"], str):
                raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")

    expected_order = ["DIRECT_DTI", "DIRECT_LOAN_AMNT", "DIRECT_PURPOSE", "DIRECT_TERM", "DERIVE_LOG_ANNUAL_INC", "DERIVE_LOG_LOAN_AMNT", "DERIVE_HOME_OWNERSHIP", "DERIVE_PAYMENT_TO_INCOME", "DERIVE_LOAN_TO_INCOME", "DERIVE_DEBT_TO_INCOME_REVOL", "DERIVE_IS_60_MONTH"]
    by_id = {item["operation_id"]: item for item in registry}
    if order != expected_order or len(set(order)) != 11 or any(operation_id not in by_id for operation_id in order):
        raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    targets = [by_id[operation_id]["target_feature"] for operation_id in order]
    authorized = set(contract["dependency_partition"]["direct_user_supplied"]) | set(contract["dependency_partition"]["derived"])
    if len(set(targets)) != 11 or set(targets) != authorized:
        raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")

    context_policy = contract["available_context_contract"]
    reference_policy = contract["operand_reference_contract"]
    public_sources = set(context_policy.get("initial_public_source_fields", []))
    baseline_features = set(resolve_contract_reference(contract, context_policy["initial_baseline_feature_reference"]))
    if public_sources != set(contract["source_field_contract"]["exact_fields"]) or len(public_sources) != 6 or len(baseline_features) != 49:
        raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    if (
        context_policy.get("initial_context_public_source_count") != 6
        or context_policy.get("initial_context_baseline_feature_count") != 49
        or set(context_policy.get("metadata_excluded_from_operand_context", [])) != {"synthetic_baseline_profile_id", "synthetic_completion_acknowledged"}
        or context_policy.get("operation_target_becomes_available_after_execution") is not True
        or reference_policy.get("public_source_fields_reference") != "available_context_contract.initial_public_source_fields"
        or reference_policy.get("baseline_canonical_features_reference") != "available_context_contract.initial_baseline_feature_reference"
        or reference_policy.get("prior_operation_targets_follow_execution_order") is not True
        or reference_policy.get("unresolved_references_allowed") is not False
        or any(reference_policy.get(field) is not True for field in (
            "source_fields_must_resolve_before_execution",
            "ratio_numerator_must_resolve_before_execution",
            "ratio_denominator_field_must_resolve_before_execution",
            "mapping_reference_must_resolve_before_execution",
            "allowed_values_reference_must_resolve_before_execution",
            "target_must_be_authorized_model_feature",
        ))
    ):
        raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    expected_classification = {
        "annual_inc": ["PUBLIC_SOURCE_FIELD"],
        "dti": ["PUBLIC_SOURCE_FIELD", "BASELINE_CANONICAL_FEATURE"],
        "home_ownership": ["PUBLIC_SOURCE_FIELD"],
        "loan_amnt": ["PUBLIC_SOURCE_FIELD", "BASELINE_CANONICAL_FEATURE"],
        "purpose": ["PUBLIC_SOURCE_FIELD", "BASELINE_CANONICAL_FEATURE"],
        "term_months": ["PUBLIC_SOURCE_FIELD", "BASELINE_CANONICAL_FEATURE"],
        "installment": ["BASELINE_CANONICAL_FEATURE"],
        "revol_bal": ["BASELINE_CANONICAL_FEATURE"],
    }
    if reference_policy.get("allowed_source_classifications") != ["PUBLIC_SOURCE_FIELD", "BASELINE_CANONICAL_FEATURE", "PRIOR_OPERATION_TARGET"] or reference_policy.get("required_operand_classification") != expected_classification:
        raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    available = public_sources | baseline_features
    prior_targets: set[str] = set()
    for operation_id in order:
        operation = by_id[operation_id]
        references = set(operation["source_fields"])
        if operation["operation_type"] == "RATIO_CLIP_FLOAT32":
            references |= {operation["numerator"], operation["denominator"]["field"]}
        if not references <= available:
            raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        for reference in references:
            classifications = set()
            if reference in public_sources:
                classifications.add("PUBLIC_SOURCE_FIELD")
            if reference in baseline_features:
                classifications.add("BASELINE_CANONICAL_FEATURE")
            if reference in prior_targets:
                classifications.add("PRIOR_OPERATION_TARGET")
            if not classifications:
                raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        if operation["operation_type"] == "IDENTITY_CATEGORICAL":
            allowed_values = resolve_contract_reference(contract, operation["allowed_values_reference"])
            if not isinstance(allowed_values, list) or not allowed_values:
                raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        if operation["operation_type"] == "ORDINAL_MAP_FLOAT32":
            mapping = resolve_contract_reference(contract, operation["mapping_reference"])
            if not isinstance(mapping, dict) or not mapping:
                raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        target = operation["target_feature"]
        if target not in authorized or target not in baseline_features:
            raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        available.add(target)
        prior_targets.add(target)
    baseline_targets = resolve_contract_reference(contract, by_id["PRESERVE_BASELINE"]["target_features_reference"])
    if set(baseline_targets) != set(contract["dependency_partition"]["synthetic_baseline_passthrough"]):
        raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    validate_fingerprint_contract(contract)


def evaluate_operation(operation_type: str, operands: dict, contract: dict) -> object:
    if operation_type == "IDENTITY_NUMERIC":
        value = operands["value"]
        if isinstance(value, bool) or not math.isfinite(float(value)):
            raise ValueError("invalid numeric identity")
        return float(value)
    if operation_type == "IDENTITY_EXACT_INTEGER":
        if type(operands["value"]) is not int:
            raise ValueError("invalid exact integer")
        return operands["value"]
    if operation_type == "IDENTITY_CATEGORICAL":
        if type(operands["value"]) is not str:
            raise ValueError("invalid category")
        return operands["value"]
    if operation_type == "LOG1P_FLOAT32":
        value = float(operands["value"])
        if not math.isfinite(value) or value <= 0:
            raise ValueError("invalid log input")
        return float32(math.log1p(value))
    if operation_type == "ORDINAL_MAP_FLOAT32":
        mapping = contract["home_ownership_mapping"]["public_mapping"]
        if operands["value"] not in mapping:
            raise ValueError("unknown category")
        return float32(mapping[operands["value"]])
    if operation_type == "RATIO_CLIP_FLOAT32":
        numerator = float(operands["numerator"])
        denominator = float(operands["denominator"])
        if not all(math.isfinite(v) for v in (numerator, denominator)) or denominator == 0:
            raise ValueError("invalid ratio")
        value = numerator / denominator
        value = min(float(operands["clip_upper"]), max(float(operands["clip_lower"]), value))
        return float32(value)
    if operation_type == "EQUALS_FLAG_INT8":
        return 1 if operands["value"] == operands["comparison_value"] else 0
    if operation_type == "BASELINE_PASSTHROUGH":
        return copy.deepcopy(operands["value"])
    raise ValueError("unsupported operation type")


def validate_public_request(source: dict, metadata: dict, input_contract: dict) -> None:
    expected_source = set(input_contract["source_field_contract"]["fields"])
    expected_metadata = set(input_contract["system_metadata_field_set_policy"]["exact_fields"])
    if set(source) != expected_source or set(metadata) != expected_metadata:
        raise ValueError("field set invalid")
    if metadata["synthetic_completion_acknowledged"] is not True:
        raise ValueError("acknowledgement invalid")
    for field in ("annual_inc", "dti", "loan_amnt"):
        value = source[field]
        if isinstance(value, bool) or not math.isfinite(float(value)):
            raise ValueError("numeric invalid")
        rule = input_contract["field_constraints"][field]
        if not rule["minimum"] <= float(value) <= rule["maximum"]:
            raise ValueError("range invalid")
    if type(source["term_months"]) is not int or source["term_months"] not in (36, 60):
        raise ValueError("term invalid")
    if source["home_ownership"] not in input_contract["field_constraints"]["home_ownership"]["public_allowed_categories"]:
        raise ValueError("home invalid")
    if source["purpose"] not in input_contract["field_constraints"]["purpose"]["public_allowed_categories"]:
        raise ValueError("purpose invalid")


def validate_baseline_profile(contract: dict, profile_id: str, rows: list[dict]) -> dict[str, object]:
    baseline_contract = contract["baseline_profile_contract"]
    if profile_id not in baseline_contract["allowed_profile_ids"]:
        raise MappingFailure("BASIC_FORM_BASELINE_ID_INVALID")
    if any(row["mapping_status"] not in baseline_contract["allowed_mapping_statuses"] for row in rows):
        raise MappingFailure("BASIC_FORM_BASELINE_NOT_READY")
    limitation_contract = contract["limitation_status_contract"]
    alignment_contract = contract["row_level_limitation_alignment_contract"]
    required = set(resolve_contract_reference(contract, baseline_contract["required_limitation_aware_features_reference"]))
    declared = set(resolve_contract_reference(contract, alignment_contract["limitation_status_contract_reference"]))
    row_limitation_features = {
        row["canonical_feature"] for row in rows
        if row["mapping_status"] == "READY_WITH_LIMITATION"
    }
    if (
        baseline_contract["ready_with_limitation_requires_limitation_contract_active"] is not True
        or limitation_contract["complete"] is not True
        or alignment_contract["exact_set_equality_required"] is not True
        or alignment_contract["required_row_level_limitation_count_per_profile"] != 2
        or alignment_contract["required_ready_count_per_profile"] != 47
        or alignment_contract["row_status_for_required_features"] != "READY_WITH_LIMITATION"
        or alignment_contract["row_status_for_all_other_features"] != "READY"
        or required != {"grade_encoded", "credit_age_months"}
        or declared != required
        or row_limitation_features != required
    ):
        raise MappingFailure("BASIC_FORM_BASELINE_NOT_READY")
    names = [row["canonical_feature"] for row in rows]
    if any(dependency not in names for dependency in baseline_contract["required_dependencies"]):
        raise MappingFailure("BASIC_FORM_BASELINE_DEPENDENCY_MISSING")
    if len(rows) != baseline_contract["required_row_count_per_profile"]:
        raise MappingFailure("BASIC_FORM_BASELINE_FEATURE_COUNT_INVALID")
    if len(set(names)) != len(names):
        raise MappingFailure("BASIC_FORM_BASELINE_FEATURE_DUPLICATE")
    if set(names) != set(contract["model_feature_contract"]["ordered_feature_names"]):
        raise MappingFailure("BASIC_FORM_BASELINE_FEATURE_SET_MISMATCH")
    purpose_categories = set(contract["purpose_categorical_transport"]["exact_category_order"])
    purpose_rows = [row for row in rows if row["canonical_feature"] == "purpose"]
    if len(purpose_rows) != 1 or type(purpose_rows[0]["synthetic_value"]) is not str or purpose_rows[0]["synthetic_value"] not in purpose_categories:
        raise MappingFailure("BASIC_FORM_BASELINE_VALUE_INVALID")
    payload = {}
    for row in rows:
        feature = row["canonical_feature"]
        raw_value = row["synthetic_value"]
        if feature == "purpose":
            payload[feature] = raw_value
            continue
        try:
            value = float(raw_value)
        except (TypeError, ValueError) as error:
            raise MappingFailure("BASIC_FORM_BASELINE_VALUE_INVALID") from error
        if isinstance(raw_value, bool) or not math.isfinite(value):
            raise MappingFailure("BASIC_FORM_BASELINE_VALUE_INVALID")
        payload[feature] = value
    if any(row["payload_compatible"] != "True" for row in rows):
        raise MappingFailure("BASIC_FORM_BASELINE_NOT_READY")
    return payload


def evaluate_operation_from_contract(operation: dict, context: dict, contract: dict) -> object:
    operation_type = operation["operation_type"]
    source_fields = operation.get("source_fields", [])
    try:
        operands = {field: context[field] for field in source_fields}
    except KeyError as error:
        raise MappingFailure("BASIC_FORM_DERIVED_VALUE_INVALID") from error
    if operation_type == "IDENTITY_NUMERIC":
        value = operands[source_fields[0]]
        if isinstance(value, bool) or not math.isfinite(float(value)):
            raise MappingFailure("BASIC_FORM_DERIVED_VALUE_INVALID")
        return float(value)
    if operation_type == "IDENTITY_EXACT_INTEGER":
        value = operands[source_fields[0]]
        if type(value) is not int or value not in operation["allowed_values"]:
            raise MappingFailure("BASIC_FORM_DERIVED_VALUE_INVALID")
        return value
    if operation_type == "IDENTITY_CATEGORICAL":
        value = operands[source_fields[0]]
        allowed = resolve_contract_reference(contract, operation["allowed_values_reference"])
        if type(value) is not str or value not in allowed:
            raise MappingFailure("BASIC_FORM_DERIVED_VALUE_INVALID")
        return value
    if operation_type == "LOG1P_FLOAT32":
        if operation["function"] != "NATURAL_LOG1P":
            raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        value = float(operands[source_fields[0]])
        if operation["positive_finite_input_required"] and (not math.isfinite(value) or value <= 0):
            raise MappingFailure("BASIC_FORM_DERIVED_VALUE_INVALID")
        result = float32(math.log1p(value))
    elif operation_type == "ORDINAL_MAP_FLOAT32":
        mapping = resolve_contract_reference(contract, operation["mapping_reference"])
        value = operands[source_fields[0]]
        if value not in mapping:
            raise MappingFailure("BASIC_FORM_DERIVED_VALUE_INVALID")
        result = float32(mapping[value])
    elif operation_type == "RATIO_CLIP_FLOAT32":
        numerator = float(context[operation["numerator"]])
        denominator_spec = operation["denominator"]
        denominator = float(context[denominator_spec["field"]]) / float(denominator_spec["divide_by"])
        if not all(math.isfinite(value) for value in (numerator, denominator)) or denominator == 0:
            raise MappingFailure("BASIC_FORM_DERIVED_VALUE_INVALID")
        arithmetic = numerator / denominator
        if not math.isfinite(arithmetic):
            raise MappingFailure("BASIC_FORM_DERIVED_VALUE_INVALID")
        clipped = min(float(operation["clip_upper"]), max(float(operation["clip_lower"]), arithmetic))
        result = float32(clipped)
    elif operation_type == "EQUALS_FLAG_INT8":
        result = operation["true_output"] if operands[source_fields[0]] == operation["comparison_value"] else operation["false_output"]
        if type(result) is not int or result not in (0, 1):
            raise MappingFailure("BASIC_FORM_DERIVED_VALUE_INVALID")
        return result
    else:
        raise MappingFailure("BASIC_FORM_OPERATION_TYPE_INVALID")
    if not math.isfinite(result):
        raise MappingFailure("BASIC_FORM_DERIVED_VALUE_INVALID")
    return result


def payload_fingerprint_from_contract(contract: dict, payload: dict) -> str:
    policy = contract["payload_fingerprint_contract"]
    class_sets, ordered, tags = validate_fingerprint_contract(contract)
    direct_numeric = class_sets["direct_user_numeric"]
    exact_integer = class_sets["exact_integer"]
    float32_derived = class_sets["float32_derived"]
    categories = class_sets["category"]
    baseline_numeric = class_sets["baseline_numeric"]
    records = []
    for index, feature in enumerate(ordered):
        value = payload[feature]
        if feature in categories:
            tag, representation = tags["category"], str(value)
        elif feature in exact_integer:
            tag, representation = tags["exact_integer"], str(int(value))
        elif feature in float32_derived:
            tag, representation = tags["numeric"], str(float32_bits(value))
        elif feature in direct_numeric or feature in baseline_numeric:
            tag, representation = tags["numeric"], format(float(value), ".17g")
        else:
            raise MappingFailure("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        records.append(f"{index}|{feature}|{tag}|{representation}")
    separator = {"LF": "\n"}[policy["record_separator"]]
    encoded = separator.join(records).encode({"UTF-8": "utf-8"}[policy["input_encoding"]])
    return {"SHA-256": hashlib.sha256}[policy["algorithm"]](encoded).hexdigest()


def assemble_from_mapping_contract(
    contract: dict,
    input_contract: dict,
    profiles: dict,
    source: dict,
    metadata: dict,
    operation_evaluator=evaluate_operation_from_contract,
    expected_fingerprint: str | None = None,
) -> tuple[dict, dict, str]:
    validate_public_request(source, metadata, input_contract)
    validate_mapping_contract(contract)
    profile_id = metadata["synthetic_baseline_profile_id"]
    if profile_id not in profiles:
        raise MappingFailure("BASIC_FORM_BASELINE_ID_INVALID")
    baseline = validate_baseline_profile(contract, profile_id, profiles[profile_id])
    passthrough = contract["dependency_partition"]["synthetic_baseline_passthrough"]
    payload = {feature: copy.deepcopy(baseline[feature]) for feature in passthrough}
    context = {**baseline, **source, **payload}
    by_id = {item["operation_id"]: item for item in contract["operation_registry"]}
    authorized = set(contract["dependency_partition"]["direct_user_supplied"]) | set(contract["dependency_partition"]["derived"])
    for operation_id in contract["operation_execution_order"]:
        operation = by_id[operation_id]
        target = operation["target_feature"]
        if target not in authorized:
            raise MappingFailure("BASIC_FORM_IMPACT_CLOSURE_INVALID")
        value = operation_evaluator(operation, context, contract)
        if target in contract["dependency_partition"]["derived"]:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise MappingFailure("BASIC_FORM_DERIVED_VALUE_INVALID")
            if operation["operation_type"] == "EQUALS_FLAG_INT8" and (type(value) is not int or value not in (0, 1)):
                raise MappingFailure("BASIC_FORM_DERIVED_VALUE_INVALID")
            if operation.get("output_dtype") == "float32" and float32(value) != value:
                raise MappingFailure("BASIC_FORM_DERIVED_VALUE_INVALID")
        payload[target] = value
        context[target] = value
    if set(payload) != set(contract["model_feature_contract"]["ordered_feature_names"]):
        raise MappingFailure("BASIC_FORM_IMPACT_CLOSURE_INVALID")
    ordered_payload = {feature: payload[feature] for feature in contract["model_feature_contract"]["ordered_feature_names"]}
    if contract["provenance_contract"]["counts"] != {"USER_SUPPLIED": 4, "DERIVED": 7, "SYNTHETIC_BASELINE": 38, "TOTAL": 49}:
        raise MappingFailure("BASIC_FORM_PROVENANCE_INVALID")
    if set(contract["limitation_status_contract"]["limitation_aware_features"]) != {"grade_encoded", "credit_age_months"}:
        raise MappingFailure("BASIC_FORM_LIMITATION_STATUS_INVALID")
    fingerprint = payload_fingerprint_from_contract(contract, ordered_payload)
    if expected_fingerprint is not None and fingerprint != expected_fingerprint:
        raise MappingFailure("BASIC_FORM_PAYLOAD_FINGERPRINT_MISMATCH")
    return baseline, ordered_payload, fingerprint


def validate_mapping_state(
    contract: dict,
    profile_id: str,
    rows: list[dict],
    operation_types: set[str],
    model_order: list[str],
    overwrite_set: set[str],
    provenance_counts: dict[str, int],
    limitation_set: set[str],
) -> str:
    if profile_id not in contract["baseline_profile_contract"]["allowed_profile_ids"]:
        return "BASIC_FORM_BASELINE_ID_INVALID"
    names = [row["canonical_feature"] for row in rows]
    if "installment" not in names or "revol_bal" not in names:
        return "BASIC_FORM_BASELINE_DEPENDENCY_MISSING"
    if len(names) != 49:
        return "BASIC_FORM_BASELINE_FEATURE_COUNT_INVALID"
    if len(set(names)) != len(names):
        return "BASIC_FORM_BASELINE_FEATURE_DUPLICATE"
    expected = set(contract["model_feature_contract"]["ordered_feature_names"])
    if set(names) != expected:
        return "BASIC_FORM_BASELINE_FEATURE_SET_MISMATCH"
    values = profile_payload(rows)
    if not math.isfinite(values["installment"]) or not math.isfinite(values["revol_bal"]):
        return "BASIC_FORM_BASELINE_VALUE_INVALID"
    if not operation_types <= set(contract["operation_type_allowlist"]):
        return "BASIC_FORM_OPERATION_TYPE_INVALID"
    authorized = set(contract["dependency_partition"]["direct_user_supplied"]) | set(contract["dependency_partition"]["derived"])
    if overwrite_set != authorized:
        return "BASIC_FORM_IMPACT_CLOSURE_INVALID"
    if model_order != contract["model_feature_contract"]["ordered_feature_names"]:
        return "BASIC_FORM_MODEL_ORDER_INVALID"
    if provenance_counts != {"USER_SUPPLIED": 4, "DERIVED": 7, "SYNTHETIC_BASELINE": 38, "TOTAL": 49}:
        return "BASIC_FORM_PROVENANCE_INVALID"
    if limitation_set != {"grade_encoded", "credit_age_months"}:
        return "BASIC_FORM_LIMITATION_STATUS_INVALID"
    return "valid"


class BasicFormRuntimeMappingContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_json(CONTRACT_PATH)
        cls.vectors = load_json(VECTORS_PATH)
        cls.input_contract = load_json(INPUT_CONTRACT_PATH)
        cls.model_manifest = load_json(MODEL_MANIFEST_PATH)
        cls.profiles = load_profiles()

    def test_frozen_artifact_integrity(self) -> None:
        expected = {
            "app/src/demo_inference.py": "1eb8fdf3a39e4775f5817c2a4620dc7c6669d0d7ad844932f411fc25ebbc9074",
            "tests/test_stage9_controlled_runtime_adapter.py": "fa277e2a3fc323739e1e86e9e2b51ea779cbc836f7a43980189ffef449cac2b8",
            "outputs/stage9/stage9_public_inference_contract.json": "8fb783382577d73ed6d329baa8d82432c538d16a91b224a2f30987a8c795ea47",
            "outputs/stage9/stage9_public_input_constraint_contract.json": "d94e3a5de3d36e9856a2821303f00a749debc69a416f318e0dff50199b83bdae",
            "outputs/stage9/stage9_public_input_constraint_golden_vectors.json": "9d7ef9bb54a1bfb07954b99176f3ddc5a966ed7ad22f0e2c8d03071fd6a4982a",
            "tests/test_stage9_public_input_constraint_contract.py": "787b33e81f2fe426e3930e22829c69f825215e2e4a6692e702284c192c3224dd",
            "outputs/stage9/stage9_sample_profile_categorical_repair_contract.json": "98b391bd31af98d7ff51cf1d92c848d170df93ec2bbf30e9e0d2b161874b1482",
            "artifacts/contracts/cell_group_7/sample_profiles/sample_profile_feature_matrix.csv": "c16f1786900ae0ec7878aac2dbc87018c34de459ae9a36dfabf0a43ca92f1bd6",
            "artifacts/contracts/manifest/cell_group_7_contract_export_manifest.json": "626c5369dfe9a70ed2b37bd3aa43fb90abc0c2466f2b0635e41b4728e7adfbf9",
            "artifacts/model/model_artifact_manifest.json": "9c49149b1a3f72fc6e0f6fe5e5efa84f5c81f65224c1bd08daded1f6231461fd",
            "artifacts/model/final_model_calibrated.pkl": "b022b545bd7bb4294018a26a7d10af977e3c452b7f219dbdd9113adeac367cbf",
            "artifacts/model/final_threshold.json": "e45a19822f77d6b74cf5e76c0c0e6ff2f993bad4ab91e507509b3d74d410e28b",
        }
        for relative_path, digest in expected.items():
            self.assertEqual(sha256(ROOT / relative_path), digest)

    def test_ordered_feature_contract(self) -> None:
        ordered = self.contract["model_feature_contract"]["ordered_feature_names"]
        manifest_order = self.model_manifest["features"]["ordered_feature_names"]
        self.assertEqual(len(ordered), 49)
        self.assertEqual(len(set(ordered)), 49)
        self.assertNotIn("", ordered)
        self.assertEqual(ordered, manifest_order)
        self.assertEqual(ordered.index("purpose"), 40)

    def test_dependency_partition(self) -> None:
        partition = self.contract["dependency_partition"]
        direct = set(partition["direct_user_supplied"])
        derived = set(partition["derived"])
        baseline = set(partition["synthetic_baseline_passthrough"])
        self.assertEqual((len(direct), len(derived), len(baseline)), (4, 7, 38))
        self.assertFalse(direct & derived or direct & baseline or derived & baseline)
        self.assertEqual(direct | derived | baseline, set(self.contract["model_feature_contract"]["ordered_feature_names"]))

    def test_operation_registry_is_structured_and_allowlisted(self) -> None:
        allowed = set(self.contract["operation_type_allowlist"])
        registry = self.contract["operation_registry"]
        self.assertTrue(all(item["operation_type"] in allowed for item in registry))
        text = json.dumps(registry).lower()
        for forbidden in ("eval(", "exec(", "lambda ", "placeholder", "arbitrary expression"):
            self.assertNotIn(forbidden, text)
        self.assertNotIn("UNKNOWN", {item["operation_type"] for item in registry})
        self.assertTrue(all("expression" not in item and "python_source" not in item for item in registry))
        required_types = {"IDENTITY_NUMERIC", "IDENTITY_EXACT_INTEGER", "IDENTITY_CATEGORICAL", "LOG1P_FLOAT32", "ORDINAL_MAP_FLOAT32", "RATIO_CLIP_FLOAT32", "EQUALS_FLAG_INT8", "BASELINE_PASSTHROUGH"}
        self.assertEqual({item["operation_type"] for item in registry}, required_types)
        validate_mapping_contract(self.contract)

    def test_operation_execution_order(self) -> None:
        expected = ["DIRECT_DTI", "DIRECT_LOAN_AMNT", "DIRECT_PURPOSE", "DIRECT_TERM", "DERIVE_LOG_ANNUAL_INC", "DERIVE_LOG_LOAN_AMNT", "DERIVE_HOME_OWNERSHIP", "DERIVE_PAYMENT_TO_INCOME", "DERIVE_LOAN_TO_INCOME", "DERIVE_DEBT_TO_INCOME_REVOL", "DERIVE_IS_60_MONTH"]
        order = self.contract["operation_execution_order"]
        by_id = {item["operation_id"]: item for item in self.contract["operation_registry"]}
        targets = [by_id[operation_id]["target_feature"] for operation_id in order]
        authorized = set(self.contract["dependency_partition"]["direct_user_supplied"]) | set(self.contract["dependency_partition"]["derived"])
        self.assertEqual(order, expected)
        self.assertEqual(len(set(order)), 11)
        self.assertEqual(len(set(targets)), 11)
        self.assertEqual(set(targets), authorized)

    def test_exact_operation_registry_closure_and_mutations(self) -> None:
        registry = self.contract["operation_registry"]
        order = self.contract["operation_execution_order"]
        closure = self.contract["exact_operation_registry_contract"]
        ids = [operation["operation_id"] for operation in registry]
        expected = set(order) | {"PRESERVE_BASELINE"}
        baseline_operations = [operation for operation in registry if operation["operation_type"] == "BASELINE_PASSTHROUGH"]
        self.assertEqual(len(registry), 12)
        self.assertEqual(len(order), 11)
        self.assertEqual(len(baseline_operations), 1)
        self.assertEqual(ids.count("PRESERVE_BASELINE"), 1)
        self.assertEqual(set(ids), expected)
        self.assertEqual(set(closure["expected_registry_operation_ids"]), expected)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids) - expected, set())
        self.assertEqual(expected - set(ids), set())

        extra = copy.deepcopy(self.contract)
        extra["operation_registry"].append({
            "operation_id": "EXTRA_UNUSED_DTI",
            "operation_type": "IDENTITY_NUMERIC",
            "source_fields": ["dti"],
            "target_feature": "dti",
            "logical_type": "finite numeric",
            "value_source": "USER_SUPPLIED",
        })
        with self.assertRaisesRegex(MappingFailure, "BASIC_FORM_MAPPING_CONTRACT_INVALID"):
            validate_mapping_contract(extra)

        second_baseline = copy.deepcopy(self.contract)
        duplicate_baseline = copy.deepcopy(next(operation for operation in registry if operation["operation_id"] == "PRESERVE_BASELINE"))
        duplicate_baseline["operation_id"] = "PRESERVE_BASELINE_SECOND"
        second_baseline["operation_registry"].append(duplicate_baseline)
        with self.assertRaisesRegex(MappingFailure, "BASIC_FORM_MAPPING_CONTRACT_INVALID"):
            validate_mapping_contract(second_baseline)

        missing = copy.deepcopy(self.contract)
        missing["operation_registry"] = [operation for operation in missing["operation_registry"] if operation["operation_id"] != "DIRECT_DTI"]
        with self.assertRaisesRegex(MappingFailure, "BASIC_FORM_MAPPING_CONTRACT_INVALID"):
            validate_mapping_contract(missing)

    def test_structural_operand_reference_closure_and_mutations(self) -> None:
        policy = self.contract["available_context_contract"]
        public_sources = set(policy["initial_public_source_fields"])
        baseline_features = set(resolve_contract_reference(self.contract, policy["initial_baseline_feature_reference"]))
        available = public_sources | baseline_features
        prior_targets: set[str] = set()
        by_id = {operation["operation_id"]: operation for operation in self.contract["operation_registry"]}
        self.assertEqual(public_sources, {"annual_inc", "dti", "home_ownership", "loan_amnt", "purpose", "term_months"})
        self.assertEqual(len(baseline_features), 49)
        for operation_id in self.contract["operation_execution_order"]:
            operation = by_id[operation_id]
            references = set(operation["source_fields"])
            if operation["operation_type"] == "RATIO_CLIP_FLOAT32":
                references |= {operation["numerator"], operation["denominator"]["field"]}
            self.assertTrue(references <= available)
            self.assertTrue(all(reference in public_sources or reference in baseline_features or reference in prior_targets for reference in references))
            if operation["operation_type"] == "IDENTITY_CATEGORICAL":
                self.assertIsInstance(resolve_contract_reference(self.contract, operation["allowed_values_reference"]), list)
            if operation["operation_type"] == "ORDINAL_MAP_FLOAT32":
                self.assertIsInstance(resolve_contract_reference(self.contract, operation["mapping_reference"]), dict)
            available.add(operation["target_feature"])
            prior_targets.add(operation["target_feature"])

        unknown_source = copy.deepcopy(self.contract)
        next(operation for operation in unknown_source["operation_registry"] if operation["operation_id"] == "DERIVE_LOG_ANNUAL_INC")["source_fields"] = ["unknown_source"]
        with self.assertRaisesRegex(MappingFailure, "BASIC_FORM_MAPPING_CONTRACT_INVALID"):
            validate_mapping_contract(unknown_source)

        unknown_numerator = copy.deepcopy(self.contract)
        ratio = next(operation for operation in unknown_numerator["operation_registry"] if operation["operation_id"] == "DERIVE_PAYMENT_TO_INCOME")
        ratio["numerator"] = "unknown_numerator"
        ratio["source_fields"][0] = "unknown_numerator"
        with self.assertRaisesRegex(MappingFailure, "BASIC_FORM_MAPPING_CONTRACT_INVALID"):
            validate_mapping_contract(unknown_numerator)

        unknown_denominator = copy.deepcopy(self.contract)
        ratio = next(operation for operation in unknown_denominator["operation_registry"] if operation["operation_id"] == "DERIVE_PAYMENT_TO_INCOME")
        ratio["denominator"]["field"] = "unknown_denominator"
        ratio["source_fields"][1] = "unknown_denominator"
        with self.assertRaisesRegex(MappingFailure, "BASIC_FORM_MAPPING_CONTRACT_INVALID"):
            validate_mapping_contract(unknown_denominator)

        unknown_mapping = copy.deepcopy(self.contract)
        next(operation for operation in unknown_mapping["operation_registry"] if operation["operation_id"] == "DERIVE_HOME_OWNERSHIP")["mapping_reference"] = "home_ownership_mapping.unknown"
        with self.assertRaisesRegex(MappingFailure, "BASIC_FORM_MAPPING_CONTRACT_INVALID"):
            validate_mapping_contract(unknown_mapping)

        unknown_allowlist = copy.deepcopy(self.contract)
        next(operation for operation in unknown_allowlist["operation_registry"] if operation["operation_id"] == "DIRECT_PURPOSE")["allowed_values_reference"] = "purpose_categorical_transport.unknown"
        with self.assertRaisesRegex(MappingFailure, "BASIC_FORM_MAPPING_CONTRACT_INVALID"):
            validate_mapping_contract(unknown_allowlist)

    def test_request_assembly_is_registry_driven_without_hardcoded_targets(self) -> None:
        tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        function = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "assemble_from_mapping_contract"
        )
        string_constants = {
            node.value for node in ast.walk(function)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        derived = set(self.contract["dependency_partition"]["derived"])
        self.assertTrue(derived.isdisjoint(string_constants))
        function_text = ast.unparse(function)
        self.assertIn("operation_registry", function_text)
        self.assertIn("operation_execution_order", function_text)
        self.assertNotIn("math.log1p", function_text)
        test_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "BasicFormRuntimeMappingContractTests")
        golden_test = next(node for node in test_class.body if isinstance(node, ast.FunctionDef) and node.name == "test_complete_mapping_golden_vectors")
        called_names = {
            node.func.id for node in ast.walk(golden_test)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertIn("assemble_from_mapping_contract", called_names)
        self.assertTrue(called_names.isdisjoint({"validate_mapping_state", "evaluate_operation", "evaluate_operation_from_contract"}))

    def test_operation_registry_required_parameters(self) -> None:
        schemas = self.contract["operation_parameter_contract"]
        for operation in self.contract["operation_registry"]:
            schema = schemas[operation["operation_type"]]
            self.assertTrue(set(schema["required_fields"]) <= set(operation))
        mutated = copy.deepcopy(self.contract)
        next(item for item in mutated["operation_registry"] if item["operation_id"] == "DERIVE_PAYMENT_TO_INCOME").pop("clip_upper")
        with self.assertRaisesRegex(MappingFailure, "BASIC_FORM_MAPPING_CONTRACT_INVALID"):
            validate_mapping_contract(mutated)

    def test_operation_unit_vectors(self) -> None:
        for vector in self.vectors["operation_unit_vectors"]:
            with self.subTest(vector=vector["vector_id"]):
                actual = evaluate_operation(vector["operation_type"], vector["input_operands"], self.contract)
                if "expected_float32_uint32_bits" in vector:
                    self.assertEqual(float32_bits(actual), vector["expected_float32_uint32_bits"])
                    self.assertEqual(actual, vector["expected_decimal_value"])
                else:
                    self.assertEqual(actual, vector["expected_value"])
                self.assertEqual(vector["public_request_status"], "NOT_A_PUBLIC_REQUEST")

    def test_historical_formula_parameters(self) -> None:
        operations = operation_by_target(self.contract)
        self.assertEqual(operations["log_annual_inc"]["function"], "NATURAL_LOG1P")
        self.assertEqual(operations["log_loan_amnt"]["output_dtype"], "float32")
        self.assertEqual((operations["payment_to_income"]["clip_lower"], operations["payment_to_income"]["clip_upper"]), (0, 10))
        self.assertEqual((operations["loan_to_income"]["clip_lower"], operations["loan_to_income"]["clip_upper"]), (0, 20))
        self.assertEqual((operations["debt_to_income_revol"]["clip_lower"], operations["debt_to_income_revol"]["clip_upper"]), (0, 50))
        self.assertEqual(operations["is_60_month"]["output_dtype"], "int8")
        self.assertFalse(self.contract["home_ownership_mapping"]["historical_fillna_fallback_reproduced"])

    def test_all_baseline_profiles_are_safe(self) -> None:
        expected_features = set(self.contract["model_feature_contract"]["ordered_feature_names"])
        purposes = set(self.contract["purpose_categorical_transport"]["exact_category_order"])
        self.assertEqual(set(self.profiles), set(self.contract["baseline_profile_contract"]["allowed_profile_ids"]))
        for profile_id, rows in self.profiles.items():
            with self.subTest(profile=profile_id):
                names = [row["canonical_feature"] for row in rows]
                self.assertEqual(len(rows), 49)
                self.assertEqual(len(set(names)), 49)
                self.assertEqual(set(names), expected_features)
                self.assertTrue(all(row["payload_compatible"] == "True" for row in rows))
                payload = validate_baseline_profile(self.contract, profile_id, rows)
                numeric_features = [feature for feature in payload if feature != "purpose"]
                self.assertEqual(len(numeric_features), 48)
                self.assertTrue(all(math.isfinite(payload[feature]) for feature in numeric_features))
                self.assertIn(payload["purpose"], purposes)

    def test_baseline_mapping_status_enforcement(self) -> None:
        profile_id = "SP_LOW_RISK_SIGNAL"
        accepted_rows = copy.deepcopy(self.profiles[profile_id])
        self.assertIn("READY_WITH_LIMITATION", {row["mapping_status"] for row in accepted_rows})
        validate_baseline_profile(self.contract, profile_id, accepted_rows)
        inactive_disclosure = copy.deepcopy(self.contract)
        inactive_disclosure["limitation_status_contract"]["complete"] = False
        with self.assertRaisesRegex(MappingFailure, "BASIC_FORM_BASELINE_NOT_READY"):
            validate_baseline_profile(inactive_disclosure, profile_id, accepted_rows)
        rejected_rows = copy.deepcopy(accepted_rows)
        rejected_rows[0]["mapping_status"] = "NOT_READY"
        with self.assertRaisesRegex(MappingFailure, "BASIC_FORM_BASELINE_NOT_READY"):
            validate_baseline_profile(self.contract, profile_id, rejected_rows)

    def test_row_level_limitation_alignment_for_all_profiles_and_mutation(self) -> None:
        required = {"grade_encoded", "credit_age_months"}
        for profile_id, rows in self.profiles.items():
            with self.subTest(profile=profile_id):
                limitation_features = {row["canonical_feature"] for row in rows if row["mapping_status"] == "READY_WITH_LIMITATION"}
                self.assertEqual(limitation_features, required)
                self.assertEqual(sum(row["mapping_status"] == "READY_WITH_LIMITATION" for row in rows), 2)
                self.assertEqual(sum(row["mapping_status"] == "READY" for row in rows), 47)
                validate_baseline_profile(self.contract, profile_id, rows)
        mutated = copy.deepcopy(self.profiles["SP_LOW_RISK_SIGNAL"])
        next(row for row in mutated if row["canonical_feature"] == "grade_encoded")["mapping_status"] = "READY"
        next(row for row in mutated if row["canonical_feature"] == "credit_age_months")["mapping_status"] = "READY"
        next(row for row in mutated if row["canonical_feature"] == "open_acc")["mapping_status"] = "READY_WITH_LIMITATION"
        with self.assertRaisesRegex(MappingFailure, "BASIC_FORM_BASELINE_NOT_READY"):
            validate_baseline_profile(self.contract, "SP_LOW_RISK_SIGNAL", mutated)

    def test_nonfinite_baseline_passthrough_rejected(self) -> None:
        profile_id = "SP_LOW_RISK_SIGNAL"
        rows = copy.deepcopy(self.profiles[profile_id])
        next(row for row in rows if row["canonical_feature"] == "open_acc")["synthetic_value"] = "NaN"
        with self.assertRaisesRegex(MappingFailure, "BASIC_FORM_BASELINE_VALUE_INVALID"):
            validate_baseline_profile(self.contract, profile_id, rows)

    def test_complete_mapping_golden_vectors(self) -> None:
        authorized = set(self.contract["dependency_partition"]["direct_user_supplied"]) | set(self.contract["dependency_partition"]["derived"])
        for vector in self.vectors["request_level_vectors"]:
            with self.subTest(vector=vector["vector_id"]):
                baseline, payload, fingerprint = assemble_from_mapping_contract(
                    self.contract, self.input_contract, self.profiles,
                    vector["source_inputs"], vector["system_metadata"],
                    expected_fingerprint=vector["expected_ordered_payload_sha256"],
                )
                self.assertEqual(set(payload), set(self.contract["model_feature_contract"]["ordered_feature_names"]))
                for feature, expected in vector["expected_impacted_feature_outputs"].items():
                    self.assertEqual(payload[feature], expected)
                for feature, expected_bits in vector["expected_float32_bits"].items():
                    self.assertEqual(float32_bits(payload[feature]), expected_bits)
                for feature in self.contract["dependency_partition"]["synthetic_baseline_passthrough"]:
                    self.assertEqual(payload[feature], baseline[feature])
                actual_differences = {feature for feature in payload if payload[feature] != baseline[feature]}
                self.assertTrue(actual_differences <= authorized)
                self.assertEqual(len(self.contract["dependency_partition"]["synthetic_baseline_passthrough"]), vector["expected_unchanged_baseline_feature_count"])
                self.assertEqual(fingerprint, vector["expected_ordered_payload_sha256"])

    def test_contract_parameter_mutations_drive_assembly(self) -> None:
        vector = self.vectors["request_level_vectors"][0]
        source, metadata = vector["source_inputs"], vector["system_metadata"]
        _, original_payload, original_fingerprint = assemble_from_mapping_contract(self.contract, self.input_contract, self.profiles, source, metadata)

        ratio_mutation = copy.deepcopy(self.contract)
        next(item for item in ratio_mutation["operation_registry"] if item["operation_id"] == "DERIVE_PAYMENT_TO_INCOME")["denominator"]["divide_by"] = 13
        _, ratio_payload, ratio_fingerprint = assemble_from_mapping_contract(ratio_mutation, self.input_contract, self.profiles, source, metadata)
        self.assertNotEqual(ratio_payload["payment_to_income"], original_payload["payment_to_income"])
        self.assertNotEqual(ratio_fingerprint, original_fingerprint)
        self.assertNotEqual(ratio_fingerprint, vector["expected_ordered_payload_sha256"])

        comparison_mutation = copy.deepcopy(self.contract)
        next(item for item in comparison_mutation["operation_registry"] if item["operation_id"] == "DERIVE_IS_60_MONTH")["comparison_value"] = 36
        _, comparison_payload, comparison_fingerprint = assemble_from_mapping_contract(comparison_mutation, self.input_contract, self.profiles, source, metadata)
        self.assertNotEqual(comparison_payload["is_60_month"], original_payload["is_60_month"])
        self.assertNotEqual(comparison_fingerprint, original_fingerprint)

        function_mutation = copy.deepcopy(self.contract)
        next(item for item in function_mutation["operation_registry"] if item["operation_id"] == "DERIVE_LOG_ANNUAL_INC")["function"] = "LOG10"
        with self.assertRaisesRegex(MappingFailure, "BASIC_FORM_MAPPING_CONTRACT_INVALID"):
            assemble_from_mapping_contract(function_mutation, self.input_contract, self.profiles, source, metadata)

    def test_derived_nonfinite_result_rejected(self) -> None:
        vector = self.vectors["request_level_vectors"][0]
        def injected_evaluator(operation: dict, context: dict, contract: dict) -> object:
            if operation["operation_id"] == "DERIVE_LOG_ANNUAL_INC":
                return float("nan")
            return evaluate_operation_from_contract(operation, context, contract)
        with self.assertRaisesRegex(MappingFailure, "BASIC_FORM_DERIVED_VALUE_INVALID"):
            assemble_from_mapping_contract(self.contract, self.input_contract, self.profiles, vector["source_inputs"], vector["system_metadata"], operation_evaluator=injected_evaluator)

    def test_provenance_counts(self) -> None:
        provenance = self.contract["provenance_contract"]
        self.assertEqual(provenance["counts"], {"USER_SUPPLIED": 4, "DERIVED": 7, "SYNTHETIC_BASELINE": 38, "TOTAL": 49})
        self.assertEqual(sum(provenance["counts"][key] for key in ("USER_SUPPLIED", "DERIVED", "SYNTHETIC_BASELINE")), 49)
        self.assertTrue(provenance["system_metadata_excluded"])
        self.assertEqual(set(provenance["outside_matrix_user_sources"]), {"annual_inc", "home_ownership"})

    def test_limitation_status(self) -> None:
        limitation = self.contract["limitation_status_contract"]
        self.assertEqual(set(limitation["limitation_aware_features"]), {"grade_encoded", "credit_age_months"})
        self.assertEqual(limitation["limitation_aware_count"], 2)
        self.assertEqual(limitation["standard_count"], 47)
        self.assertEqual(limitation["home_ownership_encoded_status"], "STANDARD")

    def test_purpose_transport(self) -> None:
        transport = self.contract["purpose_categorical_transport"]
        self.assertEqual(len(transport["exact_category_order"]), 14)
        self.assertEqual(len(set(transport["exact_category_order"])), 14)
        self.assertIn("pandas categorical", transport["future_transport_rule"])
        self.assertFalse(transport["implemented_in_this_step"])

    def test_invalid_mapping_vectors(self) -> None:
        vectors = self.vectors["invalid_mapping_vectors"]
        self.assertEqual(len(vectors), 21)
        profile_id = "SP_LOW_RISK_SIGNAL"
        base_rows = copy.deepcopy(self.profiles[profile_id])
        allowed_operations = set(self.contract["operation_type_allowlist"])
        order = list(self.contract["model_feature_contract"]["ordered_feature_names"])
        authorized = set(self.contract["dependency_partition"]["direct_user_supplied"]) | set(self.contract["dependency_partition"]["derived"])
        provenance = {"USER_SUPPLIED": 4, "DERIVED": 7, "SYNTHETIC_BASELINE": 38, "TOTAL": 49}
        limitations = {"grade_encoded", "credit_age_months"}
        request_vector = self.vectors["request_level_vectors"][0]
        for vector in vectors:
            with self.subTest(vector=vector["vector_id"]):
                scenario = vector["failure_scenario"]
                pid = profile_id
                rows = copy.deepcopy(base_rows)
                operations = set(allowed_operations)
                candidate_order = list(order)
                overwrites = set(authorized)
                counts = dict(provenance)
                limitation_set = set(limitations)
                try:
                    if scenario == "unknown baseline profile":
                        validate_baseline_profile(self.contract, "UNKNOWN", rows)
                    elif scenario == "baseline feature count mismatch":
                        rows = [row for row in rows if row["canonical_feature"] != "open_acc"]
                        validate_baseline_profile(self.contract, pid, rows)
                    elif scenario == "duplicate baseline canonical feature":
                        rows[-1]["canonical_feature"] = rows[0]["canonical_feature"]
                        validate_baseline_profile(self.contract, pid, rows)
                    elif scenario == "missing baseline installment":
                        rows = [row for row in rows if row["canonical_feature"] != "installment"]
                        validate_baseline_profile(self.contract, pid, rows)
                    elif scenario == "missing baseline revol_bal":
                        rows = [row for row in rows if row["canonical_feature"] != "revol_bal"]
                        validate_baseline_profile(self.contract, pid, rows)
                    elif scenario == "non-finite baseline dependency":
                        next(row for row in rows if row["canonical_feature"] == "installment")["synthetic_value"] = "NaN"
                        validate_baseline_profile(self.contract, pid, rows)
                    elif scenario == "baseline model-feature set mismatch":
                        next(row for row in rows if row["canonical_feature"] == "open_acc")["canonical_feature"] = "unexpected_feature"
                        validate_baseline_profile(self.contract, pid, rows)
                    elif scenario == "baseline row has disallowed mapping_status":
                        rows[0]["mapping_status"] = "NOT_READY"
                        validate_baseline_profile(self.contract, pid, rows)
                    elif scenario == "non-finite non-dependency baseline feature":
                        next(row for row in rows if row["canonical_feature"] == "open_acc")["synthetic_value"] = "NaN"
                        validate_baseline_profile(self.contract, pid, rows)
                    elif scenario == "required structured operation parameter missing":
                        mutated = copy.deepcopy(self.contract)
                        next(item for item in mutated["operation_registry"] if item["operation_id"] == "DERIVE_PAYMENT_TO_INCOME").pop("clip_upper")
                        validate_mapping_contract(mutated)
                    elif scenario == "unsupported operation type":
                        mutated = copy.deepcopy(self.contract)
                        next(item for item in mutated["operation_registry"] if item["operation_id"] == "DERIVE_LOG_ANNUAL_INC")["operation_type"] = "EVAL_EXPRESSION"
                        validate_mapping_contract(mutated)
                    elif scenario == "test-only injected non-finite derived operation result":
                        def injected_evaluator(operation: dict, context: dict, contract: dict) -> object:
                            if operation["operation_id"] == "DERIVE_LOG_ANNUAL_INC":
                                return float("nan")
                            return evaluate_operation_from_contract(operation, context, contract)
                        assemble_from_mapping_contract(
                            self.contract, self.input_contract, self.profiles,
                            request_vector["source_inputs"], request_vector["system_metadata"],
                            operation_evaluator=injected_evaluator,
                        )
                    elif scenario == "valid assembled payload compared with deliberately altered expected hash":
                        assemble_from_mapping_contract(
                            self.contract, self.input_contract, self.profiles,
                            request_vector["source_inputs"], request_vector["system_metadata"],
                            expected_fingerprint="0" * 64,
                        )
                    elif scenario == "extra unused operation exists in operation registry":
                        mutated = copy.deepcopy(self.contract)
                        mutated["operation_registry"].append({"operation_id": "EXTRA_UNUSED_DTI", "operation_type": "IDENTITY_NUMERIC", "source_fields": ["dti"], "target_feature": "dti", "logical_type": "finite numeric", "value_source": "USER_SUPPLIED"})
                        validate_mapping_contract(mutated)
                    elif scenario == "operation contains unresolved source or operand reference":
                        mutated = copy.deepcopy(self.contract)
                        next(item for item in mutated["operation_registry"] if item["operation_id"] == "DERIVE_LOG_ANNUAL_INC")["source_fields"] = ["unknown_source"]
                        validate_mapping_contract(mutated)
                    elif scenario == "one model feature belongs to multiple fingerprint representation classes":
                        mutated = copy.deepcopy(self.contract)
                        mutated["payload_fingerprint_contract"]["feature_representation_classes"]["direct_user_numeric"].append("open_acc")
                        payload_fingerprint_from_contract(mutated, {})
                    elif scenario == "row-level READY_WITH_LIMITATION set does not equal frozen limitation-aware feature set":
                        next(row for row in rows if row["canonical_feature"] == "grade_encoded")["mapping_status"] = "READY"
                        next(row for row in rows if row["canonical_feature"] == "credit_age_months")["mapping_status"] = "READY"
                        next(row for row in rows if row["canonical_feature"] == "open_acc")["mapping_status"] = "READY_WITH_LIMITATION"
                        validate_baseline_profile(self.contract, pid, rows)
                    else:
                        if scenario == "unauthorized twelfth feature override":
                            overwrites.add("installment")
                        elif scenario == "model feature order mismatch":
                            candidate_order[0], candidate_order[1] = candidate_order[1], candidate_order[0]
                        elif scenario == "provenance count mismatch":
                            counts["SYNTHETIC_BASELINE"] = 37
                        elif scenario == "limitation-aware set mismatch":
                            limitation_set.add("home_ownership_encoded")
                        actual = validate_mapping_state(
                            self.contract, pid, rows, operations, candidate_order,
                            overwrites, counts, limitation_set,
                        )
                        if actual != "valid":
                            raise MappingFailure(actual)
                    actual = "valid"
                except MappingFailure as failure:
                    actual = failure.code
                self.assertEqual(actual, vector["expected_failure_code"])
                self.assertEqual(vector["expected_status"], "invalid")

    def test_exact_mapping_failure_code_coverage(self) -> None:
        expected = set(self.contract["failure_code_contract"]["mapping_specific_codes"])
        actual = {vector["expected_failure_code"] for vector in self.vectors["invalid_mapping_vectors"]}
        self.assertEqual(len(expected), 15)
        self.assertEqual(actual, expected)

    def test_golden_vector_summary(self) -> None:
        self.assertEqual(
            self.vectors["summary"],
            {
                "request_level_vector_count": 7,
                "operation_unit_vector_count": 17,
                "invalid_mapping_vector_count": 21,
                "total_vector_count": 45,
            },
        )

    def test_payload_fingerprint_is_deterministic(self) -> None:
        vector = self.vectors["request_level_vectors"][0]
        _, payload, first = assemble_from_mapping_contract(
            self.contract, self.input_contract, self.profiles,
            vector["source_inputs"], vector["system_metadata"],
        )
        second = payload_fingerprint_from_contract(self.contract, copy.deepcopy(payload))
        self.assertEqual(first, second)
        self.assertEqual(first, vector["expected_ordered_payload_sha256"])
        self.assertEqual(len(first), 64)

    def test_fingerprint_policy_is_complete_and_contract_driven(self) -> None:
        policy = self.contract["payload_fingerprint_contract"]
        self.assertEqual(policy["algorithm"], "SHA-256")
        self.assertEqual(policy["input_encoding"], "UTF-8")
        self.assertEqual(policy["record_separator"], "LF")
        self.assertEqual(policy["direct_user_numeric_representation"], "PYTHON_FORMAT_DOT_17G_FLOAT64")
        self.assertEqual(policy["baseline_numeric_representation"], "PYTHON_FORMAT_DOT_17G_FLOAT64")
        self.assertEqual(set(policy["feature_representation_classes"]["direct_user_numeric"]), {"dti", "loan_amnt"})
        vector = self.vectors["request_level_vectors"][0]
        _, payload, expected = assemble_from_mapping_contract(self.contract, self.input_contract, self.profiles, vector["source_inputs"], vector["system_metadata"])
        self.assertEqual(payload_fingerprint_from_contract(self.contract, payload), expected)

    def test_fingerprint_representation_classes_exact_partition_and_mutations(self) -> None:
        class_sets, ordered, _ = validate_fingerprint_contract(self.contract)
        expected_counts = {"direct_user_numeric": 2, "exact_integer": 2, "float32_derived": 6, "category": 1, "baseline_numeric": 38}
        self.assertEqual({name: len(values) for name, values in class_sets.items()}, expected_counts)
        self.assertEqual(sum(len(values) for values in class_sets.values()), 49)
        self.assertEqual(set().union(*class_sets.values()), set(ordered))
        for left_index, left in enumerate(class_sets):
            for right in list(class_sets)[left_index + 1:]:
                self.assertFalse(class_sets[left] & class_sets[right])

        vector = self.vectors["request_level_vectors"][0]
        _, payload, _ = assemble_from_mapping_contract(self.contract, self.input_contract, self.profiles, vector["source_inputs"], vector["system_metadata"])
        overlap = copy.deepcopy(self.contract)
        overlap["payload_fingerprint_contract"]["feature_representation_classes"]["direct_user_numeric"].append("open_acc")
        with self.assertRaisesRegex(MappingFailure, "BASIC_FORM_MAPPING_CONTRACT_INVALID"):
            payload_fingerprint_from_contract(overlap, payload)

        missing = copy.deepcopy(self.contract)
        missing["payload_fingerprint_contract"]["feature_representation_classes"]["direct_user_numeric"].remove("dti")
        with self.assertRaisesRegex(MappingFailure, "BASIC_FORM_MAPPING_CONTRACT_INVALID"):
            payload_fingerprint_from_contract(missing, payload)

        unexpected = copy.deepcopy(self.contract)
        unexpected["payload_fingerprint_contract"]["feature_representation_classes"]["direct_user_numeric"][0] = "unexpected_feature"
        with self.assertRaisesRegex(MappingFailure, "BASIC_FORM_MAPPING_CONTRACT_INVALID"):
            payload_fingerprint_from_contract(unexpected, payload)

        duplicate = copy.deepcopy(self.contract)
        duplicate["payload_fingerprint_contract"]["feature_representation_classes"]["category"].append("purpose")
        with self.assertRaisesRegex(MappingFailure, "BASIC_FORM_MAPPING_CONTRACT_INVALID"):
            payload_fingerprint_from_contract(duplicate, payload)

    def test_fingerprint_policy_mutations_are_rejected(self) -> None:
        vector = self.vectors["request_level_vectors"][0]
        _, payload, _ = assemble_from_mapping_contract(self.contract, self.input_contract, self.profiles, vector["source_inputs"], vector["system_metadata"])
        for field, value in (("algorithm", "MD5"), ("record_separator", "CRLF"), ("direct_user_numeric_representation", "ROUND_TO_2_DECIMALS")):
            mutated = copy.deepcopy(self.contract)
            mutated["payload_fingerprint_contract"][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(MappingFailure, "BASIC_FORM_MAPPING_CONTRACT_INVALID"):
                payload_fingerprint_from_contract(mutated, payload)

    def test_payload_fingerprint_mismatch_rejected(self) -> None:
        vector = self.vectors["request_level_vectors"][0]
        altered = "0" * 64
        self.assertNotEqual(altered, vector["expected_ordered_payload_sha256"])
        with self.assertRaisesRegex(MappingFailure, "BASIC_FORM_PAYLOAD_FINGERPRINT_MISMATCH"):
            assemble_from_mapping_contract(self.contract, self.input_contract, self.profiles, vector["source_inputs"], vector["system_metadata"], expected_fingerprint=altered)

    def test_golden_vector_privacy(self) -> None:
        privacy = self.vectors["privacy"]
        self.assertFalse(privacy["personal_data_used"])
        self.assertTrue(privacy["synthetic_vectors_only"])
        self.assertFalse(privacy["complete_model_payload_recorded"])
        self.assertFalse(privacy["model_matrix_recorded"])
        self.assertFalse(privacy["probability_recorded"])
        self.assertFalse(self.vectors["model_inference_executed"])

    def test_no_runtime_activation_imports_or_calls(self) -> None:
        tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
        imported = set()
        called_attributes = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                called_attributes.add(node.func.attr)
        prohibited_imports = {"app", "streamlit", "joblib", "pickle", "sklearn", "numpy", "pandas", "subprocess", "socket", "http", "urllib", "requests"}
        self.assertTrue(imported.isdisjoint(prohibited_imports))
        self.assertTrue(called_attributes.isdisjoint({"predict", "predict_proba"}))

    def test_non_goals_and_authorization(self) -> None:
        non_goals = self.contract["non_goals"]
        self.assertFalse(non_goals["application_source_modified"])
        self.assertFalse(non_goals["mapping_runtime_implemented"])
        self.assertFalse(non_goals["model_loaded"])
        self.assertFalse(non_goals["model_inference_executed"])
        authorization = self.contract["next_step_authorization"]
        self.assertFalse(authorization["stage9_step5_rerun_authorized"])
        self.assertFalse(authorization["public_deployment_authorized"])


if __name__ == "__main__":
    unittest.main()
