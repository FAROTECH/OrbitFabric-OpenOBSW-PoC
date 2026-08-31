from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from integration_package.adapter.model import AdapterFailure
from integration_package.adapter.opensvf_materializer import (
    CAMPAIGN_REL,
    MANIFEST_REL,
    PROCEDURE_REL,
    SPACECRAFT_REL,
    materialize_opensvf_plan,
)
from integration_package.adapter.verification_plan import (
    write_verification_projection_plan,
)


def _reference_plan() -> dict:
    return {
        "kind": "orbitfabric.verification_projection_plan",
        "plan_version": "0.1-candidate",
        "status": "executable_subset",
        "source": {
            "scenario_id": "stage7_10_ping_verification",
            "scenario_name": "Stage 7.10 ping verification",
            "scenario_description": None,
            "scenario_sha256": "0" * 64,
            "orbitfabric_version": "1.2.0",
        },
        "core_input": {
            "kind": "orbitfabric.integration_input_set",
            "input_set_version": "0.1-candidate",
            "input_set_sha256": "1" * 64,
            "mission_id": "opensvf-openobsw-poc",
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


def _write_inputs(root: Path, plan: dict | None = None) -> tuple[Path, Path]:
    plan_path = root / "plan.json"
    write_verification_projection_plan(plan_path, plan or _reference_plan())

    spacecraft = root / "spacecraft_source.yaml"
    spacecraft.write_text(
        "version: 1\n"
        "spacecraft: Stage7.10-Test\n"
        "obsw:\n"
        "  type: pipe\n"
        "  binary: ../bin/obsw_sim\n"
        "simulation:\n"
        "  dt: 0.1\n"
        "  stop_time: 10.0\n"
        "  realtime: true\n",
        encoding="utf-8",
    )
    return plan_path, spacecraft


class OpenSVFMaterializerTests(unittest.TestCase):
    def test_reference_plan_materializes_expected_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, spacecraft = _write_inputs(root)
            output = root / "bundle"
            manifest = materialize_opensvf_plan(plan, spacecraft, output)

            self.assertTrue((output / PROCEDURE_REL).is_file())
            self.assertTrue((output / CAMPAIGN_REL).is_file())
            self.assertTrue((output / SPACECRAFT_REL).is_file())
            self.assertTrue((output / MANIFEST_REL).is_file())
            self.assertEqual(len(manifest["operation_trace"]), 4)

    def test_generated_procedure_uses_resolved_apid_and_plan_operation_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, spacecraft = _write_inputs(root)
            output = root / "bundle"
            materialize_opensvf_plan(plan, spacecraft, output)

            source = (output / PROCEDURE_REL).read_text(encoding="utf-8")

        self.assertIn("apid=0x010", source)
        self.assertNotIn("apid=0x001", source)
        for operation_id in ("op-0001", "op-0002", "op-0003", "op-0004"):
            self.assertIn(operation_id, source)
        self.assertNotIn("ctx.wait(", source)
        self.assertNotIn("schedule_tc(", source)

    def test_blocked_plan_is_rejected(self) -> None:
        plan = _reference_plan()
        plan["status"] = "blocked"
        plan["atoms"][0]["disposition"] = "blocked"
        plan["atoms"][0]["reason"] = "fixture"
        plan["atoms"][0]["binding_id"] = None
        plan["atoms"][0]["operation_ids"] = []
        plan["operations"] = []
        plan["accounting"].update(
            {
                "projected_atoms": 0,
                "blocked_atoms": 1,
                "projected_source_actions": 0,
                "profile_verification_obligations": 0,
            }
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path, spacecraft = _write_inputs(root, plan)
            with self.assertRaises(AdapterFailure) as context:
                materialize_opensvf_plan(plan_path, spacecraft, root / "bundle")

        self.assertEqual(context.exception.code, "OFI-VPROJ-MAT-001")

    def test_zero_operation_executable_plan_is_rejected(self) -> None:
        plan = _reference_plan()
        atom = plan["atoms"][0]
        atom["kind"] = "scenario_metadata"
        atom["role"] = "metadata"
        atom["source"] = None
        atom["binding_id"] = None
        atom["operation_ids"] = []
        plan["operations"] = []
        plan["accounting"].update(
            {
                "source_actions": 0,
                "projected_source_actions": 0,
                "profile_verification_obligations": 0,
            }
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path, spacecraft = _write_inputs(root, plan)
            with self.assertRaises(AdapterFailure) as context:
                materialize_opensvf_plan(plan_path, spacecraft, root / "bundle")

        self.assertEqual(context.exception.code, "OFI-VPROJ-MAT-001")

    def test_spacecraft_template_is_copied_byte_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, spacecraft = _write_inputs(root)
            output = root / "bundle"
            materialize_opensvf_plan(plan, spacecraft, output)
            self.assertEqual(
                spacecraft.read_bytes(),
                (output / SPACECRAFT_REL).read_bytes(),
            )

    def test_spacecraft_binary_path_resolves_inside_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, spacecraft = _write_inputs(root)
            output = root / "bundle"
            materialize_opensvf_plan(plan, spacecraft, output)

            materialized = output / SPACECRAFT_REL
            payload = yaml.safe_load(materialized.read_text(encoding="utf-8"))
            binary = payload["obsw"]["binary"]
            resolved = (materialized.parent / binary).resolve()

            self.assertEqual(binary, "../bin/obsw_sim")
            self.assertEqual(resolved, (output / "bin" / "obsw_sim").resolve())

    def test_operation_trace_maps_every_plan_operation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, spacecraft = _write_inputs(root)
            output = root / "bundle"
            manifest = materialize_opensvf_plan(plan, spacecraft, output)

        self.assertEqual(
            [item["plan_operation_id"] for item in manifest["operation_trace"]],
            ["op-0001", "op-0002", "op-0003", "op-0004"],
        )
        self.assertEqual(
            [item["native_primitive"] for item in manifest["operation_trace"]],
            ["ctx.tc", "ctx.expect_tm", "ctx.expect_tm", "ctx.expect_tm"],
        )

    def test_repeated_materialization_is_byte_stable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, spacecraft = _write_inputs(root)
            first = root / "first"
            second = root / "second"

            materialize_opensvf_plan(plan, spacecraft, first)
            materialize_opensvf_plan(plan, spacecraft, second)

            for relative in (
                PROCEDURE_REL,
                CAMPAIGN_REL,
                SPACECRAFT_REL,
                MANIFEST_REL,
            ):
                self.assertEqual(
                    (first / relative).read_bytes(),
                    (second / relative).read_bytes(),
                    relative.as_posix(),
                )


if __name__ == "__main__":
    unittest.main()
