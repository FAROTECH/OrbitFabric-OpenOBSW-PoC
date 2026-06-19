#!/usr/bin/env python3
"""Validate Stage 6.8 YAMCS/MDB runtime visibility readiness.

This script intentionally does not launch YAMCS.

It verifies that the PoC runtime input manifest already exposes a generated
XTCE/MDB artifact that can be used as the next handoff point for YAMCS runtime
visibility work.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

MANIFEST_PATH = REPO_ROOT / "execution" / "opensvf" / "poc_runtime_inputs.yaml"
EXPECTED_MDB_RELATIVE_PATH = "execution/generated/poc_xtce_mdb.xml"
EXPECTED_PARAMETER_NAME = "eps_obc_bus_voltage_mv"
EXPECTED_HK_CONTAINER_NAME = "TM_3_25_HK"


def fail(message: str) -> None:
    raise SystemExit(
        "Stage 6.8 YAMCS/MDB runtime visibility readiness: FAIL\n"
        f"{message}"
    )


def read_text(path: Path) -> str:
    if not path.is_file():
        fail(f"Required file not found: {path}")
    return path.read_text(encoding="utf-8")


def extract_generated_mdb_path(manifest_text: str) -> str:
    match = re.search(
        r"generated_xtce_mdb:\s*\n(?:[ \t]+[^\n]*\n)*?[ \t]+path:\s*([^\n]+)",
        manifest_text,
    )
    if match is None:
        fail("Manifest does not expose generated_artifacts.generated_xtce_mdb.path")

    return match.group(1).strip().strip("'\"")


def validate_manifest(manifest_text: str) -> Path:
    mdb_relative_path = extract_generated_mdb_path(manifest_text)

    if mdb_relative_path != EXPECTED_MDB_RELATIVE_PATH:
        fail(
            "Unexpected generated XTCE/MDB path in manifest:\n"
            f"expected: {EXPECTED_MDB_RELATIVE_PATH}\n"
            f"actual:   {mdb_relative_path}"
        )

    if not re.search(r"yamcs_runtime_execution:\s*false\b", manifest_text):
        fail("Manifest must still declare current_boundary.yamcs_runtime_execution: false")

    return REPO_ROOT / mdb_relative_path


def validate_xtce_mdb(mdb_path: Path) -> None:
    xml_text = read_text(mdb_path)

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        fail(f"Generated XTCE/MDB is not valid XML: {exc}")

    ns = {"xtce": "http://www.omg.org/spec/XTCE/20180204"}

    parameter = root.find(
        f".//xtce:Parameter[@name='{EXPECTED_PARAMETER_NAME}']",
        ns,
    )
    if parameter is None:
        fail(f"Generated XTCE/MDB does not contain parameter {EXPECTED_PARAMETER_NAME}")

    hk_container = root.find(
        f".//xtce:SequenceContainer[@name='{EXPECTED_HK_CONTAINER_NAME}']",
        ns,
    )
    if hk_container is None:
        fail(
            "Generated XTCE/MDB does not contain sequence container "
            f"{EXPECTED_HK_CONTAINER_NAME}"
        )


def main() -> int:
    manifest_text = read_text(MANIFEST_PATH)
    mdb_path = validate_manifest(manifest_text)
    validate_xtce_mdb(mdb_path)

    print("Stage 6.8 YAMCS/MDB runtime visibility readiness")
    print(f"Repository root: {REPO_ROOT}")
    print(f"Runtime input manifest: {MANIFEST_PATH.relative_to(REPO_ROOT)}")
    print(f"Generated XTCE/MDB: {mdb_path.relative_to(REPO_ROOT)}")
    print(f"Parameter marker: {EXPECTED_PARAMETER_NAME}")
    print(f"HK container marker: {EXPECTED_HK_CONTAINER_NAME}")
    print("YAMCS runtime execution: false")
    print("Stage 6.8 YAMCS/MDB runtime visibility readiness: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
