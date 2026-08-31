#!/usr/bin/env python3
"""Validate Stage 7.10d OrbitFabric scenario -> Verification Projection Plan."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


EXPECTED_ORBITFABRIC_COMMIT = "b1aa95408710f697b0ee144a7b41f2376395e01f"
EXPECTED_ORBITFABRIC_VERSION = "1.2.0"

EXPECTED_SCENARIO = "stage7_10_ping_verification"
EXPECTED_MISSION = "opensvf-openobsw-poc"
EXPECTED_MODEL_VERSION = "0.1.0"
EXPECTED_BINDING = "cmd.ping"

REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_PATH = (
    REPO_ROOT / "orbitfabric_models" / "scenarios" / "stage7_10_ping_verification.yaml"
)
MISSION_DIR = REPO_ROOT / "orbitfabric_models" / "mission"
PROFILE_PATH = REPO_ROOT / "projection_profiles" / "poc_openobsw_opensvf.yaml"


def _git_head(repo: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_status(repo: Path) -> str:
    return subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _write_scenario(path: Path, mission_dir: Path, *, args: dict, expect: dict) -> None:
    payload = {
        "scenario": {
            "id": "stage7_10_negative",
            "name": "Stage 7.10 negative fixture",
            "description": "Temporary acceptance fixture.",
        },
        "mission": {"path": str(mission_dir.resolve())},
        "initial_state": {"mode": "NOMINAL", "telemetry": {}},
        "steps": [
            {
                "t": 5,
                "command": "obc.ping",
                "args": args,
                "expect": expect,
            }
        ],
    }
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )


def _run_unit_tests() -> None:
    import unittest

    suite = unittest.defaultTestLoader.loadTestsFromName(
        "integration_package.tests.test_verification_projector"
    )
    result = unittest.TextTestRunner(verbosity=0).run(suite)
    if not result.wasSuccessful():
        raise AssertionError("Stage 7.10d unit tests failed")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate and validate the Stage 7.10d Verification Projection Plan "
            "from a real OrbitFabric scenario using OrbitFabric Core v1.2.0."
        )
    )
    parser.add_argument("--orbitfabric-repo", required=True, type=Path)
    parser.add_argument(
        "--plan-output",
        type=Path,
        default=Path(tempfile.gettempdir())
        / "orbitfabric_stage7_10_verification_projection_plan.json",
    )
    args = parser.parse_args()

    orbitfabric_repo = args.orbitfabric_repo.resolve()
    plan_output = args.plan_output.resolve()

    actual_core = _git_head(orbitfabric_repo)
    if actual_core != EXPECTED_ORBITFABRIC_COMMIT:
        raise SystemExit(
            "OrbitFabric checkout does not match the Stage 7.10d reference "
            f"{EXPECTED_ORBITFABRIC_COMMIT}; got {actual_core}"
        )

    before_core_status = _git_status(orbitfabric_repo)

    core_src = str((orbitfabric_repo / "src").resolve())
    if core_src not in sys.path:
        sys.path.insert(0, core_src)

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    import orbitfabric
    from orbitfabric.export.integration_input_set import write_integration_input_set
    from orbitfabric.model.scenario_loader import ScenarioLoader

    from integration_package.adapter.core_input import load_core_input_set
    from integration_package.adapter.model import AdapterFailure
    from integration_package.adapter.profile import load_projection_profile
    from integration_package.adapter.verification_plan import (
        verification_projection_plan_bytes,
        write_verification_projection_plan,
    )
    from integration_package.adapter.verification_projector import (
        project_verification_scenario,
    )

    assert orbitfabric.__version__ == EXPECTED_ORBITFABRIC_VERSION

    loaded = ScenarioLoader().load(SCENARIO_PATH)
    assert loaded.scenario.scenario.id == EXPECTED_SCENARIO
    assert loaded.mission_model.spacecraft.id == EXPECTED_MISSION
    assert loaded.mission_model.spacecraft.model_version == EXPECTED_MODEL_VERSION

    with tempfile.TemporaryDirectory(prefix="stage7_10d_core_input_") as directory:
        input_dir = Path(directory) / "input_set"
        result = write_integration_input_set(MISSION_DIR, input_dir)
        assert result.succeeded

        core = load_core_input_set(result.manifest_path)
        profile = load_projection_profile(PROFILE_PATH)

        plan = project_verification_scenario(
            SCENARIO_PATH,
            result.manifest_path,
            PROFILE_PATH,
        )

        assert plan["status"] == "executable_subset"
        assert plan["source"]["scenario_id"] == EXPECTED_SCENARIO
        assert plan["core_input"]["mission_id"] == EXPECTED_MISSION
        assert plan["core_input"]["model_version"] == EXPECTED_MODEL_VERSION

        assert plan["accounting"] == {
            "source_atoms": 6,
            "projected_atoms": 2,
            "not_projected_atoms": 4,
            "blocked_atoms": 0,
            "source_actions": 1,
            "source_expectations": 3,
            "projected_source_actions": 1,
            "projected_source_expectations": 0,
            "profile_verification_obligations": 3,
        }

        atoms = {item["kind"]: item for item in plan["atoms"]}
        assert atoms["scenario_metadata"]["disposition"] == "projected"
        assert atoms["initial_mode"]["disposition"] == "not_projected"
        assert atoms["command"]["disposition"] == "projected"
        assert atoms["command"]["binding_id"] == EXPECTED_BINDING
        assert atoms["expect_command_status"]["disposition"] == "not_projected"
        assert atoms["expect_event"]["disposition"] == "not_projected"
        assert atoms["expect_scenario_status"]["disposition"] == "not_projected"

        assert atoms["command"]["scenario_t"] == 5

        operations = plan["operations"]
        assert [item["operation"] for item in operations] == [
            "pus_tc",
            "expect_pus_tm",
            "expect_pus_tm",
            "expect_pus_tm",
        ]
        assert operations[0]["origin"] == "profile_mapping"
        assert operations[0]["resolved"] == {
            "apid": 16,
            "service": 17,
            "subtype": 1,
            "data_hex": "",
        }
        assert [item["resolved"] for item in operations[1:]] == [
            {"service": 1, "subtype": 1},
            {"service": 17, "subtype": 2},
            {"service": 1, "subtype": 7},
        ]
        assert all(
            item["origin"] == "profile_expected_response"
            for item in operations[1:]
        )
        assert not {"wait", "schedule_tc"} & {
            item["operation"] for item in operations
        }

        second = project_verification_scenario(
            SCENARIO_PATH,
            result.manifest_path,
            PROFILE_PATH,
        )
        assert verification_projection_plan_bytes(plan) == (
            verification_projection_plan_bytes(second)
        )

        write_verification_projection_plan(plan_output, plan)
        assert plan_output.is_file()

        # Negative: arguments must block rather than guess an encoder.
        args_scenario = Path(directory) / "command_args.yaml"
        _write_scenario(
            args_scenario,
            MISSION_DIR,
            args={"unexpected": 1},
            expect={"command_status": "ACCEPTED"},
        )
        blocked = project_verification_scenario(
            args_scenario,
            result.manifest_path,
            PROFILE_PATH,
        )
        assert blocked["status"] == "blocked"
        assert blocked["operations"] == []
        assert blocked["diagnostics"][0]["code"] == "OFI-VPROJ-CMDARGS-001"

        # Negative: unknown nested expectation semantics must fail closed.
        unknown_scenario = Path(directory) / "unknown_expect.yaml"
        _write_scenario(
            unknown_scenario,
            MISSION_DIR,
            args={},
            expect={"future_semantic": True},
        )
        try:
            project_verification_scenario(
                unknown_scenario,
                result.manifest_path,
                PROFILE_PATH,
            )
        except AdapterFailure as exc:
            assert exc.code == "OFI-VPROJ-SCENARIO-002"
        else:
            raise AssertionError("Unknown expectation semantics were accepted")

        # The loaded objects are consumed inputs only; projector has no OpenSVF dependency.
        assert core.sha256 == plan["core_input"]["input_set_sha256"]
        assert profile.sha256 == plan["profile"]["sha256"]
        assert "svf" not in sys.modules

    _run_unit_tests()

    after_core_status = _git_status(orbitfabric_repo)
    assert after_core_status == before_core_status

    print("Stage 7.10d verification projector acceptance: PASS")
    print(f"  OrbitFabric reference: {EXPECTED_ORBITFABRIC_COMMIT}")
    print(f"  scenario: {SCENARIO_PATH}")
    print("  native OrbitFabric ScenarioLoader validation PASS")
    print("  Core Integration Input Set generation/consumption PASS")
    print("  target Profile compatibility preflight reuse PASS")
    print("  semantic atom decomposition PASS")
    print("  obc.ping -> Profile cmd.ping -> PUS TC(17,1) PASS")
    print("  Profile expected_responses -> 3 target TM obligations PASS")
    print("  command_status remains not_projected PASS")
    print("  expect_event remains not_projected PASS")
    print("  scenario_status remains not_projected PASS")
    print("  scenario time remains provenance-only PASS")
    print("  command-argument fail-closed behavior PASS")
    print("  unknown expectation fail-closed behavior PASS")
    print("  deterministic plan bytes PASS")
    print("  no OpenSVF import/materialization PASS")
    print("  OrbitFabric working tree remained unchanged PASS")
    print("  Stage 7.10d unit test suite PASS")
    print(f"  plan JSON: {plan_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
