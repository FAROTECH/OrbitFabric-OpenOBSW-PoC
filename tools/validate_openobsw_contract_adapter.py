#!/usr/bin/env python3
"""Validate OpenOBSW consumption of the generated OrbitFabric contract.

This Stage 4.2 validation wrapper lives in the PoC repository.

It does not modify OpenOBSW. It configures and builds OpenOBSW twice:

1. Default OpenOBSW build, OrbitFabric adapter disabled.
2. OrbitFabric-enabled host-sim build, consuming the generated
   mission_contract.h from this PoC repository.

The goal is to keep the OpenOBSW contract adapter handoff reproducible from
the PoC workspace without moving runtime behavior into generated artifacts.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OPENOBSW_REPO = "../openobsw"
DEFAULT_CONTRACT_DIR = REPO_ROOT / "generated_artifacts" / "flight_software"


def run_command(command: list[str], cwd: Path | None = None) -> None:
    print("+ " + " ".join(command))
    subprocess.run(command, cwd=cwd, check=True)


def require_file(path: Path, description: str) -> None:
    if not path.is_file():
        raise SystemExit(f"{description} not found: {path}")


def require_dir(path: Path, description: str) -> None:
    if not path.is_dir():
        raise SystemExit(f"{description} not found: {path}")


def configure_build_test(
    openobsw_repo: Path,
    build_dir: Path,
    contract_dir: Path | None,
    orbitfabric_enabled: bool,
) -> None:
    configure_command = [
        "cmake",
        "-S",
        str(openobsw_repo),
        "-B",
        str(build_dir),
        f"-DPython3_EXECUTABLE={sys.executable}",
        "-DOBSW_BUILD_TESTS=ON",
        "-DOBSW_BUILD_SIM=ON",
    ]

    if orbitfabric_enabled:
        configure_command.extend([
            "-DOBSW_ENABLE_ORBITFABRIC_CONTRACT=ON",
            f"-DORBITFABRIC_CONTRACT_DIR={contract_dir}",
        ])

    run_command(configure_command)
    run_command(["cmake", "--build", str(build_dir)])
    run_command(["ctest", "--test-dir", str(build_dir), "--output-on-failure"])


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the OpenOBSW optional OrbitFabric contract adapter."
    )
    parser.add_argument(
        "--openobsw-repo",
        default=DEFAULT_OPENOBSW_REPO,
        help="Path to the OpenOBSW repository. Default: ../openobsw",
    )
    parser.add_argument(
        "--contract-dir",
        default=str(DEFAULT_CONTRACT_DIR),
        help=(
            "Directory containing generated mission_contract.h. "
            "Default: generated_artifacts/flight_software"
        ),
    )
    parser.add_argument(
        "--default-build-dir",
        default="build_stage4_default",
        help="Default OpenOBSW build directory name/path.",
    )
    parser.add_argument(
        "--orbitfabric-build-dir",
        default="build_stage4_orbitfabric",
        help="OrbitFabric-enabled OpenOBSW build directory name/path.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove validation build directories before configuring.",
    )

    args = parser.parse_args()

    openobsw_repo = Path(args.openobsw_repo).resolve()
    contract_dir = Path(args.contract_dir).resolve()

    require_dir(openobsw_repo, "OpenOBSW repository")
    require_file(openobsw_repo / "CMakeLists.txt", "OpenOBSW CMakeLists.txt")
    require_file(contract_dir / "mission_contract.h", "Generated mission_contract.h")

    default_build_dir = Path(args.default_build_dir)
    orbitfabric_build_dir = Path(args.orbitfabric_build_dir)

    if not default_build_dir.is_absolute():
        default_build_dir = openobsw_repo / default_build_dir
    if not orbitfabric_build_dir.is_absolute():
        orbitfabric_build_dir = openobsw_repo / orbitfabric_build_dir

    if args.clean:
        shutil.rmtree(default_build_dir, ignore_errors=True)
        shutil.rmtree(orbitfabric_build_dir, ignore_errors=True)

    print("Validating default OpenOBSW build without OrbitFabric adapter")
    configure_build_test(
        openobsw_repo=openobsw_repo,
        build_dir=default_build_dir,
        contract_dir=None,
        orbitfabric_enabled=False,
    )

    print("Validating OpenOBSW host-sim build with OrbitFabric adapter enabled")
    configure_build_test(
        openobsw_repo=openobsw_repo,
        build_dir=orbitfabric_build_dir,
        contract_dir=contract_dir,
        orbitfabric_enabled=True,
    )

    print("OpenOBSW OrbitFabric contract adapter validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
