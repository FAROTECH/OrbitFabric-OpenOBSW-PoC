from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import rfc8785

from integration_package.adapter.model import AdapterFailure
from integration_package.adapter.preflight import run_project

REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = REPO_ROOT / "projection_profiles" / "poc_openobsw_opensvf.yaml"

SURFACE_SPECS = {
    "entity_index": ("required", "orbitfabric.entity_index", "0.1", "entity_index.json"),
    "lint_report": ("required", "orbitfabric-lint", "v1", "lint_report.json"),
    "mission_snapshot": (
        "required",
        "orbitfabric.mission_snapshot",
        "0.1-candidate",
        "mission_snapshot.json",
    ),
    "model_summary": ("companion", "orbitfabric.model_summary", "0.1", "model_summary.json"),
    "relationship_manifest": (
        "required",
        "orbitfabric.relationship_manifest",
        "0.1-candidate",
        "relationship_manifest.json",
    ),
}


def _write_json(path: Path, payload: dict) -> str:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _input_set_digest(manifest: dict) -> str:
    surfaces = []
    for record in sorted(manifest["surfaces"], key=lambda item: item["role"]):
        surfaces.append(
            {
                "role": record["role"],
                "requirement": record["requirement"],
                "status": record["status"],
                "kind": record["kind"],
                "format_version": record["format_version"],
                "sha256": record["sha256"],
                "unavailable_reason": record["unavailable_reason"],
            }
        )
    payload = {
        "kind": manifest["kind"],
        "input_set_version": manifest["input_set_version"],
        "orbitfabric_version": manifest["orbitfabric_version"],
        "mission": manifest["mission"],
        "load_result": manifest["load_result"],
        "lint_result": manifest["lint_result"],
        "surfaces": surfaces,
    }
    return hashlib.sha256(rfc8785.dumps(payload)).hexdigest()


def _build_input_set(root: Path, *, packet_members: list[str] | None = None) -> Path:
    if packet_members is None:
        packet_members = ["eps.obc.bus_voltage_mv"]
    mission = {"id": "poc-cubesat", "model_version": "0.1.0"}
    model = {
        "telemetry": [
            {
                "id": "eps.obc.bus_voltage_mv",
                "name": "OBC Bus Voltage",
                "type": "uint16",
                "unit": "mV",
                "source": "eps",
                "limits": {"warning_high": 3500},
                "description": "OBC bus voltage.",
            }
        ],
        "commands": [
            {
                "id": "obc.ping",
                "target": "obc",
                "arguments": [],
                "description": "Ping command.",
            }
        ],
        "events": [
            {
                "id": "obc.ping_requested",
                "source": "obc",
                "severity": "info",
                "description": "Ping requested.",
            },
            {
                "id": "eps.voltage_out_of_bounds",
                "source": "eps",
                "severity": "warning",
                "description": "Voltage out of bounds.",
            },
        ],
        "packets": [
            {
                "id": "obc_hk",
                "name": "OBC Housekeeping Packet",
                "telemetry": packet_members,
                "description": "OBC housekeeping.",
            }
        ],
    }
    snapshot = {
        "kind": "orbitfabric.mission_snapshot",
        "snapshot_version": "0.1-candidate",
        "result": "loaded",
        "mission": mission,
        "model": model,
    }
    entities = [
        {"domain": domain, "id": item["id"], "entity_type": domain}
        for domain, items in model.items()
        for item in items
    ]
    payloads = {
        "mission_snapshot": snapshot,
        "entity_index": {
            "kind": "orbitfabric.entity_index",
            "index_version": "0.1",
            "mission": mission,
            "entities": entities,
        },
        "relationship_manifest": {
            "kind": "orbitfabric.relationship_manifest",
            "manifest_version": "0.1-candidate",
            "mission": mission,
            "relationships": [],
        },
        "lint_report": {
            "tool": "orbitfabric-lint",
            "version": "1.2.0",
            "result": "passed",
            "mission": mission["id"],
            "model_version": mission["model_version"],
            "findings": [],
        },
        "model_summary": {
            "kind": "orbitfabric.model_summary",
            "summary_version": "0.1",
            "mission": mission,
        },
    }

    surfaces = []
    for role in sorted(SURFACE_SPECS):
        requirement, kind, format_version, filename = SURFACE_SPECS[role]
        digest = _write_json(root / filename, payloads[role])
        surfaces.append(
            {
                "role": role,
                "requirement": requirement,
                "status": "available",
                "kind": kind,
                "format_version": format_version,
                "path": filename,
                "sha256": digest,
                "unavailable_reason": None,
            }
        )

    manifest = {
        "kind": "orbitfabric.integration_input_set",
        "input_set_version": "0.1-candidate",
        "orbitfabric_version": "1.2.0",
        "mission": mission,
        "load_result": "loaded",
        "lint_result": "passed",
        "surfaces": surfaces,
    }
    manifest["input_set_sha256"] = _input_set_digest(manifest)
    manifest_path = root / "integration_input_manifest.json"
    _write_json(manifest_path, manifest)
    return manifest_path


def _profile_variant(root: Path, old: str, new: str) -> Path:
    content = PROFILE_PATH.read_text(encoding="utf-8")
    if old not in content:
        raise AssertionError(f"Profile fixture mutation anchor not found: {old!r}")
    path = root / "profile.yaml"
    path.write_text(content.replace(old, new, 1), encoding="utf-8")
    return path


class AdapterSlice1Tests(unittest.TestCase):
    def test_canonical_slice_resolves_four_bindings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = _build_input_set(Path(directory))
            result = run_project(manifest, PROFILE_PATH)

        self.assertEqual(result["result"], "succeeded")
        self.assertEqual(
            [item["id"] for item in result["mappings"]],
            [
                "mapping.cmd.ping",
                "mapping.event.voltage_out_of_bounds",
                "mapping.packet.obc_hk",
                "mapping.tm.obc_bus_voltage",
            ],
        )
        resolutions = {item["id"]: item["value"] for item in result["resolutions"]}
        self.assertEqual(resolutions["resolution.cmd.ping.target_action"], "reuse_existing")
        self.assertEqual(resolutions["resolution.cmd.ping.target_name"], "are_you_alive")
        self.assertEqual(resolutions["resolution.event.voltage_out_of_bounds.severity"], "MEDIUM")
        self.assertEqual(resolutions["resolution.event.voltage_out_of_bounds.pus_subtype"], 3)
        self.assertEqual(result["coverage"]["summary"], {"not_projected": 1, "projected": 4})
        self.assertEqual(result["artifacts"], [])
        self.assertNotIn("dhs.obc.ping", json.dumps(result, sort_keys=True))

    def test_checkout_cli_writes_machine_readable_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = _build_input_set(root)
            output = root / "result"
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
            payload = json.loads((output / "integration_result.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["result"], "succeeded")
        self.assertEqual(len(payload["mappings"]), 4)

    def test_tampered_core_surface_reports_surface_digest_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = _build_input_set(root)
            snapshot = root / "mission_snapshot.json"
            snapshot.write_text(snapshot.read_text(encoding="utf-8") + " ", encoding="utf-8")
            with self.assertRaises(AdapterFailure) as context:
                run_project(manifest, PROFILE_PATH)
        self.assertEqual(context.exception.code, "OFI-INPUT-SURFACE-002")

    def test_unresolved_core_source_is_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = _build_input_set(root)
            profile = _profile_variant(root, "        id: obc.ping\n", "        id: obc.missing\n")
            with self.assertRaises(AdapterFailure) as context:
                run_project(manifest, profile)
        self.assertEqual(context.exception.code, "OFI-SOURCE-001")
        self.assertEqual(context.exception.phase, "source_resolution")

    def test_parameter_collision_reports_allocation_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = _build_input_set(root)
            profile = _profile_variant(root, "        parameter_id: 0x6001\n", "        parameter_id: 0x4001\n")
            with self.assertRaises(AdapterFailure) as context:
                run_project(manifest, profile)
        self.assertEqual(context.exception.code, "OFI-COMP-ALLOC-001")

    def test_hk_membership_failure_reports_hk_code_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = _build_input_set(root, packet_members=[])
            with self.assertRaises(AdapterFailure) as context:
                run_project(manifest, PROFILE_PATH)
        self.assertEqual(context.exception.code, "OFI-PROJ-HK-001")


if __name__ == "__main__":
    unittest.main()
