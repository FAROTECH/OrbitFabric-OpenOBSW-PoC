from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io import canonical_input_set_sha256, load_json, resolve_contained_file, sha256_file
from .model import AdapterFailure, INPUT_SET_VERSION


SURFACE_SPECS = {
    "entity_index": ("required", "orbitfabric.entity_index", "0.1", "kind", "index_version"),
    "lint_report": ("required", "orbitfabric-lint", "v1", "tool", None),
    "mission_snapshot": (
        "required",
        "orbitfabric.mission_snapshot",
        "0.1-candidate",
        "kind",
        "snapshot_version",
    ),
    "model_summary": ("companion", "orbitfabric.model_summary", "0.1", "kind", "summary_version"),
    "relationship_manifest": (
        "required",
        "orbitfabric.relationship_manifest",
        "0.1-candidate",
        "kind",
        "manifest_version",
    ),
}


@dataclass(frozen=True)
class CoreInputSet:
    manifest_path: Path
    manifest: dict[str, Any]
    surfaces: dict[str, dict[str, Any]]
    entity_index: dict[str, Any]
    mission_snapshot: dict[str, Any]
    relationship_manifest: dict[str, Any]
    model_summary: dict[str, Any] | None
    entities: dict[tuple[str, str], dict[str, Any]]

    @property
    def mission(self) -> dict[str, str]:
        return self.manifest["mission"]

    @property
    def sha256(self) -> str:
        return self.manifest["input_set_sha256"]

    def resolve_source(self, domain: str, identifier: str) -> dict[str, Any]:
        key = (domain, identifier)
        entity = self.entities.get(key)
        if entity is None:
            raise AdapterFailure(
                "OFI-SOURCE-001",
                "source_resolution",
                f"Core source does not resolve through Entity Index: {domain}/{identifier}",
                sources=[{"domain": domain, "id": identifier}],
            )
        return entity

    def semantic_object(self, domain: str, identifier: str) -> dict[str, Any]:
        self.resolve_source(domain, identifier)
        model = self.mission_snapshot.get("model")
        if not isinstance(model, dict):
            raise AdapterFailure(
                "OFI-SOURCE-002",
                "source_resolution",
                "Mission Snapshot does not contain a loaded model",
                sources=[{"domain": domain, "id": identifier}],
            )
        collection = model.get(domain)
        if not isinstance(collection, list):
            raise AdapterFailure(
                "OFI-SOURCE-002",
                "source_resolution",
                f"Mission Snapshot domain is not available as an entity collection: {domain}",
                sources=[{"domain": domain, "id": identifier}],
            )
        matches = [item for item in collection if isinstance(item, dict) and item.get("id") == identifier]
        if len(matches) != 1:
            raise AdapterFailure(
                "OFI-SOURCE-002",
                "source_resolution",
                f"Expected exactly one Mission Snapshot object for {domain}/{identifier}, found {len(matches)}",
                sources=[{"domain": domain, "id": identifier}],
            )
        return matches[0]


def _mission_identity(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    mission = payload.get("mission")
    if not isinstance(mission, dict):
        return (None, None)
    return (mission.get("id"), mission.get("model_version"))


def load_core_input_set(manifest_path: Path) -> CoreInputSet:
    manifest_path = manifest_path.resolve()
    manifest = load_json(manifest_path)
    if manifest.get("kind") != "orbitfabric.integration_input_set":
        raise AdapterFailure(
            "OFI-INPUT-MANIFEST-001",
            "input_compatibility",
            "Unsupported Core Integration Input Manifest kind",
        )
    if manifest.get("input_set_version") != INPUT_SET_VERSION:
        raise AdapterFailure(
            "OFI-INPUT-MANIFEST-001",
            "input_compatibility",
            f"Unsupported Core Integration Input Set version: {manifest.get('input_set_version')!r}",
        )

    expected_digest = manifest.get("input_set_sha256")
    actual_digest = canonical_input_set_sha256(manifest)
    if expected_digest != actual_digest:
        raise AdapterFailure(
            "OFI-INPUT-DIGEST-001",
            "input_compatibility",
            f"Core input_set_sha256 mismatch: declared {expected_digest!r}, computed {actual_digest}",
        )

    if manifest.get("load_result") != "loaded":
        raise AdapterFailure(
            "OFI-INPUT-STATE-001",
            "input_compatibility",
            f"Projection requires load_result=loaded, got {manifest.get('load_result')!r}",
        )
    if manifest.get("lint_result") not in {"passed", "passed_with_warnings"}:
        raise AdapterFailure(
            "OFI-INPUT-STATE-002",
            "input_compatibility",
            f"Projection blocked by Core lint_result={manifest.get('lint_result')!r}",
        )
    mission = manifest.get("mission")
    if not isinstance(mission, dict) or not mission.get("id") or not mission.get("model_version"):
        raise AdapterFailure(
            "OFI-INPUT-MANIFEST-001",
            "input_compatibility",
            "Loaded Core Integration Input Set must expose Mission identity",
        )

    records = manifest.get("surfaces")
    if not isinstance(records, list):
        raise AdapterFailure("OFI-INPUT-MANIFEST-001", "input_compatibility", "surfaces must be an array")
    by_role: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("role"), str):
            raise AdapterFailure("OFI-INPUT-MANIFEST-001", "input_compatibility", "Invalid surface record")
        by_role.setdefault(record["role"], []).append(record)

    payloads: dict[str, dict[str, Any]] = {}
    root = manifest_path.parent
    for role, (requirement, kind, format_version, identity_field, native_version_field) in SURFACE_SPECS.items():
        role_records = by_role.get(role, [])
        if len(role_records) != 1:
            raise AdapterFailure(
                "OFI-INPUT-SURFACE-001",
                "input_compatibility",
                f"Expected exactly one Core surface record for role {role}, found {len(role_records)}",
            )
        record = role_records[0]
        if record.get("requirement") != requirement or record.get("kind") != kind or record.get("format_version") != format_version:
            raise AdapterFailure(
                "OFI-INPUT-SURFACE-001",
                "input_compatibility",
                f"Incompatible Core surface declaration for role {role}",
            )
        status = record.get("status")
        if status != "available":
            if requirement == "companion" and status == "unavailable":
                continue
            raise AdapterFailure(
                "OFI-INPUT-SURFACE-001",
                "input_compatibility",
                f"Required Core surface {role} is not available",
            )
        path = record.get("path")
        declared_sha = record.get("sha256")
        if not isinstance(path, str) or not isinstance(declared_sha, str):
            raise AdapterFailure("OFI-INPUT-SURFACE-001", "input_compatibility", f"Invalid available surface record for {role}")
        surface_path = resolve_contained_file(root, path, code="OFI-INPUT-SURFACE-001")
        actual_sha = sha256_file(surface_path)
        if actual_sha != declared_sha:
            raise AdapterFailure(
                "OFI-INPUT-SURFACE-002",
                "input_compatibility",
                f"Core surface digest mismatch for {role}: declared {declared_sha}, computed {actual_sha}",
            )
        payload = load_json(surface_path)
        if payload.get(identity_field) != kind:
            raise AdapterFailure(
                "OFI-INPUT-SURFACE-001",
                "input_compatibility",
                f"Core surface native identity mismatch for {role}",
            )
        if native_version_field is not None and payload.get(native_version_field) != format_version:
            raise AdapterFailure(
                "OFI-INPUT-SURFACE-001",
                "input_compatibility",
                f"Core surface native version mismatch for {role}",
            )
        payloads[role] = payload

    expected_mission = (mission["id"], mission["model_version"])
    for role in ("mission_snapshot", "entity_index", "relationship_manifest"):
        if _mission_identity(payloads[role]) != expected_mission:
            raise AdapterFailure(
                "OFI-INPUT-IDENTITY-001",
                "input_compatibility",
                f"Mission identity mismatch between manifest and {role}",
            )
    model_summary = payloads.get("model_summary")
    if model_summary is not None and _mission_identity(model_summary) != expected_mission:
        raise AdapterFailure(
            "OFI-INPUT-IDENTITY-001",
            "input_compatibility",
            "Mission identity mismatch between manifest and model_summary",
        )
    if payloads["mission_snapshot"].get("result") != "loaded":
        raise AdapterFailure("OFI-INPUT-STATE-001", "input_compatibility", "Mission Snapshot result is not loaded")

    entities_payload = payloads["entity_index"].get("entities")
    if not isinstance(entities_payload, list):
        raise AdapterFailure("OFI-INPUT-SURFACE-001", "input_compatibility", "Entity Index entities array missing")
    entities: dict[tuple[str, str], dict[str, Any]] = {}
    for item in entities_payload:
        if not isinstance(item, dict) or not isinstance(item.get("domain"), str) or not isinstance(item.get("id"), str):
            raise AdapterFailure("OFI-INPUT-SURFACE-001", "input_compatibility", "Invalid Entity Index entity record")
        key = (item["domain"], item["id"])
        if key in entities:
            raise AdapterFailure("OFI-INPUT-SURFACE-001", "input_compatibility", f"Duplicate Entity Index identity: {key}")
        entities[key] = item

    return CoreInputSet(
        manifest_path=manifest_path,
        manifest=manifest,
        surfaces=payloads,
        entity_index=payloads["entity_index"],
        mission_snapshot=payloads["mission_snapshot"],
        relationship_manifest=payloads["relationship_manifest"],
        model_summary=model_summary,
        entities=entities,
    )
