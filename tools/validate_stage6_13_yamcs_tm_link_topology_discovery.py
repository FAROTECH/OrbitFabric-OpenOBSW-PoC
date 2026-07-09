#!/usr/bin/env python3
"""Validate Stage 6.13 YAMCS TM link topology discovery."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, NoReturn

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
OPENSVF_ROOT = (REPO_ROOT / "../opensvf").resolve()

OPENSVF_REQUIREMENTS = OPENSVF_ROOT / "REQUIREMENTS.md"
OPENSVF_BRIDGE = OPENSVF_ROOT / "src" / "svf" / "ground" / "yamcs_bridge.py"
OPENSVF_BRIDGE_TEST = OPENSVF_ROOT / "tests" / "integration" / "test_yamcs_bridge.py"
OPENSVF_YAMCS_CONFIG = OPENSVF_ROOT / "yamcs" / "etc" / "yamcs.opensvf.yaml"

POC_YAMCS_CONFIG = REPO_ROOT / "execution" / "yamcs" / "etc" / "yamcs.opensvf.yaml"
DOC_PATH = REPO_ROOT / "docs" / "stage6_13_yamcs_tm_link_topology_discovery.md"


def fail(message: str) -> NoReturn:
    raise SystemExit(
        "Stage 6.13 YAMCS TM link topology discovery: FAIL\n"
        f"{message}"
    )


def read_text(path: Path) -> str:
    if not path.is_file():
        fail(f"Required file not found: {path}")
    return path.read_text(encoding="utf-8")


def require_contains(path: Path, markers: list[str]) -> None:
    text = read_text(path)
    for marker in markers:
        if marker not in text:
            fail(f"Missing marker in {path}: {marker}")


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        loaded = yaml.safe_load(read_text(path))
    except yaml.YAMLError as exc:
        fail(f"YAML parse failed for {path}: {exc}")

    if not isinstance(loaded, dict):
        fail(f"YAML root must be a mapping: {path}")
    return loaded


def get_link(config: dict[str, Any], name: str, path: Path) -> dict[str, Any]:
    links = config.get("dataLinks")
    if not isinstance(links, list):
        fail(f"{path} must define dataLinks")

    for link in links:
        if isinstance(link, dict) and link.get("name") == name:
            return link
    fail(f"{path} missing data link: {name}")


def validate_opensvf_requirements() -> None:
    require_contains(
        OPENSVF_REQUIREMENTS,
        [
            "SVF-DEV-133",
            "YamcsBridge",
            "TCP server on port 10015 for TM downlink",
            "UDP server on port 10025 for TC uplink",
            "SVF-DEV-134",
            "forward raw PUS TM packets",
            "SVF-DEV-135",
            "receive PUS TC packets from YAMCS via UDP",
            "SVF-DEV-138",
            "PusPacketPreprocessor",
            "useLocalGenerationTime=true",
        ],
    )


def validate_opensvf_bridge_implementation() -> None:
    require_contains(
        OPENSVF_BRIDGE,
        [
            "YAMCS connects TO SVF",
            "SVF is the TCP server for TM",
            "TM flow: SVF -> YAMCS via TCP (YAMCS connects as client to port 10015)",
            "TC flow: YAMCS -> SVF via UDP",
            "TM_PORT = 10015",
            "TC_PORT = 10025",
            'self._tm_server.bind(("127.0.0.1", self._tm_port))',
            "self._tm_server.listen(1)",
            "self._tm_conn, addr = self._tm_server.accept()",
            "self._tm_conn.sendall(packet)",
            'self._tc_server.bind(("0.0.0.0", self._tc_port))',
            "data, addr = self._tc_server.recvfrom(4096)",
        ],
    )


def validate_opensvf_bridge_tests() -> None:
    require_contains(
        OPENSVF_BRIDGE_TEST,
        [
            "test_bridge_accepts_yamcs_tm_connection",
            "test_bridge_sends_tm_to_yamcs",
            "test_bridge_receives_tc_from_yamcs",
            'tm_sock.connect(("127.0.0.1"',
            "bridge.send_tm(pkt)",
            "received == pkt",
            "tc_sock.sendto",
            "bridge.get_tc()",
        ],
    )


def validate_yamcs_configs() -> None:
    opensvf = load_yaml(OPENSVF_YAMCS_CONFIG)
    poc = load_yaml(POC_YAMCS_CONFIG)

    opensvf_tm = get_link(opensvf, "tm-in", OPENSVF_YAMCS_CONFIG)
    poc_tm = get_link(poc, "tm-in", POC_YAMCS_CONFIG)

    expected_tm = {
        "class": "org.yamcs.tctm.TcpTmDataLink",
        "host": "127.0.0.1",
        "port": 10015,
        "stream": "tm_realtime",
        "packetPreprocessorClassName": "org.yamcs.pus.PusPacketPreprocessor",
    }
    for key, expected in expected_tm.items():
        if opensvf_tm.get(key) != expected:
            fail(f"Unexpected OpenSVF tm-in {key}: {opensvf_tm.get(key)}")
        if poc_tm.get(key) != expected:
            fail(f"Unexpected PoC tm-in {key}: {poc_tm.get(key)}")

    for label, link in [("OpenSVF", opensvf_tm), ("PoC", poc_tm)]:
        args = link.get("packetPreprocessorArgs")
        if not isinstance(args, dict) or args.get("useLocalGenerationTime") is not True:
            fail(f"{label} tm-in must set useLocalGenerationTime: true")

    opensvf_tc = get_link(opensvf, "tc-out", OPENSVF_YAMCS_CONFIG)
    poc_tc = get_link(poc, "tc-out", POC_YAMCS_CONFIG)

    expected_tc = {
        "class": "org.yamcs.tctm.UdpTcDataLink",
        "host": "127.0.0.1",
        "port": 10025,
        "stream": "tc_realtime",
    }
    for key, expected in expected_tc.items():
        if opensvf_tc.get(key) != expected:
            fail(f"Unexpected OpenSVF tc-out {key}: {opensvf_tc.get(key)}")
        if poc_tc.get(key) != expected:
            fail(f"Unexpected PoC tc-out {key}: {poc_tc.get(key)}")


def validate_doc() -> None:
    require_contains(
        DOC_PATH,
        [
            "Stage 6.13 - YAMCS TM Link Topology Discovery",
            "YAMCS TcpTmDataLink",
            "TCP client",
            "YamcsBridge",
            "TCP server on 127.0.0.1:10015",
            "status: UNAVAIL",
            "dataInCount: 0",
            "claim YAMCS packet consumption",
            "claim MDB packet classification",
        ],
    )


def fetch_optional_link_state() -> dict[str, Any] | None:
    try:
        with urllib.request.urlopen(
            "http://localhost:8090/api/links/opensvf/tm-in",
            timeout=2.0,
        ) as response:
            payload = response.read().decode("utf-8")
    except (
        urllib.error.URLError,
        TimeoutError,
        ConnectionError,
        OSError,
    ):
        return None

    try:
        loaded = json.loads(payload)
    except json.JSONDecodeError:
        return None

    if not isinstance(loaded, dict):
        return None
    return loaded


def main() -> int:
    validate_opensvf_requirements()
    validate_opensvf_bridge_implementation()
    validate_opensvf_bridge_tests()
    validate_yamcs_configs()
    validate_doc()

    link_state = fetch_optional_link_state()

    print("Stage 6.13 YAMCS TM link topology discovery")
    print(f"Repository root: {REPO_ROOT}")
    print(f"OpenSVF repository: {OPENSVF_ROOT}")
    print("OpenSVF YamcsBridge TM role: TCP server on 127.0.0.1:10015")
    print("YAMCS tm-in role: TcpTmDataLink client to 127.0.0.1:10015")
    print("TC role: YAMCS UdpTcDataLink sends to OpenSVF UDP server on 127.0.0.1:10025")
    print("PoC YAMCS config mirrors OpenSVF tm-in/tc-out topology: true")
    if link_state is None:
        print("Runtime YAMCS link API observed: false")
    else:
        print("Runtime YAMCS link API observed: true")
        print(f"tm-in status: {link_state.get('status')}")
        print(f"tm-in detailedStatus: {link_state.get('detailedStatus')}")
        print(f"tm-in dataInCount: {link_state.get('dataInCount')}")
    print("Live OpenSVF/YamcsBridge execution: false")
    print("Live OpenOBSW packet generation: false")
    print("YAMCS packet consumption: false")
    print("YAMCS MDB classification observed: false")
    print("Closed-loop runtime execution: false")
    print("Stage 6.13 YAMCS TM link topology discovery: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
