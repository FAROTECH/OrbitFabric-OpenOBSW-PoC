#!/usr/bin/env python3
"""Validate the Stage 6 runtime campaign discovery descriptor.

This validator does not execute YAMCS, Renode, Docker, CI, OpenSVF runtime
campaigns, or OpenOBSW runtime telemetry/event mapping.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_DISCOVERY_ID = "poc_runtime_campaign_discovery"
EXPECTED_STAGE = "6.0"

REQUIRED_BASELINE_INPUTS = {
    "campaign_descriptor",
    "evidence_bundle_generator",
    "xtce_mdb",
    "srdb",
    "flight_contract",
    "openobsw_host_sim",
}

REQUIRED_YAMCS_QUESTIONS = {
    "how_to_load_generated_xtce_mdb",
    "how_to_configure_local_instance",
    "how_to_observe_tm_1_1_tm_17_2_tm_1_7",
    "how_to_expose_command_injection_path",
}

REQUIRED_OPENSVF_QUESTIONS = {
    "how_to_reference_generated_xtce_mdb",
    "how_to_model_tc_17_1_campaign_step",
    "how_to_collect_runtime_evidence",
}

REQUIRED_OPENOBSW_QUESTIONS = {
    "how_to_connect_host_sim_to_ground_runtime",
    "whether_type_frame_protocol_can_be_bridged_directly",
    "whether_a_poc_bridge_process_is_needed",
}

EXPECTED_VISIBILITY = {
    "eps_obc_bus_voltage_mv",
    "TM_3_25_HK",
    "TC_17_1_or_equivalent_ping_command_path",
    "TM_1_1",
    "TM_17_2",
    "TM_1_7",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def load_yaml(path: Path) -> dict:
    require(path.is_file(), f"Runtime discovery descriptor not found: {path}")

    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)

    require(isinstance(data, dict), "Runtime discovery descriptor must be a YAML mapping")
    return data


def require_keys(mapping: dict, required: set[str], label: str) -> None:
    missing = required.difference(mapping.keys())
    require(not missing, f"Missing {label}: {sorted(missing)}")


def require_list_items(values: object, required: set[str], label: str) -> None:
    require(isinstance(values, list), f"{label} must be a list")
    value_set = set(values)
    missing = required.difference(value_set)
    require(not missing, f"Missing {label}: {sorted(missing)}")


def validate_baseline_inputs(data: dict) -> None:
    inputs = data.get("baseline_inputs")
    require(isinstance(inputs, dict), "baseline_inputs must be a mapping")
    require_keys(inputs, REQUIRED_BASELINE_INPUTS, "baseline_inputs")

    for key in REQUIRED_BASELINE_INPUTS:
        value = inputs[key]
        require(isinstance(value, str) and value, f"baseline_inputs.{key} must be a non-empty string")


def validate_runtime_questions(data: dict) -> None:
    questions = data.get("runtime_questions")
    require(isinstance(questions, dict), "runtime_questions must be a mapping")

    require_list_items(questions.get("yamcs"), REQUIRED_YAMCS_QUESTIONS, "runtime_questions.yamcs")
    require_list_items(questions.get("opensvf"), REQUIRED_OPENSVF_QUESTIONS, "runtime_questions.opensvf")
    require_list_items(questions.get("openobsw"), REQUIRED_OPENOBSW_QUESTIONS, "runtime_questions.openobsw")


def validate_first_runtime_experiment(data: dict) -> None:
    experiment = data.get("first_runtime_experiment")
    require(isinstance(experiment, dict), "first_runtime_experiment must be a mapping")

    require(isinstance(experiment.get("goal"), str) and experiment["goal"], "first_runtime_experiment.goal must be non-empty")
    require_list_items(
        experiment.get("expected_visibility"),
        EXPECTED_VISIBILITY,
        "first_runtime_experiment.expected_visibility",
    )


def validate_boundary(data: dict) -> None:
    boundary = data.get("current_boundary")
    require(isinstance(boundary, dict), "current_boundary must be a mapping")

    for key, value in boundary.items():
        require(value is False, f"current_boundary.{key} must be false")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the Stage 6 runtime campaign discovery descriptor."
    )
    parser.add_argument(
        "--discovery",
        default="execution/campaigns/poc_runtime_discovery.yaml",
        help="Path to the Stage 6 runtime discovery descriptor.",
    )

    args = parser.parse_args()

    discovery_path = Path(args.discovery)
    if not discovery_path.is_absolute():
        discovery_path = REPO_ROOT / discovery_path

    data = load_yaml(discovery_path)

    require(data.get("discovery_id") == EXPECTED_DISCOVERY_ID, "Unexpected discovery_id")
    require(str(data.get("stage")) == EXPECTED_STAGE, "Unexpected stage")

    validate_baseline_inputs(data)
    validate_runtime_questions(data)
    validate_first_runtime_experiment(data)
    validate_boundary(data)

    print("Stage 6 runtime campaign discovery validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
