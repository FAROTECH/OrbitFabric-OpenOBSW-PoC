from __future__ import annotations

from pathlib import Path
from typing import Any

from .artifact_support import (
    CONTRIBUTION_FILES,
    CONTRIBUTION_MANIFEST_PATH,
    FLIGHT_CONTRACT_PATH,
    artifact_record,
    reset_project_outputs,
    sha256_file,
    write_json,
    write_text,
    write_yaml,
)
from .baseline import TargetBaseline
from .core_input import CoreInputSet
from .flight_contract import render_flight_contract
from .model import AdapterFailure
from .profile import ProjectionProfile
from .srdb_contribution import build_srdb_contribution


def generate_project_artifacts(
    output_dir: Path,
    core: CoreInputSet,
    profile: ProjectionProfile,
    baseline: TargetBaseline,
    resolved: dict[str, dict[str, Any]],
    mappings: list[dict[str, Any]],
    resolutions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Materialize the Stage 7.4 handoff without mutating any target checkout."""
    mapping_ids = [item["id"] for item in mappings]
    try:
        write_text(
            output_dir / FLIGHT_CONTRACT_PATH,
            render_flight_contract(core, profile, mappings, resolutions),
        )

        records, reused_targets = build_srdb_contribution(
            profile, baseline, resolved, mappings, resolutions
        )
        for role, relative_path in CONTRIBUTION_FILES.items():
            write_yaml(output_dir / relative_path, role, records[role])

        files = [
            {
                "role": role,
                "path": relative_path.name,
                "sha256": sha256_file(output_dir / relative_path),
            }
            for role, relative_path in CONTRIBUTION_FILES.items()
        ]
        contribution_manifest = {
            "kind": "orbitfabric.openobsw_opensvf.obsw_srdb_contribution",
            "contribution_version": "0.1-candidate",
            "mode": "additive",
            "complete_srdb": False,
            "integration": {
                "id": profile.document["integration"]["id"],
                "schema_version": profile.schema_version,
            },
            "profile": {
                "id": profile.id,
                "version": profile.version,
                "sha256": profile.sha256,
            },
            "mission": {
                "id": core.mission["id"],
                "model_version": core.mission["model_version"],
            },
            "inputs": {
                "core_input_set": {
                    "kind": core.manifest["kind"],
                    "version": core.manifest["input_set_version"],
                    "sha256": core.sha256,
                }
            },
            "target": {
                "obsw_srdb": baseline.document["projection_target"]["obsw_srdb"],
                "target_baseline": baseline.document["id"],
            },
            "files": files,
            "reused_targets": reused_targets,
        }
        write_json(output_dir / CONTRIBUTION_MANIFEST_PATH, contribution_manifest)
    except AdapterFailure:
        reset_project_outputs(output_dir)
        raise
    except (OSError, TypeError, ValueError, KeyError) as exc:
        reset_project_outputs(output_dir)
        raise AdapterFailure(
            "OFI-ARTIFACT-GENERATE-001",
            "artifact_generation",
            f"Required project artifact generation failed: {exc}",
        ) from exc

    return [
        artifact_record(
            artifact_id="flight.mission_contract",
            kind="openobsw.mission_contract_header",
            media_type="text/x-c",
            relative_path=FLIGHT_CONTRACT_PATH,
            output_dir=output_dir,
            mapping_ids=mapping_ids,
        ),
        artifact_record(
            artifact_id="ground.obsw_srdb_contribution",
            kind="obsw_srdb.contribution_bundle",
            media_type="application/json",
            relative_path=CONTRIBUTION_MANIFEST_PATH,
            output_dir=output_dir,
            mapping_ids=mapping_ids,
        ),
    ]


__all__ = ["generate_project_artifacts", "reset_project_outputs"]
