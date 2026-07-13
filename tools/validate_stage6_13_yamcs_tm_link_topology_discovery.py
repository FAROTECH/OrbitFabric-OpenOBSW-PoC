#!/usr/bin/env python3
"""Validate Stage 6.13 YAMCS TM link topology discovery."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, NoReturn

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
OPENSVF_ROOT = Path(
    os.environ.get("OPENSVF_ROOT", str(REPO_ROOT / "../opensvf"))
).resolve()

OPENSVF_REQUIREMENTS = OPENSVF_ROOT / "REQUIREMENTS.md"
OPENSVF_BRIDGE = OPENSVF_ROOT / "src" / "svf" / "ground" / "yamcs_bridge.py"
OPENSVF_BRIDGE_TEST = OPENSVF_ROOT / "tests" / "integration" / "test_yamcs_bridge.py"
OPENSVF_YAMCS_CONFIG = OPENSVF_ROOT / "yamcs" / "etc" / "yamcs.opensvf.yaml"

POC_YAMCS_CONFIG = REPO_ROOT / "execution" / "yamcs" / "etc" / "yamcs.opensvf.yaml"
DOC_PATH = REPO_ROOT / "docs" / "stage6_13_yamcs_tm_link_topology_discovery.md"


EXPECTED_TM_LINK = {
    "class": "org.yamcs.tctm.TcpTmDataLink",
    "host": "127.0.0.1",
    "port": 10015,
    "stream": "tm_realtime",
    "packetPreprocessorClassName": "org.yamcs.pus.PusPacketPreprocessor",
}

EXPECTED_TC_LINK = {
    "class": "org.yamcs.tctm.UdpTcDataLink",
    "host": "127.0.0.1",
    "port": 10025,
    "stream": "tc_realtime",
}


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


def validate_expected_link(
    link: dict[str, Any],
    expected_values: dict[str, Any],
    label: str,
) -> None:
    for key, expected in expected_values.items():
        if link.get(key) != expected:
            fail(f"Unexpected {label} {key}: {link.get(key)}")


def validate_expected_tm_link(link: dict[str, Any], label: str) -> None:
    validate_expected_link(link, EXPECTED_TM_LINK, label)

    args = link.get("packetPreprocessorArgs")
    if not isinstance(args, dict) or args.get("useLocalGenerationTime") is not True:
        fail(f"{label} must set useLocalGenerationTime: true")


def validate_expected_tc_link(link: dict[str, Any], label: str) -> None:
    validate_expected_link(link, EXPECTED_TC_LINK, label)


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


def validate_opensvf_yamcs_config() -> None:
    config = load_yaml(OPENSVF_YAMCS_CONFIG)

    tm_link = get_link(config, "tm-in", OPENSVF_YAMCS_CONFIG)
    tc_link = get_link(config, "tc-out", OPENSVF_YAMCS_CONFIG)

    validate_expected_tm_link(tm_link, "OpenSVF tm-in")
    validate_expected_tc_link(tc_link, "OpenSVF tc-out")


def validate_poc_yamcs_config() -> None:
    config = load_yaml(POC_YAMCS_CONFIG)

    tm_link = get_link(config, "tm-in", POC_YAMCS_CONFIG)
    tc_link = get_link(config, "tc-out", POC_YAMCS_CONFIG)

    validate_expected_tm_link(tm_link, "PoC tm-in")
    validate_expected_tc_link(tc_link, "PoC tc-out")


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
    opensvf_present = OPENSVF_ROOT.is_dir()

    if opensvf_present:
        validate_opensvf_requirements()
        validate_opensvf_bridge_implementation()
        validate_opensvf_bridge_tests()
        validate_opensvf_yamcs_config()
    else:
        print(
            f"NOTICE: OpenSVF repo not found at {OPENSVF_ROOT} "
            "— skipping OpenSVF topology checks"
        )

    validate_poc_yamcs_config()
    validate_doc()

    link_state = fetch_optional_link_state()

    print("Stage 6.13 YAMCS TM link topology discovery")
    print(f"Repository root: {REPO_ROOT}")
    print(f"OpenSVF repository: {OPENSVF_ROOT}")
    print(f"OpenSVF topology checks observed: {str(opensvf_present).lower()}")
    print("OpenSVF YamcsBridge TM role: TCP server on 127.0.0.1:10015")
    print("YAMCS tm-in role: TcpTmDataLink client to 127.0.0.1:10015")
    print("TC role: YAMCS UdpTcDataLink sends to OpenSVF UDP server on 127.0.0.1:10025")
    print("PoC YAMCS config matches expected tm-in/tc-out topology: true")
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
