from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from integration_package.adapter.model import AdapterFailure
from integration_package.adapter.verification_plan import (
    validate_verification_projection_plan,
    validate_verification_projection_provenance,
    verification_projection_plan_bytes,
    write_verification_projection_plan,
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


class VerificationProjectionPlanTests(unittest.TestCase):
    def test_reference_plan_validates(self) -> None:
        validate_verification_projection_plan(_reference_plan())

    def test_duplicate_atom_id_is_rejected(self) -> None:
        plan = _reference_plan()
        duplicate = copy.deepcopy(plan["atoms"][0])
        duplicate["operation_ids"] = []
        duplicate["binding_id"] = None
        duplicate["disposition"] = "not_projected"
        duplicate["reason"] = "duplicate fixture"
        plan["atoms"].append(duplicate)
        plan["accounting"]["source_atoms"] = 2
        plan["accounting"]["not_projected_atoms"] = 1
        with self.assertRaises(AdapterFailure) as context:
            validate_verification_projection_plan(plan)
        self.assertEqual(context.exception.code, "OFI-VPROJ-PLAN-001")

    def test_operation_reference_integrity_is_enforced(self) -> None:
        plan = _reference_plan()
        plan["operations"][0]["source_atom_id"] = "atom-9999"
        with self.assertRaises(AdapterFailure):
            validate_verification_projection_plan(plan)

    def test_operation_ordering_is_enforced(self) -> None:
        plan = _reference_plan()
        plan["operations"][2]["order"] = 99
        with self.assertRaises(AdapterFailure):
            validate_verification_projection_plan(plan)

    def test_accounting_is_recomputed(self) -> None:
        plan = _reference_plan()
        plan["accounting"]["profile_verification_obligations"] = 2
        with self.assertRaises(AdapterFailure):
            validate_verification_projection_plan(plan)

    def test_blocked_atom_requires_blocked_status(self) -> None:
        plan = _reference_plan()
        atom = plan["atoms"][0]
        atom["disposition"] = "blocked"
        atom["binding_id"] = None
        atom["operation_ids"] = []
        atom["reason"] = "missing executable binding"
        plan["operations"] = []
        plan["accounting"].update(
            {
                "projected_atoms": 0,
                "blocked_atoms": 1,
                "projected_source_actions": 0,
                "profile_verification_obligations": 0,
            }
        )
        with self.assertRaises(AdapterFailure):
            validate_verification_projection_plan(plan)

    def test_projected_command_requires_one_pus_tc(self) -> None:
        plan = _reference_plan()
        plan["operations"] = plan["operations"][1:]
        for index, operation in enumerate(plan["operations"]):
            operation["order"] = index
        plan["atoms"][0]["operation_ids"] = [
            operation["id"] for operation in plan["operations"]
        ]
        with self.assertRaises(AdapterFailure):
            validate_verification_projection_plan(plan)

    def test_projected_expectation_is_rejected_in_v0(self) -> None:
        plan = _reference_plan()
        plan["atoms"][0]["kind"] = "expect_command"
        plan["atoms"][0]["role"] = "expectation"
        plan["accounting"]["source_actions"] = 0
        plan["accounting"]["source_expectations"] = 1
        plan["accounting"]["projected_source_actions"] = 0
        plan["accounting"]["projected_source_expectations"] = 1
        with self.assertRaises(AdapterFailure):
            validate_verification_projection_plan(plan)

    def test_exact_profile_operations_are_verified(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            scenario = Path(directory) / "scenario.yaml"
            scenario.write_text("scenario: stage7_10_ping\n", encoding="utf-8")
            plan = _reference_plan()
            plan["source"]["scenario_sha256"] = hashlib.sha256(
                scenario.read_bytes()
            ).hexdigest()
            validate_verification_projection_provenance(
                plan,
                scenario_path=scenario,
                core=_core(),
                profile=_profile(),
            )

    def test_profile_expected_response_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            scenario = Path(directory) / "scenario.yaml"
            scenario.write_text("scenario: stage7_10_ping\n", encoding="utf-8")
            plan = _reference_plan()
            plan["source"]["scenario_sha256"] = hashlib.sha256(
                scenario.read_bytes()
            ).hexdigest()
            plan["operations"][2]["resolved"]["subtype"] = 99
            with self.assertRaises(AdapterFailure) as context:
                validate_verification_projection_provenance(
                    plan,
                    scenario_path=scenario,
                    core=_core(),
                    profile=_profile(),
                )
        self.assertEqual(context.exception.code, "OFI-VPROJ-PROVENANCE-001")

    def test_deterministic_writer_is_byte_stable(self) -> None:
        plan = _reference_plan()
        first = verification_projection_plan_bytes(plan)
        second = verification_projection_plan_bytes(copy.deepcopy(plan))
        self.assertEqual(first, second)
        self.assertTrue(first.endswith(b"\n"))

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            write_verification_projection_plan(path, plan)
            self.assertEqual(path.read_bytes(), first)


if __name__ == "__main__":
    unittest.main()
