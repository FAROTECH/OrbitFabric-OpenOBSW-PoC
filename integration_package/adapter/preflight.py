from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .artifact_support import artifact_record
from .artifacts import generate_project_artifacts
from .baseline import load_target_baseline
from .core_input import CoreInputSet, load_core_input_set
from .coverage import build_coverage
from .model import (
    ADAPTER_ID,
    ADAPTER_VERSION,
    INTEGRATION_ID,
    RESULT_VERSION,
    AdapterFailure,
)
from .opensvf_materializer import (
    CAMPAIGN_REL,
    MANIFEST_REL,
    PROCEDURE_REL,
    SPACECRAFT_REL,
    materialize_opensvf_plan,
)
from .profile import ProjectionProfile, load_projection_profile
from .projection import resolve_core_bindings, resolve_projection
from .verification_plan import write_verification_projection_plan
from .verification_projector import project_verification_scenario


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
VERIFICATION_ROOT = Path("verification_projection")
VERIFICATION_PLAN_PATH = VERIFICATION_ROOT / "verification_projection_plan.json"
VERIFICATION_MATERIALIZATION_ROOT = VERIFICATION_ROOT / "opensvf"
DEFAULT_SPACECRAFT_TEMPLATE = (
    PACKAGE_ROOT / "resources" / "opensvf" / "stage7_10_spacecraft.yaml"
)


def _success_result(
    core: CoreInputSet,
    profile: ProjectionProfile,
    mappings: list[dict[str, Any]],
    resolutions: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
    *,
    operation_id: str = "project",
    operation_inputs: list[dict[str, Any]] | None = None,
    evidence: list[dict[str, Any]] | None = None,
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
        "operation": {"id": operation_id},
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
            "operation_inputs": operation_inputs or [],
        },
        "capabilities": capabilities,
        "artifacts": artifacts,
        "mappings": mappings,
        "resolutions": resolutions,
        "diagnostics": [],
        "coverage": build_coverage(core, profile, mappings),
        "evidence": evidence or [],
        "external_tools": [],
    }


def _load_projection_context(
    input_set_manifest: Path,
    profile_path: Path,
    *,
    schema_path: Path | None = None,
) -> tuple[
    CoreInputSet,
    ProjectionProfile,
    Any,
    dict[str, dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    core = load_core_input_set(input_set_manifest)
    profile_kwargs = {"schema_path": schema_path} if schema_path is not None else {}
    profile = load_projection_profile(profile_path, **profile_kwargs)
    resolved = resolve_core_bindings(core, profile)
    baseline_id = profile.document["settings"]["compatibility"]["target_baseline"]
    baseline = load_target_baseline(baseline_id)
    mappings, resolutions = resolve_projection(core, profile, baseline, resolved)
    return core, profile, baseline, resolved, mappings, resolutions


def run_project(
    input_set_manifest: Path,
    profile_path: Path,
    *,
    schema_path: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    core, profile, baseline, resolved, mappings, resolutions = _load_projection_context(
        input_set_manifest,
        profile_path,
        schema_path=schema_path,
    )
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


def _reset_verification_outputs(output_dir: Path) -> None:
    root = output_dir / VERIFICATION_ROOT
    if root.exists():
        if not root.is_dir():
            raise AdapterFailure(
                "OFI-VPROJ-OUTPUT-001",
                "verification_projection",
                f"Expected Adapter verification output to be a directory: {root}",
            )
        shutil.rmtree(root)


def run_verification_projection(
    input_set_manifest: Path,
    profile_path: Path,
    scenario_path: Path,
    *,
    schema_path: Path | None = None,
    output_dir: Path,
) -> dict[str, Any]:
    """Project one explicitly bound Core Scenario into OpenSVF verification assets."""

    core, profile, _baseline, _resolved, mappings, resolutions = _load_projection_context(
        input_set_manifest,
        profile_path,
        schema_path=schema_path,
    )

    plan = project_verification_scenario(
        scenario_path,
        input_set_manifest,
        profile_path,
    )
    if plan["status"] != "executable_subset":
        blocking = [
            item["message"]
            for item in plan.get("diagnostics", [])
            if item.get("severity") == "ERROR"
        ]
        detail = blocking[0] if blocking else "verification projection is not executable"
        raise AdapterFailure(
            "OFI-VPROJ-OPERATION-001",
            "verification_projection",
            detail,
        )

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    _reset_verification_outputs(output_dir)

    plan_path = output_dir / VERIFICATION_PLAN_PATH
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    write_verification_projection_plan(plan_path, plan)

    materialization_root = output_dir / VERIFICATION_MATERIALIZATION_ROOT
    materialization_manifest = materialize_opensvf_plan(
        plan_path,
        DEFAULT_SPACECRAFT_TEMPLATE,
        materialization_root,
    )

    artifacts = [
        artifact_record(
            artifact_id="verification.projection_plan",
            kind="orbitfabric.verification_projection_plan",
            media_type="application/json",
            relative_path=VERIFICATION_PLAN_PATH,
            output_dir=output_dir,
            mapping_ids=[],
        ),
        artifact_record(
            artifact_id="verification.opensvf_materialization",
            kind="orbitfabric.opensvf_materialization",
            media_type="application/json",
            relative_path=VERIFICATION_MATERIALIZATION_ROOT / MANIFEST_REL,
            output_dir=output_dir,
            mapping_ids=[],
        ),
        artifact_record(
            artifact_id="verification.opensvf_procedure",
            kind="opensvf.procedure",
            media_type="text/x-python",
            relative_path=VERIFICATION_MATERIALIZATION_ROOT / PROCEDURE_REL,
            output_dir=output_dir,
            mapping_ids=[],
        ),
        artifact_record(
            artifact_id="verification.opensvf_campaign",
            kind="opensvf.campaign",
            media_type="application/yaml",
            relative_path=VERIFICATION_MATERIALIZATION_ROOT / CAMPAIGN_REL,
            output_dir=output_dir,
            mapping_ids=[],
        ),
        artifact_record(
            artifact_id="verification.opensvf_spacecraft",
            kind="opensvf.spacecraft_config",
            media_type="application/yaml",
            relative_path=VERIFICATION_MATERIALIZATION_ROOT / SPACECRAFT_REL,
            output_dir=output_dir,
            mapping_ids=[],
        ),
    ]

    scenario_input = {
        "role": "scenario",
        "status": "available",
        "id": plan["source"]["scenario_id"],
        "sha256": plan["source"]["scenario_sha256"],
        "reason": None,
    }
    evidence = [
        {
            "kind": "orbitfabric.openobsw_opensvf.verification_projection_accounting",
            "status": plan["status"],
            "scenario_id": plan["source"]["scenario_id"],
            "scenario_sha256": plan["source"]["scenario_sha256"],
            "accounting": plan["accounting"],
            "operation_trace": materialization_manifest["operation_trace"],
        }
    ]

    return _success_result(
        core,
        profile,
        mappings,
        resolutions,
        artifacts,
        operation_id="verification_projection",
        operation_inputs=[scenario_input],
        evidence=evidence,
    )
