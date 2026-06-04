#!/usr/bin/env python3
"""Generate a local Stage 5 evidence bundle.

This tool does not execute YAMCS, Renode, Docker or CI.

It captures local evidence for the current PoC validation boundary by running:

1. Stage 5 campaign descriptor validation.
2. Full OrbitFabric/OpenOBSW PoC pipeline validation.

It also records local provenance and artifact hashes so the evidence can be
traced back to a specific repository state and generated artifact set.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "execution" / "evidence" / "poc_ping_closed_loop_evidence.json"

HASHED_ARTIFACTS = [
    "execution/campaigns/poc_ping_closed_loop.yaml",
    "generated_artifacts/flight_software/mission_contract.h",
    "generated_artifacts/ground_segment/poc_srdb.yaml",
    "execution/generated/poc_xtce_mdb.xml",
]


def run_git(command: list[str]) -> str:
    proc = subprocess.run(
        ["git", *command],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        return proc.stderr.strip()
    return proc.stdout.strip()


def file_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def artifact_record(relative_path: str) -> dict:
    path = REPO_ROOT / relative_path

    return {
        "path": relative_path,
        "exists": path.is_file(),
        "size_bytes": path.stat().st_size if path.is_file() else None,
        "sha256": file_sha256(path),
    }


def collect_provenance() -> dict:
    status_short = run_git(["status", "--short"])

    return {
        "repo_root": str(REPO_ROOT),
        "python_executable": sys.executable,
        "python_version": sys.version,
        "platform": platform.platform(),
        "git": {
            "branch": run_git(["rev-parse", "--abbrev-ref", "HEAD"]),
            "head": run_git(["rev-parse", "HEAD"]),
            "head_short": run_git(["rev-parse", "--short", "HEAD"]),
            "status_short": status_short,
            "dirty": bool(status_short),
        },
        "artifacts": [artifact_record(path) for path in HASHED_ARTIFACTS],
    }


def run_capture(command: list[str]) -> dict:
    started_at = datetime.now(timezone.utc).isoformat()

    print()
    print("+ " + " ".join(command))
    print()

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    proc = subprocess.Popen(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        bufsize=1,
    )

    output_lines: list[str] = []

    assert proc.stdout is not None
    for line in proc.stdout:
        print(line, end="")
        output_lines.append(line)

    returncode = proc.wait()
    finished_at = datetime.now(timezone.utc).isoformat()

    combined_output = "".join(output_lines)

    return {
        "command": command,
        "started_at": started_at,
        "finished_at": finished_at,
        "returncode": returncode,
        "stdout": combined_output,
        "stderr": "",
        "passed": returncode == 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate local Stage 5 PoC evidence bundle."
    )
    parser.add_argument(
        "--opensvf-repo",
        default="../opensvf",
        help="Path to the OpenSVF repository. Default: ../opensvf",
    )
    parser.add_argument(
        "--openobsw-repo",
        default="../openobsw",
        help="Path to the OpenOBSW repository. Default: ../openobsw",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output evidence JSON path.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Pass --clean to the full PoC pipeline validation runner.",
    )

    args = parser.parse_args()

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = REPO_ROOT / output_path

    python = sys.executable

    pipeline_command = [
        python,
        "-u",
        str(REPO_ROOT / "tools" / "validate_poc_pipeline.py"),
        "--opensvf-repo",
        args.opensvf_repo,
        "--openobsw-repo",
        args.openobsw_repo,
    ]

    if args.clean:
        pipeline_command.append("--clean")

    steps = [
        {
            "id": "validate_stage5_campaign_plan",
            "result": run_capture([
                python,
                "-u",
                str(REPO_ROOT / "tools" / "validate_stage5_campaign_plan.py"),
            ]),
        },
        {
            "id": "validate_poc_pipeline",
            "result": run_capture(pipeline_command),
        },
    ]

    passed = all(step["result"]["passed"] for step in steps)

    evidence = {
        "evidence_id": "poc_ping_closed_loop_evidence",
        "stage": "5.2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "campaign_descriptor": "execution/campaigns/poc_ping_closed_loop.yaml",
        "scope": {
            "yamcs_runtime_execution": False,
            "renode_execution": False,
            "docker_workflow": False,
            "ci_workflow": False,
            "openobsw_telemetry_runtime_mapping": False,
            "openobsw_event_runtime_mapping": False,
            "housekeeping_runtime_mapping": False,
        },
        "steps": steps,
        "provenance": collect_provenance(),
        "passed": passed,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(evidence, indent=2, sort_keys=True),
        encoding="utf-8",
        newline="\n",
    )

    print()
    print(f"Stage 5 evidence bundle written to: {output_path}")

    if not passed:
        raise SystemExit("Stage 5 evidence bundle generation: FAIL")

    print("Stage 5 evidence bundle generation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
