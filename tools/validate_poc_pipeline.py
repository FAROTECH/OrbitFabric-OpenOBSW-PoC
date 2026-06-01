#!/usr/bin/env python3
"""Run the complete local OrbitFabric/OpenOBSW PoC validation pipeline.

This Stage 4.4 wrapper lives in the PoC repository.

It does not modify OpenSVF.
It does not modify OpenOBSW.
It orchestrates the existing local generation and validation tools in the
expected model-first order.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OPENSVF_REPO = "../opensvf"
DEFAULT_OPENOBSW_REPO = "../openobsw"


def run_command(command: list[str], cwd: Path = REPO_ROOT) -> None:
    print()
    print("+ " + " ".join(command))
    subprocess.run(command, cwd=cwd, check=True)


def require_dir(path: Path, description: str) -> None:
    if not path.is_dir():
        raise SystemExit(f"{description} not found: {path}")


def require_file(path: Path, description: str) -> None:
    if not path.is_file():
        raise SystemExit(f"{description} not found: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the complete OrbitFabric/OpenOBSW PoC validation pipeline."
    )
    parser.add_argument(
        "--opensvf-repo",
        default=DEFAULT_OPENSVF_REPO,
        help="Path to the OpenSVF repository. Default: ../opensvf",
    )
    parser.add_argument(
        "--openobsw-repo",
        default=DEFAULT_OPENOBSW_REPO,
        help="Path to the OpenOBSW repository. Default: ../openobsw",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean OpenOBSW validation build directories before rebuilding.",
    )

    args = parser.parse_args()

    opensvf_repo = Path(args.opensvf_repo).resolve()
    openobsw_repo = Path(args.openobsw_repo).resolve()

    require_dir(opensvf_repo, "OpenSVF repository")
    require_dir(openobsw_repo, "OpenOBSW repository")
    require_file(openobsw_repo / "CMakeLists.txt", "OpenOBSW CMakeLists.txt")

    python = sys.executable

    steps: list[tuple[str, list[str]]] = [
        (
            "Generate PoC artifacts",
            [
                python,
                str(REPO_ROOT / "tools" / "generate_poc_artifacts.py"),
            ],
        ),
        (
            "Validate generated SRDB through OpenSVF XTCE path",
            [
                python,
                str(REPO_ROOT / "tools" / "validate_opensvf_srdb_xtce.py"),
                "--opensvf-repo",
                str(opensvf_repo),
            ],
        ),
        (
            "Generate PoC XTCE/YAMCS MDB through OpenSVF",
            [
                python,
                str(REPO_ROOT / "tools" / "generate_poc_xtce_mdb.py"),
                "--opensvf-repo",
                str(opensvf_repo),
            ],
        ),
        (
            "Validate OpenOBSW OrbitFabric contract adapter handoff",
            [
                python,
                str(REPO_ROOT / "tools" / "validate_openobsw_contract_adapter.py"),
                "--openobsw-repo",
                str(openobsw_repo),
            ],
        ),
        (
            "Run OpenOBSW host-sim ping smoke validation",
            [
                python,
                str(REPO_ROOT / "tools" / "validate_openobsw_ping_smoke.py"),
            ],
        ),
    ]

    if args.clean:
        steps[3][1].append("--clean")

    print("OrbitFabric/OpenOBSW PoC pipeline validation")
    print(f"PoC repo:      {REPO_ROOT}")
    print(f"OpenSVF repo:  {opensvf_repo}")
    print(f"OpenOBSW repo: {openobsw_repo}")

    for index, (title, command) in enumerate(steps, start=1):
        print()
        print(f"[{index}/{len(steps)}] {title}")
        run_command(command)

    print()
    print("OrbitFabric/OpenOBSW PoC pipeline validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
