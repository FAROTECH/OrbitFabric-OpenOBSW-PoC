#!/usr/bin/env python3
"""Stage 7.10c validator-first acceptance for Verification Projection Plans."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from integration_package.adapter.model import AdapterFailure
from integration_package.adapter.verification_plan import (
    validate_verification_projection_plan,
    validate_verification_projection_provenance,
    verification_projection_plan_bytes,
)

CASES_PATH = (
    REPO_ROOT / "integration_package" / "tests" / "stage7_10_projection_cases.json"
)


def _reference_plan() -> dict:
    return {
        "kind": "orbitfabric.verification_projection_plan",
        "plan_version": "0.1-candidate",
        "status": "executable_subset",
        "source": {
            "scenario_id": "stage7_10_ping",
            "scenario_name": "Stage 7.10 ping",
            "scenario_description": None,
            "scenario_sha256": "0" * 64,
            "orbitfabric_version": "1.2.0",
        },
        "core_input": {
            "kind": "orbitfabric.integration_input_set",
            "input_set_version": "0.1-candidate",
            "input_set_sha256": "1" * 64,
            "mission_id": "poc-cubesat",
            "model_version": "0.1.0",
        },
        "profile": {
            "kind": "orbitfabric.projection_profile",
            "profile_version": "0.1-candidate",
            "id": "poc-openobsw-opensvf",
            "version": "0.3.0",
            "sha256": "2" * 64,
        },
        "integration": {
            "id": "orbitfabric-openobsw-opensvf",
            "schema_version": "0.1-candidate",
            "adapter": {
                "id": "orbitfabric-openobsw-opensvf",
                "version": "0.1.0-dev.2",
            },
        },
        "accounting": {
            "source_atoms": 1,
            "projected_atoms": 1,
            "not_projected_atoms": 0,
            "blocked_atoms": 0,
            "source_actions": 1,
            "source_expectations": 0,
            "projected_source_actions": 1,
            "projected_source_expectations": 0,
            "profile_verification_obligations": 3,
        },
        "atoms": [
            {
                "id": "atom-0001",
                "kind": "command",
                "role": "action",
                "step_index": 0,
                "scenario_t": 5,
                "disposition": "projected",
                "source": {"domain": "commands", "id": "obc.ping"},
                "binding_id": "cmd.ping",
                "operation_ids": [
                    "op-0001",
                    "op-0002",
                    "op-0003",
                    "op-0004",
                ],
                "reason": None,
            }
        ],
        "operations": [
            {
                "id": "op-0001",
                "order": 0,
                "operation": "pus_tc",
                "source_atom_id": "atom-0001",
                "binding_id": "cmd.ping",
                "origin": "profile_mapping",
                "resolved": {
                    "apid": 16,
                    "service": 17,
                    "subtype": 1,
                    "data_hex": "",
                },
            },
            {
                "id": "op-0002",
                "order": 1,
                "operation": "expect_pus_tm",
                "source_atom_id": "atom-0001",
                "binding_id": "cmd.ping",
                "origin": "profile_expected_response",
                "resolved": {"service": 1, "subtype": 1},
            },
            {
                "id": "op-0003",
                "order": 2,
                "operation": "expect_pus_tm",
                "source_atom_id": "atom-0001",
                "binding_id": "cmd.ping",
                "origin": "profile_expected_response",
                "resolved": {"service": 17, "subtype": 2},
            },
            {
                "id": "op-0004",
                "order": 3,
                "operation": "expect_pus_tm",
                "source_atom_id": "atom-0001",
                "binding_id": "cmd.ping",
                "origin": "profile_expected_response",
                "resolved": {"service": 1, "subtype": 7},
            },
        ],
        "diagnostics": [],
    }


def _core() -> SimpleNamespace:
    return SimpleNamespace(
        manifest={
            "kind": "orbitfabric.integration_input_set",
            "input_set_version": "0.1-candidate",
            "input_set_sha256": "1" * 64,
            "orbitfabric_version": "1.2.0",
            "mission": {"id": "poc-cubesat", "model_version": "0.1.0"},
        },
        sha256="1" * 64,
        mission={"id": "poc-cubesat", "model_version": "0.1.0"},
    )


def _profile() -> SimpleNamespace:
    binding = {
        "id": "cmd.ping",
        "intent": "project",
        "sources": [{"domain": "commands", "id": "obc.ping"}],
        "config": {
            "pus": {"service": 17, "subtype": 1},
            "expected_responses": [
                {"service": 1, "subtype": 1},
                {"service": 17, "subtype": 2},
                {"service": 1, "subtype": 7},
            ],
        },
    }
    return SimpleNamespace(
        document={
            "kind": "orbitfabric.projection_profile",
            "profile_version": "0.1-candidate",
            "settings": {"pus": {"tc_apid": 16}},
        },
        id="poc-openobsw-opensvf",
        version="0.3.0",
        sha256="2" * 64,
        bindings=[binding],
    )


def _expect_plan_failure(label: str, plan: dict) -> None:
    try:
        validate_verification_projection_plan(plan)
    except AdapterFailure as exc:
        if exc.code != "OFI-VPROJ-PLAN-001":
            raise AssertionError(f"{label}: unexpected code {exc.code}") from exc
        print(f"  {label} PASS")
        return
    raise AssertionError(f"{label}: invalid plan was accepted")


def _run_unit_tests() -> None:
    suite = unittest.defaultTestLoader.loadTestsFromName(
        "integration_package.tests.test_verification_projection_plan"
    )
    result = unittest.TextTestRunner(verbosity=0).run(suite)
    if not result.wasSuccessful():
        raise AssertionError("Stage 7.10c unit tests failed")


def main() -> int:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    ids = [item["id"] for item in cases["cases"]]
    expected_ids = [f"VP-{index:03d}" for index in range(1, 17)]
    assert ids == expected_ids

    plan = _reference_plan()
    validate_verification_projection_plan(plan)

    print("Stage 7.10c Verification Projection Plan validator acceptance:")
    print("  schema + reference plan PASS")

    invalid = copy.deepcopy(plan)
    invalid["accounting"]["profile_verification_obligations"] = 2
    _expect_plan_failure("exact atom/operation accounting", invalid)

    invalid = copy.deepcopy(plan)
    invalid["operations"][0]["source_atom_id"] = "atom-9999"
    _expect_plan_failure("atom -> operation reference integrity", invalid)

    invalid = copy.deepcopy(plan)
    invalid["operations"][2]["order"] = 99
    _expect_plan_failure("contiguous operation ordering", invalid)

    invalid = copy.deepcopy(plan)
    invalid["operations"] = invalid["operations"][1:]
    for index, operation in enumerate(invalid["operations"]):
        operation["order"] = index
    invalid["atoms"][0]["operation_ids"] = [
        operation["id"] for operation in invalid["operations"]
    ]
    _expect_plan_failure("projected command requires one PUS TC", invalid)

    invalid = copy.deepcopy(plan)
    invalid["operations"][1]["binding_id"] = "cmd.other"
    _expect_plan_failure("atom/operation binding integrity", invalid)

    with tempfile.TemporaryDirectory() as directory:
        scenario = Path(directory) / "scenario.yaml"
        scenario.write_text("scenario: stage7_10_ping\n", encoding="utf-8")
        provenance_plan = _reference_plan()
        provenance_plan["source"]["scenario_sha256"] = hashlib.sha256(
            scenario.read_bytes()
        ).hexdigest()

        validate_verification_projection_provenance(
            provenance_plan,
            scenario_path=scenario,
            core=_core(),
            profile=_profile(),
        )
        print("  exact Core/Profile/scenario provenance PASS")
        print("  exact Profile PUS mapping + expected_responses PASS")

        mismatch = copy.deepcopy(provenance_plan)
        mismatch["operations"][2]["resolved"]["subtype"] = 99
        try:
            validate_verification_projection_provenance(
                mismatch,
                scenario_path=scenario,
                core=_core(),
                profile=_profile(),
            )
        except AdapterFailure as exc:
            assert exc.code == "OFI-VPROJ-PROVENANCE-001"
            print("  Profile verification obligation mismatch rejection PASS")
        else:
            raise AssertionError("Profile obligation mismatch was accepted")

    first = verification_projection_plan_bytes(plan)
    second = verification_projection_plan_bytes(copy.deepcopy(plan))
    assert first == second
    assert first.endswith(b"\n")
    print("  deterministic JSON bytes PASS")

    _run_unit_tests()
    print("  unit test suite PASS")
    print("  acceptance matrix VP-001..VP-016 present PASS")

    print("Stage 7.10c validator-first acceptance: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
