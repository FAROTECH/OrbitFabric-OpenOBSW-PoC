#!/usr/bin/env python3
"""Validate Stage 6.20 final integration evidence matrix."""

from __future__ import annotations

import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable, NoReturn


REPO_ROOT = Path(__file__).resolve().parents[1]

DOC = REPO_ROOT / "docs/stage6_20_final_integration_evidence_matrix.md"
MISSION_CONTRACT = REPO_ROOT / "generated_artifacts/flight_software/mission_contract.h"
GROUND_SRDB = REPO_ROOT / "generated_artifacts/ground_segment/poc_srdb.yaml"
MDB_GENERATOR = REPO_ROOT / "tools/generate_poc_xtce_mdb.py"
GENERATED_MDB = REPO_ROOT / "execution/generated/poc_xtce_mdb.xml"

STAGE_VALIDATORS = {
    "stage6.11": REPO_ROOT / "tools/validate_stage6_11_yamcs_s5_event_mdb_projection.py",
    "stage6.12": REPO_ROOT / "tools/validate_stage6_12_yamcs_contract_packet_visibility_probe.py",
    "stage6.17": REPO_ROOT / "tools/validate_stage6_17_live_openobsw_hk_tm_yamcs_path_probe.py",
    "stage6.18": REPO_ROOT / "tools/validate_stage6_18_live_openobsw_event_yamcs_path_probe.py",
    "stage6.19": REPO_ROOT / "tools/validate_stage6_19_yamcs_tc_direction_closure.py",
}

STAGE_DOCS = {
    "stage6.11": REPO_ROOT / "docs/stage6_11_yamcs_s5_event_mdb_projection.md",
    "stage6.12": REPO_ROOT / "docs/stage6_12_yamcs_contract_packet_visibility_probe.md",
    "stage6.17": REPO_ROOT / "docs/stage6_17_live_openobsw_hk_tm_yamcs_path_probe.md",
    "stage6.18": REPO_ROOT / "docs/stage6_18_live_openobsw_event_yamcs_path_probe.md",
    "stage6.19": REPO_ROOT / "docs/stage6_19_yamcs_tc_direction_closure.md",
}

RUNTIME_DRIVERS = {
    "stage6.17": REPO_ROOT / "execution/yamcs/stage6_17_live_openobsw_hk_driver.py",
    "stage6.18": REPO_ROOT / "execution/yamcs/stage6_18_live_openobsw_event_driver.py",
    "stage6.19": REPO_ROOT / "execution/yamcs/stage6_19_yamcs_tc_direction_driver.py",
}

EXPECTED_MDB_CONTAINERS = {
    "TM_3_25_HK",
    "TM_5_3_Event",
    "TM_1_1_Accept",
    "TM_17_2_Pong",
    "TM_1_7_Complete",
}

EXPECTED_MDB_COMMANDS = {
    "TC_17_1_AreYouAlive",
}

EXPECTED_DOC_TERMS = [
    "OrbitFabric Mission Model",
    "eps.obc.bus_voltage_mv",
    "TM_3_25_HK",
    "TC_17_1_AreYouAlive",
    "TM_1_1_Accept",
    "TM_17_2_Pong",
    "TM_1_7_Complete",
    "eps.voltage_out_of_bounds",
    "OF_EVENT_VOLTAGE_OUT_OF_BOUNDS = 0x5001",
    "TM_5_3_Event",
    "raw[17:19]",
    "production mission integration",
    "hardware target execution",
    "Renode or STM32 execution",
    "production FDIR",
    "production commanding authorization",
    "broader OpenOBSW/OpenSVF integration",
]

EXPECTED_STAGE_MARKERS = {
    "stage6.17": [
        "TM_3_25_HK",
        "Live OpenOBSW TM(3,25)",
        "OpenSVF YamcsBridge",
        "YAMCS TcpTmDataLink",
        "Stage 6.17 live OpenOBSW HK TM to YAMCS path probe: PASS",
    ],
    "stage6.18": [
        "TM_5_3_Event",
        "OpenOBSW TM(5,3) event_id raw[17:19] = 0x5001: true",
        "YAMCS TC command path execution: false",
        "Stage 6.18 live OpenOBSW event to YAMCS path probe: PASS",
    ],
    "stage6.19": [
        "YAMCS REST TC command release accepted: true",
        "YAMCS-originated TC observed by OpenSVF YamcsBridge: true",
        "YAMCS-originated TC forwarded to OBCEmulatorAdapter.receive_tc: true",
        "OpenOBSW TC(17,1) reception path exercised: true",
        "Representative PUS response path observed: true",
        "YAMCS command history accepted/sent record observed: true",
        "YAMCS TC command path execution: true",
        "Stage 6.19 YAMCS TC direction closure probe: PASS",
    ],
}


def fail(message: str) -> NoReturn:
    raise SystemExit(
        "Stage 6.20 final integration evidence matrix: FAIL\n"
        f"{message}"
    )


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text()


def require_file(path: Path) -> None:
    if not path.is_file():
        fail(f"Required file not found: {path}")


def require_contains(text: str, marker: str, path: Path) -> None:
    if marker not in text:
        fail(f"Missing marker in {path}: {marker}")


def require_any_contains(text: str, markers: Iterable[str], path: Path) -> None:
    if not any(marker in text for marker in markers):
        fail(f"None of the expected markers were found in {path}: {list(markers)}")


def run(command: list[str]) -> None:
    print("+ " + " ".join(command), flush=True)
    result = subprocess.run(command, cwd=REPO_ROOT, text=True, check=False)
    if result.returncode != 0:
        fail(f"Command failed with exit code {result.returncode}: {' '.join(command)}")


def validate_required_files() -> None:
    for path in [
        DOC,
        MISSION_CONTRACT,
        GROUND_SRDB,
        MDB_GENERATOR,
        GENERATED_MDB,
        *STAGE_VALIDATORS.values(),
        *STAGE_DOCS.values(),
        *RUNTIME_DRIVERS.values(),
    ]:
        require_file(path)

    print("Stage 6.20 required evidence files present: true")


def validate_generated_mdb() -> None:
    run(["python3", str(MDB_GENERATOR.relative_to(REPO_ROOT))])
    require_file(GENERATED_MDB)

    xml_text = read_text(GENERATED_MDB)
    root = ET.fromstring(xml_text)

    ns = {"xtce": "http://www.omg.org/spec/XTCE/20180204"}

    for container in EXPECTED_MDB_CONTAINERS:
        node = root.find(f".//xtce:SequenceContainer[@name='{container}']", ns)
        if node is None:
            fail(f"Generated MDB missing SequenceContainer: {container}")
        print(f"Generated MDB container {container}: true")

    for command in EXPECTED_MDB_COMMANDS:
        node = root.find(f".//xtce:MetaCommand[@name='{command}']", ns)
        if node is None:
            fail(f"Generated MDB missing MetaCommand: {command}")
        print(f"Generated MDB command {command}: true")

    for marker in [
        "eps_obc_bus_voltage_mv",
        "of_event_id",
        "OF_EVENT_VOLTAGE_OUT_OF_BOUNDS = 0x5001",
        "eps.voltage_out_of_bounds",
    ]:
        require_contains(xml_text, marker, GENERATED_MDB)

    if "<FixedValue>136</FixedValue>" not in xml_text:
        fail("Generated MDB does not keep of_event_id at bit offset 136")

    print("Generated MDB event offset raw[17:19] / bit offset 136: true")


def validate_contract_and_srdb() -> None:
    contract = read_text(MISSION_CONTRACT)
    srdb = read_text(GROUND_SRDB)

    for marker in [
        "OF_EVENT_VOLTAGE_OUT_OF_BOUNDS = 0x5001",
        "obc_bus_voltage_mv",
    ]:
        require_contains(contract, marker, MISSION_CONTRACT)

    require_contains(srdb, "eps.obc.bus_voltage_mv", GROUND_SRDB)

    print("Flight contract telemetry/event markers present: true")
    print("Ground SRDB telemetry marker present: true")


def validate_stage_evidence_markers() -> None:
    for stage, markers in EXPECTED_STAGE_MARKERS.items():
        validator_text = read_text(STAGE_VALIDATORS[stage])
        doc_text = read_text(STAGE_DOCS[stage])
        combined = validator_text + "\n" + doc_text

        for marker in markers:
            require_contains(combined, marker, STAGE_VALIDATORS[stage])

        print(f"{stage} evidence markers present: true")


def validate_driver_markers() -> None:
    stage617_driver = read_text(RUNTIME_DRIVERS["stage6.17"])
    stage617_evidence = "\n".join([
        stage617_driver,
        read_text(STAGE_VALIDATORS["stage6.17"]),
        read_text(STAGE_DOCS["stage6.17"]),
    ])
    stage618 = read_text(RUNTIME_DRIVERS["stage6.18"])
    stage619 = read_text(RUNTIME_DRIVERS["stage6.19"])

    for marker in [
        "observed live OpenOBSW TM(3,25)",
        "attached real YamcsBridge to OBCEmulatorAdapter._yamcs_bridge",
    ]:
        require_contains(stage617_evidence, marker, RUNTIME_DRIVERS["stage6.17"])

    for marker in [
        "OF_EVENT_VOLTAGE_OUT_OF_BOUNDS = 0x5001",
        "OpenOBSW TM(5,3) event_id raw[17:19] = 0x5001: true",
        "TC(8,1) OrbitFabric event trigger injected into OpenOBSW: true",
    ]:
        require_contains(stage618, marker, RUNTIME_DRIVERS["stage6.18"])

    for marker in [
        'EXPECTED_TC_HEX = "1810c00000041111010000"',
        "YAMCS REST TC command release accepted: true",
        "YAMCS-originated TC observed by OpenSVF YamcsBridge: true",
        "YAMCS-originated TC forwarded to OBCEmulatorAdapter.receive_tc: true",
        "OpenOBSW TC(17,1) reception path exercised: true",
        "YAMCS TC command path execution: true",
    ]:
        require_contains(stage619, marker, RUNTIME_DRIVERS["stage6.19"])

    print("Runtime driver evidence markers present: true")


def validate_stage620_doc() -> None:
    text = read_text(DOC)

    for marker in EXPECTED_DOC_TERMS:
        require_contains(text, marker, DOC)

    for marker in [
        "Housekeeping telemetry",
        "Ping command path",
        "Event / warning telemetry",
    ]:
        require_contains(text, marker, DOC)

    print("Stage 6.20 evidence matrix documentation markers present: true")


def main() -> int:
    print("Stage 6.20 final integration evidence matrix")
    print(f"Repository root: {REPO_ROOT}")

    validate_required_files()
    validate_generated_mdb()
    validate_contract_and_srdb()
    validate_stage_evidence_markers()
    validate_driver_markers()
    validate_stage620_doc()

    print("\nEvidence matrix rows validated: true")
    print("OrbitFabric telemetry row eps.obc.bus_voltage_mv -> TM(3,25) -> TM_3_25_HK: true")
    print("OrbitFabric command row ping -> TC(17,1) -> TM(1,1)/TM(17,2)/TM(1,7): true")
    print("OrbitFabric event row eps.voltage_out_of_bounds -> OF_EVENT_VOLTAGE_OUT_OF_BOUNDS=0x5001 -> TM(5,3): true")
    print("Generated flight contract evidence present: true")
    print("Generated SRDB/YAMCS MDB evidence present: true")
    print("OpenOBSW runtime evidence references present: true")
    print("OpenSVF observed path evidence references present: true")
    print("YAMCS observed path evidence references present: true")
    print("Production mission integration claim: false")
    print("Hardware target execution claim: false")
    print("Renode or STM32 execution claim: false")
    print("Production FDIR claim: false")
    print("Production commanding authorization/security claim: false")
    print("Broader OpenOBSW/OpenSVF integration claim: false")
    print("Stage 6.20 final integration evidence matrix: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
