"""Stage 9 Step 6 release-candidate readiness tests."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "outputs/stage9/stage9_public_deployment_readiness_report.json"
RC_MANIFEST_PATH = ROOT / "outputs/stage9/stage9_public_release_candidate_manifest.json"

AUTHORIZED_STEP6_PATHS = (
    "tests/test_stage9_public_deployment_readiness.py",
    "outputs/stage9/stage9_public_deployment_readiness_report.md",
    "outputs/stage9/stage9_public_deployment_readiness_report.json",
    "outputs/stage9/stage9_public_release_candidate_manifest.json",
    "outputs/stage9/stage9_public_deployment_checklist.md",
    "outputs/stage9/stage9_step6_artifact_manifest.json",
)
EXCLUDED_PATH_COMPONENTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "node_modules",
    "venv",
}

FROZEN_HASHES = {
    "app/src/advanced_editor_runtime.py": "981551af627f56f0298017e8b015e4fc2ae5f6fcb9c4e4a6a6a17a645f15b84c",
    "app/src/advanced_editor_inference.py": "eaceabecd22ec584d51fea4adbedcbf7d5b29c3e598a6ced088247eae173d77c",
    "app/src/mode_view.py": "7f62b0f479f009e4255215edb7a03f5c63bbbe8122dd4f16a93ea192a745369d",
    "app/src/pages.py": "08d451d5fb40239611dd83f59fc3866c26010b1fad4791c45f824b5e7294a9c8",
    "app/src/payload_preview.py": "f5cc519df9869e09c41ddbc452ad4af0ebbf7655740b1cf4772b029e19150d60",
    "app/src/ui_text.py": "7596bbe80f4443008b759ddcb2df17b3fcef1d8e48c416b9e94aae39635b61ff",
    "tests/test_stage9_public_input_completion_ui_integration.py": "524b0473339a118979159958072839d4f04df99466c99967e66a689effd07160",
    "outputs/stage9/stage9_public_input_completion_ui_smoke_results.json": "39e3b8b790edbb4eaa0c7f3449290d9910532ff443f60d41f5f14206fde9819c",
    "outputs/stage9/stage9_public_input_completion_ui_integration_report.md": "3f4c570f9c565c23a45673731ceca72287092533fcb1f6924ed23f87ceb4fb3b",
    "outputs/stage9/stage9_public_input_completion_ui_integration_report.json": "1712910272f1a8f048369650073f993d9ee247364b8fa35795e399053b34cf82",
    "outputs/stage9/stage9_step5_artifact_manifest.json": "9719d7ad1e924bd3232fd5115dc4f24e2cdc4b087604ca4418e1cd7daa1a2fb2",
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


def git_paths(*args: str) -> tuple[str, ...]:
    raw = subprocess.check_output(["git", *args, "-z"], cwd=ROOT)
    return tuple(item.decode("utf-8") for item in raw.split(b"\0") if item)


def authorized_release_paths() -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    tracked = git_paths("ls-files")
    tracked_set = set(tracked)
    missing_authorized = tuple(
        path for path in AUTHORIZED_STEP6_PATHS if not (ROOT / path).exists()
    )
    if missing_authorized:
        raise AssertionError(f"authorized Step 6 path is missing: {missing_authorized!r}")
    authorized_untracked = tuple(
        path for path in AUTHORIZED_STEP6_PATHS
        if path not in tracked_set and (ROOT / path).exists()
    )
    actual_untracked = git_paths("ls-files", "--others", "--exclude-standard")
    unexpected_untracked = tuple(sorted(set(actual_untracked) - set(authorized_untracked)))
    missing_authorized_untracked = tuple(sorted(set(actual_untracked) ^ set(authorized_untracked)))
    if unexpected_untracked or missing_authorized_untracked:
        raise AssertionError(
            "release union has an unauthorized or missing untracked path: "
            f"unexpected={unexpected_untracked!r}, symmetric_difference={missing_authorized_untracked!r}"
        )

    root_resolved = ROOT.resolve()
    union = tuple(sorted(set(tracked) | set(authorized_untracked)))
    for relative_path in union:
        relative = Path(relative_path)
        if relative.is_absolute() or ".." in relative.parts:
            raise AssertionError(f"unsafe release path: {relative_path}")
        if set(relative.parts) & EXCLUDED_PATH_COMPONENTS:
            raise AssertionError(f"excluded release path: {relative_path}")
        source = ROOT / relative
        if source.is_symlink() or not source.is_file():
            raise AssertionError(f"release path is not a regular non-symlink file: {relative_path}")
        try:
            source.resolve().relative_to(root_resolved)
        except ValueError as exc:
            raise AssertionError(f"release path escapes repository: {relative_path}") from exc
    return union, tuple(sorted(tracked)), tuple(sorted(authorized_untracked))


def populate_release_candidate(destination: Path) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    union, tracked, authorized_untracked = authorized_release_paths()
    destination_resolved = destination.resolve()
    for relative_path in union:
        target = destination / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target_resolved = target.resolve()
        try:
            target_resolved.relative_to(destination_resolved)
        except ValueError as exc:
            raise AssertionError(f"candidate path escapes destination: {relative_path}") from exc
        shutil.copyfile(ROOT / relative_path, target)
    return union, tracked, authorized_untracked


def run_clean(code: str, *, cwd: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["XDG_CACHE_HOME"] = tempfile.gettempdir()
    return subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=cwd,
        env=environment,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )


class FrozenIntegrityTests(unittest.TestCase):
    def test_frozen_integrity(self) -> None:
        for relative_path, expected in FROZEN_HASHES.items():
            with self.subTest(path=relative_path):
                self.assertEqual(sha256(ROOT / relative_path), expected)


class EntryPointAndClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(RC_MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_entry_point_readiness(self) -> None:
        entry = ROOT / "app/streamlit_app.py"
        self.assertTrue(entry.is_file())
        self.assertFalse(entry.is_symlink())
        tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
        self.assertIn("app/streamlit_app.py", tracked)
        self.assertNotRegex(entry.read_text(encoding="utf-8"), r"/home/|/Users/|[A-Za-z]:\\\\Users\\\\|/mnt/data|/tmp/")

    def test_runtime_artifact_closure(self) -> None:
        self.assertEqual(self.manifest["runtime_artifact_count"], len(self.manifest["runtime_artifacts"]))
        for record in self.manifest["runtime_artifacts"]:
            path = ROOT / record["relative_path"]
            with self.subTest(path=record["relative_path"]):
                self.assertTrue(path.is_file())
                self.assertFalse(path.is_symlink())
                self.assertGreater(path.stat().st_size, 0)
                self.assertEqual(sha256(path), record["sha256"])
                self.assertTrue(record["tracked"])
                self.assertTrue(record["inside_repository"])


class DependencyAndConfigurationTests(unittest.TestCase):
    def test_canonical_dependency_definition(self) -> None:
        candidates = [ROOT / "requirements.txt", ROOT / "app/requirements.txt"]
        self.assertEqual([p for p in candidates if p.exists()], [ROOT / "requirements.txt"])
        text = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
        for package in ("streamlit", "pandas", "numpy", "scikit-learn", "joblib", "lightgbm"):
            self.assertRegex(text, rf"(?m)^{re.escape(package)}(?:==|~=|>=|<=|>|<)")
        self.assertNotRegex(text, r"file://|--index-url|--extra-index-url|\s-e\s|/[a-z0-9_.-]+/")
        self.assertNotRegex(text, r"jupyter|notebook|pytest|ruff|flake8")

    def test_streamlit_configuration_safety(self) -> None:
        text = (ROOT / ".streamlit/config.toml").read_text(encoding="utf-8")
        self.assertIn('showErrorDetails = "none"', text)
        self.assertIn("gatherUsageStats = false", text)
        self.assertNotRegex(text, r"(?i)enableXsrfProtection\s*=\s*false|enableCORS\s*=\s*false")
        self.assertNotRegex(text, r"(?m)^\s*(?:port|address|serverPort|serverAddress)\s*=")
        self.assertFalse((ROOT / ".streamlit/secrets.toml").exists())


class StaticSafetyTests(unittest.TestCase):
    def test_absolute_path_network_persistence_and_input_boundaries(self) -> None:
        forbidden_imports = {"requests", "httpx", "urllib", "urllib3", "socket", "aiohttp"}
        forbidden_calls = {
            "urlopen", "create_connection", "file_uploader", "camera_input", "text_input",
            "text_area", "chat_input", "to_sql", "executemany", "write_text", "write_bytes",
        }
        for path in sorted((ROOT / "app").rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertFalse({item.name.split(".")[0] for item in node.names} & forbidden_imports)
                elif isinstance(node, ast.ImportFrom):
                    self.assertNotIn((node.module or "").split(".")[0], forbidden_imports)
                elif isinstance(node, ast.Call):
                    name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
                    self.assertNotIn(name, forbidden_calls)
                elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                    self.assertNotRegex(node.value, r"/home/|/Users/|[A-Za-z]:\\\\Users\\\\|/mnt/data|/tmp/")

    def test_secret_scan(self) -> None:
        patterns = (
            ("private_key", re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
            ("openai_key", re.compile(rb"\bsk-[A-Za-z0-9_-]{20,}")),
            ("github_token", re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{20,}")),
            ("aws_access_key", re.compile(rb"\bAKIA[0-9A-Z]{16}\b")),
            ("password_assignment", re.compile(rb"(?i)\b(?:password|passwd|pwd)\s*[:=]\s*['\"][^'\"\r\n]{8,}['\"]")),
            ("credential_bearing_url", re.compile(rb"(?i)\bhttps?://[^\s/:]+:[^\s/@]+@")),
            ("database_url_with_credentials", re.compile(rb"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^\s/:]+:[^\s/@]+@")),
            ("service_account_private_key", re.compile(rb"(?i)['\"]private_key['\"]\s*:\s*['\"][^'\"\r\n]{20,}")),
            ("azure_account_key", re.compile(rb"(?i)\b(?:AccountKey|Ocp-Apim-Subscription-Key)\s*[:=]\s*[^\s'\"]{20,}")),
            ("generic_token_assignment", re.compile(rb"(?i)\b(?:access[_-]?token|api[_-]?key|secret[_-]?key)\s*[:=]\s*['\"][A-Za-z0-9_./+=-]{20,}['\"]")),
        )
        union, tracked, authorized_untracked = authorized_release_paths()
        self.assertEqual(len(union), len(tracked) + len(authorized_untracked))
        findings = []
        for relative_path in union:
            data = (ROOT / relative_path).read_bytes()
            findings.extend(
                (relative_path, label) for label, pattern in patterns if pattern.search(data)
            )
        self.assertEqual(findings, [])


class HermeticReleaseCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._candidate_directory = tempfile.TemporaryDirectory(
            prefix="stage9_step6_test_release_candidate_"
        )
        cls.release_root = Path(cls._candidate_directory.name)
        cls.union, cls.tracked, cls.authorized_untracked = populate_release_candidate(
            cls.release_root
        )

    @classmethod
    def tearDownClass(cls) -> None:
        candidate = cls.release_root
        cls._candidate_directory.cleanup()
        if candidate.exists():
            raise AssertionError(f"test release candidate was not removed: {candidate}")

    def run_candidate(self, code: str, *, external_cwd: bool = False) -> subprocess.CompletedProcess[str]:
        if external_cwd:
            code = f"import os; os.chdir({str(self.release_root)!r}); " + code
            return run_clean(code, cwd=Path(tempfile.gettempdir()))
        return run_clean(code, cwd=self.release_root)

    def test_builder_uses_exact_authorized_union(self) -> None:
        self.assertGreater(len(self.union), 0)
        self.assertEqual(set(self.union), set(self.tracked) | set(self.authorized_untracked))
        self.assertEqual(set(self.authorized_untracked), set(AUTHORIZED_STEP6_PATHS) - set(self.tracked))
        candidate_files = {
            path.relative_to(self.release_root).as_posix()
            for path in self.release_root.rglob("*") if path.is_file()
        }
        self.assertEqual(candidate_files, set(self.union))
        self.assertFalse(any(path.is_symlink() for path in self.release_root.rglob("*")))
        self.assertFalse(
            any(set(Path(path).parts) & EXCLUDED_PATH_COMPONENTS for path in candidate_files)
        )

    def test_no_fixed_release_root_dependency(self) -> None:
        historical_root = str(Path(tempfile.gettempdir()) / "stage9_step6_release_candidate")
        source = Path(__file__).read_text(encoding="utf-8")
        self.assertNotIn(historical_root, source)
        self.assertNotEqual(self.release_root, Path(historical_root))
        self.assertTrue(self.release_root.name.startswith("stage9_step6_test_release_candidate_"))

    def test_clean_copy_imports_from_root_and_external_cwd(self) -> None:
        self.assertTrue(self.release_root.is_dir())
        self.assertFalse((self.release_root / ".git").exists())
        imports = r'''
from pathlib import Path
import app.streamlit_app as entry
import app.src.pages as pages
import app.src.demo_inference as demo
import app.src.basic_form_inference as basic
import app.src.advanced_editor_inference as advanced
candidate = Path.cwd().resolve()
origins = [Path(module.__file__).resolve() for module in (entry, pages, demo, basic, advanced)]
assert len(origins) == 5
assert all(origin.is_relative_to(candidate) for origin in origins), origins
print("PASS")
'''
        root_result = self.run_candidate(imports)
        self.assertEqual(root_result.returncode, 0, root_result.stderr)
        self.assertIn("PASS", root_result.stdout)
        external_result = self.run_candidate(imports, external_cwd=True)
        self.assertEqual(external_result.returncode, 0, external_result.stderr)
        self.assertIn("PASS", external_result.stdout)

    def test_three_mode_release_smoke(self) -> None:
        code = r'''
import json
from app.src import demo_inference as frozen
from app.src.advanced_editor_inference import run_advanced_editor_inference
from app.src.advanced_editor_runtime import advanced_editor_contract_summary
from app.src.basic_form_inference import run_basic_form_inference
profiles=("SP_LOW_RISK_SIGNAL","SP_MEDIUM_RISK_SIGNAL","SP_HIGHER_RISK_SIGNAL","SP_MIXED_SIGNAL","SP_LIMITATION_TRANSPARENCY")
expected={"SP_LOW_RISK_SIGNAL":0.18398918594172425,"SP_MEDIUM_RISK_SIGNAL":0.35650623885918004,"SP_HIGHER_RISK_SIGNAL":0.31875881523272215,"SP_MIXED_SIGNAL":0.400390625,"SP_LIMITATION_TRANSPARENCY":0.4418604651162791}
for profile in profiles:
    a=frozen.run_committed_sample_profile_inference(profile); b=frozen.run_committed_sample_profile_inference(profile)
    assert a.inference_status=="available" and a.calibrated_default_probability==b.calibrated_default_probability
vectors=json.load(open("outputs/stage9/stage9_basic_form_runtime_mapping_golden_vectors.json"))["request_level_vectors"]
for vector in vectors:
    a=run_basic_form_inference(vector["source_inputs"],vector["system_metadata"]); b=run_basic_form_inference(vector["source_inputs"],vector["system_metadata"])
    assert a.inference_status=="available" and a.calibrated_default_probability==b.calibrated_default_probability
summary=advanced_editor_contract_summary(); order=summary["ordered_feature_names"]
for profile in profiles:
    payload=summary["canonical_reset_projections"][profile]
    request={"mode":"ADVANCED_EDITOR","system_metadata":{"advanced_editor_profile_id":profile,"advanced_editor_acknowledged":True,"edited_feature_names":[]},"payload_rows":[{"feature_index":i,"feature_name":name,"value":payload[name]} for i,name in enumerate(order)]}
    a=run_advanced_editor_inference(request); b=run_advanced_editor_inference(request)
    assert a.calibrated_default_probability==expected[profile]==b.calibrated_default_probability
print("PASS")
'''
        result = self.run_candidate(code)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_invalid_clean_copy_smoke(self) -> None:
        code = r'''
from unittest import mock
from app.src import demo_inference as frozen
from app.src.advanced_editor_inference import run_advanced_editor_inference
from app.src.advanced_editor_runtime import advanced_editor_contract_summary
s=advanced_editor_contract_summary(); order=s["ordered_feature_names"]; profile="SP_LOW_RISK_SIGNAL"; payload=s["canonical_reset_projections"][profile]
def request(): return {"mode":"ADVANCED_EDITOR","system_metadata":{"advanced_editor_profile_id":profile,"advanced_editor_acknowledged":True,"edited_feature_names":[]},"payload_rows":[{"feature_index":i,"feature_name":name,"value":payload[name]} for i,name in enumerate(order)]}
cases=[]
x=request(); x["system_metadata"]["advanced_editor_acknowledged"]=False; cases.append(x)
x=request(); next(r for r in x["payload_rows"] if r["feature_name"]=="dti")["value"]=12.5; cases.append(x)
x=request(); x["system_metadata"]["edited_feature_names"]=["dti"]; cases.append(x)
x=request(); x["payload_rows"].append({"feature_index":49,"feature_name":"extra","value":1}); cases.append(x)
x=request(); x["system_metadata"]["edited_feature_names"]=["is_60_month"]; cases.append(x)
x=request(); x["system_metadata"]["full_name"]="prohibited"; cases.append(x)
with mock.patch.object(frozen,"_verified_runtime") as runtime:
    for case in cases:
        result=run_advanced_editor_inference(case)
        assert result.inference_status=="unavailable" and result.calibrated_default_probability is None
    assert runtime.call_count==0
print("PASS")
'''
        result = self.run_candidate(code)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_clean_copy_apptest_all_pages_and_modes(self) -> None:
        code = r'''
from streamlit.testing.v1 import AppTest
pages=("Overview","Contract Readiness","Demo Input Modes","Payload Builder & Preview","Safe Demo Inference","Governance & Limitations")
for page in pages:
    app=AppTest.from_file("app/streamlit_app.py",default_timeout=30).run()
    app.sidebar.radio[0].set_value(page).run(); assert len(app.exception)==0
app=AppTest.from_file("app/streamlit_app.py",default_timeout=30).run()
app.sidebar.radio[0].set_value("Safe Demo Inference").run()
mode=next(r for r in app.radio if r.label=="Public Input Mode")
assert mode.value=="Basic Form"
for label in ("Basic Form","Sample Profiles","Advanced Editor — Technical Mode"):
    app=AppTest.from_file("app/streamlit_app.py",default_timeout=30).run()
    app.sidebar.radio[0].set_value("Safe Demo Inference").run()
    next(r for r in app.radio if r.label=="Public Input Mode").set_value(label).run()
    assert len(app.exception)==0
assert all(not box.value for box in app.checkbox)
assert not any("Controlled Inference Result" in item.value for item in app.subheader)
assert len(app.text_input)==0 and len(app.text_area)==0
assert len(app.get("file_uploader"))==0 and len(app.get("camera_input"))==0
assert any("fictional portfolio demonstration" in item.value for item in app.warning)
print("PASS")
'''
        result = self.run_candidate(code)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_clean_copy_apptest_profile_reset_cycle(self) -> None:
        code = r'''
from streamlit.testing.v1 import AppTest
app=AppTest.from_file("app/streamlit_app.py",default_timeout=30).run()
app.sidebar.radio[0].set_value("Safe Demo Inference").run()
next(r for r in app.radio if r.label=="Public Input Mode").set_value("Advanced Editor — Technical Mode").run()
profile=next(widget for widget in app.selectbox if widget.label=="Canonical reset profile")
initial="SP_LOW_RISK_SIGNAL"
alternative="SP_MEDIUM_RISK_SIGNAL"
assert profile.value==initial and alternative in profile.options
dti=next(widget for widget in app.number_input if widget.label=="dti")
initial_dti=dti.value
dti.set_value(15.0)
app.checkbox[0].set_value(True)
app.run()
assert next(widget for widget in app.number_input if widget.label=="dti").value==15.0
assert app.checkbox[0].value
assert not any("Controlled Inference Result" in title.value for title in app.subheader)
next(widget for widget in app.selectbox if widget.label=="Canonical reset profile").set_value(alternative).run()
assert next(widget for widget in app.selectbox if widget.label=="Canonical reset profile").value==alternative
assert next(widget for widget in app.number_input if widget.label=="dti").value!=15.0
assert next(widget for widget in app.selectbox if widget.label=="term_months").value==60
assert "is_60_month: 1 (read-only; derived from term_months)" in [caption.value for caption in app.caption]
assert not app.checkbox[0].value
assert not any("Controlled Inference Result" in title.value for title in app.subheader)
next(widget for widget in app.selectbox if widget.label=="Canonical reset profile").set_value(initial).run()
assert next(widget for widget in app.number_input if widget.label=="dti").value==initial_dti
assert next(widget for widget in app.selectbox if widget.label=="term_months").value==36
assert "is_60_month: 0 (read-only; derived from term_months)" in [caption.value for caption in app.caption]
assert not app.checkbox[0].value
assert not any("Controlled Inference Result" in title.value for title in app.subheader)
assert len(app.exception)==0
print("PASS")
'''
        result = self.run_candidate(code)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS", result.stdout)


class GeneratedEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))

    def test_headless_startup_evidence(self) -> None:
        evidence = self.report["headless_startup"]
        self.assertTrue(evidence["passed"])
        self.assertTrue(evidence["server_started"])
        self.assertEqual(evidence["traceback_count"], 0)
        self.assertFalse(evidence["server_process_remaining"])

    def test_release_evidence_privacy(self) -> None:
        for path in (
            ROOT / "outputs/stage9/stage9_public_release_candidate_manifest.json",
            ROOT / "outputs/stage9/stage9_public_deployment_checklist.md",
        ):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("/home/wira", text)
            self.assertNotRegex(text, r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")
        privacy = self.report["privacy_boundary"]
        self.assertEqual(privacy["personal_field_count"], 0)
        self.assertFalse(privacy["raw_input_logging_present"])
        self.assertFalse(privacy["complete_payload_logging_present"])


if __name__ == "__main__":
    unittest.main()
