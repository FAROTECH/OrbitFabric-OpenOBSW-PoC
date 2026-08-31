from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from integration_package.adapter.model import AdapterFailure
from integration_package.adapter.verification_projector import (
    project_loaded_scenario,
)
from integration_package.adapter.verification_plan import (
    verification_projection_plan_bytes,
)


class _Core:
    def __init__(self) -> None:
        self.manifest = {
            "kind": "orbitfabric.integration_input_set",
            "input_set_version": "0.1-candidate",
            "input_set_sha256": "1" * 64,
            "orbitfabric_version": "1.2.0",
            "mission": {
                "id": "opensvf-openobsw-poc",
                "model_version": "0.1.0",
            },
        }
        self.sha256 = "1" * 64
        self.mission = self.manifest["mission"]
        self.entities = {
            ("modes", "NOMINAL"),
            ("commands", "obc.ping"),
            ("events", "obc.ping_requested"),
        }

    def resolve_source(self, domain: str, identifier: str) -> dict:
        if (domain, identifier) not in self.entities:
            raise AdapterFailure(
                "OFI-SOURCE-001",
                "source_resolution",
                f"missing {domain}/{identifier}",
            )
        return {"domain": domain, "id": identifier}


def _profile(*, intent: str = "project", duplicate: bool = False) -> SimpleNamespace:
    binding = {
        "id": "cmd.ping",
        "intent": intent,
        "sources": [{"domain": "commands", "id": "obc.ping"}],
        "config": (
            {
                "pus": {"service": 17, "subtype": 1},
                "expected_responses": [
                    {"service": 1, "subtype": 1},
                    {"service": 17, "subtype": 2},
                    {"service": 1, "subtype": 7},
                ],
            }
            if intent == "project"
            else {}
        ),
    }
    bindings = [binding]
    if duplicate:
        other = copy.deepcopy(binding)
        other["id"] = "cmd.ping.alt"
        bindings.append(other)
    return SimpleNamespace(
        document={
            "kind": "orbitfabric.projection_profile",
            "profile_version": "0.1-candidate",
            "settings": {
                "pus": {"tc_apid": 16},
                "compatibility": {"target_baseline": "unused-in-unit-test"},
            },
        },
        id="poc-openobsw-opensvf",
        version="0.3.0",
        schema_version="0.1-candidate",
        sha256="2" * 64,
        bindings=bindings,
    )


def _loaded(
    *,
    args: dict | None = None,
    expect: dict | None = None,
    event: str | None = "obc.ping_requested",
    mission_id: str = "opensvf-openobsw-poc",
) -> SimpleNamespace:
    metadata = SimpleNamespace(
        id="stage7_10_ping_verification",
        name="Stage 7.10 ping verification",
        description="Unit-test scenario",
    )
    steps = [
        SimpleNamespace(
            t=5,
            command="obc.ping",
            args={} if args is None else args,
            inject=None,
            expect_event=None,
            expect_mode=None,
            expect_command=None,
            expect_telemetry=None,
            expect={"command_status": "ACCEPTED"} if expect is None else expect,
        ),
        SimpleNamespace(
            t=6,
            command=None,
            args={},
            inject=None,
            expect_event=event,
            expect_mode=None,
            expect_command=None,
            expect_telemetry=None,
            expect=None,
        ),
        SimpleNamespace(
            t=7,
            command=None,
            args={},
            inject=None,
            expect_event=None,
            expect_mode=None,
            expect_command=None,
            expect_telemetry=None,
            expect={"scenario_status": "PASSED"},
        ),
    ]
    scenario = SimpleNamespace(
        scenario=metadata,
        initial_state=SimpleNamespace(mode="NOMINAL", telemetry={}),
        steps=steps,
    )
    mission = SimpleNamespace(
        spacecraft=SimpleNamespace(id=mission_id, model_version="0.1.0")
    )
    return SimpleNamespace(scenario=scenario, mission_model=mission)


def _scenario_file() -> tempfile.TemporaryDirectory:
    return tempfile.TemporaryDirectory()


class VerificationProjectorTests(unittest.TestCase):
    def _project(
        self,
        loaded: SimpleNamespace,
        *,
        profile: SimpleNamespace | None = None,
    ) -> dict:
        with tempfile.TemporaryDirectory() as directory:
            scenario = Path(directory) / "scenario.yaml"
            scenario.write_text("scenario: fixture\n", encoding="utf-8")
            with patch(
                "integration_package.adapter.verification_projector."
                "_validate_target_profile_compatibility"
            ):
                return project_loaded_scenario(
                    loaded,
                    scenario_path=scenario,
                    core=_Core(),
                    profile=profile or _profile(),
                    orbitfabric_version="1.2.0",
                )

    def test_reference_slice_projects_only_ping_action(self) -> None:
        plan = self._project(_loaded())
        self.assertEqual(plan["status"], "executable_subset")
        self.assertEqual(
            plan["accounting"],
            {
                "source_atoms": 6,
                "projected_atoms": 2,
                "not_projected_atoms": 4,
                "blocked_atoms": 0,
                "source_actions": 1,
                "source_expectations": 3,
                "projected_source_actions": 1,
                "projected_source_expectations": 0,
                "profile_verification_obligations": 3,
            },
        )
        self.assertEqual(
            [item["operation"] for item in plan["operations"]],
            ["pus_tc", "expect_pus_tm", "expect_pus_tm", "expect_pus_tm"],
        )
        self.assertEqual(plan["operations"][0]["resolved"]["service"], 17)
        self.assertEqual(plan["operations"][0]["resolved"]["subtype"], 1)

    def test_command_status_is_explicitly_not_projected(self) -> None:
        plan = self._project(_loaded())
        atoms = {item["kind"]: item for item in plan["atoms"]}
        self.assertEqual(
            atoms["expect_command_status"]["disposition"],
            "not_projected",
        )
        self.assertEqual(
            plan["operations"][1]["origin"],
            "profile_expected_response",
        )

    def test_scenario_time_is_provenance_only(self) -> None:
        plan = self._project(_loaded())
        command = next(item for item in plan["atoms"] if item["kind"] == "command")
        self.assertEqual(command["scenario_t"], 5)
        self.assertNotIn(
            "wait",
            {item["operation"] for item in plan["operations"]},
        )
        self.assertNotIn(
            "schedule_tc",
            {item["operation"] for item in plan["operations"]},
        )

    def test_command_arguments_block_projection(self) -> None:
        plan = self._project(_loaded(args={"value": 1}))
        self.assertEqual(plan["status"], "blocked")
        codes = [item["code"] for item in plan["diagnostics"]]
        self.assertEqual(codes, ["OFI-VPROJ-CMDARGS-001"])
        command = next(item for item in plan["atoms"] if item["kind"] == "command")
        self.assertEqual(command["disposition"], "blocked")
        self.assertEqual(plan["operations"], [])

    def test_missing_binding_blocks_projection(self) -> None:
        profile = _profile()
        profile.bindings = []
        plan = self._project(_loaded(), profile=profile)
        self.assertEqual(plan["status"], "blocked")
        self.assertEqual(
            plan["diagnostics"][0]["code"],
            "OFI-VPROJ-BINDING-001",
        )

    def test_do_not_project_binding_blocks_projection(self) -> None:
        plan = self._project(_loaded(), profile=_profile(intent="do_not_project"))
        self.assertEqual(plan["status"], "blocked")
        self.assertEqual(
            plan["diagnostics"][0]["code"],
            "OFI-VPROJ-INTENT-001",
        )

    def test_ambiguous_binding_blocks_projection(self) -> None:
        plan = self._project(_loaded(), profile=_profile(duplicate=True))
        self.assertEqual(plan["status"], "blocked")
        self.assertEqual(
            plan["diagnostics"][0]["code"],
            "OFI-VPROJ-AMBIGUOUS-001",
        )

    def test_unknown_nested_expectation_is_rejected(self) -> None:
        loaded = _loaded(expect={"future_semantic": True})
        with tempfile.TemporaryDirectory() as directory:
            scenario = Path(directory) / "scenario.yaml"
            scenario.write_text("scenario: fixture\n", encoding="utf-8")
            with patch(
                "integration_package.adapter.verification_projector."
                "_validate_target_profile_compatibility"
            ):
                with self.assertRaises(AdapterFailure) as context:
                    project_loaded_scenario(
                        loaded,
                        scenario_path=scenario,
                        core=_Core(),
                        profile=_profile(),
                        orbitfabric_version="1.2.0",
                    )
        self.assertEqual(context.exception.code, "OFI-VPROJ-SCENARIO-002")

    def test_mission_identity_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            scenario = Path(directory) / "scenario.yaml"
            scenario.write_text("scenario: fixture\n", encoding="utf-8")
            with self.assertRaises(AdapterFailure) as context:
                project_loaded_scenario(
                    _loaded(mission_id="other-mission"),
                    scenario_path=scenario,
                    core=_Core(),
                    profile=_profile(),
                    orbitfabric_version="1.2.0",
                )
        self.assertEqual(context.exception.code, "OFI-VPROJ-PROVENANCE-001")

    def test_identical_inputs_produce_identical_plan_bytes(self) -> None:
        first = self._project(_loaded())
        second = self._project(_loaded())
        # Scenario fixture bytes and semantic inputs are identical.
        self.assertEqual(
            verification_projection_plan_bytes(first),
            verification_projection_plan_bytes(second),
        )


if __name__ == "__main__":
    unittest.main()
