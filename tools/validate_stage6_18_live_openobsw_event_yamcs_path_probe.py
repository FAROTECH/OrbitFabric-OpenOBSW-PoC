#!/usr/bin/env python3
"""Validate Stage 6.18 live OpenOBSW event to YAMCS path probe."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, NoReturn


REPO_ROOT = Path(__file__).resolve().parents[1]

OPENSVF_ROOT = Path(os.environ.get("OPENSVF_ROOT", str(REPO_ROOT / "../opensvf"))).resolve()
OPENOBSW_ROOT = Path(os.environ.get("OPENOBSW_ROOT", str(REPO_ROOT / "../openobsw"))).resolve()

OPENSVF_BRIDGE = OPENSVF_ROOT / "src" / "svf" / "ground" / "yamcs_bridge.py"
OPENOBSW_CMAKE = OPENOBSW_ROOT / "CMakeLists.txt"
OPENOBSW_SIM_MAIN = OPENOBSW_ROOT / "sim" / "main.c"
OPENOBSW_SRDB = OPENOBSW_ROOT / "srdb" / "pyproject.toml"

BASE_COMPOSE = REPO_ROOT / "execution" / "yamcs" / "docker-compose.candidate.yml"
OVERRIDE_COMPOSE = REPO_ROOT / "execution" / "yamcs" / "docker-compose.stage6_18.live-openobsw-event.yml"
DRIVER = REPO_ROOT / "execution" / "yamcs" / "stage6_18_live_openobsw_event_driver.py"
DOC_PATH = REPO_ROOT / "docs" / "stage6_18_live_openobsw_event_yamcs_path_probe.md"

API_ROOT = "http://localhost:8090/api/"
TM_LINK_API = "http://localhost:8090/api/links/opensvf/tm-in"
PACKETS_API = "http://localhost:8090/api/archive/opensvf/packets"
CONTAINERS_API = "http://localhost:8090/api/mdb/opensvf/containers"

EXPECTED_EVENT_CONTAINER = "TM_5_3_Event"


def fail(message: str) -> NoReturn:
    raise SystemExit(
        "Stage 6.18 live OpenOBSW event to YAMCS path probe: FAIL\n"
        f"{message}"
    )


def run(args: list[str], *, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=REPO_ROOT,
        check=check,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )


def docker_compose_args() -> list[str]:
    return ["docker", "compose", "-f", str(BASE_COMPOSE), "-f", str(OVERRIDE_COMPOSE)]


def require_file(path: Path) -> None:
    if not path.is_file():
        fail(f"Required file not found: {path}")


def require_contains(path: Path, markers: list[str]) -> None:
    require_file(path)
    text = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in text:
            fail(f"Missing marker in {path}: {marker}")


def validate_static_inputs(opensvf_present: bool, openobsw_present: bool) -> None:
    sidecar_dockerfile = OVERRIDE_COMPOSE.parent / "Dockerfile.stage6_18.live-openobsw-event"

    require_file(BASE_COMPOSE)
    require_file(OVERRIDE_COMPOSE)
    require_file(sidecar_dockerfile)
    require_file(DRIVER)
    require_file(DOC_PATH)

    require_contains(
        OVERRIDE_COMPOSE,
        [
            "live-openobsw-event",
            "orbitfabric-stage6-18-live-openobsw-event:local",
            "Dockerfile.stage6_18.live-openobsw-event",
            'network_mode: "service:yamcs"',
            "${OPENSVF_ROOT:-../../../opensvf}:/workspace/opensvf:ro",
            "${OPENOBSW_ROOT:-../../../openobsw}:/workspace/openobsw:ro",
            "runtime/build tooling already present in cached image ==",
            "/workspace/openobsw/srdb",
            "stage6_18_live_openobsw_event_driver.py",
        ],
    )

    require_contains(
        sidecar_dockerfile,
        [
            "FROM ubuntu:24.04",
            "apt-get install -y --no-install-recommends",
            "build-essential",
            "cmake",
            "git",
            "file",
            "python3",
            "python3-pip",
            "python3-venv",
            "ca-certificates",
        ],
    )

    require_contains(
        DRIVER,
        [
            "build_openobsw_sim",
            "OBSW_ENABLE_ORBITFABRIC_CONTRACT",
            "ORBITFABRIC_CONTRACT_DIR",
            "build_orbitfabric_event_tc",
            "raw[17:19]",
            "OBCEmulatorAdapter",
            "YamcsBridge",
            'setattr(adapter, "_yamcs_bridge", bridge)',
            "_parse_tm",
            "TM(5,3)",
            "Live OpenOBSW TM(5,3) observed by OBCEmulatorAdapter: true",
            "OpenOBSW TM(5,3) event_id raw[17:19] = 0x5001: true",
            "TC(8,1) OrbitFabric event trigger injected into OpenOBSW: true",
        ],
    )

    require_contains(
        DOC_PATH,
        [
            "Stage 6.18 - Live OpenOBSW Event to YAMCS Path Probe",
            "Linux-built OpenOBSW obsw_sim",
            "OBCEmulatorAdapter pipe mode",
            "real OpenSVF YamcsBridge",
            "YAMCS packet archive",
            "TM_5_3_Event",
            "Live OpenOBSW TM(5,3) packet layout",
            "raw[17:19]",
            "bit offset is therefore `136`",
            "bit offset 88",
            "Optional sibling repository behavior",
            "missing optional sibling repository must not produce a `Required file not found` failure",
            "does not claim",
            "YAMCS TC command path execution",
        ],
    )

    if opensvf_present:
        require_contains(OPENSVF_BRIDGE, ["class YamcsBridge", "send_tm", "TM_PORT = 10015", "TC_PORT = 10025"])

    if openobsw_present:
        require_file(OPENOBSW_CMAKE)
        require_file(OPENOBSW_SIM_MAIN)
        require_file(OPENOBSW_SRDB)
        require_contains(
            OPENOBSW_SIM_MAIN,
            [
                "OBSW_ENABLE_ORBITFABRIC_CONTRACT",
                "OF_EVENT_VOLTAGE_OUT_OF_BOUNDS",
                "OBSW_OF_S8_FN_REPORT_VOLTAGE_OUT_OF_BOUNDS",
                "obsw_s5_report",
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
    for idx in range(1, 121):
        try:
            fetch_json(API_ROOT)
            print(f"YAMCS API ready after {idx}s")
            return
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, json.JSONDecodeError, ValueError):
            time.sleep(1.0)
    fail("YAMCS API did not become ready")


def wait_for_tm_link() -> dict[str, Any]:
    last: dict[str, Any] | None = None
    for idx in range(1, 91):
        try:
            state = fetch_json(TM_LINK_API)
            last = state
            status = state.get("status")
            detailed = state.get("detailedStatus")
            data_in = int(state.get("dataInCount", "0"))
            data_out = int(state.get("dataOutCount", "0"))
            print(
                f"[{idx:02d}] tm-in status={status} dataInCount={data_in} "
                f"dataOutCount={data_out} detailedStatus={detailed}"
            )
            if data_in >= 1:
                if status != "OK":
                    print(
                        "tm-in has consumed live packets but is no longer connected; "
                        "accepting dataInCount evidence for Stage 6.18"
                    )
                return state
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"[{idx:02d}] tm-in API unavailable: {exc}")
        time.sleep(2.0)
    fail(f"tm-in link did not consume live OpenOBSW TM; last={last}")


def container_matches(container: dict[str, Any], expected_name: str) -> bool:
    for key in ("name", "qualifiedName"):
        value = container.get(key)
        if isinstance(value, str) and value.endswith(expected_name):
            return True
    return False


def validate_mdb_container(expected_name: str) -> dict[str, Any]:
    query = urllib.parse.urlencode({"q": expected_name, "limit": "20"})
    response = fetch_json(f"{CONTAINERS_API}?{query}")
    containers = response.get("containers")
    if not isinstance(containers, list):
        fail(f"Unexpected containers response for {expected_name}: {response}")
    matches = [c for c in containers if isinstance(c, dict) and container_matches(c, expected_name)]
    if not matches:
        fail(f"MDB container not visible through API: {expected_name}")
    return matches[0]


def packet_name(packet_record: dict[str, Any]) -> str:
    for key in ("name", "qualifiedName", "packetName", "containerName"):
        value = packet_record.get(key)
        if isinstance(value, str):
            return value

    packet_id = packet_record.get("id")
    if isinstance(packet_id, dict):
        for key in ("name", "qualifiedName", "packetName", "containerName"):
            value = packet_id.get(key)
            if isinstance(value, str):
                return value

    if isinstance(packet_id, str):
        return packet_id

    return ""


def packet_link(packet_record: dict[str, Any]) -> str:
    for key in ("link", "linkName", "dataLinkName"):
        value = packet_record.get(key)
        if isinstance(value, str):
            return value
    return ""


def decode_packet(packet_record: dict[str, Any]) -> bytes | None:
    candidates: list[Any] = []
    for key in ("packet", "data", "binary", "body"):
        if key in packet_record:
            candidates.append(packet_record.get(key))
    packet = packet_record.get("packet")
    if isinstance(packet, dict):
        for key in ("binary", "data", "body"):
            if key in packet:
                candidates.append(packet.get(key))
    for value in candidates:
        if isinstance(value, str):
            try:
                return base64.b64decode(value, validate=True)
            except Exception:
                try:
                    return bytes.fromhex(value)
                except Exception:
                    continue
        if isinstance(value, list) and all(isinstance(x, int) for x in value):
            try:
                return bytes(value)
            except Exception:
                continue
    return None


def fetch_archive_packets() -> list[dict[str, Any]]:
    query = urllib.parse.urlencode({"limit": "100", "order": "desc"})
    response = fetch_json(f"{PACKETS_API}?{query}")
    packets = response.get("packets")
    if isinstance(packets, list):
        return [p for p in packets if isinstance(p, dict)]
    if isinstance(response.get("packet"), list):
        return [p for p in response["packet"] if isinstance(p, dict)]
    raise ValueError(f"Unexpected packet archive response: {response}")


def is_tm_5_3_event(raw: bytes) -> bool:
    return (
        len(raw) >= 19
        and raw[7] == 5
        and raw[8] == 3
        and raw[17] == 0x50
        and raw[18] == 0x01
    )


def wait_for_live_event_archive_and_classification() -> tuple[list[dict[str, Any]], bool]:
    last_count = 0
    last_names: list[str] = []
    last_links: list[str] = []
    last_sizes: list[int] = []
    for idx in range(1, 91):
        try:
            packets = fetch_archive_packets()
            last_count = len(packets)
            last_names = [packet_name(packet) for packet in packets]
            last_links = [packet_link(packet) for packet in packets]
            decoded = [raw for packet in packets for raw in [decode_packet(packet)] if raw is not None]
            last_sizes = [len(raw) for raw in decoded]
            live_event_archived = any(is_tm_5_3_event(raw) for raw in decoded)
            event_classified = any(EXPECTED_EVENT_CONTAINER in packet_name(packet) for packet in packets)
            print(
                f"[{idx:02d}] archive packets={last_count} live_event_archived={live_event_archived} "
                f"event_classified={event_classified} names={last_names} links={last_links} sizes={last_sizes}"
            )
            if live_event_archived and event_classified:
                return packets, event_classified
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"[{idx:02d}] packet archive API unavailable: {exc}")
        time.sleep(2.0)
    fail(
        "YAMCS live OpenOBSW event archive/classification target not met: "
        f"last_count={last_count} last_names={last_names} last_links={last_links} last_sizes={last_sizes}"
    )


def service_logs(service: str, tail: str = "520") -> str:
    result = run(docker_compose_args() + ["logs", "--no-color", "--tail", tail, service], check=False, capture=True)
    return result.stdout or ""



def marker_timeout_seconds(default_s: int) -> int:
    """Return the driver-marker timeout, allowing slow cold-Docker overrides."""
    value = os.environ.get("STAGE618_DRIVER_MARKER_TIMEOUT_S")
    if value is None:
        return default_s
    try:
        parsed = int(value)
    except ValueError:
        fail(f"Invalid STAGE618_DRIVER_MARKER_TIMEOUT_S value: {value!r}")
    if parsed <= 0:
        fail(f"STAGE618_DRIVER_MARKER_TIMEOUT_S must be positive, got: {parsed}")
    return parsed


def wait_for_driver_marker(marker: str, *, timeout_s: int = 420) -> str:
    """Wait until the live OpenOBSW sidecar reaches a required log marker."""
    deadline = time.monotonic() + float(timeout_s)
    last_logs = ""

    while time.monotonic() < deadline:
        last_logs = service_logs("live-openobsw-event", tail="620")

        if marker in last_logs:
            print(f"Driver marker observed: {marker}")
            return last_logs

        interesting = [
            line
            for line in last_logs.splitlines()
            if (
                "Stage 6.18 sidecar" in line
                or "[stage6.18 driver]" in line
                or "Built target obsw_sim" in line
                or "error" in line.lower()
                or "traceback" in line.lower()
                or "failed" in line.lower()
            )
        ]

        if interesting:
            print("Waiting for live-openobsw-event driver marker; recent sidecar state:")
            for line in interesting[-12:]:
                print(line)
        else:
            print("Waiting for live-openobsw-event driver marker; no driver logs yet")

        time.sleep(5.0)

    print("Last live-openobsw-event logs before timeout:")
    print(last_logs)
    fail(f"Driver marker not observed before timeout: {marker}")


def validate_driver_observed_live_event() -> str:
    wait_for_driver_marker(
        "Live OpenOBSW TM(5,3) observed by OBCEmulatorAdapter: true",
        timeout_s=60,
    )

    logs = service_logs("live-openobsw-event", tail="620")

    required = [
        "built obsw_sim",
        "ELF 64-bit",
        "attached real YamcsBridge to OBCEmulatorAdapter._yamcs_bridge",
        "observed live OpenOBSW TM(5,3)",
        "Live OpenOBSW TM(5,3) observed by OBCEmulatorAdapter: true",
        "OpenOBSW TM(5,3) event_id raw[17:19] = 0x5001: true",
        "TC(8,1) OrbitFabric event trigger injected into OpenOBSW: true",
        "OpenSVF YamcsBridge attached through OBCEmulatorAdapter TM hook: true",
    ]

    for marker in required:
        if marker not in logs:
            fail(f"Driver logs missing required live OpenOBSW marker: {marker}")

    return logs


def print_logs() -> None:
    result = run(
        docker_compose_args() + ["logs", "--no-color", "--tail", "620", "yamcs", "live-openobsw-event"],
        check=False,
        capture=True,
    )
    if result.stdout:
        print(result.stdout)


def main() -> int:
    opensvf_present = OPENSVF_ROOT.is_dir()
    openobsw_present = OPENOBSW_ROOT.is_dir()

    validate_static_inputs(opensvf_present, openobsw_present)

    print("Stage 6.18 live OpenOBSW event to YAMCS path probe")
    print(f"Repository root: {REPO_ROOT}")
    print(f"OpenSVF repository: {OPENSVF_ROOT}")
    print(f"OpenOBSW repository: {OPENOBSW_ROOT}")

    if not opensvf_present:
        print(f"NOTICE: OpenSVF repo not found at {OPENSVF_ROOT} — skipping live OpenSVF/OpenOBSW/YAMCS runtime probe")
        print("Live OpenOBSW-generated TM observed: false")
        print("Stage 6.18 live OpenOBSW event to YAMCS path probe: PASS")
        return 0

    if not openobsw_present:
        print(f"NOTICE: OpenOBSW repo not found at {OPENOBSW_ROOT} — skipping live OpenOBSW/YAMCS runtime probe")
        print("Live OpenOBSW-generated TM observed: false")
        print("Stage 6.18 live OpenOBSW event to YAMCS path probe: PASS")
        return 0

    print(f"Base compose: {BASE_COMPOSE.relative_to(REPO_ROOT)}")
    print(f"Override compose: {OVERRIDE_COMPOSE.relative_to(REPO_ROOT)}")
    print(f"Driver: {DRIVER.relative_to(REPO_ROOT)}")
    print(f"OpenSVF YamcsBridge: {OPENSVF_BRIDGE}")
    print(f"OpenOBSW CMake project: {OPENOBSW_CMAKE}")

    try:
        print("\n== Clean previous containers ==")
        run(docker_compose_args() + ["down", "--remove-orphans"], check=False)
        print("\n== Generate PoC XTCE/MDB ==")
        run(["python3", "tools/generate_poc_xtce_mdb.py"])
        print("\n== Start YAMCS candidate and live OpenOBSW event driver ==")
        run(docker_compose_args() + ["up", "--build", "-d"])
        print("\n== Wait for YAMCS API ==")
        wait_for_api()
        print("\n== Wait for live OpenOBSW driver to open YamcsBridge path ==")
        driver_marker_timeout_s = marker_timeout_seconds(420)
        print(
            "Driver marker timeout: "
            f"{driver_marker_timeout_s}s "
            "(set STAGE618_DRIVER_MARKER_TIMEOUT_S for slow cold-Docker runs)"
        )
        wait_for_driver_marker(
            "attached real YamcsBridge to OBCEmulatorAdapter._yamcs_bridge",
            timeout_s=driver_marker_timeout_s,
        )

        print("\n== Observe tm-in link ==")
        link_state = wait_for_tm_link()
        print("\n== Validate MDB container definitions through API ==")
        event_container = validate_mdb_container(EXPECTED_EVENT_CONTAINER)
        print(f"MDB container {EXPECTED_EVENT_CONTAINER}: {event_container.get('qualifiedName')}")
        print("\n== Observe live OpenOBSW packet archive and classification ==")
        packets, event_classified = wait_for_live_event_archive_and_classification()
        print("\n== Validate driver-side live OpenOBSW evidence ==")
        driver_logs = validate_driver_observed_live_event()
        print(driver_logs)
        print("\n== Runtime observation ==")
        print(f"tm-in status: {link_state.get('status')}")
        print(f"tm-in detailedStatus: {link_state.get('detailedStatus')}")
        print(f"tm-in dataInCount: {link_state.get('dataInCount')}")
        print(f"tm-in dataOutCount: {link_state.get('dataOutCount')}")
        print(f"Packet archive records observed: {len(packets)}")
        print(f"MDB container {EXPECTED_EVENT_CONTAINER} visible via API: true")
        print("Live OpenOBSW TM(5,3) raw packet archived: true")
        print(f"Packet archive classified as {EXPECTED_EVENT_CONTAINER}: {str(event_classified).lower()}")
        print("\n== Logs ==")
        print_logs()
    finally:
        print("\n== Stop containers ==")
        run(docker_compose_args() + ["down", "--remove-orphans"], check=False)

    print("\nLinux-built OpenOBSW obsw_sim execution: true")
    print("OpenSVF OBCEmulatorAdapter pipe-mode live TM observation: true")
    print("OpenSVF YamcsBridge attached through OBCEmulatorAdapter TM hook: true")
    print("YAMCS TcpTmDataLink packet consumption from live OpenOBSW path: true")
    print("YAMCS packet archive raw packet visibility: true")
    print("YAMCS MDB packet classification observed via archive name: true")
    print("YAMCS TC command path execution: false")
    print("Live OpenOBSW TM(5,3) event materialization: true")
    print("Production voltage-threshold fault trigger: false")
    print("Closed-loop runtime campaign execution: false")
    print("Stage 6.18 live OpenOBSW event to YAMCS path probe: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
