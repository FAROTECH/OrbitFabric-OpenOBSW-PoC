#!/usr/bin/env python3
"""Validate Stage 7.8 native OpenSVF runtime consumption of the OrbitFabric-derived OpenOBSW binary."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import validate_stage7_7_host_sim_runtime as stage77

EXPECTED_OPENOBSW_COMMIT = "d6ec4b47b62733aec0f73f491a5453e6865c9b03"
EXPECTED_OPENSVF_COMMIT = "667d3eadcb0bbd7814ac324b99946c4ed2f11f23"


def _load_opensvf_adapter(opensvf_repo: Path):
    sys.path.insert(0, str((opensvf_repo / "src").resolve()))
    try:
        from svf.models.dhs.obc_emulator import OBCEmulatorAdapter
    finally:
        sys.path.pop(0)
    return OBCEmulatorAdapter


def _make_sync() -> MagicMock:
    sync = MagicMock()
    sync.publish_ready = MagicMock()
    return sync


def _make_store() -> MagicMock:
    store = MagicMock()
    store.write = MagicMock()
    store.read = MagicMock(return_value=None)
    return store


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build the OrbitFabric-enabled OpenOBSW host simulator from the external "
            "composed SRDB and generated flight contract, then run it through the "
            "pinned OpenSVF OBCEmulatorAdapter pipe runtime."
        )
    )
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--openobsw-repo", required=True, type=Path)
    parser.add_argument("--opensvf-repo", required=True, type=Path)
    args = parser.parse_args()

    bundle = args.bundle.resolve()
    openobsw_repo = args.openobsw_repo.resolve()
    opensvf_repo = args.opensvf_repo.resolve()

    actual_openobsw = stage77._git_head(openobsw_repo)
    if actual_openobsw != EXPECTED_OPENOBSW_COMMIT:
        raise SystemExit(
            "OpenOBSW checkout does not match the Stage 7.8 reference "
            f"{EXPECTED_OPENOBSW_COMMIT}; got {actual_openobsw}"
        )

    actual_opensvf = stage77._git_head(opensvf_repo)
    if actual_opensvf != EXPECTED_OPENSVF_COMMIT:
        raise SystemExit(
            "OpenSVF checkout does not match the Stage 7.8 reference "
            f"{EXPECTED_OPENSVF_COMMIT}; got {actual_opensvf}"
        )

    contract_dir = bundle / "flight_software"
    contract_path = contract_dir / "mission_contract.h"
    contribution_dir = bundle / "obsw_srdb_contribution"
    if not contract_path.is_file():
        raise SystemExit(f"Stage 7.4 flight contract not found: {contract_path}")
    if not contribution_dir.is_dir():
        raise SystemExit(f"Stage 7.4 SRDB contribution not found: {contribution_dir}")

    before = stage77._source_fingerprints(openobsw_repo)

    (
        SRDBLoader,
        SRDBContributionLoader,
        SRDBComposer,
        SRDBMaterializer,
    ) = stage77._load_target_api(openobsw_repo)

    base = SRDBLoader.load(openobsw_repo / "srdb" / "data")
    contribution = SRDBContributionLoader.load(contribution_dir)
    composed = SRDBComposer.compose(base, [contribution])

    OBCEmulatorAdapter = _load_opensvf_adapter(opensvf_repo)

    with tempfile.TemporaryDirectory(prefix="stage7_8_opensvf_runtime_") as raw:
        root = Path(raw)
        assembled_dir = root / "assembled_srdb"
        build_dir = root / "build"

        SRDBMaterializer.write(composed, assembled_dir)
        reloaded = SRDBLoader.load(assembled_dir)
        assert reloaded == composed
        assert reloaded.parameter_by_id(0x6001).name == "eps_obc_bus_voltage_mv"
        assert reloaded.hk_set_by_id(5).name == "obc_hk"
        assert reloaded.event_by_id(0x5001).name == "eps_voltage_out_of_bounds"

        stage77._run(
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
            label="OpenOBSW host-sim configure for OpenSVF consumption",
        )
        stage77._run(
            ["cmake", "--build", str(build_dir), "--target", "obsw_sim"],
            label="OpenOBSW host-sim build for OpenSVF consumption",
        )

        sim_binary = build_dir / "sim" / "obsw_sim"
        assert sim_binary.is_file()

        sync = _make_sync()
        store = _make_store()
        adapter = OBCEmulatorAdapter(
            sim_path=sim_binary,
            sync_protocol=sync,
            store=store,
            sync_timeout=5.0,
            apid=0x010,
        )

        adapter.initialise()
        try:
            assert adapter._proc is not None
            assert adapter._proc.poll() is None

            # Exercise a normal OpenSVF command path while the adapter also sends
            # its native TC(17,1) heartbeat traffic on each simulation tick.
            adapter.receive("dhs.obc.mode_cmd", 1.0)

            for index in range(10):
                adapter.on_tick(t=float(index) * 0.1, dt=0.1)

            assert sync.publish_ready.call_count == 10
            assert adapter.read_port("dhs.obc.mode_cmd") == -1.0

            obt = float(adapter.read_port("dhs.obc.obt"))
            assert abs(obt - 1.0) <= 0.01, f"Unexpected OpenSVF-visible OBT: {obt}"
        finally:
            adapter.teardown()

        assert adapter._proc is None

    after = stage77._source_fingerprints(openobsw_repo)
    assert after == before, "OpenOBSW srdb/data was mutated by the Stage 7.8 workflow"

    print("Stage 7.8 OpenSVF runtime consumption acceptance: PASS")
    print(f"  bundle: {bundle}")
    print(f"  OpenOBSW reference: {EXPECTED_OPENOBSW_COMMIT}")
    print(f"  OpenSVF reference: {EXPECTED_OPENSVF_COMMIT}")
    print("  OrbitFabric artifacts -> full OpenOBSW host-sim build PASS")
    print("  native OpenSVF OBCEmulatorAdapter process startup PASS")
    print("  OpenSVF sensor/heartbeat tick synchronization PASS")
    print("  OpenSVF mode-command TC path consumption PASS")
    print("  OpenSVF-visible OBC time progression PASS")
    print("  source srdb/data remained byte-identical PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
