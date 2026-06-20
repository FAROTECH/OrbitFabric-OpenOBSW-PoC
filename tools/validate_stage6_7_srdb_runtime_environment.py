#!/usr/bin/env python3
"""Validate the Stage 6.7 SRDB runtime environment.

This validator checks that the OpenSVF Python environment can see the
OpenOBSW SRDB Python package and, optionally, that the Stage 6.5 HK
runtime smoke runs without the previous SRDB package warning.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import subprocess
import sys
from pathlib import Path


PACKAGE_WARNING = "obsw-srdb package not installed"
VERSION_MISMATCH = "SRDB VERSION MISMATCH"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"ERROR: {message}")


def check_imports(root: Path) -> str:
    openobsw_srdb = (root / ".." / "openobsw" / "srdb").resolve()
    require(openobsw_srdb.exists(), f"OpenOBSW SRDB directory not found: {openobsw_srdb}")
    require((openobsw_srdb / "pyproject.toml").exists(), "OpenOBSW SRDB pyproject.toml not found")

    obsw_spec = importlib.util.find_spec("obsw_srdb")
    svf_spec = importlib.util.find_spec("svf")

    require(
        obsw_spec is not None,
        "obsw_srdb is not importable. Run: ../opensvf/.venv/bin/python -m pip install -e ../openobsw/srdb",
    )
    require(svf_spec is not None, "svf is not importable from this Python environment")

    try:
        version = importlib.metadata.version("obsw-srdb")
    except importlib.metadata.PackageNotFoundError as exc:
        raise SystemExit("ERROR: Python distribution 'obsw-srdb' is not installed") from exc

    print(f"obsw_srdb import: PASS ({obsw_spec.origin})")
    print(f"svf import: PASS ({svf_spec.origin})")
    print(f"obsw-srdb version: {version}")
    return version


def run_campaign(root: Path) -> None:
    campaign = root / "execution" / "campaigns" / "poc_runtime_hk_smoke.yaml"
    evidence = root / "execution" / "evidence" / "poc_runtime_hk_smoke_report.json"

    require(campaign.exists(), f"Campaign not found: {campaign}")

    cmd = [
        sys.executable,
        "-m",
        "svf.campaign.cli",
        "campaign",
        str(campaign),
        "--json",
        str(evidence),
    ]

    print("Running Stage 6.5 HK runtime smoke with SRDB package visible...")
    proc = subprocess.run(
        cmd,
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    print(proc.stdout, end="")

    require(proc.returncode == 0, f"Campaign failed with exit code {proc.returncode}")
    require("PASS:" in proc.stdout, "Campaign summary missing PASS line")
    require("FAIL:          0" in proc.stdout, "Campaign reported one or more failures")
    require("ERROR:         0" in proc.stdout, "Campaign reported one or more errors")
    require(PACKAGE_WARNING not in proc.stdout, f"Unexpected SRDB package warning found: {PACKAGE_WARNING}")
    require(VERSION_MISMATCH not in proc.stdout, f"Unexpected SRDB version mismatch found: {VERSION_MISMATCH}")

    print("Stage 6.7 campaign SRDB environment check: PASS")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-campaign",
        action="store_true",
        help="also run the Stage 6.5 HK runtime smoke and check SRDB warning absence",
    )
    args = parser.parse_args()

    root = repo_root()
    print("Stage 6.7 SRDB runtime environment validation")
    print(f"Repository root: {root}")
    print(f"Python executable: {sys.executable}")

    check_imports(root)

    if args.run_campaign:
        run_campaign(root)

    print("Stage 6.7 SRDB runtime environment validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
