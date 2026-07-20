from __future__ import annotations

import ast
import csv
import hashlib
import json
import math
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "outputs/stage9"
CONTRACT_PATH = P / "stage9_advanced_editor_validation_contract.json"
VECTORS_PATH = P / "stage9_advanced_editor_validation_golden_vectors.json"
REPORT_PATH = P / "stage9_advanced_editor_validation_report.json"
MANIFEST_PATH = P / "stage9_step4_2b_artifact_manifest.json"
PROFILE_PATH = ROOT / "artifacts/contracts/cell_group_7/sample_profiles/sample_profile_feature_matrix.csv"
MAPPING_PATH = P / "stage9_basic_form_runtime_mapping_contract.json"
SOURCE_VECTOR_PATH = P / "stage9_basic_form_runtime_mapping_golden_vectors.json"
MODEL_PATH = ROOT / "artifacts/model/model_artifact_manifest.json"
SCHEMA_PATH = ROOT / "artifacts/contracts/cell_group_7/schema/canonical_demo_input_schema.csv"


def strict(path):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out: raise ValueError(key)
            out[key] = value
        return out
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


C = strict(CONTRACT_PATH); V = strict(VECTORS_PATH); R = strict(REPORT_PATH); M = strict(MAPPING_PATH); SV = strict(SOURCE_VECTOR_PATH)
ORDER = C["feature_schema"]["ordered_feature_names"]
REG = {r["feature_name"]: r for r in C["feature_registry"]}
PROJ = {p["profile_id"]: p for p in C["canonical_reset_projections"]}
VALUES = {p: {r["feature_name"]: r["value"] for r in projection["payload_rows"]} for p, projection in PROJ.items()}


class ContractError(Exception): pass
def fail(code): raise ContractError(code)


def fingerprint(payload):
    classes = C["payload_fingerprint_contract"]["feature_representation_classes"]
    category, exact, f32 = set(classes["category"]), set(classes["exact_integer"]), set(classes["float32_derived"])
    records = []
    for i, feature in enumerate(ORDER):
        value = payload[feature]
        if feature in category: tag, rep = "CATEGORY", str(value)
        elif feature in exact: tag, rep = "INT8", str(value)
        elif feature in f32: tag, rep = "NUMERIC", str(struct.unpack(">I", struct.pack(">f", float(value)))[0])
        else: tag, rep = "NUMERIC", format(float(value), ".17g")
        records.append(f"{i}|{feature}|{tag}|{rep}")
    return hashlib.sha256("\n".join(records).encode()).hexdigest()


def validate(request):
    if not isinstance(request, dict) or set(request) != {"mode", "system_metadata", "payload_rows"}: fail("ADVANCED_EDITOR_REQUEST_TYPE_INVALID")
    if request["mode"] != "ADVANCED_EDITOR": fail("ADVANCED_EDITOR_MODE_INVALID")
    metadata = request["system_metadata"]
    if not isinstance(metadata, dict): fail("ADVANCED_EDITOR_SYSTEM_METADATA_FIELD_SET_INVALID")
    if any(k in metadata for k in {"full_name", "nik", "email", "address"}): fail("ADVANCED_EDITOR_IDENTITY_FIELD_PROHIBITED")
    if any(k in metadata for k in {"notes", "personal_narrative", "free_text_notes"}): fail("ADVANCED_EDITOR_FREE_TEXT_FIELD_PROHIBITED")
    if set(metadata) != {"advanced_editor_profile_id", "advanced_editor_acknowledged", "edited_feature_names"}: fail("ADVANCED_EDITOR_SYSTEM_METADATA_FIELD_SET_INVALID")
    profile = metadata["advanced_editor_profile_id"]
    if profile not in PROJ: fail("ADVANCED_EDITOR_PROFILE_ID_INVALID")
    if metadata["advanced_editor_acknowledged"] is not True: fail("ADVANCED_EDITOR_ACKNOWLEDGEMENT_REQUIRED")
    edited = metadata["edited_feature_names"]
    if not isinstance(edited, list) or any(not isinstance(x, str) for x in edited): fail("ADVANCED_EDITOR_EDITED_FEATURE_LIST_INVALID")
    if len(edited) != len(set(edited)): fail("ADVANCED_EDITOR_EDITED_FEATURE_DUPLICATE")
    if any(x not in REG for x in edited): fail("ADVANCED_EDITOR_EDITED_FEATURE_UNKNOWN")
    if any(not REG[x]["editable"] for x in edited): fail("ADVANCED_EDITOR_LOCKED_FEATURE_EDITED")
    rows = request["payload_rows"]
    if not isinstance(rows, list): fail("ADVANCED_EDITOR_PAYLOAD_TYPE_INVALID")
    if len(rows) != 49: fail("ADVANCED_EDITOR_PAYLOAD_ROW_COUNT_INVALID")
    if any(not isinstance(row, dict) or set(row) != {"feature_index", "feature_name", "value"} for row in rows): fail("ADVANCED_EDITOR_PAYLOAD_ROW_SHAPE_INVALID")
    names = [row["feature_name"] for row in rows]
    if len(names) != len(set(names)): fail("ADVANCED_EDITOR_FEATURE_DUPLICATE")
    for index, row in enumerate(rows):
        if type(row["feature_index"]) is not int or row["feature_index"] != index: fail("ADVANCED_EDITOR_FEATURE_INDEX_INVALID")
        if not isinstance(row["feature_name"], str) or row["feature_name"] not in REG: fail("ADVANCED_EDITOR_FEATURE_NAME_INVALID")
        if row["feature_name"] != ORDER[index]: fail("ADVANCED_EDITOR_FEATURE_ORDER_INVALID")
        if isinstance(row["value"], (dict, list)): fail("ADVANCED_EDITOR_NESTED_VALUE_INVALID")
    payload = {row["feature_name"]: row["value"] for row in rows}; base = VALUES[profile]
    if not edited and payload != base and any(payload == other for p, other in VALUES.items() if p != profile): fail("ADVANCED_EDITOR_RESET_PROJECTION_INVALID")
    for feature in ORDER:
        value, rule = payload[feature], REG[feature]
        if value is None: fail("ADVANCED_EDITOR_NULL_VALUE_INVALID")
        if type(value) is bool: fail("ADVANCED_EDITOR_BOOLEAN_VALUE_INVALID")
        if rule["transport_class"] == "CATEGORY":
            if not isinstance(value, str) or value not in rule["allowed_values"]: fail("ADVANCED_EDITOR_CATEGORY_INVALID")
        elif rule["transport_class"] == "EXACT_INTEGER":
            if type(value) is not int or value not in rule["allowed_values"]: fail("ADVANCED_EDITOR_EXACT_INTEGER_INVALID")
        elif not isinstance(value, (int, float)): fail("ADVANCED_EDITOR_VALUE_TYPE_INVALID")
        elif not math.isfinite(float(value)): fail("ADVANCED_EDITOR_NON_FINITE_VALUE")
        elif rule["transport_class"] == "DISCRETE_NUMERIC" and value not in rule["allowed_values"]: fail("ADVANCED_EDITOR_DISCRETE_VALUE_INVALID")
        elif rule["transport_class"] == "CONTINUOUS_NUMERIC" and not (rule["minimum"] <= value <= rule["maximum"]): fail("ADVANCED_EDITOR_VALUE_OUT_OF_RANGE")
        elif rule["transport_class"] == "LOCKED_NUMERIC" and value != base[feature]: fail("ADVANCED_EDITOR_LOCKED_VALUE_MISMATCH")
    if payload["is_60_month"] != int(payload["term_months"] == 60): fail("ADVANCED_EDITOR_RELATIONSHIP_INVALID")
    differences = {f for f in ORDER if REG[f]["editable"] and payload[f] != base[f]}
    if set(edited) != differences: fail("ADVANCED_EDITOR_EDITED_FEATURE_SET_MISMATCH")
    return {"status": "VALID", "payload_fingerprint": fingerprint(payload), "provenance_counts": {"USER_EDITED": len(differences), "CANONICAL_RESET_PROJECTION": 49 - len(differences)}}


def request_for(profile, mutations=None, edited=None, derive_flag=True):
    payload = dict(VALUES[profile])
    for feature, value in (mutations or {}).items():
        if isinstance(value, dict): value = {"NAN": float("nan"), "POSITIVE_INFINITY": float("inf"), "NEGATIVE_INFINITY": float("-inf")}[value["special_numeric"]]
        payload[feature] = value
    if derive_flag and "term_months" in (mutations or {}) and type(payload["term_months"]) is int and payload["term_months"] in (36, 60): payload["is_60_month"] = int(payload["term_months"] == 60)
    return {"mode": "ADVANCED_EDITOR", "system_metadata": {"advanced_editor_profile_id": profile, "advanced_editor_acknowledged": True, "edited_feature_names": list(edited or [])}, "payload_rows": [{"feature_index": i, "feature_name": f, "value": payload[f]} for i, f in enumerate(ORDER)]}


def scenario(vector):
    name = vector["scenario"]; request = request_for(vector.get("base_profile_id", "SP_LOW_RISK_SIGNAL"))
    if name == "REQUEST_TYPE": return []
    if name == "MODE": request["mode"] = "BASIC_FORM"
    elif name == "MISSING_METADATA": request["system_metadata"].pop("edited_feature_names")
    elif name == "EXTRA_METADATA": request["system_metadata"]["extra"] = 1
    elif name == "UNKNOWN_PROFILE": request["system_metadata"]["advanced_editor_profile_id"] = "UNKNOWN"
    elif name == "FALSE_ACK": request["system_metadata"]["advanced_editor_acknowledged"] = False
    elif name == "EDITED_LIST_TYPE": request["system_metadata"]["edited_feature_names"] = "dti"
    elif name == "DUPLICATE_EDIT": request["system_metadata"]["edited_feature_names"] = ["dti", "dti"]
    elif name == "UNKNOWN_EDIT": request["system_metadata"]["edited_feature_names"] = ["unknown"]
    elif name == "HIDDEN_EDIT": request["payload_rows"][10]["value"] = 19.0
    elif name == "FALSE_DECLARED_EDIT": request["system_metadata"]["edited_feature_names"] = ["dti"]
    elif name == "PAYLOAD_TYPE": request["payload_rows"] = {}
    elif name == "MISSING_ROW": request["payload_rows"].pop()
    elif name == "EXTRA_ROW": request["payload_rows"].append(dict(request["payload_rows"][-1]))
    elif name == "DUPLICATE_ROW": request["payload_rows"][-1] = dict(request["payload_rows"][0])
    elif name == "WRONG_INDEX": request["payload_rows"][0]["feature_index"] = 1
    elif name == "WRONG_NAME": request["payload_rows"][0]["feature_name"] = "unknown"
    elif name == "WRONG_ORDER":
        a, b = request["payload_rows"][0], request["payload_rows"][1]; a["feature_name"], b["feature_name"] = b["feature_name"], a["feature_name"]; a["value"], b["value"] = b["value"], a["value"]
    elif name == "EXTRA_ROW_FIELD": request["payload_rows"][0]["extra"] = 1
    elif name == "MISSING_ROW_FIELD": request["payload_rows"][0].pop("value")
    elif name == "NESTED_OBJECT": request["payload_rows"][0]["value"] = {"x": 1}
    elif name == "NESTED_ARRAY": request["payload_rows"][0]["value"] = [1]
    elif name == "PROFILE_PROJECTION_MISMATCH": request = request_for("SP_MEDIUM_RISK_SIGNAL"); request["system_metadata"]["advanced_editor_profile_id"] = "SP_LOW_RISK_SIGNAL"
    elif name == "TERM_FLAG_MISMATCH_36_1": request = request_for("SP_LOW_RISK_SIGNAL", {"is_60_month": 1}, [], False)
    elif name == "TERM_FLAG_MISMATCH_60_0": request = request_for("SP_MEDIUM_RISK_SIGNAL", {"is_60_month": 0}, [], False)
    elif name == "IDENTITY_INJECTION": request["system_metadata"]["full_name"] = "Fictional Name"
    elif name == "FREE_TEXT_INJECTION": request["system_metadata"]["notes"] = "free text"
    return request


class AdvancedEditorContractTests(unittest.TestCase):
    def test_01_strict_json(self):
        for path in (CONTRACT_PATH, VECTORS_PATH, REPORT_PATH, MANIFEST_PATH): self.assertIsNotNone(strict(path))
    def test_02_authority_hash_and_schema_alignment(self):
        for item in C["authority_sources"]: self.assertEqual(hashlib.sha256((ROOT / item["relative_path"]).read_bytes()).hexdigest(), item["sha256"])
        model = strict(MODEL_PATH)["features"]["ordered_feature_names"]
        with SCHEMA_PATH.open(newline="", encoding="utf-8") as handle: schema = [r["canonical_feature_name"] for r in csv.DictReader(handle) if r["schema_mode"] == "ADVANCED_EDITOR"]
        self.assertEqual(ORDER, model); self.assertEqual(ORDER, M["model_feature_contract"]["ordered_feature_names"]); self.assertEqual(ORDER, schema)
    def test_03_partition(self):
        part = C["feature_partition"]; self.assertEqual(part["counts"], {"SYNTHETIC_BASELINE_PASSTHROUGH": 38, "DIRECT_USER_SUPPLIED": 4, "DERIVED": 7, "PROJECTED_OVERWRITE": 11, "TOTAL": 49})
        sets = [set(part[x]) for x in ("synthetic_baseline_passthrough", "direct_user_supplied", "derived")]; self.assertFalse((sets[0]&sets[1])|(sets[0]&sets[2])|(sets[1]&sets[2])); self.assertEqual(set.union(*sets), set(ORDER))
    def test_04_projection_reconstruction(self):
        source = {v["vector_id"]: v for v in SV["request_level_vectors"]}
        with PROFILE_PATH.open(newline="", encoding="utf-8") as handle: rows = list(csv.DictReader(handle))
        base = set(C["feature_partition"]["synthetic_baseline_passthrough"])
        for profile, projection in PROJ.items():
            raw = {r["canonical_feature"]: (r["synthetic_value"] if r["canonical_feature"] == "purpose" else float(r["synthetic_value"])) for r in rows if r["profile_id"] == profile}
            vector = source[projection["source_vector_id"]]; rebuilt = {f: raw[f] for f in base}; rebuilt.update(vector["expected_impacted_feature_outputs"]); rebuilt = {f: rebuilt[f] for f in ORDER}; self.assertEqual(rebuilt, VALUES[profile])
    def test_05_fingerprints(self):
        for p, projection in PROJ.items(): self.assertEqual(fingerprint(VALUES[p]), projection["expected_payload_fingerprint"])
    def test_06_raw_and_projected_conflicts(self):
        self.assertEqual(C["previous_safe_failures"]["raw_profile_authority"]["conflict_count"], 7)
        for payload in VALUES.values(): self.assertIn(payload["term_months"], [36,60]); self.assertEqual(payload["is_60_month"], int(payload["term_months"] == 60))
    def test_07_registry(self):
        required = {"feature_index","feature_name","partition_class","transport_class","editor_control","required","editable","finite_required","bool_allowed","null_allowed","minimum","maximum","allowed_values","reset_values_by_profile","reset_projection_sources","constraint_basis","limitation_status","fingerprint_representation_class"}
        self.assertEqual(len(REG),49)
        for i,f in enumerate(ORDER): self.assertTrue(required <= set(REG[f])); self.assertEqual(REG[f]["feature_index"],i); self.assertTrue(REG[f]["required"]); self.assertFalse(REG[f]["bool_allowed"]); self.assertFalse(REG[f]["null_allowed"])
    def test_08_transport_classes(self):
        self.assertEqual(REG["purpose"]["transport_class"],"CATEGORY"); self.assertEqual(REG["term_months"]["allowed_values"],[36,60]); self.assertEqual(REG["is_60_month"]["editor_control"],"READ_ONLY_DERIVED"); self.assertFalse(REG["is_60_month"]["editable"])
    def test_09_envelopes(self):
        for f,row in REG.items():
            vals=[VALUES[p][f] for p in PROJ]
            if row["transport_class"]=="CONTINUOUS_NUMERIC": self.assertEqual((row["minimum"],row["maximum"]),(min(vals),max(vals)))
    def test_10_locked_and_limitation_policy(self):
        self.assertEqual(set(C["limitation_policy"]["limitation_aware_features"]),{"grade_encoded","credit_age_months"})
        for f in ["grade_encoded","credit_age_months","is_60_month"]: self.assertFalse(REG[f]["editable"])
    def test_11_valid_resets(self):
        vectors=[v for v in V["vectors"] if v["vector_group"]=="VALID_CANONICAL_RESET"]; self.assertEqual(len(vectors),5)
        for v in vectors: self.assertEqual(validate(request_for(v["base_profile_id"]))["payload_fingerprint"],v["expected_payload_fingerprint"])
    def test_12_case_bundles(self):
        groups={"VALID_EDIT","INVALID_NUMERIC","INVALID_CATEGORY","INVALID_EXACT_INTEGER","INVALID_DISCRETE","INVALID_LOCKED_FEATURE"}
        for vector in [v for v in V["vectors"] if v["vector_group"] in groups]:
            for case in vector["cases"]:
                request=request_for(case["base_profile_id"],case["mutations"],case["edited_feature_names"],not case.get("direct_read_only_mutation",False))
                if case["expected_result"]=="VALID": self.assertEqual(validate(request)["status"],"VALID",(vector["vector_id"],case["case_id"]))
                else:
                    with self.assertRaises(ContractError,msg=(vector["vector_id"],case["case_id"])) as caught: validate(request)
                    self.assertEqual(str(caught.exception),case["expected_failure_code"],(vector["vector_id"],case["case_id"]))
    def test_13_structural_vectors(self):
        for vector in [v for v in V["vectors"] if v["vector_group"]=="INVALID_STRUCTURAL"]:
            with self.assertRaises(ContractError,msg=vector["vector_id"]) as caught: validate(scenario(vector))
            self.assertEqual(str(caught.exception),vector["expected_failure_code"])
    def test_14_difference_provenance(self):
        result=validate(request_for("SP_LOW_RISK_SIGNAL",{"dti":22.2},["dti"])); self.assertEqual(result["provenance_counts"],{"USER_EDITED":1,"CANONICAL_RESET_PROJECTION":48})
    def test_15_term_flag(self):
        for profile,term in (("SP_LOW_RISK_SIGNAL",60),("SP_MEDIUM_RISK_SIGNAL",36)): self.assertEqual(validate(request_for(profile,{"term_months":term},["term_months"]))["status"],"VALID")
    def test_16_full_coverage(self):
        s=V["summary"]; self.assertEqual(s["features_with_valid_boundary_coverage"],49); self.assertEqual(s["features_with_invalid_value_coverage"],49); self.assertEqual(s["locked_features_with_mutation_coverage"],3); self.assertTrue(s["full_feature_coverage"])
    def test_17_privacy(self):
        self.assertFalse(set(C["privacy_boundary"]["prohibited_fields"]) & set(ORDER))
    def test_18_manifest(self):
        manifest=strict(MANIFEST_PATH); self.assertEqual(manifest["artifact_count"],5)
        for item in manifest["artifacts"]: data=(ROOT/item["relative_path"]).read_bytes(); self.assertEqual(len(data),item["size_bytes"]); self.assertEqual(hashlib.sha256(data).hexdigest(),item["sha256"])
    def test_19_static_nonexecution_and_authorization(self):
        tree=ast.parse(Path(__file__).read_text(encoding="utf-8")); banned={"joblib","pickle","pandas","sklearn","streamlit","requests","urllib","socket"}
        for node in ast.walk(tree):
            if isinstance(node,ast.Import): self.assertFalse({a.name.split('.')[0] for a in node.names}&banned)
            if isinstance(node,ast.ImportFrom): self.assertNotIn((node.module or '').split('.')[0],banned)
        self.assertFalse(R["runtime_state"]["new_step4_2b_code_deserialized_model"]); self.assertFalse(R["runtime_state"]["new_step4_2b_code_executed_inference"])


if __name__ == "__main__": unittest.main()
