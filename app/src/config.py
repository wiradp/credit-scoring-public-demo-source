"""Configuration for the contract-driven Streamlit demo.

This module is intentionally limited to path constants and allowlists. It does
not load models, explainers, raw data, or runtime prediction assets.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ROOT = PROJECT_ROOT / "artifacts" / "contracts"
CONTRACT_MANIFEST_CSV = CONTRACT_ROOT / "manifest" / "cell_group_7_contract_export_manifest.csv"
CONTRACT_MANIFEST_JSON = CONTRACT_ROOT / "manifest" / "cell_group_7_contract_export_manifest.json"
STAGE_0_READINESS_REPORT = CONTRACT_ROOT / "manifest" / "stage_0_contract_export_readiness_report.json"

ALLOWED_CONTRACT_SUFFIXES = {".csv", ".json"}
BLOCKED_CONTRACT_SUFFIXES = {
    ".pkl",
    ".pickle",
    ".joblib",
    ".npy",
    ".npz",
    ".parquet",
    ".feather",
    ".db",
    ".sqlite",
    ".sav",
    ".onnx",
    ".pt",
    ".pth",
    ".h5",
}

PAGE_NAMES = [
    "Overview",
    "Contract Readiness",
    "Demo Input Modes",
    "Payload Builder & Preview",
    "Governance & Limitations",
]

STAGE_1_STATUS = "READY_WITH_WARNINGS"
NEXT_STAGE = "STAGE_3_CONTRACT_PAYLOAD_BUILDER"
