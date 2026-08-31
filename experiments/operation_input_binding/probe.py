#!/usr/bin/env python3
"""Architecture Lab probe for a minimal additional Scenario input binding.

This is deliberately not an implementation of orbitfabric.adapter_cli.v1 and does
not emit a generic Integration Result. It pressure-tests only this candidate shape:

    fixed context: Core Integration Input Set + Projection Profile
    additional operation input: one explicit Core-owned Scenario file

The probe delegates Scenario semantics to OrbitFabric Core through the existing
Stage 7.10 verification projector, writes the validated projection plan, then
materializes the plan through the existing OpenSVF materializer.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from integration_package.adapter.io import sha256_file
from integration_package.adapter.opensvf_materializer import materialize_opensvf_plan
from integration_package.adapter.verification_plan import write_verification_projection_plan
from integration_package.adapter.verification_projector import project_verification_scenario


PROBE_KIND = "orbitfabric.architecture_lab.operation_input_binding_probe"
PROBE_VERSION = "0.1-experimental"
WORKING_OPERATION_ID = "stage7_10_verification_projection"
WORKING_INPUT_ROLE = "scenario"


def _existing_file(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_file():
        raise SystemExit(f"{label} does not exist or is not a file: {resolved}")
    return resolved


def _relative_or_absolute(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def build_probe(
    *,
    scenario_path: Path,
    input_set_manifest: Path,
    profile_path: Path,
    spacecraft_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    scenario_path = _existing_file(scenario_path, "Scenario")
    input_set_manifest = _existing_file(input_set_manifest, "Core Integration Input Set manifest")
    profile_path = _existing_file(profile_path, "Projection Profile")
    spacecraft_path = _existing_file(spacecraft_path, "OpenSVF spacecraft template")
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # The existing Stage 7.10 projector remains the semantic/projection authority.
    # It uses Core ScenarioLoader and validates Scenario/IISS mission coherence.
    plan = project_verification_scenario(
        scenario_path,
        input_set_manifest,
        profile_path,
    )

    plan_path = output_dir / "verification_projection_plan.json"
    write_verification_projection_plan(plan_path, plan)

    materialization_dir = output_dir / "opensvf"
    materialization = materialize_opensvf_plan(
        plan_path,
        spacecraft_path,
        materialization_dir,
    )

    probe = {
        "kind": PROBE_KIND,
        "probe_version": PROBE_VERSION,
        "status": "passed",
        "operation": {
            "id": WORKING_OPERATION_ID,
            "note": "integration-defined working operation id; not a generic vocabulary",
        },
        "declaration_probe": {
            "additional_inputs": [
                {
                    "role": WORKING_INPUT_ROLE,
                    "requirement": "required",
                    "note": "working role identifier only; not a promoted contract",
                }
            ]
        },
        "invocation_binding": {
            "role": WORKING_INPUT_ROLE,
            "path": str(scenario_path),
            "path_semantics": "local_execution_location_only",
        },
        "consumed_input_provenance": {
            "scenario": {
                "status": "available",
                "id": plan["source"]["scenario_id"],
                "sha256": plan["source"]["scenario_sha256"],
            },
            "core_input_set": {
                "status": "available",
                "kind": plan["core_input"]["kind"],
                "version": plan["core_input"]["input_set_version"],
                "sha256": plan["core_input"]["input_set_sha256"],
                "mission_id": plan["core_input"]["mission_id"],
                "model_version": plan["core_input"]["model_version"],
            },
            "profile": {
                "status": "available",
                "kind": plan["profile"]["kind"],
                "profile_version": plan["profile"]["profile_version"],
                "id": plan["profile"]["id"],
                "version": plan["profile"]["version"],
                "sha256": plan["profile"]["sha256"],
            },
        },
        "projection": {
            "status": plan["status"],
            "accounting": plan["accounting"],
            "plan": {
                "path": _relative_or_absolute(plan_path, output_dir),
                "sha256": sha256_file(plan_path),
            },
        },
        "materialization": {
            "kind": materialization["kind"],
            "version": materialization["materialization_version"],
            "manifest": {
                "path": _relative_or_absolute(
                    materialization_dir / "materialization_manifest.json",
                    output_dir,
                ),
                "sha256": sha256_file(
                    materialization_dir / "materialization_manifest.json"
                ),
            },
            "operation_trace": materialization["operation_trace"],
        },
        "architectural_assertions": {
            "scenario_interpreted_by_core_backed_projector": True,
            "scenario_added_to_mission_level_iiss": False,
            "materializer_rereads_scenario": False,
            "generic_verification_operation_vocabulary_claimed": False,
            "adapter_cli_v1_claimed": False,
            "generic_integration_result_claimed": False,
        },
    }

    probe_path = output_dir / "operation_input_binding_probe.json"
    probe_path.write_text(
        json.dumps(probe, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return probe


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pressure-test a minimal additional Scenario operation input binding."
    )
    parser.add_argument("--scenario", required=True, type=Path)
    parser.add_argument("--input-set-manifest", required=True, type=Path)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--spacecraft", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    probe = build_probe(
        scenario_path=args.scenario,
        input_set_manifest=args.input_set_manifest,
        profile_path=args.profile,
        spacecraft_path=args.spacecraft,
        output_dir=args.output_dir,
    )
    print(json.dumps(probe, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
