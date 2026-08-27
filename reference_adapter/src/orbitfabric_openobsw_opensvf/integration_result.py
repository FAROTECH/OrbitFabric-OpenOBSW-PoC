from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .validator import ValidationInputError, _contained_path, _read_json, _read_yaml

RESULT_KIND = "orbitfabric.integration_result"
RESULT_VERSION = "0.1-candidate"
INTEGRATION_ID = "orbitfabric-openobsw-opensvf"
ADAPTER_ID = "orbitfabric-openobsw-opensvf"
PROJECT_CAPABILITIES = [
    "profile_validation",
    "projection",
    "artifact_generation",
    "traceability",
]
PROJECT_SCOPE_DOMAINS = ["commands", "events", "packets", "telemetry"]


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def available_provenance(
    *, manifest_path: Path, profile_path: Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest = _read_json(manifest_path)
    profile = _read_yaml(profile_path)

    mission = manifest.get("mission")
    if not isinstance(mission, dict):
        raise ValidationInputError("Integration Input Set has no mission identity")
    profile_identity = profile.get("profile")
    if not isinstance(profile_identity, dict):
        raise ValidationInputError("Projection Profile has no profile identity")
    integration = profile.get("integration")
    if not isinstance(integration, dict):
        raise ValidationInputError("Projection Profile has no integration identity")

    core = {
        "status": "available",
        "kind": manifest.get("kind"),
        "version": manifest.get("input_set_version"),
        "sha256": manifest.get("input_set_sha256"),
        "reason": None,
    }
    profile_provenance = {
        "status": "available",
        "kind": profile.get("kind"),
        "profile_version": profile.get("profile_version"),
        "id": profile_identity.get("id"),
        "version": profile_identity.get("version"),
        "sha256": file_sha256(profile_path),
        "reason": None,
    }
    mission_provenance = {
        "status": "available",
        "id": mission.get("id"),
        "model_version": mission.get("model_version"),
        "reason": None,
    }
    return manifest, profile, core, profile_provenance, mission_provenance


def unavailable_core(reason: str) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "kind": None,
        "version": None,
        "sha256": None,
        "reason": reason,
    }


def unavailable_profile(reason: str) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "kind": None,
        "profile_version": None,
        "id": None,
        "version": None,
        "sha256": None,
        "reason": reason,
    }


def unavailable_mission(reason: str) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "id": None,
        "model_version": None,
        "reason": reason,
    }


def artifact_record(
    *, artifact_id: str, kind: str, media_type: str, path: str | None,
    digest: str | None, status: str, reason: str | None,
    mapping_ids: list[str], requirement: str = "required"
) -> dict[str, Any]:
    return {
        "id": artifact_id,
        "kind": kind,
        "requirement": requirement,
        "status": status,
        "path": path,
        "media_type": media_type,
        "sha256": digest,
        "reason": reason,
        "retained_partial": False,
        "derived_from_mappings": sorted(mapping_ids),
    }


def build_mappings(resolved: dict[str, Any]) -> list[dict[str, Any]]:
    mappings: list[dict[str, Any]] = []
    projections = resolved.get("projections")
    if not isinstance(projections, list):
        raise ValidationInputError("resolved projections must be an array")

    for projection in projections:
        if not isinstance(projection, dict):
            continue
        binding_id = projection.get("binding_id")
        sources = projection.get("sources")
        target = projection.get("target")
        kind = projection.get("kind")
        if not isinstance(binding_id, str) or not isinstance(sources, list) or not isinstance(target, dict):
            raise ValidationInputError("resolved projection is incomplete for Result mapping")

        targets: list[dict[str, str]] = []
        c_symbol = target.get("c_symbol")
        if isinstance(c_symbol, str):
            targets.append(
                {"namespace": "openobsw", "kind": "contract_symbol", "id": c_symbol}
            )
        if kind == "telemetry_parameter":
            srdb_name = target.get("srdb_name")
            if isinstance(srdb_name, str):
                targets.append(
                    {"namespace": "opensvf", "kind": "srdb_parameter", "id": srdb_name}
                )
        if not targets:
            raise ValidationInputError(f"projection {binding_id} has no Result target identity")

        mappings.append(
            {
                "id": f"mapping.{binding_id}",
                "sources": sources,
                "profile_bindings": [binding_id],
                "targets": targets,
            }
        )
    return sorted(mappings, key=lambda item: item["id"])


def build_resolutions(resolved: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    projections = resolved.get("projections")
    if not isinstance(projections, list):
        return records

    for projection in projections:
        if not isinstance(projection, dict):
            continue
        binding_id = projection.get("binding_id")
        sources = projection.get("sources")
        values = projection.get("resolutions")
        if not isinstance(binding_id, str) or not isinstance(sources, list) or not isinstance(values, list):
            continue
        mapping_id = f"mapping.{binding_id}"

        for index, value in enumerate(values):
            if not isinstance(value, dict):
                continue
            origin = value.get("origin")
            prop = value.get("property")
            if origin not in {"core", "adapter_default", "profile"} or not isinstance(prop, str):
                continue

            anchor_binding: str | None = binding_id
            source_bindings = value.get("source_bindings")
            if origin == "profile" and isinstance(source_bindings, list) and source_bindings:
                first = source_bindings[0]
                if isinstance(first, str):
                    anchor_binding = first

            # Global Profile settings such as domain APID are intentionally omitted
            # from v0 resolutions because B.3 requires profile-origin records to be
            # anchored to a concrete Profile binding. The exact value remains in the
            # target artifact/IR and can be exposed later if the generic contract grows
            # a Profile-setting anchor.
            if origin == "profile" and prop == "target.opensvf.pus.apid":
                continue

            safe = "".join(ch if ch.isalnum() else "_" for ch in prop).strip("_")
            records.append(
                {
                    "id": f"resolution.{binding_id}.{safe}.{index}",
                    "mapping": mapping_id,
                    "binding": anchor_binding,
                    "sources": sources,
                    "property": prop,
                    "value": value.get("value"),
                    "origin": origin,
                }
            )
    return sorted(records, key=lambda item: item["id"])


def _entity_refs(manifest_path: Path, manifest: dict[str, Any]) -> list[dict[str, str]]:
    surfaces = manifest.get("surfaces")
    if not isinstance(surfaces, list):
        raise ValidationInputError("Integration Input Set surfaces must be an array")
    entity_surface = next(
        (
            item for item in surfaces
            if isinstance(item, dict) and item.get("role") == "entity_index"
        ),
        None,
    )
    if not isinstance(entity_surface, dict) or entity_surface.get("status") != "available":
        raise ValidationInputError("Entity Index is unavailable")
    relative = entity_surface.get("path")
    if not isinstance(relative, str):
        raise ValidationInputError("Entity Index has no path")
    index = _read_json(_contained_path(manifest_path.parent, relative))
    entities = index.get("entities")
    if not isinstance(entities, list):
        raise ValidationInputError("Entity Index entities must be an array")

    refs: list[dict[str, str]] = []
    for item in entities:
        if not isinstance(item, dict):
            continue
        domain, entity_id = item.get("domain"), item.get("id")
        if domain in PROJECT_SCOPE_DOMAINS and isinstance(entity_id, str):
            refs.append({"domain": domain, "id": entity_id})
    return sorted(refs, key=lambda item: (item["domain"], item["id"]))


def build_complete_coverage(
    *, manifest_path: Path, manifest: dict[str, Any], resolved: dict[str, Any], mappings: list[dict[str, Any]]
) -> dict[str, Any]:
    mapping_by_source: dict[tuple[str, str], list[str]] = {}
    binding_by_source: dict[tuple[str, str], list[str]] = {}
    for mapping in mappings:
        for source in mapping["sources"]:
            key = (source["domain"], source["id"])
            mapping_by_source.setdefault(key, []).append(mapping["id"])
            binding_by_source.setdefault(key, []).extend(mapping["profile_bindings"])

    exclusions: dict[tuple[str, str], tuple[str, str]] = {}
    for exclusion in resolved.get("exclusions", []):
        if not isinstance(exclusion, dict):
            continue
        binding = exclusion.get("binding_id")
        reason = exclusion.get("reason")
        if not isinstance(binding, str) or not isinstance(reason, str):
            continue
        for source in exclusion.get("sources", []):
            if isinstance(source, dict) and isinstance(source.get("domain"), str) and isinstance(source.get("id"), str):
                exclusions[(source["domain"], source["id"])] = (binding, reason)

    records: list[dict[str, Any]] = []
    for source in _entity_refs(manifest_path, manifest):
        key = (source["domain"], source["id"])
        if key in mapping_by_source:
            records.append(
                {
                    "source": source,
                    "state": "projected",
                    "mappings": sorted(set(mapping_by_source[key])),
                    "profile_bindings": sorted(set(binding_by_source[key])),
                    "diagnostics": [],
                    "reason": None,
                }
            )
        elif key in exclusions:
            binding, reason = exclusions[key]
            records.append(
                {
                    "source": source,
                    "state": "intentionally_not_projected",
                    "mappings": [],
                    "profile_bindings": [binding],
                    "diagnostics": [],
                    "reason": reason,
                }
            )
        else:
            records.append(
                {
                    "source": source,
                    "state": "not_projected",
                    "mappings": [],
                    "profile_bindings": [],
                    "diagnostics": [],
                    "reason": "No resolved projection or explicit do_not_project binding",
                }
            )

    counts = Counter(record["state"] for record in records)
    summary = {state: counts[state] for state in sorted(counts)}
    return {
        "status": "complete",
        "scope": {"domains": PROJECT_SCOPE_DOMAINS},
        "reason": None,
        "summary": summary,
        "records": records,
    }


def build_success_result(
    *, adapter_version: str, operation_id: str, manifest_path: Path,
    profile_path: Path, resolved: dict[str, Any], artifacts: list[dict[str, Any]]
) -> dict[str, Any]:
    manifest, profile, core, profile_provenance, mission = available_provenance(
        manifest_path=manifest_path, profile_path=profile_path
    )
    mappings = build_mappings(resolved)
    coverage = build_complete_coverage(
        manifest_path=manifest_path, manifest=manifest, resolved=resolved, mappings=mappings
    )
    integration = profile["integration"]
    return {
        "kind": RESULT_KIND,
        "result_version": RESULT_VERSION,
        "result": "succeeded",
        "integration": {
            "id": INTEGRATION_ID,
            "schema_version": integration["schema_version"],
        },
        "adapter": {"id": ADAPTER_ID, "version": adapter_version},
        "operation": {"id": operation_id},
        "mission": mission,
        "inputs": {"core_input_set": core, "profile": profile_provenance},
        "capabilities": PROJECT_CAPABILITIES,
        "artifacts": artifacts,
        "mappings": mappings,
        "resolutions": build_resolutions(resolved),
        "diagnostics": [],
        "coverage": coverage,
        "evidence": [],
        "external_tools": [],
    }


def failed_result(
    *, adapter_version: str, operation_id: str, schema_version: str | None,
    core: dict[str, Any], profile: dict[str, Any], mission: dict[str, Any],
    diagnostics: list[dict[str, Any]], artifacts: list[dict[str, Any]],
    coverage_reason: str
) -> dict[str, Any]:
    return {
        "kind": RESULT_KIND,
        "result_version": RESULT_VERSION,
        "result": "failed",
        "integration": {"id": INTEGRATION_ID, "schema_version": schema_version},
        "adapter": {"id": ADAPTER_ID, "version": adapter_version},
        "operation": {"id": operation_id},
        "mission": mission,
        "inputs": {"core_input_set": core, "profile": profile},
        "capabilities": ["profile_validation"],
        "artifacts": artifacts,
        "mappings": [],
        "resolutions": [],
        "diagnostics": diagnostics,
        "coverage": {
            "status": "unavailable",
            "scope": {"domains": PROJECT_SCOPE_DOMAINS},
            "reason": coverage_reason,
            "summary": {},
            "records": [],
        },
        "evidence": [],
        "external_tools": [],
    }


def write_result_last(output_dir: Path, result: dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "integration_result.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
