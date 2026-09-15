"""Stage 9 Step 7A automated localhost acceptance tests."""

from __future__ import annotations

import ast
import hashlib
import importlib.metadata
import json
import re
import subprocess
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

from app.src import demo_inference as frozen_adapter
from app.src import pages
from app.src.advanced_editor_inference import run_advanced_editor_inference
from app.src.advanced_editor_runtime import advanced_editor_contract_summary
from app.src.basic_form_inference import run_basic_form_inference


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_TEST_PYTHON = Path(sys.executable)
BASELINE_COMMIT = "7b877ae1448423f8c7e402af7ee2455f5973d0a7"
BASELINE_SUBJECT = "Harden portable release evidence"
BASELINE_PARENT = "c3be3eb2cf57a6de5661937caadfb27454df3a30"
PROFILE_IDS = (
    "SP_LOW_RISK_SIGNAL",
    "SP_MEDIUM_RISK_SIGNAL",
    "SP_HIGHER_RISK_SIGNAL",
    "SP_MIXED_SIGNAL",
    "SP_LIMITATION_TRANSPARENCY",
)
STEP7A_PATHS = (
    "tests/test_stage9_localhost_final_acceptance.py",
    "outputs/stage9/stage9_localhost_automated_acceptance_report.md",
    "outputs/stage9/stage9_localhost_automated_acceptance_report.json",
    "outputs/stage9/stage9_localhost_smoke_results.json",
    "outputs/stage9/stage9_localhost_manual_acceptance_checklist.md",
    "outputs/stage9/stage9_step7a_artifact_manifest.json",
)
STEP6_BASELINE_DIFF_PATHS = (
    "tests/test_stage9_public_deployment_readiness.py",
    "outputs/stage9/stage9_public_deployment_readiness_report.md",
    "outputs/stage9/stage9_public_deployment_readiness_report.json",
    "outputs/stage9/stage9_public_release_candidate_manifest.json",
    "outputs/stage9/stage9_step6_artifact_manifest.json",
)
EVIDENCE_JSON_PATHS = (
    "outputs/stage9/stage9_localhost_automated_acceptance_report.json",
    "outputs/stage9/stage9_localhost_smoke_results.json",
    "outputs/stage9/stage9_step7a_artifact_manifest.json",
)
FROZEN_HASHES = {
    "tests/test_stage9_public_deployment_readiness.py": "a347bce65f060c8aa00024daa6eeab40bb16cc22df0280978d65485a8719f5a6",
    "outputs/stage9/stage9_public_deployment_readiness_report.md": "12556c9377ad87b542d331349029d50962f97e9bbe2753f0260f601d885d0ee3",
    "outputs/stage9/stage9_public_deployment_readiness_report.json": "ca315326a234335460719dd8a9a88605cc7f0d41490351ef7954d63adf218f9b",
    "outputs/stage9/stage9_public_release_candidate_manifest.json": "d04fc8d4d3866597c218d88c75efe09c6b4c282107de5c004cb1113a68118dd6",
    "outputs/stage9/stage9_step6_artifact_manifest.json": "29179ba67831b93395de9cfc8c0080d799fa05a79e4dc71616f5e0de1b1d0880",
    "outputs/stage9/stage9_public_deployment_checklist.md": "266ba49c323d766f6ea37361a7e059f673850166a0e3d866fdcda18d106ad602",
    "requirements.txt": "7c1dfd94fb548304099c3610725890f5a0147c971b7269a3b46106ccdd672753",
    ".streamlit/config.toml": "404025286a39a192f6733f1adc272255691686498b868baf394d381f0def65c6",
    "app/streamlit_app.py": "cfe0b8dbce2466e25b5ce70207c43d1c93431005b6d94733a7bea2b7b534a50b",
    "app/src/demo_inference.py": "1eb8fdf3a39e4775f5817c2a4620dc7c6669d0d7ad844932f411fc25ebbc9074",
    "app/src/basic_form_runtime.py": "71bae84c24c2cc3f07a1ec02377f8065064db0551d2f77cc5727129c2bdaf50e",
    "app/src/basic_form_inference.py": "04d52edf6216d9970a4b42773596541b2a07cb4ba294eeae73eecfb68b37b728",
    "app/src/advanced_editor_runtime.py": "981551af627f56f0298017e8b015e4fc2ae5f6fcb9c4e4a6a6a17a645f15b84c",
    "app/src/advanced_editor_inference.py": "eaceabecd22ec584d51fea4adbedcbf7d5b29c3e598a6ced088247eae173d77c",
    "app/src/pages.py": "08d451d5fb40239611dd83f59fc3866c26010b1fad4791c45f824b5e7294a9c8",
    "app/src/mode_view.py": "7f62b0f479f009e4255215edb7a03f5c63bbbe8122dd4f16a93ea192a745369d",
    "app/src/payload_preview.py": "f5cc519df9869e09c41ddbc452ad4af0ebbf7655740b1cf4772b029e19150d60",
    "app/src/ui_text.py": "7596bbe80f4443008b759ddcb2df17b3fcef1d8e48c416b9e94aae39635b61ff",
    "artifacts/model/final_model_calibrated.pkl": "b022b545bd7bb4294018a26a7d10af977e3c452b7f219dbdd9113adeac367cbf",
    "artifacts/model/final_threshold.json": "e45a19822f77d6b74cf5e76c0c0e6ff2f993bad4ab91e507509b3d74d410e28b",
    "artifacts/model/model_artifact_manifest.json": "9c49149b1a3f72fc6e0f6fe5e5efa84f5c81f65224c1bd08daded1f6231461fd",
    "artifacts/contracts/cell_group_7/sample_profiles/sample_profile_feature_matrix.csv": "c16f1786900ae0ec7878aac2dbc87018c34de459ae9a36dfabf0a43ca92f1bd6",
    "outputs/stage9/stage9_advanced_editor_validation_contract.json": "47b688fa8620a6691ac535d686912c5ca732313e16b0ee1ea4dff214f6c750ac",
}
EXPECTED_BASIC = {
    "REQUEST_STANDARD_36": 0.18398918594172425,
    "REQUEST_60_MONTH": 0.35650623885918004,
    "REQUEST_PROFILE_HIGHER_RENT": 0.31875881523272215,
    "REQUEST_PROFILE_MIXED_OTHER": 0.400390625,
    "REQUEST_PROFILE_LIMITATION_DTI_SCALE": 0.4418604651162791,
    "REQUEST_NUMERIC_LOWER_BOUNDS": 0.24756756756756756,
    "REQUEST_NUMERIC_UPPER_BOUNDS": 0.5675675675675675,
}
EXPECTED_SAMPLE = {
    "SP_LOW_RISK_SIGNAL": 0.31875881523272215,
    "SP_MEDIUM_RISK_SIGNAL": 0.43903940886699505,
    "SP_HIGHER_RISK_SIGNAL": 0.5721649484536082,
    "SP_MIXED_SIGNAL": 0.504524886877828,
    "SP_LIMITATION_TRANSPARENCY": 0.4418604651162791,
}
EXPECTED_ADVANCED = {
    "SP_LOW_RISK_SIGNAL": 0.18398918594172425,
    "SP_MEDIUM_RISK_SIGNAL": 0.35650623885918004,
    "SP_HIGHER_RISK_SIGNAL": 0.31875881523272215,
    "SP_MIXED_SIGNAL": 0.400390625,
    "SP_LIMITATION_TRANSPARENCY": 0.4418604651162791,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_output(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


@dataclass(frozen=True)
class Step7ARepositoryClassification:
    mode: str
    step7a_scope: tuple[str, ...]
    future_stage_untracked: tuple[str, ...]


def classify_step7a_repository_state(
    *,
    current_head: str,
    baseline_is_ancestor: bool,
    head_paths: tuple[str, ...],
    index_paths: tuple[str, ...],
    actual_untracked_paths: tuple[str, ...],
    staged_name_status: tuple[tuple[str, str], ...],
    unstaged_tracked_paths: tuple[str, ...],
    regular_step7a_paths: tuple[str, ...],
) -> Step7ARepositoryClassification:
    """Classify abstract Step 7A Git state without reading Git or the filesystem."""

    authorized = set(STEP7A_PATHS)
    head = set(head_paths)
    index = set(index_paths)
    untracked = set(actual_untracked_paths)
    staged_paths = {path for _, path in staged_name_status}
    staged_additions = {path for status, path in staged_name_status if status == "A"}
    regular = set(regular_step7a_paths)

    if current_head == BASELINE_COMMIT and authorized.isdisjoint(head):
        if authorized.isdisjoint(index):
            if staged_paths:
                raise AssertionError(f"precommit-untracked state has staged paths: {tuple(sorted(staged_paths))!r}")
            missing = authorized - untracked
            unexpected = untracked - authorized
            if missing or unexpected:
                raise AssertionError(
                    "precommit-untracked scope mismatch: "
                    f"missing={tuple(sorted(missing))!r}, unexpected={tuple(sorted(unexpected))!r}"
                )
            return Step7ARepositoryClassification(
                mode="STEP7A_PRECOMMIT_UNTRACKED",
                step7a_scope=tuple(sorted(authorized)),
                future_stage_untracked=(),
            )

        if authorized <= index:
            if untracked:
                raise AssertionError(f"precommit-staged state has unexpected untracked paths: {tuple(sorted(untracked))!r}")
            missing = authorized - staged_additions
            unexpected = staged_paths - authorized
            non_additions = staged_paths - staged_additions
            if missing or unexpected or non_additions or unstaged_tracked_paths:
                raise AssertionError(
                    "precommit-staged scope mismatch: "
                    f"missing={tuple(sorted(missing))!r}, "
                    f"unexpected={tuple(sorted(unexpected))!r}, "
                    f"non_additions={tuple(sorted(non_additions))!r}, "
                    f"unstaged={tuple(sorted(unstaged_tracked_paths))!r}"
                )
            return Step7ARepositoryClassification(
                mode="STEP7A_PRECOMMIT_STAGED",
                step7a_scope=tuple(sorted(authorized)),
                future_stage_untracked=(),
            )
        raise AssertionError(
            "baseline HEAD has a partial Step 7A index state: "
            f"missing={tuple(sorted(authorized - index))!r}"
        )

    if not baseline_is_ancestor:
        raise AssertionError("Step 6 baseline is not an ancestor of current HEAD")
    missing_head = authorized - head
    missing_index = authorized - index
    missing_regular = authorized - regular
    if missing_head or missing_index or missing_regular:
        raise AssertionError(
            "postcommit Step 7A scope is incomplete: "
            f"missing_head={tuple(sorted(missing_head))!r}, "
            f"missing_index={tuple(sorted(missing_index))!r}, "
            f"missing_regular={tuple(sorted(missing_regular))!r}"
        )
    return Step7ARepositoryClassification(
        mode="POSTCOMMIT_FUTURE_STAGE",
        step7a_scope=tuple(sorted(authorized)),
        future_stage_untracked=tuple(sorted(untracked - authorized)),
    )


def current_repository_classification() -> Step7ARepositoryClassification:
    current_head = git_output("rev-parse", "HEAD")
    head_paths = tuple(git_output("ls-tree", "-r", "--name-only", "HEAD").splitlines())
    index_paths = tuple(git_output("ls-files", "--cached").splitlines())
    untracked_paths = tuple(git_output("ls-files", "--others", "--exclude-standard").splitlines())
    staged_name_status = tuple(
        tuple(line.split("\t", 1))  # type: ignore[misc]
        for line in git_output("diff", "--cached", "--name-status").splitlines()
        if line
    )
    unstaged_paths = tuple(git_output("diff", "--name-only").splitlines())
    baseline_is_ancestor = (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", BASELINE_COMMIT, "HEAD"],
            cwd=ROOT,
            check=False,
        ).returncode
        == 0
    )
    regular = tuple(
        path
        for path in STEP7A_PATHS
        if (ROOT / path).is_file() and not (ROOT / path).is_symlink()
    )
    return classify_step7a_repository_state(
        current_head=current_head,
        baseline_is_ancestor=baseline_is_ancestor,
        head_paths=head_paths,
        index_paths=index_paths,
        actual_untracked_paths=untracked_paths,
        staged_name_status=staged_name_status,  # type: ignore[arg-type]
        unstaged_tracked_paths=unstaged_paths,
        regular_step7a_paths=regular,
    )


def strict_json(path: Path) -> object:
    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate key: {key}")
            result[key] = value
        return result

    def nonfinite(value: str) -> object:
        raise ValueError(f"non-finite number: {value}")

    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=pairs,
        parse_constant=nonfinite,
    )


class AcceptanceBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.summary = advanced_editor_contract_summary()
        cls.order = tuple(cls.summary["ordered_feature_names"])
        cls.projections = cls.summary["canonical_reset_projections"]
        cls.vectors = json.loads(
            (ROOT / "outputs/stage9/stage9_basic_form_runtime_mapping_golden_vectors.json").read_text(encoding="utf-8")
        )["request_level_vectors"]

    def advanced_request(self, profile_id: str = PROFILE_IDS[0]) -> dict[str, object]:
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

    def set_advanced_value(self, request: dict[str, object], feature: str, value: object) -> None:
        for row in request["payload_rows"]:  # type: ignore[index]
            if row["feature_name"] == feature:
                row["value"] = value
                return
        self.fail(feature)


class FrozenReleaseTests(AcceptanceBase):
    def test_01_baseline_commit_object_metadata(self) -> None:
        subprocess.run(["git", "cat-file", "-e", f"{BASELINE_COMMIT}^{{commit}}"], cwd=ROOT, check=True)
        self.assertEqual(git_output("show", "-s", "--format=%H", BASELINE_COMMIT), BASELINE_COMMIT)
        self.assertEqual(git_output("show", "-s", "--format=%s", BASELINE_COMMIT), BASELINE_SUBJECT)
        self.assertEqual(git_output("show", "-s", "--format=%P", BASELINE_COMMIT), BASELINE_PARENT)
        self.assertEqual(
            set(git_output("diff-tree", "--no-commit-id", "--name-only", "-r", BASELINE_COMMIT).splitlines()),
            set(STEP6_BASELINE_DIFF_PATHS),
        )
        self.assertEqual(len(git_output("ls-tree", "-r", "--name-only", BASELINE_COMMIT).splitlines()), 99)
        self.assertEqual(
            subprocess.run(
                ["git", "merge-base", "--is-ancestor", BASELINE_COMMIT, "HEAD"],
                cwd=ROOT,
                check=False,
            ).returncode,
            0,
        )

    def test_01b_real_repository_state_is_lifecycle_valid(self) -> None:
        classification = current_repository_classification()
        self.assertIn(
            classification.mode,
            {"STEP7A_PRECOMMIT_UNTRACKED", "STEP7A_PRECOMMIT_STAGED", "POSTCOMMIT_FUTURE_STAGE"},
        )
        self.assertEqual(set(classification.step7a_scope), set(STEP7A_PATHS))

    def test_02_frozen_step6_and_application_hashes(self) -> None:
        for relative_path, expected in FROZEN_HASHES.items():
            with self.subTest(path=relative_path):
                self.assertEqual(sha256(ROOT / relative_path), expected)

    def test_03_model_is_regular_binary_not_lfs_or_symlink(self) -> None:
        model = ROOT / "artifacts/model/final_model_calibrated.pkl"
        self.assertTrue(model.is_file())
        self.assertFalse(model.is_symlink())
        self.assertEqual(model.stat().st_size, 4_881_685)
        self.assertFalse(model.read_bytes().startswith(b"version https://git-lfs.github.com/spec/v1"))

    def test_04_final_step6_release_facts(self) -> None:
        report = strict_json(ROOT / "outputs/stage9/stage9_public_deployment_readiness_report.json")
        manifest = strict_json(ROOT / "outputs/stage9/stage9_public_release_candidate_manifest.json")
        self.assertEqual(manifest["runtime_artifact_count"], 51)  # type: ignore[index]
        self.assertEqual(manifest["runtime_artifact_total_bytes"], 6_807_346)  # type: ignore[index]
        self.assertEqual(manifest["model_artifact_bytes"], 4_881_685)  # type: ignore[index]
        self.assertEqual(manifest["tracked_repository_file_count"], 99)  # type: ignore[index]
        self.assertEqual(report["validation_result"], "PASS")  # type: ignore[index]

    def test_05_active_interpreter_and_versions(self) -> None:
        self.assertEqual(ACTIVE_TEST_PYTHON, Path(sys.executable))
        self.assertEqual(sys.version_info[:3], (3, 10, 12))
        expected = {
            "streamlit": "1.51.0", "pandas": "2.3.3", "numpy": "1.26.4",
            "scikit-learn": "1.7.2", "joblib": "1.5.3", "lightgbm": "4.6.0",
        }
        for package, version in expected.items():
            self.assertEqual(importlib.metadata.version(package), version)


class LifecycleClassifierTests(unittest.TestCase):
    def base(self, **changes: object) -> dict[str, object]:
        values: dict[str, object] = {
            "current_head": BASELINE_COMMIT,
            "baseline_is_ancestor": True,
            "head_paths": ("app/streamlit_app.py",),
            "index_paths": ("app/streamlit_app.py",),
            "actual_untracked_paths": STEP7A_PATHS,
            "staged_name_status": (),
            "unstaged_tracked_paths": (),
            "regular_step7a_paths": STEP7A_PATHS,
        }
        values.update(changes)
        return values

    def classify(self, **changes: object) -> Step7ARepositoryClassification:
        return classify_step7a_repository_state(**self.base(**changes))  # type: ignore[arg-type]

    def test_lifecycle_01_valid_precommit_untracked(self) -> None:
        self.assertEqual(self.classify().mode, "STEP7A_PRECOMMIT_UNTRACKED")

    def test_lifecycle_02_unexpected_precommit_untracked_rejected(self) -> None:
        with self.assertRaisesRegex(AssertionError, "unexpected"):
            self.classify(actual_untracked_paths=STEP7A_PATHS + ("outputs/stage9/future.json",))

    def test_lifecycle_03_missing_precommit_path_rejected(self) -> None:
        with self.assertRaisesRegex(AssertionError, "missing"):
            self.classify(actual_untracked_paths=STEP7A_PATHS[:-1])

    def staged(self, **changes: object) -> Step7ARepositoryClassification:
        values: dict[str, object] = {
            "index_paths": ("app/streamlit_app.py",) + STEP7A_PATHS,
            "actual_untracked_paths": (),
            "staged_name_status": tuple(("A", path) for path in STEP7A_PATHS),
        }
        values.update(changes)
        return self.classify(**values)

    def test_lifecycle_04_valid_precommit_staged(self) -> None:
        self.assertEqual(self.staged().mode, "STEP7A_PRECOMMIT_STAGED")

    def test_lifecycle_05_unexpected_staged_path_rejected(self) -> None:
        extra = ("outputs/stage9/unexpected.json",)
        with self.assertRaisesRegex(AssertionError, "unexpected"):
            self.staged(
                index_paths=("app/streamlit_app.py",) + STEP7A_PATHS + extra,
                staged_name_status=tuple(("A", path) for path in STEP7A_PATHS + extra),
            )

    def test_lifecycle_06_missing_staged_path_rejected(self) -> None:
        with self.assertRaisesRegex(AssertionError, "missing"):
            self.staged(
                index_paths=("app/streamlit_app.py",) + STEP7A_PATHS[:-1],
                staged_name_status=tuple(("A", path) for path in STEP7A_PATHS[:-1]),
            )

    def postcommit(self, **changes: object) -> Step7ARepositoryClassification:
        values: dict[str, object] = {
            "current_head": "descendant-commit",
            "head_paths": ("app/streamlit_app.py",) + STEP7A_PATHS,
            "index_paths": ("app/streamlit_app.py",) + STEP7A_PATHS,
            "actual_untracked_paths": ("outputs/stage9/future-stage.json",),
            "staged_name_status": (),
        }
        values.update(changes)
        return self.classify(**values)

    def test_lifecycle_07_valid_postcommit_future_stage(self) -> None:
        self.assertEqual(self.postcommit().mode, "POSTCOMMIT_FUTURE_STAGE")

    def test_lifecycle_08_future_untracked_allowed_and_excluded(self) -> None:
        classified = self.postcommit()
        self.assertEqual(classified.future_stage_untracked, ("outputs/stage9/future-stage.json",))
        self.assertTrue(set(classified.step7a_scope).isdisjoint(classified.future_stage_untracked))

    def test_lifecycle_09_baseline_ancestor_required(self) -> None:
        with self.assertRaisesRegex(AssertionError, "not an ancestor"):
            self.postcommit(baseline_is_ancestor=False)

    def test_lifecycle_10_missing_committed_path_rejected(self) -> None:
        with self.assertRaisesRegex(AssertionError, "missing_head"):
            self.postcommit(head_paths=("app/streamlit_app.py",) + STEP7A_PATHS[:-1])


class AppAndModeTests(AcceptanceBase):
    def app(self):
        from streamlit.testing.v1 import AppTest

        return AppTest.from_file(str(ROOT / "app/streamlit_app.py"), default_timeout=30).run()

    @staticmethod
    def visible_text(app: object) -> str:
        values: list[str] = []
        for collection_name in (
            "title", "header", "subheader", "caption", "markdown", "info",
            "warning", "error", "success", "text",
        ):
            for item in getattr(app, collection_name, []):
                value = getattr(item, "value", "")
                if isinstance(value, str):
                    values.append(value)
        return "\n".join(values)

    @classmethod
    def normalized_visible_text(cls, app: object) -> str:
        return " ".join(cls.visible_text(app).lower().split())

    @staticmethod
    def result_present(app: object) -> bool:
        return any(
            "Controlled Inference Result" in item.value
            for item in getattr(app, "subheader", [])
        )

    def run_basic_form_ui_flow(self) -> tuple[str, str]:
        app = self.app()
        app.sidebar.radio[0].set_value("Safe Demo Inference").run()
        mode = next(radio for radio in app.radio if radio.label == "Public Input Mode")
        self.assertEqual(mode.value, "Basic Form")
        self.assertTrue(all(not checkbox.value for checkbox in app.checkbox))
        self.assertFalse(self.result_present(app))

        number = lambda label: next(widget for widget in app.number_input if widget.label == label)
        select = lambda label: next(widget for widget in app.selectbox if widget.label == label)
        button = lambda: next(widget for widget in app.button if widget.label == "Run controlled inference")
        number("Fictional annual income (USD)").set_value(65_000.0)
        number("Debt-to-income ratio (%)").set_value(18.27)
        number("Fictional requested loan amount (USD)").set_value(12_000.0)
        select("Fictional home ownership").set_value("MORTGAGE")
        select("Fictional loan purpose").set_value("other")
        select("Fictional term").set_value(36)
        select("Synthetic completion profile").set_value("SP_LOW_RISK_SIGNAL")
        app.run()
        self.assertFalse(self.result_present(app))

        button().click().run()
        self.assertTrue(self.result_present(app))
        self.assertEqual(len(app.metric), 0)
        self.assertFalse(app.checkbox[0].value)
        self.assertEqual(len(app.exception), 0)

        app.checkbox[0].set_value(True)
        button().click().run()
        self.assertTrue(self.result_present(app))
        metrics = {item.label: item.value for item in app.metric}
        self.assertEqual(metrics["Estimated model default-risk probability"], "18.3989%")
        self.assertEqual(metrics["Canonical feature count"], "49")
        self.assertEqual(len(app.exception), 0)
        visible = self.normalized_visible_text(app)
        disclosure = " ".join(
            (
                "This output is a fictional portfolio demonstration and is not a lending "
                "decision, approval recommendation, rejection recommendation, legal "
                "assessment, fairness conclusion, or production underwriting result."
            ).lower().split()
        )
        self.assertIn(disclosure, visible)
        self.assertNotIn("canonical_payload", visible)
        return metrics["Estimated model default-risk probability"], visible

    def test_06_all_six_pages_render_without_exceptions(self) -> None:
        app = self.app()
        pages_expected = (
            "Overview", "Contract Readiness", "Demo Input Modes",
            "Payload Builder & Preview", "Safe Demo Inference", "Governance & Limitations",
        )
        self.assertEqual(tuple(app.sidebar.radio[0].options), pages_expected)
        for page in pages_expected:
            with self.subTest(page=page):
                app.sidebar.radio[0].set_value(page).run()
                self.assertEqual(len(app.exception), 0)
                self.assertNotIn("/" + "home/", self.visible_text(app))

    def test_07_three_modes_default_acknowledgement_and_no_auto_inference(self) -> None:
        app = self.app()
        app.sidebar.radio[0].set_value("Safe Demo Inference").run()
        mode = next(radio for radio in app.radio if radio.label == "Public Input Mode")
        self.assertEqual(tuple(mode.options), ("Basic Form", "Sample Profiles", "Advanced Editor — Technical Mode"))
        self.assertEqual(mode.value, "Basic Form")
        self.assertTrue(all(not checkbox.value for checkbox in app.checkbox))
        self.assertFalse(any("Controlled Inference Result" in item.value for item in app.subheader))

    def test_08_privacy_widget_boundary(self) -> None:
        app = self.app()
        app.sidebar.radio[0].set_value("Safe Demo Inference").run()
        self.assertEqual(len(app.text_input), 0)
        self.assertEqual(len(app.text_area), 0)
        self.assertEqual(len(getattr(app, "file_uploader", [])), 0)
        self.assertEqual(len(getattr(app, "camera_input", [])), 0)

    def test_09_advanced_editor_profile_reset_cycle(self) -> None:
        app = self.app()
        app.sidebar.radio[0].set_value("Safe Demo Inference").run()
        next(radio for radio in app.radio if radio.label == "Public Input Mode").set_value("Advanced Editor — Technical Mode").run()
        number = lambda label: next(widget for widget in app.number_input if widget.label == label)
        select = lambda label: next(widget for widget in app.selectbox if widget.label == label)
        result_present = lambda: any("Controlled Inference Result" in item.value for item in app.subheader)
        self.assertEqual(select("Canonical reset profile").value, PROFILE_IDS[0])
        self.assertEqual(number("dti").value, 18.27)
        number("dti").set_value(15.0)
        app.checkbox[0].set_value(True)
        app.run()
        self.assertFalse(result_present())
        select("Canonical reset profile").set_value(PROFILE_IDS[1]).run()
        self.assertEqual(select("term_months").value, 60)
        self.assertIn("is_60_month: 1 (read-only; derived from term_months)", [item.value for item in app.caption])
        self.assertFalse(app.checkbox[0].value)
        select("Canonical reset profile").set_value(PROFILE_IDS[0]).run()
        self.assertEqual(number("dti").value, 18.27)
        self.assertEqual(select("term_months").value, 36)
        self.assertIn("is_60_month: 0 (read-only; derived from term_months)", [item.value for item in app.caption])
        self.assertFalse(app.checkbox[0].value)
        self.assertFalse(result_present())
        self.assertEqual(len(app.exception), 0)

    def test_09b_basic_form_end_to_end_ui_submission_twice(self) -> None:
        first_probability, first_text = self.run_basic_form_ui_flow()
        second_probability, second_text = self.run_basic_form_ui_flow()
        self.assertEqual(first_probability, second_probability)
        self.assertIn("fictional portfolio demonstration", first_text)
        self.assertIn("fictional portfolio demonstration", second_text)

    def test_09c_rendered_pre_and_post_submission_governance(self) -> None:
        app = self.app()
        app.sidebar.radio[0].set_value("Safe Demo Inference").run()
        before = self.normalized_visible_text(app)
        self.assertIn("choose one fictional-input mode", before)
        self.assertIn("inference runs only after explicit submission", before)
        self.assertIn("not a lending outcome or recommendation", before)
        _, after = self.run_basic_form_ui_flow()
        for expected in (
            "fictional portfolio demonstration",
            "not a lending decision",
            "approval recommendation",
            "rejection recommendation",
            "legal assessment",
            "fairness conclusion",
            "production underwriting result",
        ):
            self.assertIn(expected, after)

    def test_09d_rendered_governance_page_and_prohibited_claims(self) -> None:
        prohibited = (
            "loan approved", "application approved", "loan rejected", "application rejected",
            "eligible for credit", "ineligible for credit", "approve this borrower",
            "reject this borrower",
        )
        app = self.app()
        page_texts: list[str] = []
        for page in app.sidebar.radio[0].options:
            app.sidebar.radio[0].set_value(page).run()
            page_texts.append(self.normalized_visible_text(app))
        governance = page_texts[-1]
        self.assertIn("fairness audit findings are carried forward as limitations", governance)
        self.assertIn("not as proof of fairness", governance)
        self.assertIn("legal compliance", governance)
        self.assertIn("deployment authorization", governance)
        self.assertIn("does not perform", governance)
        combined = " ".join(page_texts)
        self.assertFalse(any(claim in combined for claim in prohibited))


class ControlledInferenceTests(AcceptanceBase):
    def test_10_basic_form_backend_seven_exact_deterministic_cases(self) -> None:
        self.assertEqual(len(self.vectors), 7)
        for vector in self.vectors:
            first = run_basic_form_inference(vector["source_inputs"], vector["system_metadata"])
            second = run_basic_form_inference(vector["source_inputs"], vector["system_metadata"])
            with self.subTest(case=vector["vector_id"]):
                self.assertEqual(first.inference_status, frozen_adapter.AVAILABLE)
                self.assertEqual(first.calibrated_default_probability, EXPECTED_BASIC[vector["vector_id"]])
                self.assertEqual(second.calibrated_default_probability, first.calibrated_default_probability)

    def test_11_sample_profiles_five_exact_deterministic_cases(self) -> None:
        for profile_id in PROFILE_IDS:
            first = frozen_adapter.run_committed_sample_profile_inference(profile_id)
            second = frozen_adapter.run_committed_sample_profile_inference(profile_id)
            with self.subTest(profile=profile_id):
                self.assertEqual(first.inference_status, frozen_adapter.AVAILABLE)
                self.assertEqual(first.calibrated_default_probability, EXPECTED_SAMPLE[profile_id])
                self.assertEqual(second.calibrated_default_probability, first.calibrated_default_probability)

    def test_12_advanced_editor_five_exact_parity_cases(self) -> None:
        for profile_id in PROFILE_IDS:
            first = run_advanced_editor_inference(self.advanced_request(profile_id))
            second = run_advanced_editor_inference(self.advanced_request(profile_id))
            with self.subTest(profile=profile_id):
                self.assertEqual(first.inference_status, frozen_adapter.AVAILABLE)
                self.assertEqual(first.calibrated_default_probability, EXPECTED_ADVANCED[profile_id])
                self.assertEqual(second.calibrated_default_probability, first.calibrated_default_probability)
                basic_case = next(v for v in self.vectors if v["system_metadata"]["synthetic_baseline_profile_id"] == profile_id)
                basic = run_basic_form_inference(basic_case["source_inputs"], basic_case["system_metadata"])
                self.assertEqual(first.calibrated_default_probability, basic.calibrated_default_probability)

    def test_13_eight_invalid_requests_fail_closed_before_runtime(self) -> None:
        advanced: list[dict[str, object]] = []
        request = self.advanced_request(); request["system_metadata"]["advanced_editor_acknowledged"] = False  # type: ignore[index]
        advanced.append(request)
        request = self.advanced_request(); self.set_advanced_value(request, "dti", 12.5); advanced.append(request)
        request = self.advanced_request(); request["system_metadata"]["edited_feature_names"] = ["dti"]  # type: ignore[index]
        advanced.append(request)
        request = self.advanced_request(); request["payload_rows"].append({"feature_index": 49, "feature_name": "extra", "value": 1})  # type: ignore[union-attr]
        advanced.append(request)
        request = self.advanced_request(); self.set_advanced_value(request, "grade_encoded", 99); advanced.append(request)
        request = self.advanced_request(); request["system_metadata"]["full_name"] = "prohibited"  # type: ignore[index]
        advanced.append(request)
        vector = self.vectors[0]
        basic = [
            ({**vector["source_inputs"], "dti": -1}, vector["system_metadata"]),
            ({**vector["source_inputs"], "purpose": "INVALID"}, vector["system_metadata"]),
        ]
        with (
            mock.patch.object(frozen_adapter, "_verified_runtime") as runtime,
            mock.patch.object(frozen_adapter, "_ordered_model_frame") as frame,
            mock.patch.object(frozen_adapter, "_predict_frame") as predict,
        ):
            results = [run_advanced_editor_inference(item) for item in advanced]
            results += [run_basic_form_inference(source, metadata) for source, metadata in basic]
        runtime.assert_not_called(); frame.assert_not_called(); predict.assert_not_called()
        self.assertEqual(len(results), 8)
        self.assertTrue(all(result.inference_status == frozen_adapter.UNAVAILABLE for result in results))
        self.assertTrue(all(result.calibrated_default_probability is None for result in results))


class BoundaryAndEvidenceTests(AcceptanceBase):
    def test_14_source_has_no_network_persistence_or_sensitive_widgets(self) -> None:
        forbidden_imports = {"requests", "httpx", "urllib", "urllib3", "socket", "aiohttp"}
        forbidden_calls = {"text_input", "text_area", "file_uploader", "camera_input", "to_sql", "write_text", "write_bytes"}
        for path in sorted((ROOT / "app").rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imports: set[str] = set()
            calls: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import): imports.update(item.name.split(".")[0] for item in node.names)
                if isinstance(node, ast.ImportFrom): imports.add((node.module or "").split(".")[0])
                if isinstance(node, ast.Call):
                    calls.add(node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else "")
            self.assertFalse(imports & forbidden_imports)
            self.assertFalse(calls & forbidden_calls)

    def test_15_governance_source_audit_and_no_affirmative_decision_claims(self) -> None:
        source = "\n".join((ROOT / path).read_text(encoding="utf-8").lower() for path in ("app/src/ui_text.py", "app/src/pages.py", "app/src/payload_preview.py"))
        for required in ("fictional portfolio demonstration", "not a lending decision", "production underwriting", "legal", "fairness"):
            self.assertIn(required, source)
        for prohibited in ("loan approved", "application approved", "loan rejected", "application rejected", "eligible for credit", "ineligible for credit", "approve this borrower", "reject this borrower"):
            self.assertNotIn(prohibited, source)

    def test_16_strict_json_and_required_top_level_sections(self) -> None:
        for relative_path in EVIDENCE_JSON_PATHS:
            self.assertIsInstance(strict_json(ROOT / relative_path), dict)
        report = strict_json(ROOT / EVIDENCE_JSON_PATHS[0])
        for key in (
            "repository_preconditions", "repository_lifecycle_compatibility",
            "frozen_step6_integrity", "localhost_startup", "localhost_health",
            "six_page_acceptance", "basic_form_backend_acceptance",
            "basic_form_ui_acceptance", "governance_source_audit",
            "rendered_governance_acceptance", "manual_browser_review", "validation_result",
        ):
            self.assertIn(key, report)

    def test_17_localhost_evidence_records_safe_startup_and_cleanup(self) -> None:
        smoke = strict_json(ROOT / EVIDENCE_JSON_PATHS[1])
        self.assertEqual(smoke["bind_address"], "127.0.0.1")
        self.assertTrue(smoke["server_started"])
        self.assertEqual(smoke["health_status_code"], 200)
        self.assertTrue(smoke["root_responded"])
        self.assertFalse(smoke["public_bind_present"])
        self.assertFalse(smoke["external_network_required"])
        self.assertTrue(smoke["process_cleanup"]["server_terminated"])
        self.assertFalse(smoke["process_cleanup"]["server_process_remaining"])
        self.assertTrue(smoke["process_cleanup"]["port_released"])

    def test_18_manual_checklist_remains_pending_and_unchecked(self) -> None:
        text = (ROOT / "outputs/stage9/stage9_localhost_manual_acceptance_checklist.md").read_text(encoding="utf-8")
        self.assertIn(BASELINE_COMMIT, text)
        self.assertIn("phase8-public-demo-source", text)
        self.assertIn("PENDING_HUMAN_REVIEW", text)
        self.assertNotRegex(text, r"(?m)^\s*- \[[xX]\]")
        report = strict_json(ROOT / EVIDENCE_JSON_PATHS[0])
        self.assertEqual(report["manual_browser_review"]["status"], "PENDING_HUMAN_REVIEW")
        self.assertFalse(report["manual_browser_review"]["manual_review_performed"])
        self.assertFalse(report["manual_browser_review"]["manual_pass_claimed"])
        self.assertFalse(report["next_step_authorization"]["public_deployment_authorized"])

    def test_19_artifact_manifest_hashes_and_scope(self) -> None:
        manifest = strict_json(ROOT / EVIDENCE_JSON_PATHS[2])
        self.assertEqual(manifest["artifact_count"], 5)
        self.assertEqual(manifest["baseline_commit"], BASELINE_COMMIT)
        expected = set(STEP7A_PATHS) - {EVIDENCE_JSON_PATHS[2]}
        self.assertEqual({item["relative_path"] for item in manifest["artifacts"]}, expected)
        for item in manifest["artifacts"]:
            path = ROOT / item["relative_path"]
            self.assertEqual(path.stat().st_size, item["size_bytes"])
            self.assertEqual(sha256(path), item["sha256"])

    def test_20_real_repository_scope_is_lifecycle_compatible(self) -> None:
        classified = current_repository_classification()
        self.assertIn(
            classified.mode,
            {"STEP7A_PRECOMMIT_UNTRACKED", "STEP7A_PRECOMMIT_STAGED", "POSTCOMMIT_FUTURE_STAGE"},
        )
        self.assertEqual(set(classified.step7a_scope), set(STEP7A_PATHS))

    def test_21_evidence_has_no_secrets_or_developer_absolute_paths(self) -> None:
        local_path_pattern = "|".join(
            re.escape(value)
            for value in ("/" + "home/", "/" + "Users/", "\\" + "Users" + "\\")
        )
        patterns = (
            re.compile(local_path_pattern),
            re.compile("-" * 5 + r"BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY" + "-" * 5),
            re.compile(r"\b(?:s" + r"k-|gh[pousr]_)[A-Za-z0-9_-]{20,}"),
            re.compile(r"(?i)https?://[^\s/:]+:[^\s/@]+@"),
        )
        for relative_path in STEP7A_PATHS:
            text = (ROOT / relative_path).read_text(encoding="utf-8")
            with self.subTest(path=relative_path):
                self.assertFalse(any(pattern.search(text) for pattern in patterns))


if __name__ == "__main__":
    unittest.main()
