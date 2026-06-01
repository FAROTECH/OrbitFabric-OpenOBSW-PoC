#!/usr/bin/env python3
"""Run a minimal OpenOBSW host-sim ping smoke test.

This Stage 4.3 wrapper lives in the PoC repository.

It does not modify OpenOBSW. It executes an already built OpenOBSW host
simulator with the OrbitFabric contract adapter enabled, sends a minimal
TC(17,1) CCSDS/PUS-C command packet through the host-sim type-frame protocol,
and verifies that the expected telemetry responses are emitted.

Expected TM responses:

  TM(1,1)
  TM(17,2)
  TM(1,7)
"""

from __future__ import annotations

import argparse
import struct
import subprocess
from pathlib import Path


DEFAULT_SIM_BINARY = "../openobsw/build_stage4_orbitfabric/sim/obsw_sim"
EXPECTED_TM = {(1, 1), (17, 2), (1, 7)}


def parse_int(value: str) -> int:
    return int(value, 0)


def make_tc_space_packet(apid: int, service: int, subservice: int, seq_count: int) -> bytes:
    packet = bytearray(11)

    packet[0] = 0x18 | ((apid >> 8) & 0x07)
    packet[1] = apid & 0xFF

    packet[2] = 0xC0 | ((seq_count >> 8) & 0x3F)
    packet[3] = seq_count & 0xFF

    packet[4] = 0x00
    packet[5] = 0x04

    packet[6] = 0x11
    packet[7] = service & 0xFF
    packet[8] = subservice & 0xFF
    packet[9] = 0x00
    packet[10] = 0x00

    return bytes(packet)


def make_host_sim_uplink_frame(tc_packet: bytes) -> bytes:
    return bytes([0x01]) + struct.pack(">H", len(tc_packet)) + tc_packet


def parse_host_sim_stdout(stdout: bytes) -> set[tuple[int, int]]:
    offset = 0
    tm_seen: set[tuple[int, int]] = set()

    while offset < len(stdout):
        frame_type = stdout[offset]
        offset += 1

        if frame_type == 0xFF:
            print("sync byte")
            continue

        if offset + 2 > len(stdout):
            raise SystemExit("Truncated host-sim frame length")

        length = struct.unpack(">H", stdout[offset:offset + 2])[0]
        offset += 2

        if offset + length > len(stdout):
            raise SystemExit("Truncated host-sim frame payload")

        payload = stdout[offset:offset + length]
        offset += length

        if frame_type != 0x04:
            print(f"non-TM frame type 0x{frame_type:02X}, len={length}")
            continue

        if len(payload) < 9:
            raise SystemExit(f"TM payload too short: {len(payload)} bytes")

        service = payload[7]
        subservice = payload[8]
        tm_seen.add((service, subservice))
        print(f"TM({service},{subservice})")

    return tm_seen


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run OpenOBSW host-sim TC(17,1) ping smoke validation."
    )
    parser.add_argument(
        "--sim-binary",
        default=DEFAULT_SIM_BINARY,
        help=f"Path to the OrbitFabric-enabled obsw_sim binary. Default: {DEFAULT_SIM_BINARY}",
    )
    parser.add_argument(
        "--apid",
        default="0x010",
        help="TC APID used in the generated command packet. Default: 0x010",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Host simulator timeout in seconds. Default: 5",
    )

    args = parser.parse_args()

    sim_binary = Path(args.sim_binary).resolve()
    if not sim_binary.is_file():
        raise SystemExit(
            "OpenOBSW host simulator not found: "
            f"{sim_binary}\n"
            "Run tools/validate_openobsw_contract_adapter.py first."
        )

    apid = parse_int(args.apid)
    tc_packet = make_tc_space_packet(
        apid=apid,
        service=17,
        subservice=1,
        seq_count=1,
    )
    uplink = make_host_sim_uplink_frame(tc_packet)

    proc = subprocess.Popen(
        [str(sim_binary)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        stdout, stderr = proc.communicate(input=uplink, timeout=args.timeout)
    except subprocess.TimeoutExpired as exc:
        proc.kill()
        proc.communicate()
        raise SystemExit("OpenOBSW host simulator timed out") from exc

    print(f"stdout bytes: {len(stdout)}")

    if stderr:
        print("stderr:")
        print(stderr.decode(errors="replace").strip())

    tm_seen = parse_host_sim_stdout(stdout)
    missing = EXPECTED_TM.difference(tm_seen)

    if missing:
        raise SystemExit(f"Missing expected TM packets: {sorted(missing)}")

    print("OpenOBSW host-sim ping smoke validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
