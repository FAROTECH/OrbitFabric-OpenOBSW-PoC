#!/usr/bin/env python3
"""Validate Stage 6.2 OpenSVF bridge readiness boundary.

This validator checks the PoC-side OpenSVF bridge readiness surface.

It intentionally does not execute YAMCS, OpenSVF runtime campaigns, OpenOBSW
host-sim, command injection, telemetry observation, Docker, CI, or Renode.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]

DOC_PATH = REPO_ROOT / "docs" / "stage6_2_opensvf_bridge_readiness.md"
SPACECRAFT_CONFIG_PATH = REPO_ROOT / "execution" / "opensvf" / "poc_spacecraft.yaml"
RUNTIME_INPUTS_PATH = REPO_ROOT / "execution" / "opensvf" / "poc_runtime_inputs.yaml"
RUNTIME_PING_PLAN_PATH = REPO_ROOT / "execution" / "campaigns" / "poc_runtime_ping_plan.yaml"

EXPECTED_STAGE = "6.2"
EXPECTED_RUNTIME_INPUT_ID = "poc_opensvf_bridge_readiness_inputs"
EXPECTED_CAMPAIGN_ID = "poc_runtime_ping_plan"

EXPECTED_TM_SEQUENCE = ["TM(1,1)", "TM(17,2)", "TM(1,7)"]

EXPECTED_BOUNDARY_FALSE_KEYS = [
    "yamcs_runtime_execution",
    "command_injection_runtime",
    "telemetry_runtime_observation",
    "docker_workflow",
    "ci_workflow",
    "renode_execution",
    "opensvf_proper_changes",
    "openobsw_proper_changes",
    "custom_bridge_process",
    "runtime_bridge_implementation",
]

FORBIDDEN_SPACECRAFT_KEYS = {
    "srdb",
    "srdb_path",
    "xtce",
    "xtce_path",
    "mdb",
    "mdb_path",
    "yamcs",
    "yamcs_mdb",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def load_yaml(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"YAML file not found: {path}")
    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    require(isinstance(data, dict), f"YAML file must contain a mapping: {path}")
    return data


def read_text(path: Path) -> str:
    require(path.is_file(), f"File not found: {path}")
    return path.read_text(encoding="utf-8")


def resolve_repo_path(relative_path: str) -> Path:
    return (REPO_ROOT / relative_path).resolve()


def validate_boundary_false(boundary: Any, label: str) -> None:
    require(isinstance(boundary, dict), f"{label} must be a mapping")

    for key in EXPECTED_BOUNDARY_FALSE_KEYS:
        require(boundary.get(key) is False, f"{label}.{key} must be false")


def validate_doc() -> None:
    text = read_text(DOC_PATH)

    markers = [
        "Stage 6.2 OpenSVF bridge readiness wrapper",
        "OpenSVF pipe mode as the candidate bridge",
        "does not introduce a custom bridge process",
        "execution/opensvf/poc_spacecraft.yaml",
        "execution/opensvf/poc_runtime_inputs.yaml",
        "execution/campaigns/poc_runtime_ping_plan.yaml",
        "TC(17,1)",
        "TM(1,1), TM(17,2), TM(1,7)",
        "does not invent an unsupported SRDB, XTCE, MDB or YAMCS field inside `spacecraft.yaml`",
        "YAMCS runtime execution",
        "OpenSVF proper changes",
        "OpenOBSW proper changes",
    ]

    for marker in markers:
        require(marker in text, f"Missing Stage 6.2 document marker: {marker}")


def find_forbidden_keys(data: Any, path: str = "") -> list[str]:
    found: list[str] = []

    if isinstance(data, dict):
        for key, value in data.items():
            key_path = f"{path}.{key}" if path else str(key)
            if str(key) in FORBIDDEN_SPACECRAFT_KEYS:
                found.append(key_path)
            found.extend(find_forbidden_keys(value, key_path))
    elif isinstance(data, list):
        for index, item in enumerate(data):
            found.extend(find_forbidden_keys(item, f"{path}[{index}]"))

    return found


def validate_spacecraft_config() -> None:
    data = load_yaml(SPACECRAFT_CONFIG_PATH)

    require(data.get("version") == 1, "spacecraft config version must be 1")
    require(data.get("spacecraft") == "OrbitFabric-OpenOBSW-PoC", "Unexpected spacecraft name")

    forbidden = find_forbidden_keys(data)
    require(
        not forbidden,
        "spacecraft config must not invent unsupported SRDB/XTCE/YAMCS fields: "
        + ", ".join(forbidden),
    )

    obsw = data.get("obsw")
    require(isinstance(obsw, dict), "spacecraft config must define obsw mapping")
    require(obsw.get("type") == "pipe", "obsw.type must be pipe")

    binary = obsw.get("binary")
    require(isinstance(binary, str) and binary, "obsw.binary must be a non-empty string")

    resolved_binary = (SPACECRAFT_CONFIG_PATH.parent / binary).resolve()
    expected_binary = (REPO_ROOT / "../openobsw/build_stage4_orbitfabric/sim/obsw_sim").resolve()

    require(
        resolved_binary == expected_binary,
        f"obsw.binary resolves to unexpected path: {resolved_binary}",
    )

    if not resolved_binary.exists():
        print(f"[info] OpenOBSW host-sim binary not found locally: {resolved_binary}")

    simulation = data.get("simulation")
    require(isinstance(simulation, dict), "spacecraft config must define simulation mapping")
    require(float(simulation.get("dt")) > 0.0, "simulation.dt must be positive")
    require(float(simulation.get("stop_time")) > 0.0, "simulation.stop_time must be positive")
    require(simulation.get("realtime") is False, "simulation.realtime must be false")


def validate_runtime_inputs() -> None:
    data = load_yaml(RUNTIME_INPUTS_PATH)

    require(data.get("runtime_input_id") == EXPECTED_RUNTIME_INPUT_ID, "Unexpected runtime_input_id")
    require(str(data.get("stage")) == EXPECTED_STAGE, "Unexpected stage")
    require(data.get("status") == "bridge_readiness", "status must be bridge_readiness")

    bridge = data.get("bridge_assumption")
    require(isinstance(bridge, dict), "bridge_assumption must be a mapping")
    require(bridge.get("candidate_bridge") == "opensvf_pipe_mode", "Unexpected candidate bridge")
    require(bridge.get("custom_bridge_process") is False, "custom_bridge_process must be false")

    opensvf = data.get("opensvf")
    require(isinstance(opensvf, dict), "opensvf must be a mapping")
    require(opensvf.get("spacecraft_config") == "execution/opensvf/poc_spacecraft.yaml",
            "Unexpected opensvf.spacecraft_config")
    require(opensvf.get("transport_mode") == "pipe", "opensvf.transport_mode must be pipe")
    require(
        opensvf.get("external_srdb_path_direct_support_assumed") is False,
        "external_srdb_path_direct_support_assumed must be false",
    )

    openobsw = data.get("openobsw")
    require(isinstance(openobsw, dict), "openobsw must be a mapping")
    require(
        openobsw.get("host_sim_binary") == "../openobsw/build_stage4_orbitfabric/sim/obsw_sim",
        "Unexpected openobsw.host_sim_binary",
    )

    generated = data.get("generated_artifacts")
    require(isinstance(generated, dict), "generated_artifacts must be a mapping")

    expected_artifacts = {
        "flight_contract": "generated_artifacts/flight_software/mission_contract.h",
        "generated_srdb": "generated_artifacts/ground_segment/poc_srdb.yaml",
        "generated_xtce_mdb": "execution/generated/poc_xtce_mdb.xml",
    }

    for key, expected_path in expected_artifacts.items():
        entry = generated.get(key)
        require(isinstance(entry, dict), f"generated_artifacts.{key} must be a mapping")
        require(entry.get("path") == expected_path, f"Unexpected generated_artifacts.{key}.path")

        required_for_clean_clone = entry.get("required_for_clean_clone_validation")
        require(
            isinstance(required_for_clean_clone, bool),
            f"generated_artifacts.{key}.required_for_clean_clone_validation must be boolean",
        )

        artifact_path = resolve_repo_path(expected_path)
        if required_for_clean_clone:
            require(artifact_path.is_file(), f"Required generated artifact not found: {expected_path}")
        elif not artifact_path.is_file():
            print(f"[info] Optional local generated artifact not found: {expected_path}")

    runtime_plan = data.get("runtime_plan")
    require(isinstance(runtime_plan, dict), "runtime_plan must be a mapping")
    require(runtime_plan.get("descriptor") == "execution/campaigns/poc_runtime_ping_plan.yaml",
            "Unexpected runtime_plan.descriptor")
    require(runtime_plan.get("first_command") == "TC(17,1)", "Unexpected runtime_plan.first_command")
    require(runtime_plan.get("orbitfabric_command") == "OF_CMD_PING",
            "Unexpected runtime_plan.orbitfabric_command")
    require(runtime_plan.get("expected_tm_sequence") == EXPECTED_TM_SEQUENCE,
            "Unexpected runtime_plan.expected_tm_sequence")

    dependencies = data.get("stage_dependencies")
    require(isinstance(dependencies, dict), "stage_dependencies must be a mapping")

    for key, rel_path in dependencies.items():
        require(isinstance(rel_path, str), f"stage_dependencies.{key} must be a string")
        require(resolve_repo_path(rel_path).is_file(), f"Stage dependency not found: {rel_path}")

    validate_boundary_false(data.get("current_boundary"), "current_boundary")


def validate_runtime_ping_plan() -> None:
    data = load_yaml(RUNTIME_PING_PLAN_PATH)

    require(data.get("campaign_id") == EXPECTED_CAMPAIGN_ID, "Unexpected campaign_id")
    require(str(data.get("stage")) == EXPECTED_STAGE, "Unexpected stage")
    require(data.get("status") == "readiness_plan", "status must be readiness_plan")

    bridge = data.get("bridge_assumption")
    require(isinstance(bridge, dict), "bridge_assumption must be a mapping")
    require(bridge.get("candidate_bridge") == "opensvf_pipe_mode", "Unexpected candidate bridge")
    require(bridge.get("custom_bridge_process") is False, "custom_bridge_process must be false")
    require(
        bridge.get("opensvf_proper_changes_required_now") is False,
        "opensvf_proper_changes_required_now must be false",
    )
    require(
        bridge.get("openobsw_proper_changes_required_now") is False,
        "openobsw_proper_changes_required_now must be false",
    )

    spacecraft = data.get("spacecraft_config")
    require(isinstance(spacecraft, dict), "spacecraft_config must be a mapping")
    require(spacecraft.get("path") == "execution/opensvf/poc_spacecraft.yaml",
            "Unexpected spacecraft_config.path")
    require(spacecraft.get("obsw_transport") == "pipe", "spacecraft_config.obsw_transport must be pipe")

    command = data.get("command_under_test")
    require(isinstance(command, dict), "command_under_test must be a mapping")
    require(command.get("orbitfabric_command") == "OF_CMD_PING",
            "Unexpected command_under_test.orbitfabric_command")
    require(command.get("pus_service") == 17, "Unexpected command_under_test.pus_service")
    require(command.get("pus_subtype") == 1, "Unexpected command_under_test.pus_subtype")
    require(command.get("tc") == "TC(17,1)", "Unexpected command_under_test.tc")

    tm_sequence = data.get("expected_telemetry_sequence")
    require(isinstance(tm_sequence, list), "expected_telemetry_sequence must be a list")
    require([entry.get("tm") for entry in tm_sequence] == EXPECTED_TM_SEQUENCE,
            "Unexpected expected_telemetry_sequence")

    validate_boundary_false(data.get("current_boundary"), "current_boundary")


def validate_with_opensvf_preflight(opensvf_repo: Path) -> None:
    if not opensvf_repo.is_dir():
        print(f"[skip] OpenSVF repo not found at {opensvf_repo} - preflight skipped")
        return

    src_path = opensvf_repo / "src"
    require(src_path.is_dir(), f"OpenSVF src directory not found: {src_path}")

    sys.path.insert(0, str(src_path))

    try:
        from svf.config.validator import SpacecraftValidator
    except Exception as exc:
        raise SystemExit(f"Could not import OpenSVF SpacecraftValidator: {exc}") from exc

    try:
        SpacecraftValidator.validate_or_raise(SPACECRAFT_CONFIG_PATH)
    except Exception as exc:
        raise SystemExit(f"OpenSVF SpacecraftValidator rejected PoC config: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Stage 6.2 OpenSVF bridge readiness boundary."
    )
    parser.add_argument(
        "--opensvf-repo",
        default="../opensvf",
        help="Path to the OpenSVF repository. Default: ../opensvf",
    )

    args = parser.parse_args()

    opensvf_repo = Path(args.opensvf_repo)
    if not opensvf_repo.is_absolute():
        opensvf_repo = (REPO_ROOT / opensvf_repo).resolve()

    validate_doc()
    validate_spacecraft_config()
    validate_runtime_inputs()
    validate_runtime_ping_plan()
    validate_with_opensvf_preflight(opensvf_repo)

    print("Stage 6.2 OpenSVF bridge readiness validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
