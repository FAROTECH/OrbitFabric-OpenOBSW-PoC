#!/usr/bin/env python3
"""Validate Stage 7.6 external assembled-SRDB build consumption."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

EXPECTED_OPENOBSW_BUILD_COMMIT = "d6ec4b47b62733aec0f73f491a5453e6865c9b03"
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


def _compile_build_header(build_dir: Path) -> None:
    include_dir = build_dir / "include" / "obsw"
    smoke = """
#include "srdb_generated.h"

int main(void) {
    return (SRDB_PARAM_EPS_OBC_BUS_VOLTAGE_MV == 0x6001U &&
            SRDB_EVENT_EPS_VOLTAGE_OUT_OF_BOUNDS == 0x5001U &&
            SRDB_HK_OBC_HK == 5U &&
            SRDB_TC_ARE_YOU_ALIVE_SVC == 17U &&
            SRDB_TC_ARE_YOU_ALIVE_SUBSVC == 1U) ? 0 : 1;
}
"""
    completed = subprocess.run(
        [
            "cc",
            "-x",
            "c",
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-fsyntax-only",
            "-I",
            str(include_dir),
            "-",
        ],
        input=smoke,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "CMake-produced native SRDB header failed strict C11 compile:\n"
            + completed.stdout
            + completed.stderr
        )


def _xml_local_names(xml_text: str, tag: str) -> set[str]:
    root = ET.fromstring(xml_text)
    result: set[str] = set()
    for element in root.iter():
        local = element.tag.rsplit("}", 1)[-1]
        if local == tag and "name" in element.attrib:
            result.add(element.attrib["name"])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compose and materialize the Stage 7.4 SRDB contribution through "
            "target-owned APIs, then make the native OpenOBSW CMake srdb_codegen "
            "target consume that external complete SRDB directory."
        )
    )
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--openobsw-repo", required=True, type=Path)
    args = parser.parse_args()

    bundle = args.bundle.resolve()
    openobsw_repo = args.openobsw_repo.resolve()

    actual_head = _git_head(openobsw_repo)
    if actual_head != EXPECTED_OPENOBSW_BUILD_COMMIT:
        raise SystemExit(
            "OpenOBSW checkout does not match the Stage 7.6 external-build "
            f"reference {EXPECTED_OPENOBSW_BUILD_COMMIT}; got {actual_head}"
        )

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

    with tempfile.TemporaryDirectory(prefix="stage7_6_external_build_") as raw:
        root = Path(raw)
        assembled_dir = root / "assembled_srdb"
        build_dir = root / "build"

        SRDBMaterializer.write(composed, assembled_dir)
        assert {path.name for path in assembled_dir.iterdir()} == set(_REQUIRED_SRDB_FILES)

        reloaded = SRDBLoader.load(assembled_dir)
        assert reloaded == composed
        assert reloaded.parameter_by_id(0x6001).name == "eps_obc_bus_voltage_mv"
        assert reloaded.hk_set_by_id(5).name == "obc_hk"
        assert reloaded.event_by_id(0x5001).name == "eps_voltage_out_of_bounds"

        _run(
            [
                "cmake",
                "-S",
                str(openobsw_repo),
                "-B",
                str(build_dir),
                "-DOBSW_BUILD_TESTS=OFF",
                "-DOBSW_BUILD_SIM=OFF",
                f"-DSRDB_DATA_DIR={assembled_dir}",
                f"-DPython3_EXECUTABLE={sys.executable}",
            ],
            label="OpenOBSW CMake configure with external SRDB_DATA_DIR",
        )

        cache_text = (build_dir / "CMakeCache.txt").read_text(encoding="utf-8")
        assert f"SRDB_DATA_DIR:PATH={assembled_dir}" in cache_text

        _run(
            ["cmake", "--build", str(build_dir), "--target", "srdb_codegen"],
            label="OpenOBSW native srdb_codegen build",
        )

        header_path = build_dir / "include" / "obsw" / "srdb_generated.h"
        xtce_path = build_dir / "xtce" / "mission.xtce"
        assert header_path.is_file()
        assert xtce_path.is_file()

        header = header_path.read_text(encoding="utf-8")
        assert "SRDB_PARAM_EPS_OBC_BUS_VOLTAGE_MV" in header
        assert "SRDB_EVENT_EPS_VOLTAGE_OUT_OF_BOUNDS" in header
        assert "SRDB_HK_OBC_HK" in header
        assert "SRDB_TC_ARE_YOU_ALIVE" in header
        _compile_build_header(build_dir)

        xtce = xtce_path.read_text(encoding="utf-8")
        assert "EPS_OBC_BUS_VOLTAGE_MV" in _xml_local_names(xtce, "Parameter")
        assert "TM_3_25_OBC_HK" in _xml_local_names(xtce, "SequenceContainer")

    after = _source_fingerprints(openobsw_repo)
    assert after == before, "OpenOBSW srdb/data was mutated by the external build workflow"

    print("Stage 7.6 external build consumption acceptance: PASS")
    print(f"  bundle: {bundle}")
    print(f"  OpenOBSW build reference: {EXPECTED_OPENOBSW_BUILD_COMMIT}")
    print("  target-owned complete SRDB materialization PASS")
    print("  external SRDB_DATA_DIR CMake configure PASS")
    print("  native OpenOBSW srdb_codegen target PASS")
    print("  CMake-produced C header strict C11 compile PASS")
    print("  CMake-produced XTCE contribution continuity PASS")
    print("  source srdb/data remained byte-identical PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
