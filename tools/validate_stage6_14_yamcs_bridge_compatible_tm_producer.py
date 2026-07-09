#!/usr/bin/env python3
"""Validate Stage 6.14 YAMCS bridge-compatible TM producer smoke."""

from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, NoReturn


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_COMPOSE = REPO_ROOT / "execution" / "yamcs" / "docker-compose.candidate.yml"
OVERRIDE_COMPOSE = (
    REPO_ROOT
    / "execution"
    / "yamcs"
    / "docker-compose.stage6_14.bridge-producer.yml"
)
PRODUCER = REPO_ROOT / "execution" / "yamcs" / "stage6_14_bridge_tm_producer.py"
DOC_PATH = REPO_ROOT / "docs" / "stage6_14_yamcs_bridge_compatible_tm_producer.md"

API_ROOT = "http://localhost:8090/api/"
TM_LINK_API = "http://localhost:8090/api/links/opensvf/tm-in"


def fail(message: str) -> NoReturn:
    raise SystemExit(
        "Stage 6.14 YAMCS bridge-compatible TM producer smoke: FAIL\n"
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


def validate_static_inputs() -> None:
    require_file(BASE_COMPOSE)
    require_file(OVERRIDE_COMPOSE)
    require_file(PRODUCER)

    require_contains(
        PRODUCER,
        [
            "server.bind((args.host, args.port))",
            "server.listen(1)",
            "server.accept()",
            "TM(3,25)",
            "TM(5,3)",
            "b\"\\x50\\x01\"",
            "conn.sendall(packet)",
        ],
    )

    require_contains(
        OVERRIDE_COMPOSE,
        [
            "tm-producer",
            "network_mode: \"service:yamcs\"",
            "stage6_14_bridge_tm_producer.py",
        ],
    )

    require_contains(
        DOC_PATH,
        [
            "Stage 6.14 - YAMCS Bridge-Compatible TM Producer Smoke",
            "tm-in status: OK",
            "dataInCount >= 2",
            "does not",
            "claim YAMCS MDB packet classification",
            "claim parameter/event extraction",
        ],
    )


def fetch_json(url: str, timeout: float = 2.0) -> dict[str, Any]:
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


def print_logs() -> None:
    result = run(
        docker_compose_args()
        + ["logs", "--no-color", "--tail", "260", "yamcs", "tm-producer"],
        check=False,
        capture=True,
    )
    if result.stdout:
        print(result.stdout)


def main() -> int:
    validate_static_inputs()

    print("Stage 6.14 YAMCS bridge-compatible TM producer smoke")
    print(f"Repository root: {REPO_ROOT}")
    print(f"Base compose: {BASE_COMPOSE.relative_to(REPO_ROOT)}")
    print(f"Override compose: {OVERRIDE_COMPOSE.relative_to(REPO_ROOT)}")
    print(f"Producer: {PRODUCER.relative_to(REPO_ROOT)}")

    try:
        print("\n== Clean previous containers ==")
        run(docker_compose_args() + ["down", "--remove-orphans"], check=False)

        print("\n== Generate PoC XTCE/MDB ==")
        run(["python3", "tools/generate_poc_xtce_mdb.py"])

        print("\n== Start YAMCS candidate and bridge-compatible TM producer ==")
        run(docker_compose_args() + ["up", "--build", "-d"])

        print("\n== Wait for YAMCS API ==")
        wait_for_api()

        print("\n== Observe tm-in link ==")
        state = wait_for_tm_link()

        print("\n== Runtime observation ==")
        print(f"tm-in status: {state.get('status')}")
        print(f"tm-in detailedStatus: {state.get('detailedStatus')}")
        print(f"tm-in dataInCount: {state.get('dataInCount')}")
        print(f"tm-in dataOutCount: {state.get('dataOutCount')}")

        print("\n== Logs ==")
        print_logs()

    finally:
        print("\n== Stop containers ==")
        run(docker_compose_args() + ["down", "--remove-orphans"], check=False)

    print("\nLive OpenSVF/YamcsBridge execution: false")
    print("Live OpenOBSW packet generation: false")
    print("YAMCS TcpTmDataLink packet consumption: true")
    print("YAMCS MDB classification observed: false")
    print("YAMCS parameter/event API extraction observed: false")
    print("Closed-loop runtime execution: false")
    print("Stage 6.14 YAMCS bridge-compatible TM producer smoke: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
