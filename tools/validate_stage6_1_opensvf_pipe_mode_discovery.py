#!/usr/bin/env python3
"""Validate Stage 6.1 OpenSVF pipe mode discovery boundary.

This validator checks the PoC-side Stage 6.1 discovery files and, when an
OpenSVF checkout is available, verifies the specific OpenSVF source facts that
support the discovery decision.

It does not execute YAMCS, Docker, CI, Renode, OpenSVF runtime campaigns, or
OpenOBSW runtime campaigns.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]

DOC_PATH = REPO_ROOT / "docs" / "stage6_1_opensvf_pipe_mode_discovery.md"
DESCRIPTOR_PATH = REPO_ROOT / "execution" / "campaigns" / "poc_opensvf_pipe_mode_discovery.yaml"

EXPECTED_STAGE = "6.1"
EXPECTED_DISCOVERY_ID = "poc_opensvf_pipe_mode_discovery"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def load_yaml(path: Path) -> dict:
    require(path.is_file(), f"YAML file not found: {path}")
    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    require(isinstance(data, dict), f"YAML file must contain a mapping: {path}")
    return data


def read_text(path: Path) -> str:
    require(path.is_file(), f"File not found: {path}")
    return path.read_text(encoding="utf-8")


def validate_doc() -> None:
    text = read_text(DOC_PATH)

    required_markers = [
        "Stage 6.1 OpenSVF pipe mode discovery",
        "OpenSVF already has OBSW pipe mode",
        "SpacecraftLoader accepts an external spacecraft YAML path",
        "XTCE generation appears repo-local to OpenSVF SRDB",
        "PoC-side config/wrapper",
        "YAMCS runtime execution",
        "OpenSVF proper changes",
        "OpenOBSW proper changes",
    ]

    for marker in required_markers:
        require(marker in text, f"Missing Stage 6.1 document marker: {marker}")


def validate_descriptor() -> None:
    data = load_yaml(DESCRIPTOR_PATH)

    require(data.get("discovery_id") == EXPECTED_DISCOVERY_ID, "Unexpected discovery_id")
    require(str(data.get("stage")) == EXPECTED_STAGE, "Unexpected stage")
    require(data.get("status") == "discovery", "status must be discovery")

    baseline_inputs = data.get("baseline_inputs")
    require(isinstance(baseline_inputs, dict), "baseline_inputs must be a mapping")

    required_inputs = [
        "stage6_runtime_discovery_doc",
        "stage6_runtime_discovery_descriptor",
        "stage5_campaign_descriptor",
        "generated_srdb",
        "generated_xtce_mdb",
        "generated_flight_contract",
        "openobsw_host_sim_binary",
    ]

    for key in required_inputs:
        require(key in baseline_inputs, f"Missing baseline input: {key}")
        require(isinstance(baseline_inputs[key], str), f"baseline_inputs.{key} must be a string")

    findings = data.get("findings")
    require(isinstance(findings, dict), "findings must be a mapping")
    require(findings.get("opensvf_pipe_mode_available") is True, "pipe mode finding must be true")
    require(
        findings.get("spacecraft_loader_accepts_external_yaml") is True,
        "external spacecraft YAML finding must be true",
    )
    require(
        findings.get("external_srdb_path_direct_support_found") is False,
        "external SRDB direct support finding must remain false for this stage",
    )
    require(
        findings.get("poc_side_config_wrapper_likely_required") is True,
        "PoC-side wrapper finding must be true",
    )

    boundary = data.get("current_boundary")
    require(isinstance(boundary, dict), "current_boundary must be a mapping")

    expected_false_keys = [
        "yamcs_runtime_execution",
        "command_injection_runtime",
        "telemetry_runtime_observation",
        "docker_workflow",
        "ci_workflow",
        "renode_execution",
        "opensvf_proper_changes",
        "openobsw_proper_changes",
        "runtime_bridge_implementation",
    ]

    for key in expected_false_keys:
        require(boundary.get(key) is False, f"current_boundary.{key} must be false")


def validate_opensvf_source(opensvf_repo: Path) -> None:
    require(opensvf_repo.is_dir(), f"OpenSVF repository not found: {opensvf_repo}")

    spacecraft_py = opensvf_repo / "src" / "svf" / "config" / "spacecraft.py"
    generate_xtce_py = opensvf_repo / "tools" / "generate_xtce.py"
    readme = opensvf_repo / "README.md"

    spacecraft_text = read_text(spacecraft_py)
    xtce_text = read_text(generate_xtce_py)
    readme_text = read_text(readme)

    spacecraft_markers = [
        "class SpacecraftLoader",
        "def load(",
        "obsw.type must be pipe | socket | stub",
        "obsw.binary is required when obsw.type is 'pipe'",
        "OBCEmulatorAdapter",
        "sim_path=binary_path",
    ]

    for marker in spacecraft_markers:
        require(marker in spacecraft_text, f"Missing OpenSVF spacecraft loader marker: {marker}")

    require(
        'Path("srdb/baseline").glob("*.yaml")' in xtce_text
        or "srdb/baseline" in xtce_text,
        "OpenSVF XTCE generator no longer appears to load repo-local srdb/baseline",
    )

    forbidden_external_srdb_cli_markers = [
        "--srdb",
        "--srdb-path",
        "--baseline-dir",
        "--mission-srdb",
    ]

    found_external_markers = [
        marker for marker in forbidden_external_srdb_cli_markers if marker in xtce_text
    ]

    require(
        not found_external_markers,
        "OpenSVF XTCE generator appears to expose external SRDB CLI markers: "
        + ", ".join(found_external_markers),
    )

    readme_markers = [
        "YAMCS",
        "TC pipeline",
        "TM pipeline",
        "obsw_sim",
    ]

    for marker in readme_markers:
        require(marker in readme_text, f"Missing OpenSVF README marker: {marker}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Stage 6.1 OpenSVF pipe mode discovery boundary."
    )
    parser.add_argument(
        "--opensvf-repo",
        default="../opensvf",
        help="Path to the OpenSVF repository. Default: ../opensvf",
    )

    args = parser.parse_args()

    opensvf_repo = Path(args.opensvf_repo)
    if not opensvf_repo.is_absolute():
        opensvf_repo = REPO_ROOT / opensvf_repo

    validate_doc()
    validate_descriptor()
    validate_opensvf_source(opensvf_repo)

    print("Stage 6.1 OpenSVF pipe mode discovery validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
