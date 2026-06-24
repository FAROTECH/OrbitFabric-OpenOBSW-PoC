#!/usr/bin/env python3
"""Validate Stage 6.8 YAMCS/MDB runtime visibility readiness.

This script intentionally does not launch YAMCS.

It verifies that the PoC runtime input manifest already exposes a generated
XTCE/MDB artifact that can be used as the next handoff point for YAMCS runtime
visibility work.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import yaml


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


def read_text(path: Path, generation_hint: str | None = None) -> str:
    if not path.is_file():
        message = f"Required file not found: {path}"
        if generation_hint:
            message += "\nGenerate it with:\n"
            message += f"  {generation_hint}"
        fail(message)

    return path.read_text(encoding="utf-8")


def require_mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"Manifest field must be a YAML mapping: {field_name}")

    return value


def require_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        fail(f"Manifest field must be a non-empty string: {field_name}")

    return value.strip()


def load_manifest(manifest_text: str) -> dict[str, Any]:
    try:
        loaded = yaml.safe_load(manifest_text)
    except yaml.YAMLError as exc:
        fail(f"Runtime input manifest is not valid YAML: {exc}")

    return require_mapping(loaded, "root")


def validate_manifest(manifest_text: str) -> tuple[Path, str]:
    manifest = load_manifest(manifest_text)

    generated_artifacts = require_mapping(
        manifest.get("generated_artifacts"),
        "generated_artifacts",
    )
    generated_xtce_mdb = require_mapping(
        generated_artifacts.get("generated_xtce_mdb"),
        "generated_artifacts.generated_xtce_mdb",
    )

    mdb_relative_path = require_string(
        generated_xtce_mdb.get("path"),
        "generated_artifacts.generated_xtce_mdb.path",
    )
    generation_hint = require_string(
        generated_xtce_mdb.get("generation_hint"),
        "generated_artifacts.generated_xtce_mdb.generation_hint",
    )

    if mdb_relative_path != EXPECTED_MDB_RELATIVE_PATH:
        fail(
            "Unexpected generated XTCE/MDB path in manifest:\n"
            f"expected: {EXPECTED_MDB_RELATIVE_PATH}\n"
            f"actual:   {mdb_relative_path}"
        )

    current_boundary = require_mapping(
        manifest.get("current_boundary"),
        "current_boundary",
    )
    if current_boundary.get("yamcs_runtime_execution") is not False:
        fail("Manifest must still declare current_boundary.yamcs_runtime_execution: false")

    return REPO_ROOT / mdb_relative_path, generation_hint


def validate_xtce_mdb(mdb_path: Path, generation_hint: str) -> None:
    xml_text = read_text(mdb_path, generation_hint)

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
    mdb_path, generation_hint = validate_manifest(manifest_text)
    validate_xtce_mdb(mdb_path, generation_hint)

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
