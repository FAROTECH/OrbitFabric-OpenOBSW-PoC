#!/usr/bin/env python3
"""Stage 6.18 driver for live OpenOBSW event TM delivery into YAMCS."""

from __future__ import annotations

import argparse
import inspect
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


DEFAULT_OPENSVF_ROOT = Path("/workspace/opensvf")
DEFAULT_OPENOBSW_ROOT = Path("/workspace/openobsw")

HOST = "127.0.0.1"
TM_PORT = 10015
TC_PORT = 10025

OF_EVENT_VOLTAGE_OUT_OF_BOUNDS = 0x5001
OBSW_OF_S8_FN_REPORT_VOLTAGE_OUT_OF_BOUNDS = 0x5001
DEFAULT_ORBITFABRIC_CONTRACT_DIR = Path(
    "/workspace/poc/generated_artifacts/flight_software"
)


def run(
    args: list[str],
    *,
    cwd: Path | None = None,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    print(
        "[stage6.18 driver] run: "
        + " ".join(str(a) for a in args)
        + (f" cwd={cwd}" if cwd else ""),
        flush=True,
    )
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )


def add_opensvf_src(opensvf_root: Path) -> Path:
    opensvf_src = opensvf_root / "src"
    if not opensvf_src.is_dir():
        raise RuntimeError(f"OpenSVF src directory not found: {opensvf_src}")

    if str(opensvf_src) not in sys.path:
        sys.path.insert(0, str(opensvf_src))
        print(f"[stage6.18 driver] added OpenSVF src to sys.path: {opensvf_src}", flush=True)

    return opensvf_src


def build_openobsw_sim(openobsw_root: Path, build_dir: Path, contract_dir: Path) -> Path:
    if not openobsw_root.is_dir():
        raise RuntimeError(f"OpenOBSW root not found: {openobsw_root}")
    if not contract_dir.is_dir():
        raise RuntimeError(f"OrbitFabric contract directory not found: {contract_dir}")

    print(f"[stage6.18 driver] OpenOBSW root: {openobsw_root}", flush=True)
    print(f"[stage6.18 driver] OpenOBSW build dir: {build_dir}", flush=True)
    print(f"[stage6.18 driver] OrbitFabric contract dir: {contract_dir}", flush=True)

    run([
        "cmake", "-S", str(openobsw_root), "-B", str(build_dir),
        "-DCMAKE_BUILD_TYPE=Debug",
        "-DOBSW_ENABLE_ORBITFABRIC_CONTRACT=ON",
        f"-DORBITFABRIC_CONTRACT_DIR={contract_dir}",
    ])
    run(["cmake", "--build", str(build_dir), "--target", "obsw_sim", "-j2"])

    sim = build_dir / "sim" / "obsw_sim"
    if not sim.is_file():
        raise RuntimeError(f"OpenOBSW obsw_sim was not built: {sim}")

    file_result = run(["file", str(sim)], capture=True)
    file_output = (file_result.stdout or "").strip()
    print(f"[stage6.18 driver] built obsw_sim: {sim}", flush=True)
    print(f"[stage6.18 driver] obsw_sim file: {file_output}", flush=True)

    if "ELF 64-bit" not in file_output or "x86-64" not in file_output:
        raise RuntimeError(f"Unexpected obsw_sim binary type: {file_output}")

    return sim


def make_noop_sync(sync_protocol_cls: type[Any]) -> Any:
    def _noop(self: Any, *args: Any, **kwargs: Any) -> None:
        return None

    attrs: dict[str, Any] = {
        "__doc__": "Stage 6.18 no-op SyncProtocol for direct OBCEmulatorAdapter probing.",
    }

    for name in getattr(sync_protocol_cls, "__abstractmethods__", set()):
        attrs[name] = _noop

    noop_cls = type("Stage618NoOpSync", (sync_protocol_cls,), attrs)
    noop_cls.__abstractmethods__ = frozenset()
    return noop_cls()


def instantiate_bridge(
    bridge_cls: type[Any],
    *,
    store: Any,
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
            kwargs[name] = store
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
                f"required parameter without mapping: {name}; signature={signature}"
            )

    print(f"[stage6.18 driver] instantiate YamcsBridge with kwargs={kwargs}", flush=True)
    return bridge_cls(**kwargs)


def call_lifecycle(obj: Any, names: list[str]) -> bool:
    for name in names:
        method = getattr(obj, name, None)
        if callable(method):
            print(f"[stage6.18 driver] calling {obj.__class__.__name__}.{name}()", flush=True)
            method()
            return True
    return False


def _packet_attr_int(packet: Any, names: tuple[str, ...]) -> int | None:
    for name in names:
        value = getattr(packet, name, None)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                pass

    if isinstance(packet, dict):
        for name in names:
            value = packet.get(name)
            if value is not None:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    pass

    return None


def _packet_raw_bytes(packet: Any) -> bytes | None:
    if isinstance(packet, bytes):
        return packet
    if isinstance(packet, bytearray):
        return bytes(packet)

    for name in (
        "raw",
        "raw_packet",
        "raw_bytes",
        "packet",
        "data",
        "bytes",
        "encoded",
        "encoded_packet",
    ):
        value = getattr(packet, name, None)
        if isinstance(value, bytes):
            return value
        if isinstance(value, bytearray):
            return bytes(value)

    if isinstance(packet, dict):
        for name in (
            "raw",
            "raw_packet",
            "raw_bytes",
            "packet",
            "data",
            "bytes",
            "encoded",
            "encoded_packet",
        ):
            value = packet.get(name)
            if isinstance(value, bytes):
                return value
            if isinstance(value, bytearray):
                return bytes(value)

    return None


def packet_service(packet: Any) -> int | None:
    value = _packet_attr_int(
        packet,
        (
            "service",
            "svc",
            "service_type",
            "service_id",
            "pus_service",
            "pus_svc",
        ),
    )
    if value is not None:
        return value

    raw = _packet_raw_bytes(packet)
    if raw is not None and len(raw) > 7:
        return int(raw[7])

    return None


def packet_subservice(packet: Any) -> int | None:
    value = _packet_attr_int(
        packet,
        (
            "subservice",
            "subsvc",
            "subtype",
            "message_subtype",
            "subservice_type",
            "pus_subservice",
            "pus_subsvc",
        ),
    )
    if value is not None:
        return value

    raw = _packet_raw_bytes(packet)
    if raw is not None and len(raw) > 8:
        return int(raw[8])

    return None



def build_orbitfabric_event_tc() -> bytes:
    """Build TC(8,1) host-sim OrbitFabric event trigger.

    This is injected directly into the OpenSVF OBCEmulatorAdapter/OpenOBSW
    simulation boundary. It is not a YAMCS-originated TC path claim.
    """
    return bytes([
        0x18, 0x01,  # primary header: version/type/sec-hdr/APID
        0xC0, 0x00,  # sequence flags/count
        0x00, 0x07,  # data length = 8 bytes - 1
        0x11,        # PUS version / ack flags
        0x08,        # service = 8
        0x01,        # subservice = 1
        0x00, 0x00,  # source id
        (OBSW_OF_S8_FN_REPORT_VOLTAGE_OUT_OF_BOUNDS >> 8) & 0xFF,
        OBSW_OF_S8_FN_REPORT_VOLTAGE_OUT_OF_BOUNDS & 0xFF,
        0x00,        # args_len = 0
    ])


def inject_tc_into_adapter(adapter: Any, raw_tc: bytes, *, t: float) -> list[Any]:
    receive_tc = getattr(adapter, "receive_tc", None)
    if not callable(receive_tc):
        raise RuntimeError("OBCEmulatorAdapter does not expose receive_tc()")

    try:
        packets = receive_tc(raw_tc, t=t)
    except TypeError:
        packets = receive_tc(raw_tc)

    if packets is None:
        packets = []

    print(
        "TC(8,1) OrbitFabric event trigger injected into OpenOBSW: true",
        flush=True,
    )

    if not isinstance(packets, list):
        return list(packets)

    return packets


def live_openobsw_event_id(raw: bytes) -> int | None:
    """Return TM(5,3) event id from full live OpenOBSW packet bytes."""
    if len(raw) < 19:
        return None
    if raw[7] != 5 or raw[8] != 3:
        return None
    return (raw[17] << 8) | raw[18]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 6.18 live OpenOBSW event TM driver")
    parser.add_argument("--opensvf-root", default=str(DEFAULT_OPENSVF_ROOT))
    parser.add_argument("--openobsw-root", default=str(DEFAULT_OPENOBSW_ROOT))
    parser.add_argument("--build-dir", default="/tmp/openobsw-stage618-build")
    parser.add_argument("--orbitfabric-contract-dir", default=str(DEFAULT_ORBITFABRIC_CONTRACT_DIR))
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--tm-port", type=int, default=TM_PORT)
    parser.add_argument("--tc-port", type=int, default=TC_PORT)
    parser.add_argument("--steps", type=int, default=45)
    parser.add_argument("--dt", type=float, default=1.0)
    parser.add_argument("--startup-delay", type=float, default=5.0)
    parser.add_argument("--step-delay", type=float, default=0.05)
    parser.add_argument("--sync-timeout", type=float, default=5.0)
    parser.add_argument("--linger", type=float, default=12.0)
    parser.add_argument("--apid", type=lambda x: int(x, 0), default=0x103)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    opensvf_root = Path(args.opensvf_root).resolve()
    openobsw_root = Path(args.openobsw_root).resolve()
    build_dir = Path(args.build_dir).resolve()
    contract_dir = Path(args.orbitfabric_contract_dir).resolve()

    print("[stage6.18 driver] Stage 6.18 live OpenOBSW event TM driver", flush=True)
    print(f"[stage6.18 driver] OpenSVF root: {opensvf_root}", flush=True)
    print(f"[stage6.18 driver] OpenOBSW root: {openobsw_root}", flush=True)

    add_opensvf_src(opensvf_root)

    from svf.core.abstractions import SyncProtocol
    from svf.ground.yamcs_bridge import YamcsBridge
    from svf.models.dhs.obc_emulator import OBCEmulatorAdapter
    from svf.stores.command_store import CommandStore
    from svf.stores.parameter_store import ParameterStore

    sim_path = build_openobsw_sim(openobsw_root, build_dir, contract_dir)

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
    live_event_seen = False
    tm_seen = 0
    services_seen: list[str] = []

    started = call_lifecycle(bridge, ["start", "open"])
    if not started:
        raise RuntimeError("YamcsBridge object does not expose start() or open()")

    try:
        print(
            f"[stage6.18 driver] waiting {args.startup_delay:.1f}s for YAMCS tm-in connection",
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

        observed_adapter_tm: dict[str, Any] = {
            "count": 0,
            "event": False,
            "event_id": None,
            "event_raw_hex": None,
            "labels": [],
        }

        original_parse_tm = getattr(adapter, "_parse_tm", None)
        if callable(original_parse_tm):
            def stage618_observe_parse_tm(pkt: bytes, t: float) -> Any:
                raw = bytes(pkt)
                svc = int(raw[7]) if len(raw) > 7 else None
                subsvc = int(raw[8]) if len(raw) > 8 else None
                label = f"TM({svc},{subsvc})"

                observed_adapter_tm["count"] = int(observed_adapter_tm["count"]) + 1
                observed_adapter_tm["labels"].append(label)

                print(
                    f"[stage6.18 driver] observed {label} at "
                    "OBCEmulatorAdapter._parse_tm",
                    flush=True,
                )

                event_id = live_openobsw_event_id(raw)
                if event_id is not None:
                    observed_adapter_tm["event"] = event_id == OF_EVENT_VOLTAGE_OUT_OF_BOUNDS
                    observed_adapter_tm["event_id"] = event_id
                    observed_adapter_tm["event_raw_hex"] = raw.hex()
                    print(
                        "[stage6.18 driver] observed live OpenOBSW TM(5,3) "
                        f"event_id=0x{event_id:04X} at raw[17:19]",
                        flush=True,
                    )
                    if event_id != OF_EVENT_VOLTAGE_OUT_OF_BOUNDS:
                        raise RuntimeError(
                            "Unexpected OpenOBSW TM(5,3) event id: "
                            f"0x{event_id:04X}"
                        )

                return original_parse_tm(pkt, t)

            setattr(adapter, "_parse_tm", stage618_observe_parse_tm)
            print(
                "[stage6.18 driver] wrapped OBCEmulatorAdapter._parse_tm "
                "for live TM observation",
                flush=True,
            )
        else:
            print(
                "[stage6.18 driver] WARNING: OBCEmulatorAdapter._parse_tm "
                "not available for wrapping",
                flush=True,
            )

        setattr(adapter, "_yamcs_bridge", bridge)
        print(
            "[stage6.18 driver] attached real YamcsBridge to "
            "OBCEmulatorAdapter._yamcs_bridge",
            flush=True,
        )

        adapter.initialise(0.0)

        event_tc = build_orbitfabric_event_tc()
        immediate_packets = inject_tc_into_adapter(adapter, event_tc, t=0.0)

        for packet in immediate_packets:
            raw = _packet_raw_bytes(packet)
            svc = packet_service(packet)
            subsvc = packet_subservice(packet)
            label = f"TM({svc},{subsvc})"
            services_seen.append(label)
            tm_seen += 1
            print(
                f"[stage6.18 driver] observed {label} returned by receive_tc()",
                flush=True,
            )

            event_id = live_openobsw_event_id(raw) if raw is not None else None
            if event_id is not None:
                live_event_seen = event_id == OF_EVENT_VOLTAGE_OUT_OF_BOUNDS
                observed_adapter_tm["event"] = live_event_seen
                observed_adapter_tm["event_id"] = event_id
                observed_adapter_tm["event_raw_hex"] = raw.hex() if raw is not None else None
                print(
                    "[stage6.18 driver] observed live OpenOBSW TM(5,3) "
                    f"returned by receive_tc() event_id=0x{event_id:04X} at raw[17:19]",
                    flush=True,
                )
                if event_id != OF_EVENT_VOLTAGE_OUT_OF_BOUNDS:
                    raise RuntimeError(
                        "Unexpected receive_tc OpenOBSW TM(5,3) event id: "
                        f"0x{event_id:04X}"
                    )

        for step in range(args.steps):
            t = float(step) * args.dt
            adapter.do_step(t, args.dt)

            if bool(observed_adapter_tm["event"]):
                live_event_seen = True

            packets = adapter.get_tm_queue()
            if packets:
                print(
                    f"[stage6.18 driver] step={step} t={t:.1f} "
                    f"adapter_tm_packets={len(packets)}",
                    flush=True,
                )

            for packet in packets:
                svc = packet_service(packet)
                subsvc = packet_subservice(packet)
                label = f"TM({svc},{subsvc})"
                services_seen.append(label)
                tm_seen += 1

                print(f"[stage6.18 driver] observed {label} from live OpenOBSW", flush=True)

                raw = _packet_raw_bytes(packet)
                event_id = live_openobsw_event_id(raw) if raw is not None else None
                if event_id is not None:
                    live_event_seen = event_id == OF_EVENT_VOLTAGE_OUT_OF_BOUNDS
                    print(
                        "[stage6.18 driver] observed live OpenOBSW TM(5,3) "
                        f"through OBCEmulatorAdapter queue event_id=0x{event_id:04X}",
                        flush=True,
                    )
                    if event_id != OF_EVENT_VOLTAGE_OUT_OF_BOUNDS:
                        raise RuntimeError(
                            "Unexpected queued OpenOBSW TM(5,3) event id: "
                            f"0x{event_id:04X}"
                        )

            if live_event_seen:
                break

            time.sleep(args.step_delay)

        print(f"[stage6.18 driver] tm_seen={tm_seen}", flush=True)
        print(f"[stage6.18 driver] services_seen={services_seen}", flush=True)
        print(
            f"[stage6.18 driver] adapter_parse_tm_seen={observed_adapter_tm['count']}",
            flush=True,
        )
        print(
            f"[stage6.18 driver] adapter_parse_tm_labels={observed_adapter_tm['labels']}",
            flush=True,
        )
        print(
            f"[stage6.18 driver] adapter_parse_tm_event_id={observed_adapter_tm['event_id']}",
            flush=True,
        )
        print(
            f"[stage6.18 driver] adapter_parse_tm_event_raw_hex={observed_adapter_tm['event_raw_hex']}",
            flush=True,
        )

        if not live_event_seen:
            raise RuntimeError(
                "Live OpenOBSW TM(5,3) was not observed at "
                "OBCEmulatorAdapter._parse_tm"
            )

        print("Live OpenOBSW TM(5,3) observed by OBCEmulatorAdapter: true", flush=True)
        print("OpenOBSW TM(5,3) event_id raw[17:19] = 0x5001: true", flush=True)
        print(
            "OpenSVF YamcsBridge attached through OBCEmulatorAdapter TM hook: true",
            flush=True,
        )
        print(f"[stage6.18 driver] keeping bridge alive for {args.linger:.1f}s", flush=True)
        time.sleep(args.linger)

    finally:
        if adapter is not None:
            call_lifecycle(adapter, ["teardown", "stop", "close", "shutdown"])
        call_lifecycle(bridge, ["stop", "close", "shutdown"])

    print("[stage6.18 driver] done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
