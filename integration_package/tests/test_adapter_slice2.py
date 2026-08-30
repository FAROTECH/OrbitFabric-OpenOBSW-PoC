from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from integration_package.adapter.preflight import run_project
from integration_package.tests.test_adapter_slice1 import PROFILE_PATH, REPO_ROOT, _build_input_set


class AdapterSlice2Tests(unittest.TestCase):
    def test_project_materializes_header_and_obsw_srdb_contribution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = _build_input_set(root)
            output = root / "bundle"
            result = run_project(manifest, PROFILE_PATH, output_dir=output)

            header = (output / "flight_software" / "mission_contract.h").read_text(
                encoding="utf-8"
            )
            parameters = yaml.safe_load(
                (output / "obsw_srdb_contribution" / "parameters.yaml").read_text(
                    encoding="utf-8"
                )
            )
            telecommands = yaml.safe_load(
                (output / "obsw_srdb_contribution" / "telecommands.yaml").read_text(
                    encoding="utf-8"
                )
            )
            hk_sets = yaml.safe_load(
                (output / "obsw_srdb_contribution" / "hk_sets.yaml").read_text(
                    encoding="utf-8"
                )
            )
            events = yaml.safe_load(
                (output / "obsw_srdb_contribution" / "events.yaml").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(result["result"], "succeeded")
        self.assertEqual(
            result["capabilities"],
            ["profile_validation", "projection", "artifact_generation", "traceability"],
        )
        self.assertIn("OF_TM_OBC_BUS_VOLTAGE_MV = 0x6001", header)
        self.assertIn("OF_CMD_PING = 0x1701", header)
        self.assertIn("OF_EVENT_VOLTAGE_OUT_OF_BOUNDS = 0x5001", header)
        self.assertIn("OF_HK_SET_OBC = 0x0005", header)
        self.assertIn("#define OF_HK_SET_OBC_DEFAULT_INTERVAL_TICKS 0u", header)
        self.assertIn("uint16_t eps_obc_bus_voltage_mv;", header)

        self.assertEqual(
            parameters,
            {
                "parameters": [
                    {
                        "id": 0x6001,
                        "name": "eps_obc_bus_voltage_mv",
                        "description": "OBC bus voltage.",
                        "type": "uint16",
                        "ptc": 1,
                        "pfc": 16,
                        "subsystem": "eps",
                        "unit": "mV",
                        "limits": {"soft_high": 3500},
                    }
                ]
            },
        )
        self.assertEqual(telecommands, {"telecommands": []})
        self.assertEqual(
            hk_sets,
            {
                "hk_sets": [
                    {
                        "id": 5,
                        "name": "obc_hk",
                        "description": "OBC housekeeping.",
                        "parameters": ["eps_obc_bus_voltage_mv"],
                        "default_interval_ticks": 0,
                    }
                ]
            },
        )
        self.assertEqual(
            events,
            {
                "events": [
                    {
                        "id": 0x5001,
                        "name": "eps_voltage_out_of_bounds",
                        "severity": "MEDIUM",
                        "description": "Voltage out of bounds.",
                        "safe_trigger": False,
                        "auxiliary_data": [],
                    }
                ]
            },
        )

    def test_reused_ping_is_manifested_but_not_contributed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = _build_input_set(root)
            output = root / "bundle"
            run_project(manifest, PROFILE_PATH, output_dir=output)
            contribution = json.loads(
                (output / "obsw_srdb_contribution" / "contribution_manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            telecommands = yaml.safe_load(
                (output / "obsw_srdb_contribution" / "telecommands.yaml").read_text(
                    encoding="utf-8"
                )
            )

        self.assertFalse(contribution["complete_srdb"])
        self.assertEqual(contribution["mode"], "additive")
        self.assertEqual(telecommands["telecommands"], [])
        self.assertEqual(len(contribution["reused_targets"]), 1)
        reused = contribution["reused_targets"][0]
        self.assertEqual(reused["binding"], "cmd.ping")
        self.assertEqual(reused["id"], "are_you_alive")
        self.assertNotIn("dhs.obc.ping", json.dumps(contribution, sort_keys=True))

    def test_contribution_manifest_fingerprints_every_child_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = _build_input_set(root)
            output = root / "bundle"
            run_project(manifest, PROFILE_PATH, output_dir=output)
            contribution_root = output / "obsw_srdb_contribution"
            contribution = json.loads(
                (contribution_root / "contribution_manifest.json").read_text(
                    encoding="utf-8"
                )
            )

            for record in contribution["files"]:
                path = contribution_root / record["path"]
                self.assertTrue(path.is_file())
                self.assertEqual(
                    record["sha256"],
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                )

    def test_cli_writes_result_last_with_required_artifact_digests(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = _build_input_set(root)
            output = root / "bundle"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "integration_package" / "adapter_cli.py"),
                    "run",
                    "--operation",
                    "project",
                    "--input-set-manifest",
                    str(manifest),
                    "--profile",
                    str(PROFILE_PATH),
                    "--output-dir",
                    str(output),
                ],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result_path = output / "integration_result.json"
            self.assertTrue(result_path.is_file())
            result = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(len(result["artifacts"]), 2)
            self.assertEqual(
                [item["id"] for item in result["artifacts"]],
                ["flight.mission_contract", "ground.obsw_srdb_contribution"],
            )
            for artifact in result["artifacts"]:
                self.assertEqual(artifact["status"], "generated")
                relative = Path(artifact["path"])
                self.assertFalse(relative.is_absolute())
                self.assertNotIn("..", relative.parts)
                path = output / relative
                self.assertEqual(
                    artifact["sha256"],
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                )
                self.assertEqual(
                    artifact["derived_from_mappings"],
                    sorted(item["id"] for item in result["mappings"]),
                )

    def test_cli_removes_stale_adapter_owned_outputs_before_new_run(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = _build_input_set(root)
            output = root / "bundle"
            first = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "integration_package" / "adapter_cli.py"),
                    "run",
                    "--operation",
                    "project",
                    "--input-set-manifest",
                    str(manifest),
                    "--profile",
                    str(PROFILE_PATH),
                    "--output-dir",
                    str(output),
                ],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            stale = output / "obsw_srdb_contribution" / "stale.txt"
            stale.write_text("stale\n", encoding="utf-8")
            (output / "integration_result.json").write_text("{}\n", encoding="utf-8")

            second = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "integration_package" / "adapter_cli.py"),
                    "run",
                    "--operation",
                    "project",
                    "--input-set-manifest",
                    str(manifest),
                    "--profile",
                    str(PROFILE_PATH),
                    "--output-dir",
                    str(output),
                ],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertFalse(stale.exists())
            result = json.loads(
                (output / "integration_result.json").read_text(encoding="utf-8")
            )
            self.assertEqual(result["result"], "succeeded")

    def test_integration_package_manifest_truthfully_advertises_slice2(self) -> None:
        package_path = REPO_ROOT / "integration_package" / "integration_package.json"
        package = json.loads(package_path.read_text(encoding="utf-8"))

        self.assertEqual(package["kind"], "orbitfabric.integration_package")
        self.assertEqual(package["package_version"], "0.1-candidate")
        self.assertEqual(package["adapter"]["protocol"], "orbitfabric.adapter_cli.v0")
        self.assertEqual(
            package["adapter"]["argv_prefix"],
            ["python3", "integration_package/adapter_cli.py"],
        )
        self.assertEqual(package["operations"][0]["id"], "project")
        self.assertEqual(
            package["operations"][0]["capabilities"],
            ["profile_validation", "projection", "artifact_generation", "traceability"],
        )
        self.assertEqual(
            package["profile_schemas"][0]["sha256"],
            "92bc5089b9cf88e1f48cb0ea61acb9a4f84d514918ecacf5839abd59fa51c199",
        )


if __name__ == "__main__":
    unittest.main()
