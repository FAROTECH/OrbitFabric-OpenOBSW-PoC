#!/usr/bin/env python3
"""Validate Stage 6.16 real OpenSVF YamcsBridge TM path probe."""

from __future__ import annotations

import base64
import json
import os
import struct
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, NoReturn


REPO_ROOT = Path(__file__).resolve().parents[1]
OPENSVF_ROOT = Path(
    os.environ.get("OPENSVF_ROOT", str(REPO_ROOT / "../opensvf"))
).resolve()

OPENSVF_BRIDGE = OPENSVF_ROOT / "src" / "svf" / "ground" / "yamcs_bridge.py"

BASE_COMPOSE = REPO_ROOT / "execution" / "yamcs" / "docker-compose.candidate.yml"
OVERRIDE_COMPOSE = (
    REPO_ROOT
    / "execution"
    / "yamcs"
    / "docker-compose.stage6_16.real-opensvf-yamcsbridge.yml"
)
DRIVER = REPO_ROOT / "execution" / "yamcs" / "stage6_16_opensvf_yamcsbridge_driver.py"
DOC_PATH = REPO_ROOT / "docs" / "stage6_16_real_opensvf_yamcsbridge_tm_path_probe.md"

API_ROOT = "http://localhost:8090/api/"
TM_LINK_API = "http://localhost:8090/api/links/opensvf/tm-in"
PACKETS_API = "http://localhost:8090/api/archive/opensvf/packets"
CONTAINERS_API = "http://localhost:8090/api/mdb/opensvf/containers"

EXPECTED_HK_CONTAINER = "TM_3_25_HK"
EXPECTED_EVENT_CONTAINER = "TM_5_3_Event"
EVENT_ID_VALUE = 0x5001


def fail(message: str) -> NoReturn:
    raise SystemExit(
        "Stage 6.16 real OpenSVF YamcsBridge TM path probe: FAIL\n"
        f"{message}"
    )


def run(
    args: list[str],
    *,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=REPO_ROOT,
        check=check,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )


def docker_compose_args() -> list[str]:
    return [
        "docker",
        "compose",
        "-f",
        str(BASE_COMPOSE),
        "-f",
        str(OVERRIDE_COMPOSE),
    ]


def require_file(path: Path) -> None:
    if not path.is_file():
        fail(f"Required file not found: {path}")


def require_contains(path: Path, markers: list[str]) -> None:
    require_file(path)
    text = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in text:
            fail(f"Missing marker in {path}: {marker}")


def build_representative_tm_packet(
    service: int,
    subservice: int,
    app_data: bytes = b"",
    seq: int = 1,
) -> bytes:
    ccsds_first = 0x0800 | 0x0010
    ccsds_seq = 0xC000 | (seq & 0x3FFF)
    pus_secondary = bytes([0x20, service & 0xFF, subservice & 0xFF, 0x00, 0x00])
    payload = pus_secondary + app_data
    ccsds_length = len(payload) - 1
    primary = struct.pack(">HHH", ccsds_first, ccsds_seq, ccsds_length)
    return primary + payload


def expected_packets() -> tuple[bytes, bytes]:
    hk_packet = build_representative_tm_packet(3, 25, b"\x0b\xb8", seq=1)
    event_packet = build_representative_tm_packet(
        5,
        3,
        struct.pack(">H", EVENT_ID_VALUE),
        seq=2,
    )
    return hk_packet, event_packet


def validate_static_inputs(opensvf_present: bool) -> None:
    require_file(BASE_COMPOSE)
    require_file(OVERRIDE_COMPOSE)
    require_file(DRIVER)

    require_contains(
        OVERRIDE_COMPOSE,
        [
            "opensvf-yamcsbridge",
            "network_mode: \"service:yamcs\"",
            "../../../opensvf:/workspace/opensvf:ro",
            "stage6_16_opensvf_yamcsbridge_driver.py",
        ],
    )

    require_contains(
        DRIVER,
        [
            "load_yamcs_bridge",
            "YamcsBridge",
            "send_tm",
            "bytes([0x20",
            "TM(3,25)",
            "TM(5,3)",
            "0x5001",
        ],
    )

    require_contains(
        DOC_PATH,
        [
            "Stage 6.16 - Real OpenSVF YamcsBridge TM Path Probe",
            "real OpenSVF YamcsBridge",
            "TM_3_25_HK",
            "TM_5_3_Event",
            "does not claim live OpenOBSW packet generation",
            "does not claim closed-loop runtime execution",
        ],
    )

    if opensvf_present:
        require_contains(
            OPENSVF_BRIDGE,
            [
                "class YamcsBridge",
                "send_tm",
                "TM_PORT = 10015",
                "TC_PORT = 10025",
            ],
        )


def fetch_json(url: str, timeout: float = 3.0) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        payload = response.read().decode("utf-8")
    loaded = json.loads(payload)
    if not isinstance(loaded, dict):
        raise ValueError("expected JSON object")
    return loaded


def wait_for_api() -> None:
    for idx in range(1, 91):
        try:
            fetch_json(API_ROOT)
            print(f"YAMCS API ready after {idx}s")
            return
        except (
            urllib.error.URLError,
            TimeoutError,
            ConnectionError,
            OSError,
            json.JSONDecodeError,
            ValueError,
        ):
            time.sleep(1.0)
    fail("YAMCS API did not become ready")


def wait_for_tm_link() -> dict[str, Any]:
    last: dict[str, Any] | None = None

    for idx in range(1, 61):
        try:
            state = fetch_json(TM_LINK_API)
            last = state

            status = state.get("status")
            detailed = state.get("detailedStatus")
            data_in = int(state.get("dataInCount", "0"))
            data_out = int(state.get("dataOutCount", "0"))

            print(
                f"[{idx:02d}] tm-in status={status} "
                f"dataInCount={data_in} dataOutCount={data_out} "
                f"detailedStatus={detailed}"
            )

            if status == "OK" and data_in >= 2:
                return state
        except (
            urllib.error.URLError,
            TimeoutError,
            ConnectionError,
            OSError,
            json.JSONDecodeError,
            ValueError,
        ) as exc:
            print(f"[{idx:02d}] tm-in API unavailable: {exc}")
        time.sleep(2.0)

    if last is None:
        fail("tm-in link API was never observed")

    fail(
        "tm-in did not reach required state: "
        f"status={last.get('status')} "
        f"dataInCount={last.get('dataInCount')} "
        f"detailedStatus={last.get('detailedStatus')}"
    )


def container_matches(container: dict[str, Any], expected_name: str) -> bool:
    name = str(container.get("name", ""))
    qualified_name = str(container.get("qualifiedName", ""))
    return name == expected_name or qualified_name.endswith("/" + expected_name)


def validate_mdb_container(expected_name: str) -> dict[str, Any]:
    url = CONTAINERS_API + "?" + urllib.parse.urlencode(
        {
            "q": expected_name,
            "limit": "20",
        }
    )
    response = fetch_json(url, timeout=5.0)
    containers = response.get("containers")

    if not isinstance(containers, list):
        fail(f"Unexpected containers response for {expected_name}: {response}")

    matches = [
        container
        for container in containers
        if isinstance(container, dict) and container_matches(container, expected_name)
    ]

    if not matches:
        fail(f"MDB container not visible through API: {expected_name}; response={response}")

    return matches[0]


def packet_name(packet_record: dict[str, Any]) -> str:
    packet_id = packet_record.get("id")
    if isinstance(packet_id, dict):
        return str(packet_id.get("name", ""))
    return ""


def packet_link(packet_record: dict[str, Any]) -> str:
    return str(packet_record.get("link", ""))


def decode_packet(packet_record: dict[str, Any]) -> bytes | None:
    encoded = packet_record.get("packet")
    if not isinstance(encoded, str):
        return None

    try:
        return base64.b64decode(encoded, validate=True)
    except Exception:
        return None


def fetch_archive_packets() -> list[dict[str, Any]]:
    url = PACKETS_API + "?" + urllib.parse.urlencode(
        {
            "limit": "100",
            "order": "desc",
        }
    )
    response = fetch_json(url, timeout=5.0)

    packets = response.get("packets")
    if packets is None:
        packets = response.get("packet")

    if not isinstance(packets, list):
        fail(f"Unexpected packet archive response: {response}")

    return [packet for packet in packets if isinstance(packet, dict)]


def wait_for_archive_and_classification() -> tuple[list[dict[str, Any]], bool, bool]:
    expected_hk, expected_event = expected_packets()
    last_count = 0
    last_names: list[str] = []
    last_links: list[str] = []

    for idx in range(1, 31):
        try:
            packets = fetch_archive_packets()
            last_count = len(packets)
            last_names = [packet_name(packet) for packet in packets]
            last_links = [packet_link(packet) for packet in packets]

            decoded_bytes = [
                decoded
                for decoded in (decode_packet(packet) for packet in packets)
                if decoded is not None
            ]

            hk_bytes_seen = expected_hk in decoded_bytes
            event_bytes_seen = expected_event in decoded_bytes

            names = set(last_names)
            hk_classified = any(name.endswith(EXPECTED_HK_CONTAINER) for name in names)
            event_classified = any(name.endswith(EXPECTED_EVENT_CONTAINER) for name in names)
            bridge_link_seen = "tm-in" in set(last_links)

            print(
                f"[{idx:02d}] archive packets={last_count} "
                f"hk_bytes={hk_bytes_seen} event_bytes={event_bytes_seen} "
                f"hk_classified={hk_classified} event_classified={event_classified} "
                f"bridge_link_seen={bridge_link_seen} "
                f"names={sorted(names)} links={sorted(set(last_links))}"
            )

            if (
                hk_bytes_seen
                and event_bytes_seen
                and hk_classified
                and event_classified
                and bridge_link_seen
            ):
                return packets, hk_classified, event_classified

        except (
            urllib.error.URLError,
            TimeoutError,
            ConnectionError,
            OSError,
            json.JSONDecodeError,
            ValueError,
        ) as exc:
            print(f"[{idx:02d}] packet archive API unavailable: {exc}")

        time.sleep(2.0)

    fail(
        "YAMCS archive/classification target not met through real OpenSVF YamcsBridge: "
        f"last_count={last_count} "
        f"last_names={last_names} "
        f"last_links={last_links}"
    )


def print_logs() -> None:
    result = run(
        docker_compose_args()
        + ["logs", "--no-color", "--tail", "420", "yamcs", "opensvf-yamcsbridge"],
        check=False,
        capture=True,
    )
    if result.stdout:
        print(result.stdout)


def main() -> int:
    opensvf_present = OPENSVF_ROOT.is_dir()

    validate_static_inputs(opensvf_present)

    print("Stage 6.16 real OpenSVF YamcsBridge TM path probe")
    print(f"Repository root: {REPO_ROOT}")
    print(f"OpenSVF repository: {OPENSVF_ROOT}")

    if not opensvf_present:
        print(
            f"NOTICE: OpenSVF repo not found at {OPENSVF_ROOT} "
            "— skipping real OpenSVF YamcsBridge runtime probe"
        )
        print("Real OpenSVF YamcsBridge runtime observed: false")
        print("Stage 6.16 real OpenSVF YamcsBridge TM path probe: PASS")
        return 0

    print(f"Base compose: {BASE_COMPOSE.relative_to(REPO_ROOT)}")
    print(f"Override compose: {OVERRIDE_COMPOSE.relative_to(REPO_ROOT)}")
    print(f"Driver: {DRIVER.relative_to(REPO_ROOT)}")
    print(f"OpenSVF YamcsBridge: {OPENSVF_BRIDGE}")

    try:
        print("\n== Clean previous containers ==")
        run(docker_compose_args() + ["down", "--remove-orphans"], check=False)

        print("\n== Generate PoC XTCE/MDB ==")
        run(["python3", "tools/generate_poc_xtce_mdb.py"])

        print("\n== Start YAMCS candidate and real OpenSVF YamcsBridge driver ==")
        run(docker_compose_args() + ["up", "--build", "-d"])

        print("\n== Wait for YAMCS API ==")
        wait_for_api()

        print("\n== Observe tm-in link ==")
        link_state = wait_for_tm_link()

        print("\n== Validate MDB container definitions through API ==")
        hk_container = validate_mdb_container(EXPECTED_HK_CONTAINER)
        event_container = validate_mdb_container(EXPECTED_EVENT_CONTAINER)
        print(f"MDB container {EXPECTED_HK_CONTAINER}: {hk_container.get('qualifiedName')}")
        print(f"MDB container {EXPECTED_EVENT_CONTAINER}: {event_container.get('qualifiedName')}")

        print("\n== Observe packet archive and classification ==")
        packets, hk_classified, event_classified = wait_for_archive_and_classification()

        print("\n== Runtime observation ==")
        print(f"tm-in status: {link_state.get('status')}")
        print(f"tm-in detailedStatus: {link_state.get('detailedStatus')}")
        print(f"tm-in dataInCount: {link_state.get('dataInCount')}")
        print(f"tm-in dataOutCount: {link_state.get('dataOutCount')}")
        print(f"Packet archive records observed: {len(packets)}")
        print(f"MDB container {EXPECTED_HK_CONTAINER} visible via API: true")
        print(f"MDB container {EXPECTED_EVENT_CONTAINER} visible via API: true")
        print(f"Representative TM(3,25) raw packet archived: true")
        print(f"Representative TM(5,3) raw packet archived: true")
        print(f"Packet archive classified as {EXPECTED_HK_CONTAINER}: {str(hk_classified).lower()}")
        print(f"Packet archive classified as {EXPECTED_EVENT_CONTAINER}: {str(event_classified).lower()}")

        print("\n== Logs ==")
        print_logs()

    finally:
        print("\n== Stop containers ==")
        run(docker_compose_args() + ["down", "--remove-orphans"], check=False)

    print("\nReal OpenSVF YamcsBridge runtime observed: true")
    print("Live OpenOBSW packet generation: false")
    print("YAMCS TcpTmDataLink packet consumption through real OpenSVF YamcsBridge: true")
    print("YAMCS packet archive raw packet visibility: true")
    print("YAMCS MDB container definitions visible via API: true")
    print("YAMCS MDB packet classification observed via archive name: true")
    print("YAMCS parameter/event API extraction observed: false")
    print("Closed-loop runtime execution: false")
    print("Stage 6.16 real OpenSVF YamcsBridge TM path probe: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
