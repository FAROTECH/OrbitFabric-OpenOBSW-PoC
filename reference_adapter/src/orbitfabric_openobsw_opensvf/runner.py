from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from .flight_contract import FlightContractError, write_flight_contract
from .integration_result import (
    ADAPTER_ID,
    artifact_record,
    build_mappings,
    build_success_result,
    core_provenance,
    failed_result,
    file_sha256,
    profile_provenance,
    unavailable_core,
    unavailable_mission,
    unavailable_profile,
    write_result_last,
)
from .opensvf_srdb import OpenSvfSrdbError, write_opensvf_srdb
from .projection_pipeline import resolve_projection
from .resolver import ProjectionResolutionError
from .validator import Diagnostic, ValidationInputError, validate_profile

PROJECT_OPERATION = "project"
FLIGHT_RELATIVE_PATH = "artifacts/flight/mission_contract.h"
SRDB_RELATIVE_PATH = "artifacts/ground/poc_srdb.yaml"


def adapter_version() -> str:
    try:
        return version("orbitfabric-openobsw-opensvf")
    except PackageNotFoundError:
        return "0.1.0.dev0"


def _phase(code: str) -> str:
    if code.startswith("input.") or code.startswith("entity_index."):
        return "input_compatibility"
    if code == "profile.schema":
        return "profile_schema"
    if code == "profile.source":
        return "source_resolution"
    return "projection_validation"


def _result_diagnostics(items: tuple[Diagnostic, ...] | list[Diagnostic]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        result.append(
            {
                "id": f"diag-{index:03d}",
                "owner": "integration",
                "producer": ADAPTER_ID,
                "phase": _phase(item.code),
                "severity": "ERROR",
                "code": item.code,
                "message": item.message,
                "sources": [],
                "profile_bindings": [],
                "targets": [],
            }
        )
    return result


def _exception_diagnostic(*, phase: str, code: str, message: str) -> list[dict[str, Any]]:
    return [
        {
            "id": "diag-001",
            "owner": "integration",
            "producer": ADAPTER_ID,
            "phase": phase,
            "severity": "ERROR",
            "code": code,
            "message": message,
            "sources": [],
            "profile_bindings": [],
            "targets": [],
        }
    ]


def _not_generated_artifacts(reason: str) -> list[dict[str, Any]]:
    return [
        artifact_record(
            artifact_id="flight.mission_contract",
            kind="openobsw_contract_header",
            media_type="text/x-c",
            path=None,
            digest=None,
            status="not_generated",
            reason=reason,
            mapping_ids=[],
        ),
        artifact_record(
            artifact_id="ground.opensvf_srdb",
            kind="opensvf_srdb_yaml",
            media_type="application/yaml",
            path=None,
            digest=None,
            status="not_generated",
            reason=reason,
            mapping_ids=[],
        ),
    ]


def _remove_known_artifacts(output_dir: Path) -> None:
    for relative in (FLIGHT_RELATIVE_PATH, SRDB_RELATIVE_PATH):
        path = output_dir / relative
        if path.is_file():
            path.unlink()


def _reset_bundle_marker_and_known_artifacts(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    marker = output_dir / "integration_result.json"
    if marker.is_file():
        marker.unlink()
    _remove_known_artifacts(output_dir)


def _best_effort_provenance(
    manifest_path: Path, profile_path: Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str | None]:
    try:
        _, core, mission = core_provenance(manifest_path)
    except ValidationInputError as exc:
        core = unavailable_core(str(exc))
        mission = unavailable_mission("Core input identity unavailable")

    try:
        _, profile, schema_version = profile_provenance(profile_path)
    except ValidationInputError as exc:
        profile = unavailable_profile(str(exc))
        schema_version = None

    return core, profile, mission, schema_version


def run_operation(
    *, operation_id: str, manifest_path: Path, profile_path: Path,
    output_dir: Path, schema_path: Path
) -> tuple[int, Path | None]:
    """Execute orbitfabric.adapter_cli.v0 run semantics."""
    _reset_bundle_marker_and_known_artifacts(output_dir)
    adapter_ver = adapter_version()

    core, profile_value, mission, schema_version = _best_effort_provenance(
        manifest_path, profile_path
    )

    if operation_id != PROJECT_OPERATION:
        result = failed_result(
            adapter_version=adapter_ver,
            operation_id=operation_id,
            schema_version=schema_version,
            core=core,
            profile=profile_value,
            mission=mission,
            capabilities=[],
            diagnostics=_exception_diagnostic(
                phase="input_compatibility",
                code="operation.unsupported",
                message=f"operation is not advertised by this package: {operation_id}",
            ),
            artifacts=_not_generated_artifacts("unsupported operation"),
            coverage_reason="Operation was rejected before projection",
        )
        return 1, write_result_last(output_dir, result)

    try:
        validation = validate_profile(
            manifest_path=manifest_path,
            profile_path=profile_path,
            schema_path=schema_path,
        )
    except ValidationInputError as exc:
        result = failed_result(
            adapter_version=adapter_ver,
            operation_id=operation_id,
            schema_version=schema_version,
            core=core,
            profile=profile_value,
            mission=mission,
            capabilities=["profile_validation"],
            diagnostics=_exception_diagnostic(
                phase="input_compatibility",
                code="input.read",
                message=str(exc),
            ),
            artifacts=_not_generated_artifacts("input could not be validated"),
            coverage_reason="Input/Profile identity or compatibility could not be established",
        )
        return 1, write_result_last(output_dir, result)

    if not validation.ok:
        result = failed_result(
            adapter_version=adapter_ver,
            operation_id=operation_id,
            schema_version=schema_version,
            core=core,
            profile=profile_value,
            mission=mission,
            capabilities=["profile_validation"],
            diagnostics=_result_diagnostics(validation.diagnostics),
            artifacts=_not_generated_artifacts("projection validation failed"),
            coverage_reason="Projection validation failed before reliable coverage resolution",
        )
        return 1, write_result_last(output_dir, result)

    try:
        resolved = resolve_projection(
            manifest_path=manifest_path,
            profile_path=profile_path,
            schema_path=schema_path,
        )
    except ProjectionResolutionError as exc:
        result = failed_result(
            adapter_version=adapter_ver,
            operation_id=operation_id,
            schema_version=schema_version,
            core=core,
            profile=profile_value,
            mission=mission,
            capabilities=["profile_validation", "projection"],
            diagnostics=_result_diagnostics(list(exc.diagnostics)),
            artifacts=_not_generated_artifacts("projection resolution failed"),
            coverage_reason="Projection resolution failed",
        )
        return 1, write_result_last(output_dir, result)
    except ValidationInputError as exc:
        result = failed_result(
            adapter_version=adapter_ver,
            operation_id=operation_id,
            schema_version=schema_version,
            core=core,
            profile=profile_value,
            mission=mission,
            capabilities=["profile_validation", "projection"],
            diagnostics=_exception_diagnostic(
                phase="projection_validation",
                code="projection.resolve",
                message=str(exc),
            ),
            artifacts=_not_generated_artifacts("projection resolution failed"),
            coverage_reason="Projection resolution failed",
        )
        return 1, write_result_last(output_dir, result)

    mappings = build_mappings(resolved)
    all_mapping_ids = [item["id"] for item in mappings]
    telemetry_mapping_ids = [
        item["id"]
        for item in mappings
        if any(target["namespace"] == "opensvf" for target in item["targets"])
    ]
    flight_path = output_dir / FLIGHT_RELATIVE_PATH
    srdb_path = output_dir / SRDB_RELATIVE_PATH

    try:
        write_flight_contract(resolved, flight_path)
        write_opensvf_srdb(resolved, srdb_path)
    except (FlightContractError, OpenSvfSrdbError, OSError) as exc:
        # v0 chooses no retained partial artifacts: a failed required materialization
        # leaves a failed Result plus explicit not_generated artifact records only.
        _remove_known_artifacts(output_dir)
        result = failed_result(
            adapter_version=adapter_ver,
            operation_id=operation_id,
            schema_version=schema_version,
            core=core,
            profile=profile_value,
            mission=mission,
            capabilities=["profile_validation", "projection", "artifact_generation", "traceability"],
            diagnostics=_exception_diagnostic(
                phase="artifact_generation",
                code="artifact.generate",
                message=str(exc),
            ),
            artifacts=_not_generated_artifacts("required artifact generation failed"),
            coverage_reason="Required artifact generation failed",
        )
        return 1, write_result_last(output_dir, result)

    artifacts = [
        artifact_record(
            artifact_id="flight.mission_contract",
            kind="openobsw_contract_header",
            media_type="text/x-c",
            path=FLIGHT_RELATIVE_PATH,
            digest=file_sha256(flight_path),
            status="generated",
            reason=None,
            mapping_ids=all_mapping_ids,
        ),
        artifact_record(
            artifact_id="ground.opensvf_srdb",
            kind="opensvf_srdb_yaml",
            media_type="application/yaml",
            path=SRDB_RELATIVE_PATH,
            digest=file_sha256(srdb_path),
            status="generated",
            reason=None,
            mapping_ids=telemetry_mapping_ids,
        ),
    ]
    result = build_success_result(
        adapter_version=adapter_ver,
        operation_id=operation_id,
        manifest_path=manifest_path,
        profile_path=profile_path,
        resolved=resolved,
        artifacts=artifacts,
    )
    return 0, write_result_last(output_dir, result)
