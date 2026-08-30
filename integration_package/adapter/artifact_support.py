from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import yaml

from .model import AdapterFailure
from .profile import ProjectionProfile

FLIGHT_CONTRACT_PATH = Path("flight_software/mission_contract.h")
CONTRIBUTION_ROOT = Path("obsw_srdb_contribution")
CONTRIBUTION_MANIFEST_PATH = CONTRIBUTION_ROOT / "contribution_manifest.json"
CONTRIBUTION_FILES = {
    "parameters": CONTRIBUTION_ROOT / "parameters.yaml",
    "telecommands": CONTRIBUTION_ROOT / "telecommands.yaml",
    "hk_sets": CONTRIBUTION_ROOT / "hk_sets.yaml",
    "events": CONTRIBUTION_ROOT / "events.yaml",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def write_yaml(path: Path, key: str, records: list[dict[str, Any]]) -> None:
    rendered = yaml.safe_dump(
        {key: records},
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    write_text(path, rendered)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def reset_project_outputs(output_dir: Path) -> None:
    """Remove only Adapter-owned project outputs so stale output cannot survive a new run."""
    marker = output_dir / "integration_result.json"
    if marker.is_file():
        marker.unlink()

    flight = output_dir / FLIGHT_CONTRACT_PATH
    if flight.is_file():
        flight.unlink()

    contribution = output_dir / CONTRIBUTION_ROOT
    if contribution.exists():
        if not contribution.is_dir():
            raise AdapterFailure(
                "OFI-ARTIFACT-PATH-001",
                "artifact_generation",
                f"Expected Adapter contribution output to be a directory: {contribution}",
            )
        shutil.rmtree(contribution)


def mapping_by_binding(mappings: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for mapping in mappings:
        bindings = mapping.get("profile_bindings")
        if not isinstance(bindings, list) or len(bindings) != 1 or not isinstance(bindings[0], str):
            raise AdapterFailure(
                "OFI-ARTIFACT-TRACE-001",
                "artifact_generation",
                "Artifact generation requires exactly one Profile binding per mapping",
            )
        binding = bindings[0]
        if binding in result:
            raise AdapterFailure(
                "OFI-ARTIFACT-TRACE-001",
                "artifact_generation",
                f"Duplicate mapping for Profile binding {binding}",
            )
        result[binding] = mapping
    return result


def resolution_values(resolutions: list[dict[str, Any]]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for item in resolutions:
        identifier = item.get("id")
        if not isinstance(identifier, str) or identifier in values:
            raise AdapterFailure(
                "OFI-ARTIFACT-TRACE-001",
                "artifact_generation",
                "Artifact generation requires unique resolution identities",
            )
        values[identifier] = item.get("value")
    return values


def target(mapping: dict[str, Any], namespace: str, kind: str) -> str:
    matches = [
        item.get("id")
        for item in mapping.get("targets", [])
        if item.get("namespace") == namespace and item.get("kind") == kind
    ]
    if len(matches) != 1 or not isinstance(matches[0], str):
        raise AdapterFailure(
            "OFI-ARTIFACT-TRACE-001",
            "artifact_generation",
            f"Mapping {mapping.get('id')} does not expose exactly one {namespace}/{kind} target",
        )
    return matches[0]


def projected_bindings(profile: ProjectionProfile) -> list[dict[str, Any]]:
    return sorted(
        [binding for binding in profile.bindings if binding.get("intent") == "project"],
        key=lambda item: item["id"],
    )


def artifact_record(
    *,
    artifact_id: str,
    kind: str,
    media_type: str,
    relative_path: Path,
    output_dir: Path,
    mapping_ids: list[str],
) -> dict[str, Any]:
    path = output_dir / relative_path
    return {
        "id": artifact_id,
        "kind": kind,
        "requirement": "required",
        "status": "generated",
        "path": relative_path.as_posix(),
        "media_type": media_type,
        "sha256": sha256_file(path),
        "reason": None,
        "retained_partial": False,
        "derived_from_mappings": sorted(mapping_ids),
    }
