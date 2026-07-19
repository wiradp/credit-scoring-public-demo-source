"""Contract-driven Basic Form payload assembly for the portfolio demo.

The module implements the frozen Stage 9 Steps 4.1A and 4.1B contracts. It
does not load a model, run inference, log a payload, or accept path overrides.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import json
import math
import struct
from dataclasses import dataclass, field
from functools import lru_cache
from numbers import Real
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_CONTRACT_PATH = PROJECT_ROOT / "outputs/stage9/stage9_public_input_constraint_contract.json"
MAPPING_CONTRACT_PATH = PROJECT_ROOT / "outputs/stage9/stage9_basic_form_runtime_mapping_contract.json"
PROFILE_MATRIX_PATH = PROJECT_ROOT / "artifacts/contracts/cell_group_7/sample_profiles/sample_profile_feature_matrix.csv"
MODEL_MANIFEST_PATH = PROJECT_ROOT / "artifacts/model/model_artifact_manifest.json"

INPUT_CONTRACT_ID = "STAGE9_PUBLIC_INPUT_CONSTRAINT_V1"
MAPPING_CONTRACT_ID = "STAGE9_BASIC_FORM_RUNTIME_MAPPING_V1"
EXPECTED_FILE_INTEGRITY = {
    INPUT_CONTRACT_PATH: (20_812, "d94e3a5de3d36e9856a2821303f00a749debc69a416f318e0dff50199b83bdae"),
    MAPPING_CONTRACT_PATH: (25_592, "62404f80935b1459c722d4fe72db48da5cd558916a6c9b1501cb8f59e7a6ac06"),
    PROFILE_MATRIX_PATH: (89_769, "c16f1786900ae0ec7878aac2dbc87018c34de459ae9a36dfabf0a43ca92f1bd6"),
    MODEL_MANIFEST_PATH: (5_225, "9c49149b1a3f72fc6e0f6fe5e5efa84f5c81f65224c1bd08daded1f6231461fd"),
}
SUPPORTED_OPERATION_TYPES = {
    "IDENTITY_NUMERIC",
    "IDENTITY_EXACT_INTEGER",
    "IDENTITY_CATEGORICAL",
    "LOG1P_FLOAT32",
    "ORDINAL_MAP_FLOAT32",
    "RATIO_CLIP_FLOAT32",
    "EQUALS_FLAG_INT8",
    "BASELINE_PASSTHROUGH",
}
EXPECTED_VALUE_SOURCE_COUNTS = {
    "USER_SUPPLIED": 4,
    "DERIVED": 7,
    "SYNTHETIC_BASELINE": 38,
}
EXPECTED_LIMITATION_AWARE_FEATURES = ("grade_encoded", "credit_age_months")


class BasicFormRuntimeError(ValueError):
    """Sanitized Basic Form domain failure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


_MAPPING_RESULT_SEAL = object()


@dataclass(frozen=True, init=False)
class BasicFormMappingResult:
    """Sealed internal mapping evidence; never a bearer authorization token."""

    mode: str
    mapping_contract_id: str
    input_contract_id: str
    source_inputs: Mapping[str, object] = field(repr=False)
    system_metadata: Mapping[str, object] = field(repr=False)
    payload: Mapping[str, object] = field(repr=False)
    ordered_feature_names: tuple[str, ...] = field(repr=False)
    payload_fingerprint: str
    selected_synthetic_profile_id: str
    synthetic_completion_acknowledged: bool
    value_source_counts: Mapping[str, int]
    limitation_aware_features: tuple[str, ...]
    feature_count: int
    safe_disclosure: Mapping[str, object]

    def __init__(
        self,
        *,
        _seal: object,
        mode: str,
        mapping_contract_id: str,
        input_contract_id: str,
        source_inputs: Mapping[str, object],
        system_metadata: Mapping[str, object],
        payload: Mapping[str, object],
        ordered_feature_names: tuple[str, ...],
        payload_fingerprint: str,
        selected_synthetic_profile_id: str,
        synthetic_completion_acknowledged: bool,
        value_source_counts: Mapping[str, int],
        limitation_aware_features: tuple[str, ...],
        feature_count: int,
        safe_disclosure: Mapping[str, object],
    ) -> None:
        if _seal is not _MAPPING_RESULT_SEAL:
            raise TypeError("BasicFormMappingResult construction is internal.")
        values = {
            "mode": mode,
            "mapping_contract_id": mapping_contract_id,
            "input_contract_id": input_contract_id,
            "source_inputs": MappingProxyType(copy.deepcopy(dict(source_inputs))),
            "system_metadata": MappingProxyType(copy.deepcopy(dict(system_metadata))),
            "payload": MappingProxyType(copy.deepcopy(dict(payload))),
            "ordered_feature_names": tuple(ordered_feature_names),
            "payload_fingerprint": payload_fingerprint,
            "selected_synthetic_profile_id": selected_synthetic_profile_id,
            "synthetic_completion_acknowledged": synthetic_completion_acknowledged,
            "value_source_counts": MappingProxyType(dict(value_source_counts)),
            "limitation_aware_features": tuple(limitation_aware_features),
            "feature_count": feature_count,
            "safe_disclosure": MappingProxyType(copy.deepcopy(dict(safe_disclosure))),
        }
        for name, value in values.items():
            object.__setattr__(self, name, value)


@dataclass(frozen=True)
class _Authority:
    input_contract: dict[str, Any]
    mapping_contract: dict[str, Any]
    profiles: Mapping[str, tuple[dict[str, str], ...]]
    model_order: tuple[str, ...]


def _reject_constant(value: str) -> None:
    raise ValueError(value)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _strict_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as stream:
            value = json.load(
                stream,
                parse_constant=_reject_constant,
                object_pairs_hook=_unique_object,
            )
    except (OSError, UnicodeError, ValueError, TypeError):
        raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID") from None
    if not isinstance(value, dict):
        raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError:
        raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID") from None
    return digest.hexdigest()


def _verify_fixed_file(path: Path) -> None:
    expected_size, expected_digest = EXPECTED_FILE_INTEGRITY[path]
    if (
        not path.is_file()
        or path.is_symlink()
        or path.stat().st_size != expected_size
        or _sha256(path) != expected_digest
    ):
        raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID")


def _float32(value: float) -> float:
    try:
        return struct.unpack(">f", struct.pack(">f", float(value)))[0]
    except (OverflowError, struct.error, TypeError, ValueError):
        raise BasicFormRuntimeError("BASIC_FORM_DERIVED_VALUE_INVALID") from None


def _float32_bits(value: float) -> int:
    try:
        return struct.unpack(">I", struct.pack(">f", float(value)))[0]
    except (OverflowError, struct.error, TypeError, ValueError):
        raise BasicFormRuntimeError("BASIC_FORM_PAYLOAD_FINGERPRINT_MISMATCH") from None


def _resolve(contract: Mapping[str, Any], reference: str) -> Any:
    value: Any = contract
    for part in reference.split("."):
        if not isinstance(value, Mapping) or part not in value:
            raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        value = value[part]
    return value


def _validate_input_contract(contract: Mapping[str, Any]) -> None:
    try:
        source = contract["source_field_contract"]
        metadata = contract["system_metadata_field_set_policy"]
        constraints = contract["field_constraints"]
        system = contract["system_metadata_constraints"]
        privacy = contract["privacy_and_identity_boundary"]
    except (KeyError, TypeError):
        raise BasicFormRuntimeError("BASIC_FORM_INPUT_CONTRACT_INVALID") from None
    expected_source = ["annual_inc", "dti", "home_ownership", "loan_amnt", "purpose", "term_months"]
    expected_metadata = ["synthetic_baseline_profile_id", "synthetic_completion_acknowledged"]
    if (
        contract.get("contract_id") != INPUT_CONTRACT_ID
        or source.get("fields") != expected_source
        or source.get("count") != 6
        or source.get("extra_source_field_policy") != "FAIL_CLOSED"
        or metadata.get("exact_fields") != expected_metadata
        or set(constraints) != set(expected_source)
        or set(system) != set(expected_metadata)
        or system["synthetic_completion_acknowledged"].get("required_value") is not True
        or system["synthetic_baseline_profile_id"].get("caller_supplied_baseline_payload_accepted") is not False
        or privacy.get("real_person_data_allowed") is not False
        or privacy.get("free_text_narrative_allowed") is not False
    ):
        raise BasicFormRuntimeError("BASIC_FORM_INPUT_CONTRACT_INVALID")


def _validate_fingerprint_contract(
    contract: Mapping[str, Any],
) -> tuple[dict[str, set[str]], list[str], dict[str, str]]:
    try:
        policy = contract["payload_fingerprint_contract"]
        partition = contract["fingerprint_representation_partition_contract"]
        classes = policy["feature_representation_classes"]
        tags = policy["type_tags"]
        ordered = _resolve(contract, policy["canonical_feature_order_reference"])
        raw_classes = {
            "direct_user_numeric": classes["direct_user_numeric"],
            "exact_integer": classes["exact_integer"],
            "float32_derived": classes["float32_derived"],
            "category": classes["category"],
            "baseline_numeric": _resolve(contract, classes["baseline_numeric_reference"]),
        }
    except (KeyError, TypeError):
        raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID") from None
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
    expected_counts = {
        "direct_user_numeric": 2,
        "exact_integer": 2,
        "float32_derived": 6,
        "category": 1,
        "baseline_numeric": 38,
        "total": 49,
    }
    if (
        any(policy.get(key) != value for key, value in supported.items())
        or tags != {"category": "CATEGORY", "exact_integer": "INT8", "numeric": "NUMERIC"}
        or partition.get("class_counts") != expected_counts
        or partition.get("class_names") != list(raw_classes)
        or not isinstance(ordered, list)
        or any(not isinstance(values, list) for values in raw_classes.values())
    ):
        raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    class_sets = {name: set(values) for name, values in raw_classes.items()}
    if any(len(values) != expected_counts[name] for name, values in class_sets.items()):
        raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    union = set().union(*class_sets.values())
    if sum(map(len, class_sets.values())) != 49 or union != set(ordered):
        raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    if class_sets["baseline_numeric"] != set(contract["dependency_partition"]["synthetic_baseline_passthrough"]):
        raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    return class_sets, ordered, dict(tags)


def _validate_mapping_contract(
    contract: Mapping[str, Any], model_order: tuple[str, ...] | None = None
) -> None:
    required = {
        "operation_type_allowlist", "operation_registry", "operation_parameter_contract",
        "operation_execution_order", "exact_operation_registry_contract", "assembly_algorithm",
        "dependency_partition", "model_feature_contract", "source_field_contract",
        "system_metadata_contract", "available_context_contract", "operand_reference_contract",
        "provenance_contract", "limitation_status_contract", "payload_fingerprint_contract",
        "fingerprint_representation_partition_contract", "baseline_profile_contract",
    }
    if not isinstance(contract, Mapping) or not required <= set(contract):
        raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    try:
        registry = contract["operation_registry"]
        order = contract["operation_execution_order"]
        schemas = contract["operation_parameter_contract"]
        closure = contract["exact_operation_registry_contract"]
        model = contract["model_feature_contract"]
        partition = contract["dependency_partition"]
        provenance = contract["provenance_contract"]
        limitation = contract["limitation_status_contract"]
    except (KeyError, TypeError):
        raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID") from None
    feature_order = model.get("ordered_feature_names")
    direct = partition.get("direct_user_supplied")
    derived = partition.get("derived")
    baseline = partition.get("synthetic_baseline_passthrough")
    if (
        contract.get("contract_id") != MAPPING_CONTRACT_ID
        or set(contract["operation_type_allowlist"]) != SUPPORTED_OPERATION_TYPES
        or not isinstance(registry, list)
        or not isinstance(order, list)
        or not isinstance(schemas, Mapping)
        or not isinstance(feature_order, list)
        or len(feature_order) != 49
        or len(set(feature_order)) != 49
        or model.get("feature_count") != 49
        or (model_order is not None and tuple(feature_order) != model_order)
        or not all(isinstance(values, list) for values in (direct, derived, baseline))
        or (len(direct), len(derived), len(baseline)) != (4, 7, 38)
    ):
        raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    sets = [set(direct), set(derived), set(baseline)]
    if sum(map(len, sets)) != 49 or set().union(*sets) != set(feature_order):
        raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    registry_ids = [item.get("operation_id") for item in registry if isinstance(item, Mapping)]
    baseline_ops = [item for item in registry if isinstance(item, Mapping) and item.get("operation_type") == "BASELINE_PASSTHROUGH"]
    expected_registry_ids = set(order) | {"PRESERVE_BASELINE"}
    if (
        len(registry) != 12
        or len(order) != 11
        or len(set(order)) != 11
        or len(registry_ids) != 12
        or len(set(registry_ids)) != 12
        or set(registry_ids) != expected_registry_ids
        or len(baseline_ops) != 1
        or baseline_ops[0].get("operation_id") != "PRESERVE_BASELINE"
        or closure.get("expected_registry_count") != 12
        or closure.get("expected_executable_operation_count") != 11
        or closure.get("expected_baseline_passthrough_operation_count") != 1
        or set(closure.get("expected_registry_operation_ids", [])) != expected_registry_ids
        or closure.get("unused_operations_allowed") is not False
        or closure.get("unexpected_operations_allowed") is not False
        or closure.get("missing_operations_allowed") is not False
    ):
        raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    assembly = contract["assembly_algorithm"]
    if (
        assembly.get("baseline_passthrough_precedes_operation_sequence") is not True
        or assembly.get("request_assembly_uses_operation_registry") is not True
        or assembly.get("hardcoded_derived_formula_path_allowed") is not False
    ):
        raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    allowed_sources = set(provenance.get("allowed_value_sources", []))
    by_id: dict[str, Mapping[str, Any]] = {}
    for operation in registry:
        if not isinstance(operation, Mapping):
            raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        operation_type = operation.get("operation_type")
        if operation_type not in SUPPORTED_OPERATION_TYPES:
            raise BasicFormRuntimeError("BASIC_FORM_OPERATION_TYPE_INVALID")
        schema = schemas.get(operation_type)
        if not isinstance(schema, Mapping) or any(field not in operation for field in schema.get("required_fields", [])):
            raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        if operation.get("value_source") not in allowed_sources:
            raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        if "source_field_count" in schema and len(operation.get("source_fields", [])) != schema["source_field_count"]:
            raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        by_id[str(operation["operation_id"])] = operation
    authorized_targets = set(direct) | set(derived)
    targets = [by_id[operation_id].get("target_feature") for operation_id in order]
    if len(set(targets)) != 11 or set(targets) != authorized_targets:
        raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    context_policy = contract["available_context_contract"]
    reference_policy = contract["operand_reference_contract"]
    public_sources = set(context_policy.get("initial_public_source_fields", []))
    baseline_features = set(_resolve(contract, context_policy["initial_baseline_feature_reference"]))
    if (
        public_sources != set(contract["source_field_contract"]["exact_fields"])
        or len(public_sources) != 6
        or baseline_features != set(feature_order)
        or set(context_policy.get("metadata_excluded_from_operand_context", []))
        != {"synthetic_baseline_profile_id", "synthetic_completion_acknowledged"}
        or reference_policy.get("unresolved_references_allowed") is not False
    ):
        raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    available = public_sources | baseline_features
    for operation_id in order:
        operation = by_id[operation_id]
        references = set(operation.get("source_fields", []))
        if operation["operation_type"] == "RATIO_CLIP_FLOAT32":
            denominator = operation.get("denominator")
            if not isinstance(denominator, Mapping):
                raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID")
            references |= {operation.get("numerator"), denominator.get("field")}
            try:
                divide_by = float(denominator["divide_by"])
                lower = float(operation["clip_lower"])
                upper = float(operation["clip_upper"])
            except (KeyError, TypeError, ValueError):
                raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID") from None
            if not all(map(math.isfinite, (divide_by, lower, upper))) or divide_by <= 0 or lower > upper:
                raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        if None in references or not references <= available:
            raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        if operation["operation_type"] == "IDENTITY_CATEGORICAL":
            allowed = _resolve(contract, operation["allowed_values_reference"])
            if not isinstance(allowed, list) or not allowed:
                raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        if operation["operation_type"] == "ORDINAL_MAP_FLOAT32":
            mapping = _resolve(contract, operation["mapping_reference"])
            if not isinstance(mapping, Mapping) or not mapping:
                raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        available.add(str(operation["target_feature"]))
    passthrough = _resolve(contract, baseline_ops[0]["target_features_reference"])
    if set(passthrough) != set(baseline):
        raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    if provenance.get("counts") != {**EXPECTED_VALUE_SOURCE_COUNTS, "TOTAL": 49}:
        raise BasicFormRuntimeError("BASIC_FORM_PROVENANCE_INVALID")
    if tuple(limitation.get("limitation_aware_features", [])) != EXPECTED_LIMITATION_AWARE_FEATURES:
        raise BasicFormRuntimeError("BASIC_FORM_LIMITATION_STATUS_INVALID")
    _validate_fingerprint_contract(contract)


def _read_profiles() -> dict[str, tuple[dict[str, str], ...]]:
    try:
        with PROFILE_MATRIX_PATH.open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
    except (OSError, UnicodeError, csv.Error):
        raise BasicFormRuntimeError("BASIC_FORM_BASELINE_NOT_READY") from None
    profiles: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        profiles.setdefault(row.get("profile_id", ""), []).append(row)
    return {key: tuple(value) for key, value in profiles.items()}


def _validate_baseline_profile(
    contract: Mapping[str, Any], profile_id: str, rows: tuple[dict[str, str], ...] | list[dict[str, str]]
) -> dict[str, object]:
    baseline_contract = contract["baseline_profile_contract"]
    if profile_id not in baseline_contract["allowed_profile_ids"]:
        raise BasicFormRuntimeError("BASIC_FORM_BASELINE_ID_INVALID")
    if any(row.get("mapping_status") not in baseline_contract["allowed_mapping_statuses"] for row in rows):
        raise BasicFormRuntimeError("BASIC_FORM_BASELINE_NOT_READY")
    alignment = contract["row_level_limitation_alignment_contract"]
    required = set(_resolve(contract, baseline_contract["required_limitation_aware_features_reference"]))
    declared = set(_resolve(contract, alignment["limitation_status_contract_reference"]))
    row_limited = {row.get("canonical_feature") for row in rows if row.get("mapping_status") == "READY_WITH_LIMITATION"}
    if (
        baseline_contract.get("ready_with_limitation_requires_limitation_contract_active") is not True
        or contract["limitation_status_contract"].get("complete") is not True
        or alignment.get("exact_set_equality_required") is not True
        or required != set(EXPECTED_LIMITATION_AWARE_FEATURES)
        or declared != required
        or row_limited != required
        or sum(row.get("mapping_status") == "READY" for row in rows) != 47
    ):
        raise BasicFormRuntimeError("BASIC_FORM_BASELINE_NOT_READY")
    names = [row.get("canonical_feature", "") for row in rows]
    if any(dependency not in names for dependency in baseline_contract["required_dependencies"]):
        raise BasicFormRuntimeError("BASIC_FORM_BASELINE_DEPENDENCY_MISSING")
    if len(rows) != baseline_contract["required_row_count_per_profile"]:
        raise BasicFormRuntimeError("BASIC_FORM_BASELINE_FEATURE_COUNT_INVALID")
    if len(set(names)) != len(names):
        raise BasicFormRuntimeError("BASIC_FORM_BASELINE_FEATURE_DUPLICATE")
    if set(names) != set(contract["model_feature_contract"]["ordered_feature_names"]):
        raise BasicFormRuntimeError("BASIC_FORM_BASELINE_FEATURE_SET_MISMATCH")
    purpose_categories = set(contract["purpose_categorical_transport"]["exact_category_order"])
    payload: dict[str, object] = {}
    for row in rows:
        feature = row["canonical_feature"]
        raw_value: object = row.get("synthetic_value")
        if feature == "purpose":
            if type(raw_value) is not str or raw_value not in purpose_categories:
                raise BasicFormRuntimeError("BASIC_FORM_BASELINE_VALUE_INVALID")
            payload[feature] = raw_value
        else:
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                raise BasicFormRuntimeError("BASIC_FORM_BASELINE_VALUE_INVALID") from None
            if isinstance(raw_value, bool) or not math.isfinite(value):
                raise BasicFormRuntimeError("BASIC_FORM_BASELINE_VALUE_INVALID")
            payload[feature] = value
        if row.get("payload_compatible") != "True":
            raise BasicFormRuntimeError("BASIC_FORM_BASELINE_NOT_READY")
    return payload


def _prohibited_field_code(
    source_inputs: Mapping[str, object], system_metadata: Mapping[str, object], input_contract: Mapping[str, Any]
) -> str | None:
    registry = input_contract["privacy_and_identity_boundary"]["prohibited_field_registry"]
    names = set(map(str, source_inputs)) | set(map(str, system_metadata))
    if names & set(registry["identity_field_names"]):
        return registry["identity_failure_code"]
    if names & set(registry["free_text_field_names"]):
        return registry["free_text_failure_code"]
    return None


def _validate_public_request(
    source_inputs: Mapping[str, object], system_metadata: Mapping[str, object], input_contract: Mapping[str, Any]
) -> None:
    if not isinstance(source_inputs, Mapping) or not isinstance(system_metadata, Mapping):
        raise BasicFormRuntimeError("PUBLIC_INPUT_TYPE_INVALID")
    prohibited = _prohibited_field_code(source_inputs, system_metadata, input_contract)
    if prohibited:
        raise BasicFormRuntimeError(prohibited)
    expected_source = set(input_contract["source_field_contract"]["fields"])
    expected_metadata = set(input_contract["system_metadata_field_set_policy"]["exact_fields"])
    if set(source_inputs) != expected_source or set(system_metadata) != expected_metadata:
        raise BasicFormRuntimeError("PUBLIC_INPUT_FIELD_SET_INVALID")
    if any(source_inputs[field] is None for field in expected_source):
        raise BasicFormRuntimeError("PUBLIC_INPUT_VALUE_MISSING")
    if system_metadata["synthetic_completion_acknowledged"] is not True:
        raise BasicFormRuntimeError("SYNTHETIC_COMPLETION_NOT_ACKNOWLEDGED")
    allowed_profiles = input_contract["system_metadata_constraints"]["synthetic_baseline_profile_id"]["allowed_values"]
    profile_id = system_metadata["synthetic_baseline_profile_id"]
    if type(profile_id) is not str or profile_id not in allowed_profiles:
        raise BasicFormRuntimeError("PUBLIC_INPUT_BASELINE_INVALID")
    constraints = input_contract["field_constraints"]
    for name in ("annual_inc", "dti", "loan_amnt"):
        value = source_inputs[name]
        if isinstance(value, bool) or not isinstance(value, Real):
            raise BasicFormRuntimeError("PUBLIC_INPUT_TYPE_INVALID")
        number = float(value)
        if not math.isfinite(number):
            raise BasicFormRuntimeError("PUBLIC_INPUT_NON_FINITE")
        if not constraints[name]["minimum"] <= number <= constraints[name]["maximum"]:
            raise BasicFormRuntimeError("PUBLIC_INPUT_OUT_OF_RANGE")
    term = source_inputs["term_months"]
    if type(term) is not int or term not in constraints["term_months"]["allowed_values"]:
        raise BasicFormRuntimeError("PUBLIC_INPUT_TERM_INVALID")
    for name in ("home_ownership", "purpose"):
        value = source_inputs[name]
        allowed = constraints[name]["public_allowed_categories"]
        if type(value) is not str or value not in allowed:
            raise BasicFormRuntimeError("PUBLIC_INPUT_CATEGORY_INVALID")


def _evaluate_operation(
    operation: Mapping[str, Any], context: Mapping[str, object], contract: Mapping[str, Any]
) -> object:
    operation_type = operation["operation_type"]
    source_fields = operation.get("source_fields", [])
    try:
        operands = {name: context[name] for name in source_fields}
    except KeyError:
        raise BasicFormRuntimeError("BASIC_FORM_DERIVED_VALUE_INVALID") from None
    if operation_type == "IDENTITY_NUMERIC":
        value = operands[source_fields[0]]
        if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
            raise BasicFormRuntimeError("BASIC_FORM_DERIVED_VALUE_INVALID")
        return float(value)
    if operation_type == "IDENTITY_EXACT_INTEGER":
        value = operands[source_fields[0]]
        if type(value) is not int or value not in operation["allowed_values"]:
            raise BasicFormRuntimeError("BASIC_FORM_DERIVED_VALUE_INVALID")
        return value
    if operation_type == "IDENTITY_CATEGORICAL":
        value = operands[source_fields[0]]
        allowed = _resolve(contract, operation["allowed_values_reference"])
        if type(value) is not str or value not in allowed:
            raise BasicFormRuntimeError("BASIC_FORM_DERIVED_VALUE_INVALID")
        return value
    if operation_type == "LOG1P_FLOAT32":
        if operation.get("function") != "NATURAL_LOG1P":
            raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        value = float(operands[source_fields[0]])
        if not math.isfinite(value) or value <= 0:
            raise BasicFormRuntimeError("BASIC_FORM_DERIVED_VALUE_INVALID")
        result = _float32(math.log1p(value))
    elif operation_type == "ORDINAL_MAP_FLOAT32":
        mapping = _resolve(contract, operation["mapping_reference"])
        value = operands[source_fields[0]]
        if value not in mapping:
            raise BasicFormRuntimeError("BASIC_FORM_DERIVED_VALUE_INVALID")
        result = _float32(mapping[value])
    elif operation_type == "RATIO_CLIP_FLOAT32":
        denominator_spec = operation["denominator"]
        numerator = float(context[operation["numerator"]])
        denominator = float(context[denominator_spec["field"]]) / float(denominator_spec["divide_by"])
        if not all(map(math.isfinite, (numerator, denominator))) or denominator == 0:
            raise BasicFormRuntimeError("BASIC_FORM_DERIVED_VALUE_INVALID")
        arithmetic = numerator / denominator
        clipped = min(float(operation["clip_upper"]), max(float(operation["clip_lower"]), arithmetic))
        result = _float32(clipped)
    elif operation_type == "EQUALS_FLAG_INT8":
        result = operation["true_output"] if operands[source_fields[0]] == operation["comparison_value"] else operation["false_output"]
        if type(result) is not int or result not in (0, 1):
            raise BasicFormRuntimeError("BASIC_FORM_DERIVED_VALUE_INVALID")
        return result
    else:
        raise BasicFormRuntimeError("BASIC_FORM_OPERATION_TYPE_INVALID")
    if not math.isfinite(result):
        raise BasicFormRuntimeError("BASIC_FORM_DERIVED_VALUE_INVALID")
    return result


def _payload_fingerprint(contract: Mapping[str, Any], payload: Mapping[str, object]) -> str:
    class_sets, ordered, tags = _validate_fingerprint_contract(contract)
    if set(payload) != set(ordered):
        raise BasicFormRuntimeError("BASIC_FORM_PAYLOAD_FINGERPRINT_MISMATCH")
    records: list[str] = []
    for index, feature in enumerate(ordered):
        value = payload[feature]
        if feature in class_sets["category"]:
            tag, representation = tags["category"], str(value)
        elif feature in class_sets["exact_integer"]:
            if type(value) is not int:
                raise BasicFormRuntimeError("BASIC_FORM_PAYLOAD_FINGERPRINT_MISMATCH")
            tag, representation = tags["exact_integer"], str(value)
        elif feature in class_sets["float32_derived"]:
            tag, representation = tags["numeric"], str(_float32_bits(float(value)))
        elif feature in class_sets["direct_user_numeric"] | class_sets["baseline_numeric"]:
            tag, representation = tags["numeric"], format(float(value), ".17g")
        else:
            raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID")
        records.append(f"{index}|{feature}|{tag}|{representation}")
    return hashlib.sha256("\n".join(records).encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def _load_authority() -> _Authority:
    for path in EXPECTED_FILE_INTEGRITY:
        _verify_fixed_file(path)
    input_contract = _strict_json(INPUT_CONTRACT_PATH)
    mapping_contract = _strict_json(MAPPING_CONTRACT_PATH)
    manifest = _strict_json(MODEL_MANIFEST_PATH)
    try:
        model_order = tuple(manifest["features"]["ordered_feature_names"])
    except (KeyError, TypeError):
        raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID") from None
    _validate_input_contract(input_contract)
    _validate_mapping_contract(mapping_contract, model_order)
    profiles = _read_profiles()
    if set(profiles) != set(mapping_contract["baseline_profile_contract"]["allowed_profile_ids"]):
        raise BasicFormRuntimeError("BASIC_FORM_BASELINE_NOT_READY")
    for profile_id, rows in profiles.items():
        _validate_baseline_profile(mapping_contract, profile_id, rows)
    return _Authority(input_contract, mapping_contract, MappingProxyType(profiles), model_order)


def clear_basic_form_runtime_cache() -> None:
    """Clear only cached contract data; primarily useful for isolated tests."""

    _load_authority.cache_clear()


def build_basic_form_mapping_result(
    source_inputs: Mapping[str, object], system_metadata: Mapping[str, object]
) -> BasicFormMappingResult:
    """Validate and assemble one exact 49-feature Basic Form model payload."""

    authority = _load_authority()
    _validate_public_request(source_inputs, system_metadata, authority.input_contract)
    contract = authority.mapping_contract
    profile_id = str(system_metadata["synthetic_baseline_profile_id"])
    if profile_id not in authority.profiles:
        raise BasicFormRuntimeError("BASIC_FORM_BASELINE_ID_INVALID")
    baseline = _validate_baseline_profile(contract, profile_id, authority.profiles[profile_id])
    passthrough = contract["dependency_partition"]["synthetic_baseline_passthrough"]
    payload: dict[str, object] = {name: copy.deepcopy(baseline[name]) for name in passthrough}
    context: dict[str, object] = {**baseline, **dict(source_inputs), **payload}
    by_id = {item["operation_id"]: item for item in contract["operation_registry"]}
    authorized = set(contract["dependency_partition"]["direct_user_supplied"]) | set(contract["dependency_partition"]["derived"])
    for operation_id in contract["operation_execution_order"]:
        operation = by_id[operation_id]
        target = operation["target_feature"]
        if target not in authorized:
            raise BasicFormRuntimeError("BASIC_FORM_IMPACT_CLOSURE_INVALID")
        value = _evaluate_operation(operation, context, contract)
        if target in contract["dependency_partition"]["derived"]:
            if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
                raise BasicFormRuntimeError("BASIC_FORM_DERIVED_VALUE_INVALID")
            if operation.get("output_dtype") == "float32" and _float32(float(value)) != value:
                raise BasicFormRuntimeError("BASIC_FORM_DERIVED_VALUE_INVALID")
        payload[target] = value
        context[target] = value
    ordered_names = tuple(contract["model_feature_contract"]["ordered_feature_names"])
    if set(payload) != set(ordered_names):
        raise BasicFormRuntimeError("BASIC_FORM_IMPACT_CLOSURE_INVALID")
    ordered_payload = {name: payload[name] for name in ordered_names}
    fingerprint = _payload_fingerprint(contract, ordered_payload)
    return BasicFormMappingResult(
        _seal=_MAPPING_RESULT_SEAL,
        mode="BASIC_FORM",
        mapping_contract_id=MAPPING_CONTRACT_ID,
        input_contract_id=INPUT_CONTRACT_ID,
        source_inputs=source_inputs,
        system_metadata=system_metadata,
        payload=MappingProxyType(ordered_payload),
        ordered_feature_names=ordered_names,
        payload_fingerprint=fingerprint,
        selected_synthetic_profile_id=profile_id,
        synthetic_completion_acknowledged=True,
        value_source_counts=MappingProxyType(dict(EXPECTED_VALUE_SOURCE_COUNTS)),
        limitation_aware_features=EXPECTED_LIMITATION_AWARE_FEATURES,
        feature_count=49,
        safe_disclosure=MappingProxyType({
            "fictional_synthetic_values_only": True,
            "portfolio_demo_only": True,
            "complete_payload_logging_allowed": False,
        }),
    )


def _mapping_results_exactly_match(
    original: BasicFormMappingResult,
    rebuilt: BasicFormMappingResult,
) -> bool:
    """Compare all retained and derived authorization evidence exactly."""

    if type(original) is not BasicFormMappingResult or type(rebuilt) is not BasicFormMappingResult:
        return False
    scalar_fields = (
        "mode",
        "mapping_contract_id",
        "input_contract_id",
        "payload_fingerprint",
        "selected_synthetic_profile_id",
        "synthetic_completion_acknowledged",
        "feature_count",
    )
    if any(getattr(original, name) != getattr(rebuilt, name) for name in scalar_fields):
        return False
    if original.ordered_feature_names != rebuilt.ordered_feature_names:
        return False
    if tuple(original.payload) != tuple(rebuilt.payload):
        return False
    if any(original.payload[name] != rebuilt.payload[name] for name in original.payload):
        return False
    return all((
        dict(original.source_inputs) == dict(rebuilt.source_inputs),
        dict(original.system_metadata) == dict(rebuilt.system_metadata),
        dict(original.value_source_counts) == dict(rebuilt.value_source_counts),
        original.limitation_aware_features == rebuilt.limitation_aware_features,
        dict(original.safe_disclosure) == dict(rebuilt.safe_disclosure),
    ))


def revalidate_basic_form_mapping_result(result: BasicFormMappingResult) -> None:
    """Recompute all security-relevant mapping evidence before inference."""

    if type(result) is not BasicFormMappingResult:
        raise BasicFormRuntimeError("BASIC_FORM_RESULT_TYPE_INVALID")
    authority = _load_authority()
    contract = authority.mapping_contract
    if result.mode != "BASIC_FORM":
        raise BasicFormRuntimeError("BASIC_FORM_MODE_INVALID")
    if result.input_contract_id != INPUT_CONTRACT_ID:
        raise BasicFormRuntimeError("BASIC_FORM_INPUT_CONTRACT_INVALID")
    if result.mapping_contract_id != MAPPING_CONTRACT_ID:
        raise BasicFormRuntimeError("BASIC_FORM_MAPPING_CONTRACT_INVALID")
    if result.synthetic_completion_acknowledged is not True:
        raise BasicFormRuntimeError("BASIC_FORM_ACKNOWLEDGEMENT_REQUIRED")
    if result.selected_synthetic_profile_id not in contract["baseline_profile_contract"]["allowed_profile_ids"]:
        raise BasicFormRuntimeError("BASIC_FORM_PROFILE_ID_INVALID")
    if result.feature_count != 49 or len(result.payload) != 49:
        raise BasicFormRuntimeError("BASIC_FORM_FEATURE_COUNT_INVALID")
    expected_order = tuple(contract["model_feature_contract"]["ordered_feature_names"])
    if set(result.payload) != set(expected_order):
        raise BasicFormRuntimeError("BASIC_FORM_FEATURE_SET_INVALID")
    if result.ordered_feature_names != expected_order or tuple(result.payload) != expected_order:
        raise BasicFormRuntimeError("BASIC_FORM_FEATURE_ORDER_INVALID")
    if dict(result.value_source_counts) != EXPECTED_VALUE_SOURCE_COUNTS:
        raise BasicFormRuntimeError("BASIC_FORM_PROVENANCE_INVALID")
    if result.limitation_aware_features != EXPECTED_LIMITATION_AWARE_FEATURES:
        raise BasicFormRuntimeError("BASIC_FORM_LIMITATION_STATUS_INVALID")
    purpose_categories = contract["purpose_categorical_transport"]["exact_category_order"]
    for name, value in result.payload.items():
        if name == "purpose":
            if type(value) is not str or value not in purpose_categories:
                raise BasicFormRuntimeError("BASIC_FORM_PURPOSE_INVALID")
        elif isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
            raise BasicFormRuntimeError("BASIC_FORM_FEATURE_VALUE_INVALID")
    term = result.payload["term_months"]
    if type(term) is not int or term not in (36, 60):
        raise BasicFormRuntimeError("BASIC_FORM_TERM_INVALID")
    flag = result.payload["is_60_month"]
    if type(flag) is not int or flag not in (0, 1):
        raise BasicFormRuntimeError("BASIC_FORM_TERM_INVALID")
    if _payload_fingerprint(contract, result.payload) != result.payload_fingerprint:
        raise BasicFormRuntimeError("BASIC_FORM_PAYLOAD_FINGERPRINT_MISMATCH")


def recompute_payload_fingerprint(result: BasicFormMappingResult) -> str:
    """Return the frozen-contract fingerprint after exact result-type checking."""

    if type(result) is not BasicFormMappingResult:
        raise BasicFormRuntimeError("BASIC_FORM_RESULT_TYPE_INVALID")
    return _payload_fingerprint(_load_authority().mapping_contract, result.payload)
