#!/usr/bin/env python3
"""Validate the Stage 5 planned closed-loop campaign descriptor.

This validator intentionally does not execute YAMCS, Renode, Docker, CI,
OpenSVF runtime campaigns, or OpenOBSW telemetry/event runtime mapping.

It checks that the Stage 5 campaign descriptor is structurally present and
aligned with the Stage 4 validated command path.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_CAMPAIGN_ID = "poc_ping_closed_loop"
EXPECTED_STAGE = "5.0"
EXPECTED_COMMAND = "OF_CMD_PING"
EXPECTED_TC = (17, 1)
EXPECTED_TM = {(1, 1), (17, 2), (1, 7)}

REQUIRED_INPUTS = {
    "mission_model_dir",
    "mapping_file",
    "flight_contract",
    "srdb",
    "xtce_mdb",
}

REQUIRED_STAGE4_STEPS = {
    "generate_poc_artifacts",
    "validate_opensvf_srdb_xtce",
    "generate_poc_xtce_mdb",
    "validate_openobsw_contract_adapter",
    "validate_openobsw_ping_smoke",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def load_yaml(path: Path) -> dict:
    require(path.is_file(), f"Campaign descriptor not found: {path}")

    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)

    require(isinstance(data, dict), "Campaign descriptor must be a YAML mapping")
    return data


def validate_inputs(data: dict) -> None:
    inputs = data.get("inputs")
    require(isinstance(inputs, dict), "inputs must be a mapping")

    missing = REQUIRED_INPUTS.difference(inputs.keys())
    require(not missing, f"Missing campaign inputs: {sorted(missing)}")

    for key in REQUIRED_INPUTS:
        value = inputs[key]
        require(isinstance(value, str) and value, f"inputs.{key} must be a non-empty string")


def validate_stage4_steps(data: dict) -> None:
    steps = data.get("validated_stage4_chain")
    require(isinstance(steps, list), "validated_stage4_chain must be a list")

    step_set = set(steps)
    missing = REQUIRED_STAGE4_STEPS.difference(step_set)
    require(not missing, f"Missing Stage 4 validation steps: {sorted(missing)}")


def validate_command_path(data: dict) -> None:
    command_path = data.get("command_path")
    require(isinstance(command_path, dict), "command_path must be a mapping")

    require(
        command_path.get("orbitfabric_command") == EXPECTED_COMMAND,
        f"Expected orbitfabric_command {EXPECTED_COMMAND}",
    )

    pus_tc = command_path.get("pus_tc")
    require(isinstance(pus_tc, dict), "command_path.pus_tc must be a mapping")

    require(
        (pus_tc.get("service"), pus_tc.get("subservice")) == EXPECTED_TC,
        f"Expected TC{EXPECTED_TC}",
    )

    require(
        command_path.get("openobsw_target") == "host_sim",
        "command_path.openobsw_target must be host_sim",
    )


def validate_expected_telemetry(data: dict) -> None:
    telemetry = data.get("expected_telemetry")
    require(isinstance(telemetry, list), "expected_telemetry must be a list")

    seen: set[tuple[int, int]] = set()

    for item in telemetry:
        require(isinstance(item, dict), "Each expected telemetry item must be a mapping")
        seen.add((item.get("service"), item.get("subservice")))

    missing = EXPECTED_TM.difference(seen)
    require(not missing, f"Missing expected telemetry packets: {sorted(missing)}")


def validate_boundary(data: dict) -> None:
    boundary = data.get("current_boundary")
    require(isinstance(boundary, dict), "current_boundary must be a mapping")

    expected_false_keys = [
        "yamcs_runtime_execution",
        "renode_execution",
        "docker_workflow",
        "ci_workflow",
        "openobsw_telemetry_runtime_mapping",
        "openobsw_event_runtime_mapping",
        "housekeeping_runtime_mapping",
    ]

    for key in expected_false_keys:
        require(boundary.get(key) is False, f"current_boundary.{key} must be false")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the Stage 5 planned closed-loop campaign descriptor."
    )
    parser.add_argument(
        "--campaign",
        default="execution/campaigns/poc_ping_closed_loop.yaml",
        help="Path to the Stage 5 campaign descriptor.",
    )

    args = parser.parse_args()

    campaign_path = Path(args.campaign)
    if not campaign_path.is_absolute():
        campaign_path = REPO_ROOT / campaign_path

    data = load_yaml(campaign_path)

    require(data.get("campaign_id") == EXPECTED_CAMPAIGN_ID, "Unexpected campaign_id")
    require(str(data.get("stage")) == EXPECTED_STAGE, "Unexpected stage")

    validate_inputs(data)
    validate_stage4_steps(data)
    validate_command_path(data)
    validate_expected_telemetry(data)
    validate_boundary(data)

    print("Stage 5 closed-loop campaign plan validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
