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


def failed_result(operation: str, failure: AdapterFailure) -> dict[str, Any]:
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
        },
        "capabilities": [],
        "artifacts": [],
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
