#!/usr/bin/env python3
"""Validate Stage 6.10 event/fault runtime path readiness.

This validator is intentionally static.

It does not launch YAMCS, does not run OpenSVF, does not run OpenOBSW, and does
not claim closed-loop event/fault runtime execution.
"""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]

EVENTS_MODEL = REPO_ROOT / "orbitfabric_models" / "mission" / "events.yaml"
FAULTS_MODEL = REPO_ROOT / "orbitfabric_models" / "mission" / "faults.yaml"
POC_SLICE = REPO_ROOT / "orbitfabric_models" / "poc_slice.yaml"
MISSION_CONTRACT = REPO_ROOT / "generated_artifacts" / "flight_software" / "mission_contract.h"
POC_SRDB = REPO_ROOT / "generated_artifacts" / "ground_segment" / "poc_srdb.yaml"
MDB_PATH = REPO_ROOT / "execution" / "generated" / "poc_xtce_mdb.xml"
YAMCS_INSTANCE = REPO_ROOT / "execution" / "yamcs" / "etc" / "yamcs.opensvf.yaml"
YAMCS_PROCESSOR = REPO_ROOT / "execution" / "yamcs" / "etc" / "processor.yaml"

EVENT_ID = "eps.voltage_out_of_bounds"
FAULT_ID = "eps.voltage_out_of_bounds_fault"
EVENT_NAME = "voltage_out_of_bounds"
EVENT_C_ID = "OF_EVENT_VOLTAGE_OUT_OF_BOUNDS"
EVENT_C_VALUE = "0x5001"
EVENT_SRDB_NAME = "eps.obc.voltage_out_of_bounds"
TELEMETRY_NAME = "eps.obc.bus_voltage_mv"
EXPECTED_THRESHOLD = 3500
EXPECTED_DEBOUNCE = 3
EXPECTED_PUS_SERVICE = 5
EXPECTED_PUS_SUBTYPE = 3

EXPECTED_TM_PORT = 10015
EXPECTED_TC_PORT = 10025


def fail(message: str) -> None:
    raise SystemExit(
        "Stage 6.10 event/fault runtime path readiness: FAIL\n"
        f"{message}"
    )


def read_text(path: Path) -> str:
    if not path.is_file():
        fail(f"Required file not found: {path}")
    return path.read_text(encoding="utf-8")


def load_yaml(path: Path) -> dict[str, Any]:
    text = read_text(path)
    try:
        loaded = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        fail(f"YAML parse failed for {path}: {exc}")

    if not isinstance(loaded, dict):
        fail(f"YAML root must be a mapping: {path}")

    return loaded


def require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"Expected mapping: {label}")
    return value


def require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        fail(f"Expected list: {label}")
    return value


def require_contains(text: str, marker: str, path: Path) -> None:
    if marker not in text:
        fail(f"Missing marker in {path}: {marker}")


def find_by_key(items: list[Any], key: str, expected: Any, label: str) -> dict[str, Any]:
    for item in items:
        if isinstance(item, dict) and item.get(key) == expected:
            return item
    fail(f"Missing {label}: {key}={expected}")


def validate_mission_model() -> None:
    events_model = load_yaml(EVENTS_MODEL)
    faults_model = load_yaml(FAULTS_MODEL)

    events = require_list(events_model.get("events"), "mission events")
    event = find_by_key(events, "id", EVENT_ID, "mission event")

    if event.get("source") != "eps":
        fail(f"Unexpected event source: {event.get('source')}")
    if event.get("severity") != "warning":
        fail(f"Unexpected event severity: {event.get('severity')}")
    if event.get("downlink_priority") != "high":
        fail(f"Unexpected event downlink priority: {event.get('downlink_priority')}")
    if event.get("persistence") != "store_and_downlink":
        fail(f"Unexpected event persistence: {event.get('persistence')}")

    faults = require_list(faults_model.get("faults"), "mission faults")
    fault = find_by_key(faults, "id", FAULT_ID, "mission fault")

    if fault.get("source") != "eps":
        fail(f"Unexpected fault source: {fault.get('source')}")
    if fault.get("severity") != "warning":
        fail(f"Unexpected fault severity: {fault.get('severity')}")

    condition = require_mapping(fault.get("condition"), "fault condition")
    if condition.get("telemetry") != TELEMETRY_NAME:
        fail(f"Unexpected fault telemetry: {condition.get('telemetry')}")
    if condition.get("operator") != ">":
        fail(f"Unexpected fault operator: {condition.get('operator')}")
    if condition.get("value") != EXPECTED_THRESHOLD:
        fail(f"Unexpected fault threshold: {condition.get('value')}")
    if condition.get("debounce_samples") != EXPECTED_DEBOUNCE:
        fail(f"Unexpected fault debounce: {condition.get('debounce_samples')}")

    emits = require_list(fault.get("emits"), "fault emits")
    if EVENT_ID not in emits:
        fail(f"Fault does not emit {EVENT_ID}")

    recovery = require_mapping(fault.get("recovery"), "fault recovery")
    if recovery.get("mode_transition") != "SAFE":
        fail(f"Unexpected recovery mode transition: {recovery.get('mode_transition')}")


def validate_poc_mapping() -> None:
    poc_slice = load_yaml(POC_SLICE)
    events = require_list(poc_slice.get("events"), "poc_slice events")
    event = find_by_key(events, "name", EVENT_NAME, "PoC event mapping")

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


def validate_generated_contracts() -> None:
    header = read_text(MISSION_CONTRACT)
    require_contains(header, "OF_EVENT_VOLTAGE_OUT_OF_BOUNDS = 0x5001", MISSION_CONTRACT)

    srdb = load_yaml(POC_SRDB)
    parameters = require_mapping(srdb.get("parameters"), "generated SRDB parameters")
    parameter = require_mapping(parameters.get(TELEMETRY_NAME), TELEMETRY_NAME)
    pus = require_mapping(parameter.get("pus"), f"{TELEMETRY_NAME}.pus")

    if pus.get("service") != 3 or pus.get("subservice") != 25:
        fail("Generated SRDB must preserve the existing TM(3,25) housekeeping mapping")

    if EVENT_SRDB_NAME in parameters:
        fail("Generated SRDB unexpectedly represents the event as a parameter")


def validate_mdb() -> str:
    text = read_text(MDB_PATH)
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        fail(f"Generated XTCE/MDB is not valid XML: {exc}")

    ns = {"xtce": "http://www.omg.org/spec/XTCE/20180204"}

    required_containers = [
        "PUS_Packet",
        "TM_3_25_HK",
        "TM_5_1_Event",
    ]
    for container_name in required_containers:
        found = root.find(
            f".//xtce:SequenceContainer[@name='{container_name}']",
            ns,
        )
        if found is None:
            fail(f"Generated MDB missing sequence container: {container_name}")

    tm_5_3 = root.find(".//xtce:SequenceContainer[@name='TM_5_3_Event']", ns)
    if tm_5_3 is not None:
        return "present"

    if "TM_5_3" in text or "TM(5,3)" in text:
        return "partial"

    return "pending"


def validate_yamcs_candidate() -> None:
    instance = load_yaml(YAMCS_INSTANCE)
    links = require_list(instance.get("dataLinks"), "YAMCS dataLinks")

    tm_link = find_by_key(links, "name", "tm-in", "YAMCS tm-in data link")
    expected_tm = {
        "class": "org.yamcs.tctm.TcpTmDataLink",
        "host": "127.0.0.1",
        "port": EXPECTED_TM_PORT,
        "stream": "tm_realtime",
        "packetPreprocessorClassName": "org.yamcs.pus.PusPacketPreprocessor",
    }
    for key, expected in expected_tm.items():
        if tm_link.get(key) != expected:
            fail(f"Unexpected YAMCS tm-in {key}: {tm_link.get(key)}")

    tc_link = find_by_key(links, "name", "tc-out", "YAMCS tc-out data link")
    expected_tc = {
        "class": "org.yamcs.tctm.UdpTcDataLink",
        "host": "127.0.0.1",
        "port": EXPECTED_TC_PORT,
        "stream": "tc_realtime",
    }
    for key, expected in expected_tc.items():
        if tc_link.get(key) != expected:
            fail(f"Unexpected YAMCS tc-out {key}: {tc_link.get(key)}")

    processor = load_yaml(YAMCS_PROCESSOR)
    realtime = require_mapping(processor.get("realtime"), "YAMCS realtime processor")
    config = require_mapping(realtime.get("config"), "YAMCS realtime config")

    if config.get("generateEvents") is not False:
        fail("Stage 6.10 expects processor config generateEvents: false")

    alarm = require_mapping(config.get("alarm"), "YAMCS alarm config")
    if alarm.get("parameterCheck") is not False:
        fail("Stage 6.10 expects alarm.parameterCheck: false")
    if alarm.get("parameterServer") != "disabled":
        fail("Stage 6.10 expects alarm.parameterServer: disabled")


def validate_openobsw(openobsw_repo: Path) -> None:
    s5_h = openobsw_repo / "include" / "obsw" / "pus" / "s5.h"
    s5_c = openobsw_repo / "src" / "pus" / "s5.c"
    codegen = openobsw_repo / "srdb" / "obsw_srdb" / "codegen.py"
    test_s5 = openobsw_repo / "test" / "unit" / "test_s5.c"

    s5_h_text = read_text(s5_h)
    for marker in [
        "TM(5,3)",
        "OBSW_S5_MEDIUM = 3",
        "uint16_t event_id",
        "obsw_s5_report",
    ]:
        require_contains(s5_h_text, marker, s5_h)

    s5_c_text = read_text(s5_c)
    for marker in [
        "TM(5,x) data field: event_id (2 bytes) + auxiliary data",
        "buf[0] = (uint8_t)(event_id >> 8)",
        "buf[1] = (uint8_t)(event_id & 0xFFU)",
        "obsw_pus_tm_build(ctx->tm_store, ctx->apid, seq,",
        "5, (uint8_t)severity",
    ]:
        require_contains(s5_c_text, marker, s5_c)

    codegen_text = read_text(codegen)
    for marker in [
        "TM_5_{subsvc}",
        "S5 event reports",
        "TM(5,{subsvc})",
    ]:
        require_contains(codegen_text, marker, codegen)

    test_text = read_text(test_s5)
    for marker in [
        "obsw_s5_report(&s5, OBSW_S5_MEDIUM",
        "test_auxiliary_data_appended",
        "test_event_id_in_data_field",
    ]:
        require_contains(test_text, marker, test_s5)


def validate_opensvf(opensvf_repo: Path) -> None:
    bridge = opensvf_repo / "src" / "svf" / "ground" / "yamcs_bridge.py"
    s5 = opensvf_repo / "src" / "svf" / "pus" / "services" / "s05_event_reporting.py"
    s12 = opensvf_repo / "src" / "svf" / "pus" / "services" / "s12_monitoring.py"
    bridge_test = opensvf_repo / "tests" / "integration" / "test_yamcs_bridge.py"

    bridge_text = read_text(bridge)
    for marker in [
        "TM_PORT = 10015",
        "TC_PORT = 10025",
        "def send_tm",
        "self._tm_conn.sendall(packet)",
    ]:
        require_contains(bridge_text, marker, bridge)

    s5_text = read_text(s5)
    for marker in [
        "MEDIUM      = 3",
        "PUS Service 5",
        "service=5",
        "subservice=severity",
        "struct.pack(\">H\", event_id)",
    ]:
        require_contains(s5_text, marker, s5)

    s12_text = read_text(s12)
    for marker in [
        "On-Board Monitoring",
        "PusService5.report",
        "event_id_high",
        "severity=defn.severity",
    ]:
        require_contains(s12_text, marker, s12)

    test_text = read_text(bridge_test)
    for marker in [
        "test_bridge_sends_tm_to_yamcs",
        "bridge.send_tm(pkt)",
        "test_bridge_receives_tc_from_yamcs",
    ]:
        require_contains(test_text, marker, bridge_test)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--openobsw-repo",
        default="../openobsw",
        help="Path to the OpenOBSW repository. Default: ../openobsw",
    )
    parser.add_argument(
        "--opensvf-repo",
        default="../opensvf",
        help="Path to the OpenSVF repository. Default: ../opensvf",
    )
    args = parser.parse_args()

    openobsw_repo = (REPO_ROOT / args.openobsw_repo).resolve()
    opensvf_repo = (REPO_ROOT / args.opensvf_repo).resolve()

    validate_mission_model()
    validate_poc_mapping()
    validate_generated_contracts()
    mdb_tm_5_3_state = validate_mdb()
    validate_yamcs_candidate()
    validate_openobsw(openobsw_repo)
    validate_opensvf(opensvf_repo)

    print("Stage 6.10 event/fault runtime path readiness")
    print(f"Repository root: {REPO_ROOT}")
    print(f"OpenOBSW repository: {openobsw_repo}")
    print(f"OpenSVF repository: {opensvf_repo}")
    print(f"Mission event: {EVENT_ID}")
    print(f"Mission fault: {FAULT_ID}")
    print(f"PoC event ID: {EVENT_C_ID} = {EVENT_C_VALUE}")
    print("Mapped PUS event: TM(5,3)")
    print(f"Generated MDB TM(5,3) marker: {mdb_tm_5_3_state}")
    print("OpenOBSW S5 capability: present")
    print("OpenSVF YamcsBridge capability: present")
    print("OpenSVF PUS S5 capability: present")
    print("Live OpenSVF/YamcsBridge execution: false")
    print("Live OpenOBSW event delivery into YAMCS: false")
    print("Closed-loop event/fault runtime execution: false")
    print("Stage 6.10 event/fault runtime path readiness: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
