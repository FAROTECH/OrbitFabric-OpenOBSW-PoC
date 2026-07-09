#!/usr/bin/env python3
"""Bridge-compatible TM producer for Stage 6.14.

This is a PoC-side YamcsBridge-compatible producer used to validate the
YAMCS TcpTmDataLink direction and basic packet consumption boundary.

It intentionally does not run OpenSVF YamcsBridge or OpenOBSW. It listens
on 127.0.0.1:10015 inside the YAMCS container network namespace, accepts
the YAMCS TcpTmDataLink client connection, and sends representative raw
TM packets.
"""

from __future__ import annotations

import argparse
import socket
import struct
import time


HOST = "127.0.0.1"
PORT = 10015


def build_tm_packet(
    service: int,
    subservice: int,
    app_data: bytes = b"",
    seq: int = 1,
) -> bytes:
    """Build a minimal CCSDS/PUS-like TM packet for the PoC MDB.

    Current PoC MDB assumptions:
      * 6-byte CCSDS primary header
      * 5-byte PUS-C secondary header
      * application data starts after byte offset 11 / bit offset 88

    This packet is representative for link-level YAMCS consumption smoke,
    not evidence of live OpenOBSW/OpenSVF packet generation.
    """
    ccsds_first = 0x0800 | 0x0010  # version=0, TM, secondary header, APID=0x010
    ccsds_seq = 0xC000 | (seq & 0x3FFF)
    pus_secondary = bytes([0x10, service & 0xFF, subservice & 0xFF, 0x00, 0x00])
    payload = pus_secondary + app_data
    ccsds_length = len(payload) - 1
    primary = struct.pack(">HHH", ccsds_first, ccsds_seq, ccsds_length)
    return primary + payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 6.14 TM producer")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--cycles", type=int, default=5)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--accept-timeout", type=float, default=90.0)
    parser.add_argument("--linger", type=float, default=8.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((args.host, args.port))
        server.listen(1)
        server.settimeout(args.accept_timeout)
        print(
            f"[stage6.14 producer] listening on {args.host}:{args.port}",
            flush=True,
        )

        conn, addr = server.accept()
        with conn:
            print(
                f"[stage6.14 producer] accepted YAMCS connection from {addr}",
                flush=True,
            )

            sequence = 1
            sent_count = 0
            for _ in range(args.cycles):
                packets = [
                    (
                        "TM(3,25)",
                        build_tm_packet(3, 25, b"\x0b\xb8", seq=sequence),
                    ),
                    (
                        "TM(5,3)",
                        build_tm_packet(5, 3, b"\x50\x01", seq=sequence + 1),
                    ),
                ]
                sequence += 2

                for name, packet in packets:
                    conn.sendall(packet)
                    sent_count += 1
                    print(
                        f"[stage6.14 producer] sent {name} "
                        f"len={len(packet)} seq={sequence - 2} "
                        f"hex={packet.hex()}",
                        flush=True,
                    )
                    time.sleep(args.delay)

            print(
                f"[stage6.14 producer] sent_count={sent_count}; "
                "keeping connection briefly",
                flush=True,
            )
            time.sleep(args.linger)

    print("[stage6.14 producer] done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
