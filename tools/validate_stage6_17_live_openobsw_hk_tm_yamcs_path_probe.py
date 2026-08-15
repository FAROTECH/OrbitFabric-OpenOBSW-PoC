#!/usr/bin/env python3
"""Validate Stage 6.17 live OpenOBSW HK TM to YAMCS path probe."""

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
OVERRIDE_COMPOSE = REPO_ROOT / "execution" / "yamcs" / "docker-compose.stage6_17.live-openobsw-hk.yml"
DRIVER = REPO_ROOT / "execution" / "yamcs" / "stage6_17_live_openobsw_hk_driver.py"
DOC_PATH = REPO_ROOT / "docs" / "stage6_17_live_openobsw_hk_tm_yamcs_path_probe.md"

API_ROOT = "http://localhost:8090/api/"
TM_LINK_API = "http://localhost:8090/api/links/opensvf/tm-in"
PACKETS_API = "http://localhost:8090/api/archive/opensvf/packets"
CONTAINERS_API = "http://localhost:8090/api/mdb/opensvf/containers"

EXPECTED_HK_CONTAINER = "TM_3_25_HK"


def fail(message: str) -> NoReturn:
    raise SystemExit(
        "Stage 6.17 live OpenOBSW HK TM to YAMCS path probe: FAIL\n"
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
    sidecar_dockerfile = OVERRIDE_COMPOSE.parent / "Dockerfile.stage6_17.live-openobsw-hk"

    require_file(BASE_COMPOSE)
    require_file(OVERRIDE_COMPOSE)
    require_file(sidecar_dockerfile)
    require_file(DRIVER)
    require_file(DOC_PATH)

    require_contains(
        OVERRIDE_COMPOSE,
        [
            "live-openobsw-hk",
            "orbitfabric-stage6-17-live-openobsw-hk:local",
            "Dockerfile.stage6_17.live-openobsw-hk",
            'network_mode: "service:yamcs"',
            "${OPENSVF_ROOT:-../../../opensvf}:/workspace/opensvf:ro",
            "${OPENOBSW_ROOT:-../../../openobsw}:/workspace/openobsw:ro",
            "runtime/build tooling already present in cached image ==",
            "/workspace/openobsw/srdb",
            "stage6_17_live_openobsw_hk_driver.py",
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
            "OBCEmulatorAdapter",
            "YamcsBridge",
            'setattr(adapter, "_yamcs_bridge", bridge)',
            "_parse_tm",
            "TM(3,25)",
            "Live OpenOBSW TM(3,25) observed by OBCEmulatorAdapter: true",
        ],
    )

    require_contains(
        DOC_PATH,
        [
            "Stage 6.17 - Live OpenOBSW HK TM to YAMCS Path Probe",
            "Linux-built OpenOBSW obsw_sim",
            "OBCEmulatorAdapter pipe mode",
            "real OpenSVF YamcsBridge",
            "YAMCS packet archive",
            "TM_3_25_HK",
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
                        "accepting dataInCount evidence for Stage 6.17"
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


def is_tm_3_25(raw: bytes) -> bool:
    return len(raw) >= 17 and raw[7] == 3 and raw[8] == 25


def wait_for_live_hk_archive_and_classification() -> tuple[list[dict[str, Any]], bool]:
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
            live_hk_archived = any(is_tm_3_25(raw) for raw in decoded)
            hk_classified = any(EXPECTED_HK_CONTAINER in packet_name(packet) for packet in packets)
            print(
                f"[{idx:02d}] archive packets={last_count} live_hk_archived={live_hk_archived} "
                f"hk_classified={hk_classified} names={last_names} links={last_links} sizes={last_sizes}"
            )
            if live_hk_archived and hk_classified:
                return packets, hk_classified
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"[{idx:02d}] packet archive API unavailable: {exc}")
        time.sleep(2.0)
    fail(
        "YAMCS live OpenOBSW HK archive/classification target not met: "
        f"last_count={last_count} last_names={last_names} last_links={last_links} last_sizes={last_sizes}"
    )


def service_logs(service: str, tail: str = "520") -> str:
    result = run(docker_compose_args() + ["logs", "--no-color", "--tail", tail, service], check=False, capture=True)
    return result.stdout or ""



def marker_timeout_seconds(default_s: int) -> int:
    """Return the driver-marker timeout, allowing slow cold-Docker overrides."""
    value = os.environ.get("STAGE617_DRIVER_MARKER_TIMEOUT_S")
    if value is None:
        return default_s
    try:
        parsed = int(value)
    except ValueError:
        fail(f"Invalid STAGE617_DRIVER_MARKER_TIMEOUT_S value: {value!r}")
    if parsed <= 0:
        fail(f"STAGE617_DRIVER_MARKER_TIMEOUT_S must be positive, got: {parsed}")
    return parsed


def wait_for_driver_marker(marker: str, *, timeout_s: int = 420) -> str:
    """Wait until the live OpenOBSW sidecar reaches a required log marker."""
    deadline = time.monotonic() + float(timeout_s)
    last_logs = ""

    while time.monotonic() < deadline:
        last_logs = service_logs("live-openobsw-hk", tail="620")

        if marker in last_logs:
            print(f"Driver marker observed: {marker}")
            return last_logs

        interesting = [
            line
            for line in last_logs.splitlines()
            if (
                "Stage 6.17 sidecar" in line
                or "[stage6.17 driver]" in line
                or "Built target obsw_sim" in line
                or "error" in line.lower()
                or "traceback" in line.lower()
                or "failed" in line.lower()
            )
        ]

        if interesting:
            print("Waiting for live-openobsw-hk driver marker; recent sidecar state:")
            for line in interesting[-12:]:
                print(line)
        else:
            print("Waiting for live-openobsw-hk driver marker; no driver logs yet")

        time.sleep(5.0)

    print("Last live-openobsw-hk logs before timeout:")
    print(last_logs)
    fail(f"Driver marker not observed before timeout: {marker}")


def validate_driver_observed_live_hk() -> str:
    wait_for_driver_marker(
        "Live OpenOBSW TM(3,25) observed by OBCEmulatorAdapter: true",
        timeout_s=60,
    )

    logs = service_logs("live-openobsw-hk", tail="620")

    required = [
        "built obsw_sim",
        "ELF 64-bit",
        "attached real YamcsBridge to OBCEmulatorAdapter._yamcs_bridge",
        "observed live OpenOBSW TM(3,25)",
        "Live OpenOBSW TM(3,25) observed by OBCEmulatorAdapter: true",
        "OpenSVF YamcsBridge attached through OBCEmulatorAdapter TM hook: true",
    ]

    for marker in required:
        if marker not in logs:
            fail(f"Driver logs missing required live OpenOBSW marker: {marker}")

    return logs


def print_logs() -> None:
    result = run(
        docker_compose_args() + ["logs", "--no-color", "--tail", "620", "yamcs", "live-openobsw-hk"],
        check=False,
        capture=True,
    )
    if result.stdout:
        print(result.stdout)


def main() -> int:
    opensvf_present = OPENSVF_ROOT.is_dir()
    openobsw_present = OPENOBSW_ROOT.is_dir()

    validate_static_inputs(opensvf_present, openobsw_present)

    print("Stage 6.17 live OpenOBSW HK TM to YAMCS path probe")
    print(f"Repository root: {REPO_ROOT}")
    print(f"OpenSVF repository: {OPENSVF_ROOT}")
    print(f"OpenOBSW repository: {OPENOBSW_ROOT}")

    if not opensvf_present:
        print(f"NOTICE: OpenSVF repo not found at {OPENSVF_ROOT} — skipping live OpenSVF/OpenOBSW/YAMCS runtime probe")
        print("Live OpenOBSW-generated TM observed: false")
        print("Stage 6.17 live OpenOBSW HK TM to YAMCS path probe: PASS")
        return 0

    if not openobsw_present:
        print(f"NOTICE: OpenOBSW repo not found at {OPENOBSW_ROOT} — skipping live OpenOBSW/YAMCS runtime probe")
        print("Live OpenOBSW-generated TM observed: false")
        print("Stage 6.17 live OpenOBSW HK TM to YAMCS path probe: PASS")
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
        print("\n== Start YAMCS candidate and live OpenOBSW HK driver ==")
        run(docker_compose_args() + ["up", "--build", "-d"])
        print("\n== Wait for YAMCS API ==")
        wait_for_api()
        print("\n== Wait for live OpenOBSW driver to open YamcsBridge path ==")
        driver_marker_timeout_s = marker_timeout_seconds(420)
        print(
            "Driver marker timeout: "
            f"{driver_marker_timeout_s}s "
            "(set STAGE617_DRIVER_MARKER_TIMEOUT_S for slow cold-Docker runs)"
        )
        wait_for_driver_marker(
            "attached real YamcsBridge to OBCEmulatorAdapter._yamcs_bridge",
            timeout_s=driver_marker_timeout_s,
        )

        print("\n== Observe tm-in link ==")
        link_state = wait_for_tm_link()
        print("\n== Validate MDB container definitions through API ==")
        hk_container = validate_mdb_container(EXPECTED_HK_CONTAINER)
        print(f"MDB container {EXPECTED_HK_CONTAINER}: {hk_container.get('qualifiedName')}")
        print("\n== Observe live OpenOBSW packet archive and classification ==")
        packets, hk_classified = wait_for_live_hk_archive_and_classification()
        print("\n== Validate driver-side live OpenOBSW evidence ==")
        driver_logs = validate_driver_observed_live_hk()
        print(driver_logs)
        print("\n== Runtime observation ==")
        print(f"tm-in status: {link_state.get('status')}")
        print(f"tm-in detailedStatus: {link_state.get('detailedStatus')}")
        print(f"tm-in dataInCount: {link_state.get('dataInCount')}")
        print(f"tm-in dataOutCount: {link_state.get('dataOutCount')}")
        print(f"Packet archive records observed: {len(packets)}")
        print(f"MDB container {EXPECTED_HK_CONTAINER} visible via API: true")
        print("Live OpenOBSW TM(3,25) raw packet archived: true")
        print(f"Packet archive classified as {EXPECTED_HK_CONTAINER}: {str(hk_classified).lower()}")
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
    print("Live OpenOBSW event/fault generation: false")
    print("Closed-loop runtime campaign execution: false")
    print("Stage 6.17 live OpenOBSW HK TM to YAMCS path probe: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
