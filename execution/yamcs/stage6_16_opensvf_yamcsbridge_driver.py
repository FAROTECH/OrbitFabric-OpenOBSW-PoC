#!/usr/bin/env python3
"""Stage 6.16 driver using the real OpenSVF YamcsBridge."""

from __future__ import annotations

import argparse
import importlib.util
import inspect
import struct
import sys
import time
from pathlib import Path
from typing import Any


DEFAULT_OPENSVF_ROOT = Path("/workspace/opensvf")

HOST = "127.0.0.1"
TM_PORT = 10015
TC_PORT = 10025
EVENT_ID_VALUE = 0x5001


class Stage616StoreStub:
    """Strict store stub for standalone YamcsBridge TM-path probing.

    Stage 6.16 exercises only the real YamcsBridge TM TCP path. No OpenSVF
    campaign state or TC/store interaction is expected in this stage. If the
    bridge unexpectedly touches the store, the probe must fail instead of
    silently masking that dependency.
    """

    def __getattr__(self, name: str):
        raise RuntimeError(
            "Unexpected store access in Stage 6.16 YamcsBridge TM-only probe: "
            f"{name}"
        )


def build_tm_packet(
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


def packet_sequence(cycles: int) -> list[tuple[str, bytes]]:
    sequence = 1
    packets: list[tuple[str, bytes]] = []

    for _ in range(cycles):
        packets.append(
            (
                "TM(3,25)",
                build_tm_packet(3, 25, b"\x0b\xb8", seq=sequence),
            )
        )
        sequence += 1

        packets.append(
            (
                "TM(5,3)",
                build_tm_packet(
                    5,
                    3,
                    struct.pack(">H", EVENT_ID_VALUE),
                    seq=sequence,
                ),
            )
        )
        sequence += 1

    return packets


def load_yamcs_bridge(bridge_path: Path) -> type[Any]:
    if not bridge_path.is_file():
        raise RuntimeError(f"YamcsBridge implementation not found: {bridge_path}")

    opensvf_src = bridge_path.parents[2]
    if str(opensvf_src) not in sys.path:
        sys.path.insert(0, str(opensvf_src))
        print(
            f"[stage6.16 driver] added OpenSVF src to sys.path: {opensvf_src}",
            flush=True,
        )

    spec = importlib.util.spec_from_file_location("stage6_16_yamcs_bridge", bridge_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load YamcsBridge module spec from: {bridge_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    bridge_cls = getattr(module, "YamcsBridge", None)
    if bridge_cls is None:
        raise RuntimeError(f"Module does not define YamcsBridge: {bridge_path}")

    return bridge_cls


def instantiate_bridge(
    bridge_cls: type[Any],
    *,
    host: str,
    tm_port: int,
    tc_port: int,
) -> Any:
    signature = inspect.signature(bridge_cls)
    kwargs: dict[str, Any] = {}

    for name, parameter in signature.parameters.items():
        if name == "self":
            continue

        if name == "store":
            kwargs[name] = Stage616StoreStub()
        elif name in {"host", "tm_host"}:
            kwargs[name] = host
        elif name == "tc_host":
            kwargs[name] = "0.0.0.0"
        elif name in {"tm_port", "port"}:
            kwargs[name] = tm_port
        elif name == "tc_port":
            kwargs[name] = tc_port
        elif parameter.default is inspect._empty:
            raise RuntimeError(
                "Unsupported YamcsBridge constructor signature; "
                f"required parameter without mapping: {name}; "
                f"signature={signature}"
            )

    print(
        f"[stage6.16 driver] instantiate YamcsBridge with kwargs={kwargs}",
        flush=True,
    )
    return bridge_cls(**kwargs)


def call_lifecycle(bridge: Any, method_names: list[str]) -> bool:
    for method_name in method_names:
        method = getattr(bridge, method_name, None)
        if callable(method):
            print(f"[stage6.16 driver] calling bridge.{method_name}()", flush=True)
            method()
            return True
    return False


def send_packet_with_retry(
    bridge: Any,
    name: str,
    packet: bytes,
    *,
    timeout: float,
) -> None:
    send_tm = getattr(bridge, "send_tm", None)
    if not callable(send_tm):
        raise RuntimeError("YamcsBridge object does not expose send_tm(packet)")

    deadline = time.monotonic() + timeout
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            send_tm(packet)
            print(
                f"[stage6.16 driver] sent {name} "
                f"len={len(packet)} hex={packet.hex()}",
                flush=True,
            )
            return
        except Exception as exc:
            last_error = exc
            print(
                f"[stage6.16 driver] send retry for {name}: {exc}",
                flush=True,
            )
            time.sleep(0.5)

    raise RuntimeError(f"Could not send {name} through YamcsBridge: {last_error}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 6.16 OpenSVF YamcsBridge driver")
    parser.add_argument("--opensvf-root", default=str(DEFAULT_OPENSVF_ROOT))
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--tm-port", type=int, default=TM_PORT)
    parser.add_argument("--tc-port", type=int, default=TC_PORT)
    parser.add_argument("--cycles", type=int, default=20)
    parser.add_argument("--delay", type=float, default=0.25)
    parser.add_argument("--send-timeout", type=float, default=90.0)
    parser.add_argument("--linger", type=float, default=12.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    opensvf_root = Path(args.opensvf_root).resolve()
    bridge_path = opensvf_root / "src" / "svf" / "ground" / "yamcs_bridge.py"

    print(f"[stage6.16 driver] OpenSVF root: {opensvf_root}", flush=True)
    print(f"[stage6.16 driver] YamcsBridge path: {bridge_path}", flush=True)

    bridge_cls = load_yamcs_bridge(bridge_path)
    bridge = instantiate_bridge(
        bridge_cls,
        host=args.host,
        tm_port=args.tm_port,
        tc_port=args.tc_port,
    )

    started = call_lifecycle(bridge, ["start", "open"])
    if not started:
        raise RuntimeError("YamcsBridge object does not expose start() or open()")

    try:
        sent_count = 0
        for name, packet in packet_sequence(args.cycles):
            send_packet_with_retry(
                bridge,
                name,
                packet,
                timeout=args.send_timeout if sent_count == 0 else 5.0,
            )
            sent_count += 1
            time.sleep(args.delay)

        print(
            f"[stage6.16 driver] sent_count={sent_count}; keeping bridge alive",
            flush=True,
        )
        time.sleep(args.linger)
    finally:
        call_lifecycle(bridge, ["stop", "close", "shutdown"])

    print("[stage6.16 driver] done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
