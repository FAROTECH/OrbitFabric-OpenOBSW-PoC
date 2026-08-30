#!/usr/bin/env python3
"""Validate Stage 7.7 full OpenOBSW host-sim build and runtime consumption."""

from __future__ import annotations

import argparse
import hashlib
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

EXPECTED_OPENOBSW_HOST_SIM_COMMIT = "d6ec4b47b62733aec0f73f491a5453e6865c9b03"
_REQUIRED_SRDB_FILES = (
    "spacecraft.yaml",
    "parameters.yaml",
    "telecommands.yaml",
    "hk_sets.yaml",
    "events.yaml",
)


def _git_head(repo: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _source_fingerprints(openobsw_repo: Path) -> dict[str, str]:
    root = openobsw_repo / "srdb" / "data"
    return {name: _sha256(root / name) for name in _REQUIRED_SRDB_FILES}


def _load_target_api(openobsw_repo: Path):
    sys.path.insert(0, str((openobsw_repo / "srdb").resolve()))
    try:
        from obsw_srdb import (
            SRDBComposer,
            SRDBContributionLoader,
            SRDBLoader,
            SRDBMaterializer,
        )
    finally:
        sys.path.pop(0)
    return SRDBLoader, SRDBContributionLoader, SRDBComposer, SRDBMaterializer


def _run(command: list[str], *, label: str) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"{label} failed with exit code {completed.returncode}:\n"
            + completed.stdout
            + completed.stderr
        )
    return completed


def _parse_tm_frames(data: bytes) -> list[bytes]:
    packets: list[bytes] = []
    offset = 0
    while offset < len(data):
        frame_type = data[offset]
        if frame_type == 0xFF:
            offset += 1
            continue
        if frame_type != 0x04:
            offset += 1
            continue
        offset += 1
        if offset + 2 > len(data):
            break
        length = struct.unpack(">H", data[offset:offset + 2])[0]
        offset += 2
        if offset + length > len(data):
            break
        packets.append(data[offset:offset + length])
        offset += length
    return packets


def _run_sim(sim_binary: Path, framed_tc: bytes, *, label: str) -> tuple[list[bytes], str]:
    completed = subprocess.run(
        [str(sim_binary)],
        input=framed_tc,
        capture_output=True,
        check=False,
        timeout=5,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"{label} failed with exit code {completed.returncode}:\n"
            + completed.stderr.decode(errors="replace")
        )
    return _parse_tm_frames(completed.stdout), completed.stderr.decode(errors="replace")


def _tc_frame(packet: bytes) -> bytes:
    return b"\x01" + struct.pack(">H", len(packet)) + packet


def _ping_tc() -> bytes:
    # TC(17,1), APID 0x001. The OrbitFabric host-sim adapter resolves the
    # generated OF_CMD_PING contract onto the existing wildcard OpenOBSW route.
    packet = bytes([
        0x18, 0x01,
        0xC0, 0x00,
        0x00, 0x04,
        0x11,
        0x11,
        0x01,
        0x00, 0x00,
    ])
    return _tc_frame(packet)


def _event_tc() -> bytes:
    # TC(8,1) host-sim function trigger. Function ID 0x5001 is the existing
    # host-sim hook that materializes OF_EVENT_VOLTAGE_OUT_OF_BOUNDS as TM(5,3).
    packet = bytes([
        0x18, 0x01,
        0xC0, 0x00,
        0x00, 0x07,
        0x11,
        0x08,
        0x01,
        0x00, 0x00,
        0x50, 0x01,
        0x00,
    ])
    return _tc_frame(packet)


def _service_pairs(packets: list[bytes]) -> list[tuple[int, int]]:
    return [(packet[7], packet[8]) for packet in packets if len(packet) >= 9]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compose and materialize the Stage 7.4 contribution, build the full "
            "OpenOBSW host simulator against both the external assembled SRDB and "
            "generated OrbitFabric flight contract, then execute runtime smoke tests."
        )
    )
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--openobsw-repo", required=True, type=Path)
    args = parser.parse_args()

    bundle = args.bundle.resolve()
    openobsw_repo = args.openobsw_repo.resolve()

    actual_head = _git_head(openobsw_repo)
    if actual_head != EXPECTED_OPENOBSW_HOST_SIM_COMMIT:
        raise SystemExit(
            "OpenOBSW checkout does not match the Stage 7.7 host-sim reference "
            f"{EXPECTED_OPENOBSW_HOST_SIM_COMMIT}; got {actual_head}"
        )

    contract_dir = bundle / "flight_software"
    contract_path = contract_dir / "mission_contract.h"
    if not contract_path.is_file():
        raise SystemExit(f"Stage 7.4 flight contract not found: {contract_path}")

    before = _source_fingerprints(openobsw_repo)

    (
        SRDBLoader,
        SRDBContributionLoader,
        SRDBComposer,
        SRDBMaterializer,
    ) = _load_target_api(openobsw_repo)

    base = SRDBLoader.load(openobsw_repo / "srdb" / "data")
    contribution = SRDBContributionLoader.load(bundle / "obsw_srdb_contribution")
    composed = SRDBComposer.compose(base, [contribution])

    with tempfile.TemporaryDirectory(prefix="stage7_7_host_sim_") as raw:
        root = Path(raw)
        assembled_dir = root / "assembled_srdb"
        build_dir = root / "build"

        SRDBMaterializer.write(composed, assembled_dir)
        reloaded = SRDBLoader.load(assembled_dir)
        assert reloaded == composed

        _run(
            [
                "cmake",
                "-S",
                str(openobsw_repo),
                "-B",
                str(build_dir),
                "-DOBSW_BUILD_TESTS=OFF",
                "-DOBSW_BUILD_SIM=ON",
                "-DOBSW_ENABLE_ORBITFABRIC_CONTRACT=ON",
                f"-DORBITFABRIC_CONTRACT_DIR={contract_dir}",
                f"-DSRDB_DATA_DIR={assembled_dir}",
                f"-DPython3_EXECUTABLE={sys.executable}",
            ],
            label="OpenOBSW host-sim CMake configure",
        )

        cache_text = (build_dir / "CMakeCache.txt").read_text(encoding="utf-8")
        assert f"SRDB_DATA_DIR:PATH={assembled_dir}" in cache_text
        assert f"ORBITFABRIC_CONTRACT_DIR:PATH={contract_dir}" in cache_text
        assert "OBSW_ENABLE_ORBITFABRIC_CONTRACT:BOOL=ON" in cache_text

        _run(
            ["cmake", "--build", str(build_dir), "--target", "obsw_sim"],
            label="OpenOBSW full host-sim build",
        )

        sim_binary = build_dir / "sim" / "obsw_sim"
        assert sim_binary.is_file()

        generated_header = build_dir / "include" / "obsw" / "srdb_generated.h"
        assert generated_header.is_file()
        generated_text = generated_header.read_text(encoding="utf-8")
        assert "SRDB_PARAM_EPS_OBC_BUS_VOLTAGE_MV" in generated_text
        assert "SRDB_HK_OBC_HK" in generated_text

        ping_packets, ping_log = _run_sim(sim_binary, _ping_tc(), label="OrbitFabric ping runtime smoke")
        ping_pairs = _service_pairs(ping_packets)
        assert (1, 1) in ping_pairs
        assert (17, 2) in ping_pairs
        assert (1, 7) in ping_pairs
        assert "OrbitFabric: OF_CMD_PING" in ping_log

        event_packets, event_log = _run_sim(sim_binary, _event_tc(), label="OrbitFabric event runtime smoke")
        event_pairs = _service_pairs(event_packets)
        assert (5, 3) in event_pairs
        tm53 = next(packet for packet in event_packets if len(packet) >= 19 and packet[7] == 5 and packet[8] == 3)
        event_id = (tm53[17] << 8) | tm53[18]
        assert event_id == 0x5001
        assert "OF_EVENT_VOLTAGE_OUT_OF_BOUNDS" in event_log

    after = _source_fingerprints(openobsw_repo)
    assert after == before, "OpenOBSW srdb/data was mutated by the Stage 7.7 workflow"

    print("Stage 7.7 OpenOBSW host-sim runtime acceptance: PASS")
    print(f"  bundle: {bundle}")
    print(f"  OpenOBSW host-sim reference: {EXPECTED_OPENOBSW_HOST_SIM_COMMIT}")
    print("  external composed SRDB -> full obsw_sim build PASS")
    print("  generated mission_contract.h -> obsw_sim compile PASS")
    print("  OrbitFabric ping TC(17,1) -> TM(17,2) runtime PASS")
    print("  OrbitFabric event 0x5001 -> TM(5,3) runtime PASS")
    print("  source srdb/data remained byte-identical PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
