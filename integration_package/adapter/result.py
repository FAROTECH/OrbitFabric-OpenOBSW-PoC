from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .model import ADAPTER_ID, ADAPTER_VERSION, INTEGRATION_ID, RESULT_VERSION, AdapterFailure


def unavailable_input(reason: str, *, profile: bool = False) -> dict[str, Any]:
    if profile:
        return {
            "status": "unavailable",
            "kind": None,
            "profile_version": None,
            "id": None,
            "version": None,
            "sha256": None,
            "reason": reason,
        }
    return {
        "status": "unavailable",
        "kind": None,
        "version": None,
        "sha256": None,
        "reason": reason,
    }


def unavailable_operation_input(role: str, reason: str) -> dict[str, Any]:
    return {
        "role": role,
        "status": "unavailable",
        "id": None,
        "sha256": None,
        "reason": reason,
    }


def _not_generated_artifacts(reason: str) -> list[dict[str, Any]]:
    return [
        {
            "id": "flight.mission_contract",
            "kind": "openobsw.mission_contract_header",
            "requirement": "required",
            "status": "not_generated",
            "path": None,
            "media_type": "text/x-c",
            "sha256": None,
            "reason": reason,
            "retained_partial": False,
            "derived_from_mappings": [],
        },
        {
            "id": "ground.obsw_srdb_contribution",
            "kind": "obsw_srdb.contribution_bundle",
            "requirement": "required",
            "status": "not_generated",
            "path": None,
            "media_type": "application/json",
            "sha256": None,
            "reason": reason,
            "retained_partial": False,
            "derived_from_mappings": [],
        },
    ]


def failed_result(
    operation: str,
    failure: AdapterFailure,
    *,
    operation_inputs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    artifact_phase = failure.phase == "artifact_generation"
    capabilities = (
        ["profile_validation", "projection", "artifact_generation", "traceability"]
        if artifact_phase
        else []
    )
    return {
        "kind": "orbitfabric.integration_result",
        "result_version": RESULT_VERSION,
        "result": "failed",
        "integration": {"id": INTEGRATION_ID, "schema_version": None},
        "adapter": {"id": ADAPTER_ID, "version": ADAPTER_VERSION},
        "operation": {"id": operation},
        "mission": {
            "status": "unavailable",
            "id": None,
            "model_version": None,
            "reason": "Core input identity unavailable",
        },
        "inputs": {
            "core_input_set": unavailable_input("Core input provenance unavailable"),
            "profile": unavailable_input(
                "Projection Profile provenance unavailable",
                profile=True,
            ),
            "operation_inputs": operation_inputs or [],
        },
        "capabilities": capabilities,
        "artifacts": _not_generated_artifacts(failure.message) if artifact_phase else [],
        "mappings": [],
        "resolutions": [],
        "diagnostics": [failure.as_diagnostic()],
        "coverage": {
            "status": "unavailable",
            "scope": {"domains": []},
            "reason": failure.message,
            "summary": {},
            "records": [],
        },
        "evidence": [],
        "external_tools": [],
    }


def write_result(output_dir: Path, payload: dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "integration_result.json"
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path
