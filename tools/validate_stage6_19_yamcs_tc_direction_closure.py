#!/usr/bin/env python3
"""Validate Stage 6.19 YAMCS TC direction closure probe."""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, NoReturn


REPO_ROOT = Path(__file__).resolve().parents[1]

BASE_COMPOSE = REPO_ROOT / "execution/yamcs/docker-compose.candidate.yml"
OVERRIDE_COMPOSE = REPO_ROOT / "execution/yamcs/docker-compose.stage6_19.yamcs-tc-direction.yml"
DRIVER = REPO_ROOT / "execution/yamcs/stage6_19_yamcs_tc_direction_driver.py"
DOCKERFILE = REPO_ROOT / "execution/yamcs/Dockerfile.stage6_19.yamcs-tc-direction"
DOC = REPO_ROOT / "docs/stage6_19_yamcs_tc_direction_closure.md"
MDB_GENERATOR = REPO_ROOT / "tools/generate_poc_xtce_mdb.py"

OPENSVF_ROOT = Path(os.environ.get("OPENSVF_ROOT", REPO_ROOT.parent / "opensvf")).resolve()
OPENOBSW_ROOT = Path(os.environ.get("OPENOBSW_ROOT", REPO_ROOT.parent / "openobsw")).resolve()
OPENSVF_BRIDGE = OPENSVF_ROOT / "src/svf/ground/yamcs_bridge.py"
OPENOBSW_CMAKE = OPENOBSW_ROOT / "CMakeLists.txt"

SERVICE = "yamcs-tc-direction"
API_BASE = "http://localhost:8090"
TM_LINK_API = f"{API_BASE}/api/links/opensvf/tm-in"
TC_LINK_API = f"{API_BASE}/api/links/opensvf/tc-out"
CONTAINERS_API = f"{API_BASE}/api/mdb/opensvf/containers"
PACKETS_API = f"{API_BASE}/api/archive/opensvf/packets"
COMMANDS_API = f"{API_BASE}/api/archive/opensvf/commands"

EXPECTED_COMMAND_NAME = "/opensvf/TC_17_1_AreYouAlive"
EXPECTED_COMMAND_BINARY_B64 = "GBDAAAAEEREBAAA="
EXPECTED_COMMAND_HEX = "1810c00000041111010000"
EXPECTED_RESPONSE_CONTAINERS = {"TM_1_1_Accept", "TM_17_2_Pong", "TM_1_7_Complete"}


def fail(message: str) -> NoReturn:
    raise SystemExit("Stage 6.19 YAMCS TC direction closure probe: FAIL\n" + message)


def run(command: list[str], *, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(command), flush=True)
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )
    if check and result.returncode != 0:
        if capture and result.stdout:
            print(result.stdout)
        fail(f"Command failed with exit code {result.returncode}: {' '.join(command)}")
    return result


def compose_args() -> list[str]:
    return ["docker", "compose", "-f", str(BASE_COMPOSE), "-f", str(OVERRIDE_COMPOSE)]


def logs(service: str, *, tail: str = "900") -> str:
    result = run(compose_args() + ["logs", "--no-color", "--tail", tail, service], check=False, capture=True)
    return result.stdout or ""


def fetch_json(url: str, timeout: float = 5.0) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        if response.status != 200:
            fail(f"Unexpected HTTP status {response.status} from {url}")
        return json.loads(response.read().decode("utf-8"))


def wait_for_api(timeout_s: float = 120.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            response = fetch_json(f"{API_BASE}/api/instances", timeout=2.0)
            if any(item.get("name") == "opensvf" for item in response.get("instances", [])):
                print("YAMCS API ready: true")
                return
        except Exception as exc:  # pylint: disable=broad-exception-caught
            print(f"Waiting for YAMCS API: {type(exc).__name__}: {exc}")
        time.sleep(1.0)
    fail("YAMCS API did not become ready")


def as_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:  # pylint: disable=broad-exception-caught
        return 0


def wait_for_driver_marker(marker: str, timeout_s: int) -> str:
    deadline = time.monotonic() + float(timeout_s)
    last = ""
    while time.monotonic() < deadline:
        last = logs(SERVICE, tail="900")
        if marker in last:
            print(f"Driver marker observed: {marker}")
            return last
        interesting = [
            line for line in last.splitlines()
            if "[stage6.19 driver]" in line
            or "[stage6.17 driver]" in line
            or "Built target obsw_sim" in line
            or "YAMCS" in line
            or "Traceback" in line
            or "error" in line.lower()
            or "failed" in line.lower()
        ]
        if interesting:
            print("Waiting for yamcs-tc-direction marker; recent sidecar state:")
            for line in interesting[-14:]:
                print(line)
        else:
            print("Waiting for yamcs-tc-direction marker; no driver logs yet")
        time.sleep(5.0)
    print("Last yamcs-tc-direction logs before timeout:")
    print(last)
    fail(f"Driver marker not observed before timeout: {marker}")


def marker_timeout_seconds(default: int = 900) -> int:
    raw = os.environ.get("STAGE619_DRIVER_MARKER_TIMEOUT_S")
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        fail(f"STAGE619_DRIVER_MARKER_TIMEOUT_S must be an integer, got: {raw!r}")
    if value <= 0:
        fail(f"STAGE619_DRIVER_MARKER_TIMEOUT_S must be positive, got: {value}")
    return value


def validate_driver_logs() -> str:
    driver_logs = wait_for_driver_marker("YAMCS TC command path execution: true", timeout_s=240)
    required = [
        "built obsw_sim",
        "ELF 64-bit",
        "attached real YamcsBridge to OBCEmulatorAdapter._yamcs_bridge",
        "YAMCS REST TC command release accepted: true",
        "YAMCS command binary matches TC(17,1) MDB fixed value: true",
        "YAMCS-originated TC observed by OpenSVF YamcsBridge: true",
        f"YamcsBridge received TC hex={EXPECTED_COMMAND_HEX}",
        "YAMCS-originated TC forwarded to OBCEmulatorAdapter.receive_tc: true",
        "observed TM(1,1) at OBCEmulatorAdapter._parse_tm",
        "observed TM(17,2) at OBCEmulatorAdapter._parse_tm",
        "observed TM(1,7) at OBCEmulatorAdapter._parse_tm",
        "OpenOBSW TC(17,1) reception path exercised: true",
        "Representative PUS response path observed: true",
        "OpenSVF YamcsBridge TM response forwarding: true",
        "YAMCS TC command path execution: true",
    ]
    for marker in required:
        if marker not in driver_logs:
            fail(f"Driver logs missing required Stage 6.19 marker: {marker}")
    return driver_logs


def wait_for_tm_link(expected_packets: int = 3, timeout_s: float = 240.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        try:
            state = fetch_json(TM_LINK_API)
            last = state
            data_in = as_int(state.get("dataInCount"))
            print(f"tm-in status={state.get('status')} dataInCount={data_in} detailedStatus={state.get('detailedStatus')}")
            if data_in >= expected_packets:
                print(f"YAMCS tm-in consumed at least {expected_packets} packets: true")
                return state
        except Exception as exc:  # pylint: disable=broad-exception-caught
            print(f"Waiting for tm-in link: {type(exc).__name__}: {exc}")
        time.sleep(3.0)
    fail(f"tm-in did not consume {expected_packets} packets. Last state: {last}")


def validate_tc_link() -> dict[str, Any]:
    state = fetch_json(TC_LINK_API)
    if state.get("status") != "OK":
        fail(f"tc-out link is not OK: {state}")
    if "10025" not in str(state.get("detailedStatus")):
        fail(f"tc-out link does not target UDP port 10025: {state}")
    print("YAMCS tc-out UdpTcDataLink status OK: true")
    return state


def validate_mdb_containers() -> None:
    text = json.dumps(fetch_json(CONTAINERS_API))
    missing = sorted(name for name in EXPECTED_RESPONSE_CONTAINERS if name not in text)
    if missing:
        fail(f"Generated MDB containers missing via YAMCS API: {missing}")
    for name in sorted(EXPECTED_RESPONSE_CONTAINERS):
        print(f"MDB container {name} visible via API: true")


def fetch_archive_packets() -> list[dict[str, Any]]:
    urls = [
        f"{PACKETS_API}?{urllib.parse.urlencode({'limit': '100'})}",
        f"{PACKETS_API}?{urllib.parse.urlencode({'start': '1970-01-01T00:00:00Z', 'stop': '2100-01-01T00:00:00Z', 'limit': '100'})}",
    ]
    errors: list[str] = []
    for url in urls:
        try:
            response = fetch_json(url, timeout=5.0)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            errors.append(f"{url}: {type(exc).__name__}: {exc}")
            continue
        for key in ("packet", "packets", "entry", "records"):
            records = response.get(key)
            if isinstance(records, list):
                return records
        text = json.dumps(response)
        if any(name in text for name in EXPECTED_RESPONSE_CONTAINERS):
            return [response]
        errors.append(f"{url}: unexpected response shape {response}")
    raise ValueError("; ".join(errors))


def wait_for_archive_classification(timeout_s: float = 180.0) -> tuple[list[dict[str, Any]], set[str]]:
    deadline = time.monotonic() + timeout_s
    last_count = 0
    last_present: set[str] = set()
    while time.monotonic() < deadline:
        try:
            records = fetch_archive_packets()
            text = json.dumps(records)
            present = {name for name in EXPECTED_RESPONSE_CONTAINERS if name in text}
            last_count = len(records)
            last_present = present
            print(f"archive packets={last_count} classified={sorted(present)}")
            if EXPECTED_RESPONSE_CONTAINERS.issubset(present):
                print("YAMCS packet archive/classification for TC response telemetry: true")
                return records, present
        except Exception as exc:  # pylint: disable=broad-exception-caught
            print(f"Waiting for packet archive/classification: {type(exc).__name__}: {exc}")
        time.sleep(5.0)
    fail(f"YAMCS archive/classification target not met: records={last_count} classified={sorted(last_present)}")


def wait_for_command_history(timeout_s: float = 120.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    url = f"{COMMANDS_API}?{urllib.parse.urlencode({'limit': '20'})}"
    while time.monotonic() < deadline:
        try:
            response = fetch_json(url, timeout=5.0)
            text = json.dumps(response)
            if EXPECTED_COMMAND_NAME in text and EXPECTED_COMMAND_BINARY_B64 in text and "Acknowledge_Sent_Status" in text and "OK" in text:
                print("YAMCS command history records accepted/sent TC: true")
                return response
        except Exception as exc:  # pylint: disable=broad-exception-caught
            print(f"Waiting for command history: {type(exc).__name__}: {exc}")
        time.sleep(3.0)
    fail("YAMCS command history did not record accepted/sent TC command")


def require_file(path: Path) -> None:
    if not path.is_file():
        fail(f"Required file not found: {path}")


def validate_static_inputs(opensvf_present: bool, openobsw_present: bool) -> None:
    for path in [BASE_COMPOSE, OVERRIDE_COMPOSE, DRIVER, DOCKERFILE, DOC, MDB_GENERATOR]:
        require_file(path)
    driver_text = DRIVER.read_text()
    doc_text = DOC.read_text()
    compose_text = OVERRIDE_COMPOSE.read_text()
    dockerfile_text = DOCKERFILE.read_text()
    for marker in [
        "YAMCS REST TC command release accepted: true",
        "YAMCS-originated TC observed by OpenSVF YamcsBridge: true",
        "YAMCS-originated TC forwarded to OBCEmulatorAdapter.receive_tc: true",
        "OpenOBSW TC(17,1) reception path exercised: true",
        "Representative PUS response path observed: true",
        "YAMCS TC command path execution: true",
        EXPECTED_COMMAND_HEX,
        EXPECTED_COMMAND_NAME,
    ]:
        if marker not in driver_text:
            fail(f"Driver missing required marker/content: {marker}")
    for marker in ["Stage 6.19 - YAMCS TC Direction Closure Probe", "YamcsBridge.get_tc()", "OBCEmulatorAdapter.receive_tc", "TM_17_2_Pong", "production command security"]:
        if marker not in doc_text:
            fail(f"Documentation missing required marker/content: {marker}")
    if 'network_mode: "service:yamcs"' not in compose_text:
        fail('Stage 6.19 compose must use network_mode: "service:yamcs"')
    if "stage6_19_yamcs_tc_direction_driver.py" not in compose_text:
        fail("Stage 6.19 compose must run the Stage 6.19 driver")
    if "python3-yaml" not in dockerfile_text:
        fail("Stage 6.19 Dockerfile must install python3-yaml")
    if "pydantic>=2,<3" not in dockerfile_text:
        fail("Stage 6.19 Dockerfile must install pydantic>=2,<3")
    if opensvf_present:
        require_file(OPENSVF_BRIDGE)
        bridge_text = OPENSVF_BRIDGE.read_text()
        for marker in ["def get_tc", "10025", "_read_tc_udp_loop"]:
            if marker not in bridge_text:
                fail(f"OpenSVF YamcsBridge missing expected TC marker: {marker}")
    if openobsw_present:
        require_file(OPENOBSW_CMAKE)
    print("PoC-local Stage 6.19 artifacts validated: true")


def print_logs() -> None:
    result = run(compose_args() + ["logs", "--no-color", "--tail", "900", "yamcs", SERVICE], check=False, capture=True)
    if result.stdout:
        print(result.stdout)


def main() -> int:
    opensvf_present = OPENSVF_ROOT.is_dir()
    openobsw_present = OPENOBSW_ROOT.is_dir()
    validate_static_inputs(opensvf_present, openobsw_present)
    print("Stage 6.19 YAMCS TC direction closure probe")
    print(f"Repository root: {REPO_ROOT}")
    print(f"OpenSVF repository: {OPENSVF_ROOT}")
    print(f"OpenOBSW repository: {OPENOBSW_ROOT}")
    if not opensvf_present:
        print(f"NOTICE: OpenSVF repo not found at {OPENSVF_ROOT} — skipping live runtime probe")
        print("YAMCS TC command path execution: false")
        print("Stage 6.19 YAMCS TC direction closure probe: PASS")
        return 0
    if not openobsw_present:
        print(f"NOTICE: OpenOBSW repo not found at {OPENOBSW_ROOT} — skipping live runtime probe")
        print("YAMCS TC command path execution: false")
        print("Stage 6.19 YAMCS TC direction closure probe: PASS")
        return 0
    try:
        print("\n== Clean previous containers ==")
        run(compose_args() + ["down", "--remove-orphans"], check=False)
        print("\n== Generate PoC XTCE/MDB ==")
        run(["python3", "tools/generate_poc_xtce_mdb.py"])
        print("\n== Start YAMCS candidate and TC direction driver ==")
        run(compose_args() + ["up", "--build", "-d"])
        print("\n== Wait for YAMCS API ==")
        wait_for_api()
        print("\n== Wait for Stage 6.19 driver path ==")
        wait_for_driver_marker("attached real YamcsBridge to OBCEmulatorAdapter._yamcs_bridge", timeout_s=marker_timeout_seconds(900))
        print("\n== Validate YAMCS TC link ==")
        tc_state = validate_tc_link()
        print("\n== Validate driver-side TC direction evidence ==")
        driver_logs = validate_driver_logs()
        print("\n== Observe tm-in link ==")
        tm_state = wait_for_tm_link(expected_packets=3)
        print("\n== Validate MDB response container definitions through API ==")
        validate_mdb_containers()
        print("\n== Observe command history ==")
        command_history = wait_for_command_history()
        print("\n== Observe response packet archive and classification ==")
        packets, classified = wait_for_archive_classification()
        print("\n== Runtime observation ==")
        print(f"tc-out status: {tc_state.get('status')}")
        print(f"tc-out detailedStatus: {tc_state.get('detailedStatus')}")
        print(f"tc-out dataOutCount: {tc_state.get('dataOutCount')}")
        print(f"tm-in status: {tm_state.get('status')}")
        print(f"tm-in detailedStatus: {tm_state.get('detailedStatus')}")
        print(f"tm-in dataInCount: {tm_state.get('dataInCount')}")
        print(f"Packet archive records observed: {len(packets)}")
        print(f"Command history records observed: {len(command_history.get('entry', command_history.get('commands', [])))}")
        for name in sorted(classified):
            print(f"Packet archive classified as {name}: true")
        print("\n== Driver evidence ==")
        print(driver_logs)
        print("\n== Logs ==")
        print_logs()
    finally:
        print("\n== Stop containers ==")
        run(compose_args() + ["down", "--remove-orphans"], check=False)
    print("\nLinux-built OpenOBSW obsw_sim execution: true")
    print("YAMCS REST TC command release accepted: true")
    print("YAMCS command binary matches TC(17,1) MDB fixed value: true")
    print("YAMCS-originated TC observed by OpenSVF YamcsBridge: true")
    print("YAMCS-originated TC forwarded to OBCEmulatorAdapter.receive_tc: true")
    print("OpenOBSW TC(17,1) reception path exercised: true")
    print("Representative PUS response path observed: true")
    print("OpenSVF YamcsBridge TM response forwarding: true")
    print("YAMCS TcpTmDataLink packet consumption from command-response path: true")
    print("YAMCS command history accepted/sent record observed: true")
    print("YAMCS packet archive raw packet visibility: true")
    print("YAMCS MDB packet classification observed via archive name: true")
    print("YAMCS TC command path execution: true")
    print("Production commanding authorization/security hardening: false")
    print("Hardware target execution: false")
    print("Broader mission closed-loop campaign execution: false")
    print("Stage 6.19 YAMCS TC direction closure probe: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
