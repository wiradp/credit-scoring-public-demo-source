"""Frozen-contract validation for fictional Advanced Editor requests.

This module validates a raw request against the committed Stage 9 Step 4.2B
contract.  It does not load the model, execute inference, or accept path
overrides.  The immutable result is evidence for the atomic adapter only; it is
not a public inference-authorization token.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = PROJECT_ROOT / "outputs/stage9/stage9_advanced_editor_validation_contract.json"
CONTRACT_SIZE = 111_470
CONTRACT_SHA256 = "47b688fa8620a6691ac535d686912c5ca732313e16b0ee1ea4dff214f6c750ac"
CONTRACT_ID = "STAGE9_ADVANCED_EDITOR_VALIDATION_V1"
AUTHORIZED_MODE = "ADVANCED_EDITOR"
SAFE_DISCLOSURE = (
    "This output is a fictional portfolio demonstration and is not a lending "
    "decision, approval recommendation, rejection recommendation, legal "
    "assessment, fairness conclusion, or production underwriting result."
)
_RESULT_SEAL = object()


class AdvancedEditorValidationError(ValueError):
    """Fail-closed validation error containing only a frozen failure code."""

    def __init__(self, code: str):
        self.code = str(code)
        super().__init__(self.code)


def _deep_freeze(value: Any) -> Any:
    """Return a detached, recursively immutable representation of ``value``."""

    if isinstance(value, Mapping):
        return MappingProxyType({
            key: _deep_freeze(nested)
            for key, nested in value.items()
        })
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze(nested) for nested in value)
    if isinstance(value, set):
        return frozenset(_deep_freeze(nested) for nested in value)
    return value


@dataclass(frozen=True, init=False)
class AdvancedEditorValidationResult:
    """Immutable validation evidence; complete payload is excluded from repr."""

    mode: str
    profile_id: str
    ordered_feature_names: tuple[str, ...]
    validated_canonical_payload: Mapping[str, object] = field(repr=False)
    payload_fingerprint: str
    edited_feature_names: tuple[str, ...]
    provenance_counts: Mapping[str, int]
    limitation_aware_features: tuple[str, ...]
    safe_disclosure: str
    validation_status: str

    def __init__(
        self,
        *,
        mode: str,
        profile_id: str,
        ordered_feature_names: tuple[str, ...],
        validated_canonical_payload: Mapping[str, object],
        payload_fingerprint: str,
        edited_feature_names: tuple[str, ...],
        provenance_counts: Mapping[str, int],
        limitation_aware_features: tuple[str, ...],
        safe_disclosure: str,
        validation_status: str,
        _seal: object,
    ) -> None:
        if _seal is not _RESULT_SEAL:
            raise TypeError("AdvancedEditorValidationResult cannot be constructed directly")
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "profile_id", profile_id)
        object.__setattr__(self, "ordered_feature_names", tuple(ordered_feature_names))
        object.__setattr__(
            self,
            "validated_canonical_payload",
            _deep_freeze(validated_canonical_payload),
        )
        object.__setattr__(self, "payload_fingerprint", payload_fingerprint)
        object.__setattr__(self, "edited_feature_names", tuple(edited_feature_names))
        object.__setattr__(self, "provenance_counts", _deep_freeze(provenance_counts))
        object.__setattr__(self, "limitation_aware_features", tuple(limitation_aware_features))
        object.__setattr__(self, "safe_disclosure", safe_disclosure)
        object.__setattr__(self, "validation_status", validation_status)

    def safe_metadata(self) -> dict[str, object]:
        """Return disclosure-safe evidence without raw rows or payload values."""

        return {
            "mode": self.mode,
            "profile_id": self.profile_id,
            "feature_count": len(self.ordered_feature_names),
            "payload_fingerprint": self.payload_fingerprint,
            "edited_feature_count": len(self.edited_feature_names),
            "edited_feature_names": list(self.edited_feature_names),
            "provenance_counts": dict(self.provenance_counts),
            "limitation_aware_features": list(self.limitation_aware_features),
            "validation_status": self.validation_status,
            "safe_disclosure": self.safe_disclosure,
        }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _strict_json(path: Path) -> dict[str, Any]:
    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in pairs:
            if key in output:
                raise AdvancedEditorValidationError("ADVANCED_EDITOR_CONTRACT_INVALID")
            output[key] = value
        return output

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=object_pairs,
            parse_constant=lambda _token: (_ for _ in ()).throw(ValueError()),
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_CONTRACT_INVALID") from None
    if not isinstance(value, dict):
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_CONTRACT_INVALID")
    return value


@lru_cache(maxsize=1)
def _authority() -> tuple[
    Mapping[str, Any],
    tuple[str, ...],
    Mapping[str, Mapping[str, Any]],
    Mapping[str, Mapping[str, object]],
]:
    try:
        if CONTRACT_PATH.is_symlink() or CONTRACT_PATH.stat().st_size != CONTRACT_SIZE:
            raise AdvancedEditorValidationError("ADVANCED_EDITOR_CONTRACT_INVALID")
    except OSError:
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_CONTRACT_INVALID") from None
    if _sha256(CONTRACT_PATH) != CONTRACT_SHA256:
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_CONTRACT_INVALID")
    contract = _strict_json(CONTRACT_PATH)
    try:
        order = tuple(contract["feature_schema"]["ordered_feature_names"])
        registry_rows = contract["feature_registry"]
        projection_rows = contract["canonical_reset_projections"]
        limitation_features = tuple(contract["limitation_policy"]["limitation_aware_features"])
        request_contract = contract["request_contract"]
    except (KeyError, TypeError):
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_CONTRACT_INVALID") from None
    if (
        contract.get("contract_id") != CONTRACT_ID
        or contract.get("validation_status") != "PASS"
        or len(order) != 49
        or len(set(order)) != 49
        or not isinstance(registry_rows, list)
        or len(registry_rows) != 49
        or not isinstance(projection_rows, list)
        or len(projection_rows) != 5
        or set(limitation_features) != {"grade_encoded", "credit_age_months"}
        or request_contract.get("mode") != AUTHORIZED_MODE
    ):
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_CONTRACT_INVALID")
    registry: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(registry_rows):
        if (
            not isinstance(row, dict)
            or row.get("feature_index") != index
            or row.get("feature_name") != order[index]
            or row.get("required") is not True
            or row.get("bool_allowed") is not False
            or row.get("null_allowed") is not False
        ):
            raise AdvancedEditorValidationError("ADVANCED_EDITOR_CONTRACT_INVALID")
        registry[order[index]] = row
    projections: dict[str, dict[str, object]] = {}
    for projection in projection_rows:
        if not isinstance(projection, dict) or projection.get("fingerprint_match") is not True:
            raise AdvancedEditorValidationError("ADVANCED_EDITOR_RESET_PROJECTION_INVALID")
        profile_id = projection.get("profile_id")
        rows = projection.get("payload_rows")
        if not isinstance(profile_id, str) or profile_id in projections or not isinstance(rows, list) or len(rows) != 49:
            raise AdvancedEditorValidationError("ADVANCED_EDITOR_RESET_PROJECTION_INVALID")
        payload: dict[str, object] = {}
        for index, row in enumerate(rows):
            if not isinstance(row, dict) or row.get("feature_index") != index or row.get("feature_name") != order[index]:
                raise AdvancedEditorValidationError("ADVANCED_EDITOR_RESET_PROJECTION_INVALID")
            payload[order[index]] = row.get("value")
        if _payload_fingerprint(contract, order, payload) != projection.get("expected_payload_fingerprint"):
            raise AdvancedEditorValidationError("ADVANCED_EDITOR_RESET_FINGERPRINT_MISMATCH")
        projections[profile_id] = payload
    if set(projections) != set(request_contract["system_metadata"]["allowed_profile_ids"]):
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_RESET_VECTOR_MAPPING_INVALID")
    return (
        _deep_freeze(contract),
        order,
        _deep_freeze(registry),
        _deep_freeze(projections),
    )


def clear_advanced_editor_runtime_cache() -> None:
    """Clear only the immutable contract cache; useful for integrity tests."""

    _authority.cache_clear()


def _float32_bits(value: object) -> int:
    return struct.unpack(">I", struct.pack(">f", float(value)))[0]


def _payload_fingerprint(
    contract: Mapping[str, Any],
    order: tuple[str, ...],
    payload: Mapping[str, object],
) -> str:
    try:
        classes = contract["payload_fingerprint_contract"]["feature_representation_classes"]
        category = set(classes["category"])
        exact_integer = set(classes["exact_integer"])
        float32_derived = set(classes["float32_derived"])
    except (KeyError, TypeError):
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_CONTRACT_INVALID") from None
    if set(payload) != set(order):
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_PAYLOAD_FINGERPRINT_INVALID")
    records: list[str] = []
    for index, feature in enumerate(order):
        value = payload[feature]
        if feature in category:
            tag, representation = "CATEGORY", str(value)
        elif feature in exact_integer:
            if type(value) is not int:
                raise AdvancedEditorValidationError("ADVANCED_EDITOR_PAYLOAD_FINGERPRINT_INVALID")
            tag, representation = "INT8", str(value)
        elif feature in float32_derived:
            tag, representation = "NUMERIC", str(_float32_bits(value))
        else:
            tag, representation = "NUMERIC", format(float(value), ".17g")
        records.append(f"{index}|{feature}|{tag}|{representation}")
    return hashlib.sha256("\n".join(records).encode("utf-8")).hexdigest()


def _validate_value(feature: str, value: object, rule: Mapping[str, Any], base: Mapping[str, object]) -> None:
    if value is None:
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_NULL_VALUE_INVALID")
    if type(value) is bool:
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_BOOLEAN_VALUE_INVALID")
    if isinstance(value, (Mapping, list, tuple, set)):
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_NESTED_VALUE_INVALID")
    transport = rule.get("transport_class")
    if transport == "CATEGORY":
        if not isinstance(value, str) or value not in rule.get("allowed_values", []):
            raise AdvancedEditorValidationError("ADVANCED_EDITOR_CATEGORY_INVALID")
        return
    if transport == "EXACT_INTEGER":
        if type(value) is not int or value not in rule.get("allowed_values", []):
            raise AdvancedEditorValidationError("ADVANCED_EDITOR_EXACT_INTEGER_INVALID")
        return
    if not isinstance(value, (int, float)):
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_VALUE_TYPE_INVALID")
    if not math.isfinite(float(value)):
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_NON_FINITE_VALUE")
    if transport == "DISCRETE_NUMERIC" and value not in rule.get("allowed_values", []):
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_DISCRETE_VALUE_INVALID")
    if transport == "CONTINUOUS_NUMERIC":
        minimum, maximum = rule.get("minimum"), rule.get("maximum")
        if not isinstance(minimum, (int, float)) or not isinstance(maximum, (int, float)) or not minimum <= value <= maximum:
            raise AdvancedEditorValidationError("ADVANCED_EDITOR_VALUE_OUT_OF_RANGE")
    if transport == "LOCKED_NUMERIC" and value != base[feature]:
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_LOCKED_VALUE_MISMATCH")


def validate_advanced_editor_request(
    request: Mapping[str, object],
) -> AdvancedEditorValidationResult:
    """Validate one raw request atomically against the frozen 49-feature contract."""

    if not isinstance(request, Mapping) or set(request) != {"mode", "system_metadata", "payload_rows"}:
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_REQUEST_TYPE_INVALID")
    if request["mode"] != AUTHORIZED_MODE:
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_MODE_INVALID")
    contract, order, registry, projections = _authority()
    metadata = request["system_metadata"]
    if not isinstance(metadata, Mapping):
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_SYSTEM_METADATA_FIELD_SET_INVALID")
    identity = {"full_name", "nik", "national_id", "address", "email", "telephone_number", "bank_account", "customer_id", "real_person_application_id", "employer_identity"}
    free_text = {"personal_narrative", "free_text_notes", "notes"}
    if set(metadata) & identity:
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_IDENTITY_FIELD_PROHIBITED")
    if set(metadata) & free_text:
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_FREE_TEXT_FIELD_PROHIBITED")
    expected_metadata = {"advanced_editor_profile_id", "advanced_editor_acknowledged", "edited_feature_names"}
    if set(metadata) != expected_metadata:
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_SYSTEM_METADATA_FIELD_SET_INVALID")
    profile_id = metadata["advanced_editor_profile_id"]
    if not isinstance(profile_id, str) or profile_id not in projections:
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_PROFILE_ID_INVALID")
    if metadata["advanced_editor_acknowledged"] is not True:
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_ACKNOWLEDGEMENT_REQUIRED")
    edited = metadata["edited_feature_names"]
    if not isinstance(edited, list) or any(not isinstance(name, str) for name in edited):
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_EDITED_FEATURE_LIST_INVALID")
    if len(edited) != len(set(edited)):
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_EDITED_FEATURE_DUPLICATE")
    if any(name not in registry for name in edited):
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_EDITED_FEATURE_UNKNOWN")
    if any(registry[name].get("editable") is not True for name in edited):
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_LOCKED_FEATURE_EDITED")
    rows = request["payload_rows"]
    if not isinstance(rows, list):
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_PAYLOAD_TYPE_INVALID")
    if len(rows) != 49:
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_PAYLOAD_ROW_COUNT_INVALID")
    if any(not isinstance(row, Mapping) or set(row) != {"feature_index", "feature_name", "value"} for row in rows):
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_PAYLOAD_ROW_SHAPE_INVALID")
    names = [row["feature_name"] for row in rows]
    if len(names) != len(set(names)):
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_FEATURE_DUPLICATE")
    payload: dict[str, object] = {}
    for index, row in enumerate(rows):
        if type(row["feature_index"]) is not int or row["feature_index"] != index:
            raise AdvancedEditorValidationError("ADVANCED_EDITOR_FEATURE_INDEX_INVALID")
        feature = row["feature_name"]
        if not isinstance(feature, str) or feature not in registry:
            raise AdvancedEditorValidationError("ADVANCED_EDITOR_FEATURE_NAME_INVALID")
        if feature != order[index]:
            raise AdvancedEditorValidationError("ADVANCED_EDITOR_FEATURE_ORDER_INVALID")
        payload[feature] = row["value"]
    base = projections[profile_id]
    if not edited and payload != base and any(payload == candidate for other, candidate in projections.items() if other != profile_id):
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_RESET_PROJECTION_INVALID")
    for feature in order:
        _validate_value(feature, payload[feature], registry[feature], base)
    if payload["is_60_month"] != int(payload["term_months"] == 60):
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_RELATIONSHIP_INVALID")
    differences = {
        feature for feature in order
        if registry[feature].get("editable") is True and payload[feature] != base[feature]
    }
    if set(edited) != differences:
        raise AdvancedEditorValidationError("ADVANCED_EDITOR_EDITED_FEATURE_SET_MISMATCH")
    fingerprint = _payload_fingerprint(contract, order, payload)
    provenance = {
        "USER_EDITED": len(differences),
        "CANONICAL_RESET_PROJECTION": 49 - len(differences),
    }
    return AdvancedEditorValidationResult(
        mode=AUTHORIZED_MODE,
        profile_id=profile_id,
        ordered_feature_names=order,
        validated_canonical_payload=payload,
        payload_fingerprint=fingerprint,
        edited_feature_names=tuple(feature for feature in order if feature in differences),
        provenance_counts=provenance,
        limitation_aware_features=tuple(contract["limitation_policy"]["limitation_aware_features"]),
        safe_disclosure=SAFE_DISCLOSURE,
        validation_status="VALID",
        _seal=_RESULT_SEAL,
    )


def advanced_editor_contract_summary() -> Mapping[str, object]:
    """Expose a detached, recursively immutable UI summary."""

    contract, order, registry, projections = _authority()
    return _deep_freeze({
        "contract_id": CONTRACT_ID,
        "ordered_feature_names": order,
        "feature_registry": tuple(registry[f] for f in order),
        "profile_ids": tuple(projections),
        "canonical_reset_projections": projections,
        "safe_disclosure": SAFE_DISCLOSURE,
        "difference_set_domain": contract["editability_policy"]["difference_set_domain"],
    })
