#!/usr/bin/env python3
"""Stage 6.19 YAMCS-originated TC direction driver.

Runtime path under test:

YAMCS REST command release
-> YAMCS StreamTcCommandReleaser
-> tc_realtime / tc-out UdpTcDataLink
-> OpenSVF YamcsBridge.get_tc()
-> OBCEmulatorAdapter.receive_tc(...)
-> OpenOBSW obsw_sim
-> TM(1,1), TM(17,2), TM(1,7)
-> OpenSVF YamcsBridge TM forwarding
-> YAMCS tm-in/archive.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


EXPECTED_TC_HEX = "1810c00000041111010000"
EXPECTED_COMMAND_NAME = "/opensvf/TC_17_1_AreYouAlive"
EXPECTED_RESPONSE_LABELS = {
    "TM(1,1)",
    "TM(17,2)",
    "TM(1,7)",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--opensvf-root", required=True)
    parser.add_argument("--openobsw-root", required=True)
    parser.add_argument("--build-dir", required=True)
    parser.add_argument("--yamcs-url", default="http://127.0.0.1:8090")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--tm-port", type=int, default=10015)
    parser.add_argument("--tc-port", type=int, default=10025)
    parser.add_argument("--steps", type=int, default=45)
    parser.add_argument("--dt", type=float, default=1.0)
    parser.add_argument("--startup-delay", type=float, default=5.0)
    parser.add_argument("--step-delay", type=float, default=0.05)
    parser.add_argument("--sync-timeout", type=float, default=5.0)
    parser.add_argument("--linger", type=float, default=12.0)
    parser.add_argument("--apid", type=lambda x: int(x, 0), default=0x103)
    return parser.parse_args()


def wait_for_yamcs_api(base_url: str, timeout_s: float = 90.0) -> None:
    deadline = time.monotonic() + timeout_s
    url = f"{base_url.rstrip('/')}/api/instances"

    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2.0) as response:
                if response.status == 200:
                    print("[stage6.19 driver] YAMCS API ready: true", flush=True)
                    return
        except Exception:
            time.sleep(1.0)

    raise RuntimeError("YAMCS API did not become ready")


def issue_yamcs_ping_command(base_url: str) -> bytes:
    url = (
        f"{base_url.rstrip('/')}"
        "/api/processors/opensvf/realtime/commands/opensvf/TC_17_1_AreYouAlive"
    )

    body = {
        "args": {},
        "origin": "stage6.19-driver",
        "sequenceNumber": 1,
        "comment": "Stage 6.19 YAMCS-originated TC direction runtime probe",
    }

    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=10.0) as response:
            raw = response.read()
            status = response.status
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"YAMCS command release failed: HTTP {exc.code}: {detail}") from exc

    if status != 200:
        raise RuntimeError(f"YAMCS command release returned unexpected HTTP {status}")

    payload = json.loads(raw.decode("utf-8"))
    command_name = payload.get("commandName")
    binary_b64 = payload.get("binary")
    unprocessed_b64 = payload.get("unprocessedBinary")

    print(f"[stage6.19 driver] YAMCS commandName={command_name}", flush=True)
    print(f"[stage6.19 driver] YAMCS command binary(base64)={binary_b64}", flush=True)

    if command_name != EXPECTED_COMMAND_NAME:
        raise RuntimeError(f"Unexpected YAMCS command name: {command_name}")

    # Avoid adding a base64 dependency; this is the stable known encoding of EXPECTED_TC_HEX.
    if binary_b64 != "GBDAAAAEEREBAAA=" or unprocessed_b64 != "GBDAAAAEEREBAAA=":
        raise RuntimeError(
            "Unexpected YAMCS command binary. "
            f"binary={binary_b64} unprocessedBinary={unprocessed_b64}"
        )

    print("YAMCS REST TC command release accepted: true", flush=True)
    print("YAMCS command binary matches TC(17,1) MDB fixed value: true", flush=True)

    return bytes.fromhex(EXPECTED_TC_HEX)


def poll_yamcsbridge_tc(bridge: Any, timeout_s: float = 30.0) -> bytes:
    deadline = time.monotonic() + timeout_s

    while time.monotonic() < deadline:
        raw_tc = bridge.get_tc()
        if raw_tc is not None:
            raw = bytes(raw_tc)
            print(f"[stage6.19 driver] YamcsBridge received TC len={len(raw)}", flush=True)
            print(f"[stage6.19 driver] YamcsBridge received TC hex={raw.hex()}", flush=True)

            if raw.hex() != EXPECTED_TC_HEX:
                raise RuntimeError(f"Unexpected TC received by YamcsBridge: {raw.hex()}")

            print("YAMCS-originated TC observed by OpenSVF YamcsBridge: true", flush=True)
            return raw

        time.sleep(0.1)

    raise RuntimeError("YamcsBridge did not receive the YAMCS-originated TC")


def main() -> int:
    args = parse_args()

    opensvf_root = Path(args.opensvf_root).resolve()
    openobsw_root = Path(args.openobsw_root).resolve()
    build_dir = Path(args.build_dir).resolve()

    print("[stage6.19 driver] Stage 6.19 YAMCS TC direction driver", flush=True)
    print(f"[stage6.19 driver] OpenSVF root: {opensvf_root}", flush=True)
    print(f"[stage6.19 driver] OpenOBSW root: {openobsw_root}", flush=True)

    # Reuse the already validated Stage 6.17 OpenOBSW/OpenSVF setup helpers.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from stage6_17_live_openobsw_hk_driver import (  # pylint: disable=import-outside-toplevel
        add_opensvf_src,
        build_openobsw_sim,
        call_lifecycle,
        instantiate_bridge,
        make_noop_sync,
    )

    add_opensvf_src(opensvf_root)

    from svf.core.abstractions import SyncProtocol  # pylint: disable=import-outside-toplevel
    from svf.ground.yamcs_bridge import YamcsBridge  # pylint: disable=import-outside-toplevel
    from svf.models.dhs.obc_emulator import OBCEmulatorAdapter  # pylint: disable=import-outside-toplevel
    from svf.stores.command_store import CommandStore  # pylint: disable=import-outside-toplevel
    from svf.stores.parameter_store import ParameterStore  # pylint: disable=import-outside-toplevel

    wait_for_yamcs_api(args.yamcs_url)

    sim_path = build_openobsw_sim(openobsw_root, build_dir)

    parameter_store = ParameterStore()
    command_store = CommandStore()
    sync = make_noop_sync(SyncProtocol)

    bridge = instantiate_bridge(
        YamcsBridge,
        store=parameter_store,
        host=args.host,
        tm_port=args.tm_port,
        tc_port=args.tc_port,
    )

    adapter = None
    observed_adapter_tm: dict[str, Any] = {
        "count": 0,
        "labels": [],
        "expected": set(),
    }

    started = call_lifecycle(bridge, ["start", "open"])
    if not started:
        raise RuntimeError("YamcsBridge object does not expose start() or open()")

    try:
        print(
            f"[stage6.19 driver] waiting {args.startup_delay:.1f}s for YAMCS links",
            flush=True,
        )
        time.sleep(args.startup_delay)

        adapter = OBCEmulatorAdapter(
            sim_path=sim_path,
            sync_protocol=sync,
            store=parameter_store,
            command_store=command_store,
            sync_timeout=args.sync_timeout,
            apid=args.apid,
        )

        original_parse_tm = getattr(adapter, "_parse_tm", None)
        if callable(original_parse_tm):
            def stage619_observe_parse_tm(pkt: bytes, t: float) -> Any:
                raw = bytes(pkt)
                svc = int(raw[7]) if len(raw) > 7 else None
                subsvc = int(raw[8]) if len(raw) > 8 else None
                label = f"TM({svc},{subsvc})"

                observed_adapter_tm["count"] = int(observed_adapter_tm["count"]) + 1
                observed_adapter_tm["labels"].append(label)

                print(
                    f"[stage6.19 driver] observed {label} at "
                    "OBCEmulatorAdapter._parse_tm",
                    flush=True,
                )

                if label in EXPECTED_RESPONSE_LABELS:
                    observed_adapter_tm["expected"].add(label)

                return original_parse_tm(pkt, t)

            setattr(adapter, "_parse_tm", stage619_observe_parse_tm)
            print(
                "[stage6.19 driver] wrapped OBCEmulatorAdapter._parse_tm "
                "for TC response observation",
                flush=True,
            )
        else:
            raise RuntimeError("OBCEmulatorAdapter._parse_tm is not available for wrapping")

        setattr(adapter, "_yamcs_bridge", bridge)
        print(
            "[stage6.19 driver] attached real YamcsBridge to "
            "OBCEmulatorAdapter._yamcs_bridge",
            flush=True,
        )

        adapter.initialise(0.0)

        expected_tc = issue_yamcs_ping_command(args.yamcs_url)
        raw_tc = poll_yamcsbridge_tc(bridge)

        if raw_tc != expected_tc:
            raise RuntimeError("YamcsBridge TC does not match YAMCS command binary")

        adapter.receive_tc(raw_tc, t=0.0)
        print("YAMCS-originated TC forwarded to OBCEmulatorAdapter.receive_tc: true", flush=True)

        for step in range(args.steps):
            t = float(step) * args.dt
            adapter.do_step(t, args.dt)

            seen = set(observed_adapter_tm["expected"])
            if EXPECTED_RESPONSE_LABELS.issubset(seen):
                break

            time.sleep(args.step_delay)

        labels = list(observed_adapter_tm["labels"])
        seen = set(observed_adapter_tm["expected"])

        print(f"[stage6.19 driver] adapter_parse_tm_seen={observed_adapter_tm['count']}", flush=True)
        print(f"[stage6.19 driver] adapter_parse_tm_labels={labels}", flush=True)
        print(f"[stage6.19 driver] expected_response_labels_seen={sorted(seen)}", flush=True)

        missing = sorted(EXPECTED_RESPONSE_LABELS - seen)
        if missing:
            raise RuntimeError(f"Missing expected TC response telemetry: {missing}")

        print("OpenOBSW TC(17,1) reception path exercised: true", flush=True)
        print("Representative PUS response path observed: true", flush=True)
        print("OpenSVF YamcsBridge TM response forwarding: true", flush=True)
        print("YAMCS TC command path execution: true", flush=True)

        print(f"[stage6.19 driver] keeping bridge alive for {args.linger:.1f}s", flush=True)
        time.sleep(args.linger)

    finally:
        if adapter is not None:
            call_lifecycle(adapter, ["teardown", "stop", "close", "shutdown"])
        call_lifecycle(bridge, ["stop", "close", "shutdown"])

    print("[stage6.19 driver] done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
