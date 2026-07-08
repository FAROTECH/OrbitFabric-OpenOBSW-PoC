#!/usr/bin/env python3
"""Validate Stage 6.11 YAMCS PUS Service 5 event MDB projection."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]

GENERATOR = REPO_ROOT / "tools" / "generate_poc_xtce_mdb.py"
MDB_PATH = REPO_ROOT / "execution" / "generated" / "poc_xtce_mdb.xml"
MISSION_MODEL = REPO_ROOT / "orbitfabric_models" / "poc_slice.yaml"
MISSION_CONTRACT = REPO_ROOT / "generated_artifacts" / "flight_software" / "mission_contract.h"

EVENT_ID = "eps.voltage_out_of_bounds"
POC_EVENT_NAME = "voltage_out_of_bounds"
EVENT_C_ID = "OF_EVENT_VOLTAGE_OUT_OF_BOUNDS"
EVENT_C_VALUE = "0x5001"
EVENT_SRDB_NAME = "eps.obc.voltage_out_of_bounds"
TELEMETRY_NAME = "eps.obc.bus_voltage_mv"
EXPECTED_PUS_SERVICE = 5
EXPECTED_PUS_SUBTYPE = 3
EXPECTED_THRESHOLD = 3500
EVENT_PARAMETER = "of_event_id"
EVENT_CONTAINER = "TM_5_3_Event"

XTCE_NS = {"xtce": "http://www.omg.org/spec/XTCE/20180204"}


def fail(message: str) -> None:
    raise SystemExit(f"Stage 6.11 validation failed: {message}")


def read_text(path: Path) -> str:
    if not path.is_file():
        fail(f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def load_yaml(path: Path) -> Any:
    text = read_text(path)
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        fail(f"Invalid YAML in {path}: {exc}")


def require_contains(text: str, marker: str, path: Path) -> None:
    if marker not in text:
        fail(f"Missing marker in {path}: {marker}")


def require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"Expected mapping for {label}")
    return value


def require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        fail(f"Expected list for {label}")
    return value


def find_by_key(items: list[Any], key: str, expected: Any, label: str) -> dict[str, Any]:
    for item in items:
        if isinstance(item, dict) and item.get(key) == expected:
            return item
    fail(f"Missing {label}: {key}={expected}")


def validate_generator_projection() -> None:
    text = read_text(GENERATOR)
    for marker in [
        "project_stage6_11_s5_event_mdb",
        "TM_5_3_Event",
        "of_event_id",
        "OF_EVENT_VOLTAGE_OUT_OF_BOUNDS = 0x5001",
        "eps.voltage_out_of_bounds",
    ]:
        require_contains(text, marker, GENERATOR)


def validate_mission_event_mapping() -> None:
    poc_slice = require_mapping(load_yaml(MISSION_MODEL), "poc slice")
    events = require_list(poc_slice.get("events"), "poc_slice events")
    event = find_by_key(events, "name", POC_EVENT_NAME, "PoC event mapping")

    expected_pairs = {
        "of_id": EVENT_C_ID,
        "of_id_value": int(EVENT_C_VALUE, 16),
        "srdb_name": EVENT_SRDB_NAME,
        "pus_service": EXPECTED_PUS_SERVICE,
        "pus_subtype": EXPECTED_PUS_SUBTYPE,
        "severity": "warning",
    }
    for key, expected in expected_pairs.items():
        if event.get(key) != expected:
            fail(f"Unexpected PoC event mapping {key}: {event.get(key)}")

    trigger = require_mapping(event.get("trigger"), "PoC event trigger")
    if trigger.get("parameter") != TELEMETRY_NAME:
        fail(f"Unexpected trigger parameter: {trigger.get('parameter')}")
    if trigger.get("condition") != ">":
        fail(f"Unexpected trigger condition: {trigger.get('condition')}")
    if trigger.get("threshold_mv") != EXPECTED_THRESHOLD:
        fail(f"Unexpected trigger threshold: {trigger.get('threshold_mv')}")

    contract = read_text(MISSION_CONTRACT)
    require_contains(contract, f"{EVENT_C_ID} = {EVENT_C_VALUE}", MISSION_CONTRACT)


def parse_mdb() -> ET.Element:
    text = read_text(MDB_PATH)
    try:
        return ET.fromstring(text)
    except ET.ParseError as exc:
        fail(f"Generated XTCE/MDB is not valid XML: {exc}")


def find_required(root: ET.Element, xpath: str, label: str) -> ET.Element:
    found = root.find(xpath, XTCE_NS)
    if found is None:
        fail(f"Missing {label}")
    return found


def validate_mdb_projection(root: ET.Element) -> None:
    parameter = find_required(
        root,
        f".//xtce:Parameter[@name='{EVENT_PARAMETER}']",
        EVENT_PARAMETER,
    )
    if parameter.get("parameterTypeRef") != "uint16":
        fail(f"{EVENT_PARAMETER} must use uint16 type")

    container = find_required(
        root,
        f".//xtce:SequenceContainer[@name='{EVENT_CONTAINER}']",
        EVENT_CONTAINER,
    )

    description = container.find("xtce:LongDescription", XTCE_NS)
    if description is None or description.text is None:
        fail(f"{EVENT_CONTAINER} must document the projected event")

    for marker in [EVENT_C_ID, EVENT_C_VALUE, EVENT_ID]:
        if marker not in description.text:
            fail(f"{EVENT_CONTAINER} description missing marker: {marker}")

    base = find_required(container, "xtce:BaseContainer", f"{EVENT_CONTAINER} base container")
    if base.get("containerRef") != "PUS_Packet":
        fail(f"{EVENT_CONTAINER} must derive from PUS_Packet")

    svc = find_required(
        container,
        ".//xtce:Comparison[@parameterRef='pus_svc']",
        f"{EVENT_CONTAINER} service restriction",
    )
    subsvc = find_required(
        container,
        ".//xtce:Comparison[@parameterRef='pus_subsvc']",
        f"{EVENT_CONTAINER} subservice restriction",
    )

    if svc.get("value") != "5" or svc.get("comparisonOperator") != "==":
        fail(f"{EVENT_CONTAINER} must restrict pus_svc to 5")
    if subsvc.get("value") != "3" or subsvc.get("comparisonOperator") != "==":
        fail(f"{EVENT_CONTAINER} must restrict pus_subsvc to 3")

    entry = find_required(
        container,
        f".//xtce:ParameterRefEntry[@parameterRef='{EVENT_PARAMETER}']",
        f"{EVENT_CONTAINER} event id entry",
    )
    fixed = find_required(
        entry,
        ".//xtce:FixedValue",
        f"{EVENT_CONTAINER} event id bit offset",
    )
    if fixed.text != "88":
        fail(f"{EVENT_CONTAINER} event id must start at bit offset 88")


def validate_existing_markers(root: ET.Element) -> None:
    for container_name in [
        "PUS_Packet",
        "TM_3_25_HK",
        "TM_5_1_Event",
        EVENT_CONTAINER,
    ]:
        find_required(
            root,
            f".//xtce:SequenceContainer[@name='{container_name}']",
            container_name,
        )


def main() -> int:
    validate_generator_projection()
    validate_mission_event_mapping()

    root = parse_mdb()
    validate_existing_markers(root)
    validate_mdb_projection(root)

    print("Stage 6.11 YAMCS PUS Service 5 event MDB projection")
    print(f"Repository root: {REPO_ROOT}")
    print(f"Generated XTCE/MDB: {MDB_PATH.relative_to(REPO_ROOT)}")
    print(f"Projected event: {EVENT_ID}")
    print(f"Projected event ID: {EVENT_C_ID} = {EVENT_C_VALUE}")
    print("Projected PUS event: TM(5,3)")
    print(f"Projected MDB container: {EVENT_CONTAINER}")
    print(f"Projected MDB event parameter: {EVENT_PARAMETER}")
    print("Live OpenSVF/YamcsBridge execution: false")
    print("Live OpenOBSW event delivery into YAMCS: false")
    print("Closed-loop event/fault runtime execution: false")
    print("Stage 6.11 YAMCS PUS Service 5 event MDB projection: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
