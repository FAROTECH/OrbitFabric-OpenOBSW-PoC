from __future__ import annotations

from pathlib import Path
from typing import Any

from .artifacts import generate_project_artifacts
from .baseline import load_target_baseline
from .core_input import CoreInputSet, load_core_input_set
from .coverage import build_coverage
from .model import ADAPTER_ID, ADAPTER_VERSION, INTEGRATION_ID, RESULT_VERSION
from .profile import ProjectionProfile, load_projection_profile
from .projection import resolve_core_bindings, resolve_projection


def _success_result(
    core: CoreInputSet,
    profile: ProjectionProfile,
    mappings: list[dict[str, Any]],
    resolutions: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    capabilities = ["profile_validation", "projection"]
    if artifacts:
        capabilities.append("artifact_generation")
    capabilities.append("traceability")
    return {
        "kind": "orbitfabric.integration_result",
        "result_version": RESULT_VERSION,
        "result": "succeeded",
        "integration": {"id": INTEGRATION_ID, "schema_version": profile.schema_version},
        "adapter": {"id": ADAPTER_ID, "version": ADAPTER_VERSION},
        "operation": {"id": "project"},
        "mission": {
            "status": "available",
            "id": core.mission["id"],
            "model_version": core.mission["model_version"],
            "reason": None,
        },
        "inputs": {
            "core_input_set": {
                "status": "available",
                "kind": core.manifest["kind"],
                "version": core.manifest["input_set_version"],
                "sha256": core.sha256,
                "reason": None,
            },
            "profile": {
                "status": "available",
                "kind": profile.document["kind"],
                "profile_version": profile.document["profile_version"],
                "id": profile.id,
                "version": profile.version,
                "sha256": profile.sha256,
                "reason": None,
            },
            "operation_inputs": [],
        },
        "capabilities": capabilities,
        "artifacts": artifacts,
        "mappings": mappings,
        "resolutions": resolutions,
        "diagnostics": [],
        "coverage": build_coverage(core, profile, mappings),
        "evidence": [],
        "external_tools": [],
    }


def run_project(
    input_set_manifest: Path,
    profile_path: Path,
    *,
    schema_path: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    core = load_core_input_set(input_set_manifest)
    profile_kwargs = {"schema_path": schema_path} if schema_path is not None else {}
    profile = load_projection_profile(profile_path, **profile_kwargs)
    resolved = resolve_core_bindings(core, profile)
    baseline_id = profile.document["settings"]["compatibility"]["target_baseline"]
    baseline = load_target_baseline(baseline_id)
    mappings, resolutions = resolve_projection(core, profile, baseline, resolved)
    artifacts: list[dict[str, Any]] = []
    if output_dir is not None:
        artifacts = generate_project_artifacts(
            output_dir,
            core,
            profile,
            baseline,
            resolved,
            mappings,
            resolutions,
        )
    return _success_result(core, profile, mappings, resolutions, artifacts)
