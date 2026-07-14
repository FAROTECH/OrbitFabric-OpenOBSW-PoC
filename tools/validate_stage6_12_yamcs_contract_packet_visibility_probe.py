#!/usr/bin/env python3
"""Validate Stage 6.12 YAMCS contract packet visibility probe readiness."""

from __future__ import annotations

import socket
import struct
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import NoReturn


REPO_ROOT = Path(__file__).resolve().parents[1]
MDB_PATH = REPO_ROOT / "execution" / "generated" / "poc_xtce_mdb.xml"
YAMCS_INSTANCE = REPO_ROOT / "execution" / "yamcs" / "etc" / "yamcs.opensvf.yaml"

XTCE_NS = {"xtce": "http://www.omg.org/spec/XTCE/20180204"}

TM_TCP_HOST = "127.0.0.1"
TM_TCP_PORT = 10015

HK_CONTAINER = "TM_3_25_HK"
EVENT_CONTAINER = "TM_5_3_Event"
HK_PARAMETER = "eps_obc_bus_voltage_mv"
EVENT_PARAMETER = "of_event_id"

EVENT_ID_VALUE = 0x5001


def fail(message: str) -> NoReturn:
    raise SystemExit(
        "Stage 6.12 YAMCS contract packet visibility probe: FAIL\n"
        f"{message}"
    )


def read_text(path: Path) -> str:
    if not path.is_file():
        fail(f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def build_representative_tm_packet(service: int, subservice: int, payload: bytes = b"") -> bytes:
    """Build a minimal representative CCSDS/PUS-C TM packet.

    Layout follows the current generated MDB:
    - byte 6: PUS version/spare
    - byte 7: PUS service
    - byte 8: PUS subservice
    - event ID starts at byte 11 / bit offset 88
    """
    secondary_header = bytes([0x20, service, subservice, 0x00, 0x00])
    data = secondary_header + payload
    packet_length = len(data) - 1

    primary_header = struct.pack(
        ">HHH",
        0x0801,      # representative TM APID 1
        0xC000,      # standalone packet
        packet_length,
    )
    return primary_header + data


def build_packets() -> tuple[bytes, bytes]:
    hk_packet = build_representative_tm_packet(3, 25)
    event_packet = build_representative_tm_packet(
        5,
        3,
        struct.pack(">H", EVENT_ID_VALUE),
    )
    return hk_packet, event_packet


def parse_mdb() -> ET.Element:
    text = read_text(MDB_PATH)
    try:
        return ET.fromstring(text)
    except ET.ParseError as exc:
        fail(f"Generated XTCE/MDB is not valid XML: {exc}")


def require_container(root: ET.Element, name: str) -> ET.Element:
    container = root.find(f".//xtce:SequenceContainer[@name='{name}']", XTCE_NS)
    if container is None:
        fail(f"Missing MDB container: {name}")
    return container


def require_parameter(root: ET.Element, name: str) -> ET.Element:
    parameter = root.find(f".//xtce:Parameter[@name='{name}']", XTCE_NS)
    if parameter is None:
        fail(f"Missing MDB parameter: {name}")
    return parameter


def require_restriction(container: ET.Element, parameter_ref: str, value: str) -> None:
    comparison = container.find(
        f".//xtce:Comparison[@parameterRef='{parameter_ref}']",
        XTCE_NS,
    )
    if comparison is None:
        fail(f"Missing restriction {parameter_ref} == {value}")

    if comparison.get("value") != value or comparison.get("comparisonOperator") != "==":
        fail(
            f"Unexpected restriction for {parameter_ref}: "
            f"{comparison.get('comparisonOperator')} {comparison.get('value')}"
        )


def require_fixed_offset(container: ET.Element, parameter_ref: str, expected_offset: str) -> None:
    entry = container.find(
        f".//xtce:ParameterRefEntry[@parameterRef='{parameter_ref}']",
        XTCE_NS,
    )
    if entry is None:
        fail(f"Missing parameter entry {parameter_ref}")

    fixed = entry.find(".//xtce:FixedValue", XTCE_NS)
    if fixed is None or fixed.text != expected_offset:
        fail(f"Unexpected bit offset for {parameter_ref}: {fixed.text if fixed is not None else None}")


def validate_mdb_contract() -> None:
    root = parse_mdb()

    pus = require_container(root, "PUS_Packet")
    hk = require_container(root, HK_CONTAINER)
    event = require_container(root, EVENT_CONTAINER)

    require_parameter(root, "pus_svc")
    require_parameter(root, "pus_subsvc")
    require_parameter(root, HK_PARAMETER)
    require_parameter(root, EVENT_PARAMETER)

    require_fixed_offset(pus, "pus_svc", "56")
    require_fixed_offset(pus, "pus_subsvc", "64")

    require_restriction(hk, "pus_svc", "3")
    require_restriction(hk, "pus_subsvc", "25")

    require_restriction(event, "pus_svc", "5")
    require_restriction(event, "pus_subsvc", "3")
    require_fixed_offset(event, EVENT_PARAMETER, "88")


def validate_yamcs_tm_input_boundary() -> None:
    text = read_text(YAMCS_INSTANCE)

    for marker in [
        "class: org.yamcs.tctm.TcpTmDataLink",
        "host: 127.0.0.1",
        "port: 10015",
        "stream: tm_realtime",
        "packetPreprocessorClassName: org.yamcs.pus.PusPacketPreprocessor",
    ]:
        if marker not in text:
            fail(f"Missing YAMCS TM input marker: {marker}")


def validate_packet_bytes() -> None:
    hk_packet, event_packet = build_packets()

    if hk_packet[7] != 3 or hk_packet[8] != 25:
        fail(f"Representative HK packet does not encode TM(3,25): {hk_packet.hex()}")

    if event_packet[7] != 5 or event_packet[8] != 3:
        fail(f"Representative event packet does not encode TM(5,3): {event_packet.hex()}")

    event_id = int.from_bytes(event_packet[11:13], byteorder="big")
    if event_id != EVENT_ID_VALUE:
        fail(f"Representative event packet does not encode event ID 0x5001: 0x{event_id:04x}")


def try_inject_packets() -> bool:
    hk_packet, event_packet = build_packets()

    try:
        with socket.create_connection((TM_TCP_HOST, TM_TCP_PORT), timeout=2.0) as sock:
            sock.sendall(hk_packet)
            sock.sendall(event_packet)
        return True
    except OSError:
        return False


def main() -> int:
    validate_mdb_contract()
    validate_yamcs_tm_input_boundary()
    validate_packet_bytes()

    injected = try_inject_packets()

    print("Stage 6.12 YAMCS contract packet visibility probe")
    print(f"Repository root: {REPO_ROOT}")
    print(f"Generated XTCE/MDB: {MDB_PATH.relative_to(REPO_ROOT)}")
    print("Representative TM packet: TM(3,25)")
    print("Representative event packet: TM(5,3)")
    print(f"Representative event ID: {EVENT_PARAMETER} = 0x{EVENT_ID_VALUE:04X}")
    print(f"YAMCS candidate TM input: TCP {TM_TCP_HOST}:{TM_TCP_PORT}")
    print(f"Packet injection attempted: {str(injected).lower()}")
    print("Live OpenSVF/YamcsBridge execution: false")
    print("Live OpenOBSW packet generation: false")
    print("Closed-loop runtime execution: false")
    print("Stage 6.12 YAMCS contract packet visibility probe: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
