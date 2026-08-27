from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from .validator import (
    Diagnostic,
    ValidationInputError,
    _contained_path,
    _read_json,
    _read_yaml,
    validate_profile,
)

RESOLVED_PROJECTION_KIND = "orbitfabric.openobsw_opensvf.resolved_projection"
RESOLVED_PROJECTION_VERSION = "0.1-candidate"
DEFAULT_C_SYMBOL_PREFIX = "OF_"
EXPECTED_SNAPSHOT_KIND = "orbitfabric.mission_snapshot"


@dataclass(frozen=True)
class ProjectionResolutionError(RuntimeError):
    diagnostics: tuple[Diagnostic, ...]

    def __str__(self) -> str:
        if not self.diagnostics:
            return "projection resolution failed"
        return "; ".join(f"{item.code}: {item.message}" for item in self.diagnostics)


def resolve_projection(
    *,
    manifest_path: Path,
    profile_path: Path,
    schema_path: Path,
) -> dict[str, Any]:
    """Resolve validated Core semantics and Profile target intent into adapter IR.

    The resolver consumes only the coherent Core Integration Input Set and the
    version-controlled Projection Profile. It never reads Mission Model YAML.
    """
    validation = validate_profile(
        manifest_path=manifest_path,
        profile_path=profile_path,
        schema_path=schema_path,
    )
    if not validation.ok:
        raise ProjectionResolutionError(validation.diagnostics)

    manifest = _read_json(manifest_path)
    profile = _read_yaml(profile_path)
    snapshot = _load_mission_snapshot(manifest_path, manifest)
    model = snapshot.get("model")
    if not isinstance(model, dict):
        raise ValidationInputError("Mission Snapshot does not contain a loaded model object")

    core_entities = _index_snapshot_entities(model)
    settings, setting_resolutions = _resolve_settings(profile)

    projections: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    bindings = profile.get("bindings", [])
    if not isinstance(bindings, list):
        raise ValidationInputError("Projection Profile bindings must be an array")

    for binding in bindings:
        if not isinstance(binding, dict):
            continue
        if binding.get("intent") == "do_not_project":
            exclusions.append(_resolve_exclusion(binding))
            continue
        projections.append(
            _resolve_binding(
                binding=binding,
                core_entities=core_entities,
                model=model,
                settings=settings,
            )
        )

    projections.sort(key=lambda item: item["binding_id"])
    exclusions.sort(key=lambda item: item["binding_id"])

    profile_identity = profile["profile"]
    integration_identity = profile["integration"]
    mission_identity = manifest.get("mission")
    if not isinstance(mission_identity, dict):
        raise ValidationInputError("Integration Input Set has no available mission identity")

    return {
        "kind": RESOLVED_PROJECTION_KIND,
        "resolved_projection_version": RESOLVED_PROJECTION_VERSION,
        "integration": {
            "id": integration_identity["id"],
            "schema_version": integration_identity["schema_version"],
        },
        "profile": {
            "id": profile_identity["id"],
            "version": profile_identity["version"],
        },
        "mission": {
            "id": mission_identity["id"],
            "model_version": mission_identity["model_version"],
        },
        "core_input_set": {
            "kind": manifest["kind"],
            "input_set_version": manifest["input_set_version"],
            "input_set_sha256": manifest.get("input_set_sha256"),
        },
        "settings": settings,
        "setting_resolutions": setting_resolutions,
        "projections": projections,
        "exclusions": exclusions,
    }


def write_resolved_projection(
    *,
    manifest_path: Path,
    profile_path: Path,
    schema_path: Path,
    output_file: Path,
) -> Path:
    payload = resolve_projection(
        manifest_path=manifest_path,
        profile_path=profile_path,
        schema_path=schema_path,
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_file


def _load_mission_snapshot(
    manifest_path: Path,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    surfaces = manifest.get("surfaces")
    if not isinstance(surfaces, list):
        raise ValidationInputError("Integration Input Set surfaces must be an array")

    record = next(
        (
            item
            for item in surfaces
            if isinstance(item, dict) and item.get("role") == "mission_snapshot"
        ),
        None,
    )
    if not isinstance(record, dict) or record.get("status") != "available":
        raise ValidationInputError("Mission Snapshot is unavailable")
    relative = record.get("path")
    if not isinstance(relative, str):
        raise ValidationInputError("Mission Snapshot has no path")

    snapshot = _read_json(_contained_path(manifest_path.parent, relative))
    if snapshot.get("kind") != EXPECTED_SNAPSHOT_KIND:
        raise ValidationInputError("unexpected Mission Snapshot kind")
    if snapshot.get("snapshot_version") != record.get("format_version"):
        raise ValidationInputError("Mission Snapshot version does not match Input Set manifest")
    if snapshot.get("result") != "loaded":
        raise ValidationInputError("Mission Snapshot does not represent a loaded model")
    return snapshot


def _index_snapshot_entities(model: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for domain in ("telemetry", "packets", "commands", "events"):
        values = model.get(domain)
        if not isinstance(values, list):
            raise ValidationInputError(f"Mission Snapshot model.{domain} must be an array")
        for value in values:
            if not isinstance(value, dict) or not isinstance(value.get("id"), str):
                raise ValidationInputError(f"invalid {domain} entity in Mission Snapshot")
            ref = (domain, value["id"])
            if ref in index:
                raise ValidationInputError(
                    f"duplicate Mission Snapshot source: {domain}/{value['id']}"
                )
            index[ref] = value
    return index


def _resolve_settings(profile: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    authored = profile.get("settings")
    authored_settings = authored if isinstance(authored, dict) else {}
    flight_contract = authored_settings.get("flight_contract")
    flight_contract = flight_contract if isinstance(flight_contract, dict) else {}
    opensvf = authored_settings.get("opensvf")
    opensvf = opensvf if isinstance(opensvf, dict) else {}

    if "c_symbol_prefix" in flight_contract:
        c_symbol_prefix = flight_contract["c_symbol_prefix"]
        prefix_origin = "profile"
    else:
        c_symbol_prefix = DEFAULT_C_SYMBOL_PREFIX
        prefix_origin = "adapter_default"

    domain_apids = opensvf.get("domain_apids", {})
    if not isinstance(domain_apids, dict):
        domain_apids = {}

    settings = {
        "flight_contract": {"c_symbol_prefix": c_symbol_prefix},
        "opensvf": {"domain_apids": dict(sorted(domain_apids.items()))},
    }
    resolutions = [
        {
            "property": "settings.flight_contract.c_symbol_prefix",
            "origin": prefix_origin,
            "value": c_symbol_prefix,
        }
    ]
    for domain, apid in sorted(domain_apids.items()):
        resolutions.append(
            {
                "property": f"settings.opensvf.domain_apids.{domain}",
                "origin": "profile",
                "value": apid,
            }
        )
    return settings, resolutions


def _resolve_binding(
    *,
    binding: dict[str, Any],
    core_entities: dict[tuple[str, str], dict[str, Any]],
    model: dict[str, Any],
    settings: dict[str, Any],
) -> dict[str, Any]:
    binding_id = binding["id"]
    sources = binding["sources"]
    source = sources[0]
    source_ref = (source["domain"], source["id"])
    semantic = core_entities.get(source_ref)
    if semantic is None:
        raise ValidationInputError(
            f"validated source disappeared from Mission Snapshot: {source_ref[0]}/{source_ref[1]}"
        )

    config = binding["config"]
    kind = config["kind"]
    target, resolutions = _resolve_target(
        source=source,
        config=config,
        c_symbol_prefix=settings["flight_contract"]["c_symbol_prefix"],
    )

    core_semantics: dict[str, Any] = {"source": semantic}
    if kind == "housekeeping_packet":
        member_ids = semantic.get("telemetry", [])
        if not isinstance(member_ids, list):
            raise ValidationInputError(
                f"packet {source['id']} telemetry membership must be an array"
            )
        telemetry_index = {
            item["id"]: item
            for item in model.get("telemetry", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        members = []
        for member_id in member_ids:
            member = telemetry_index.get(member_id)
            if member is None:
                raise ValidationInputError(
                    f"packet {source['id']} references missing telemetry {member_id}"
                )
            members.append(member)
        core_semantics["telemetry_members"] = members

    return {
        "binding_id": binding_id,
        "kind": kind,
        "sources": [{"domain": source["domain"], "id": source["id"]}],
        "core_semantics": core_semantics,
        "target": target,
        "resolutions": resolutions,
    }


def _resolve_target(
    *,
    source: dict[str, Any],
    config: dict[str, Any],
    c_symbol_prefix: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    target: dict[str, Any] = {"kind": config["kind"]}
    resolutions: list[dict[str, Any]] = []

    for property_name in ("numeric_id", "sid", "pus", "verification"):
        if property_name in config:
            target[property_name] = config[property_name]
            resolutions.append(
                {
                    "property": f"target.{property_name}",
                    "origin": "profile",
                    "value": config[property_name],
                }
            )

    if "srdb_name" in config:
        srdb_name = config["srdb_name"]
        srdb_origin = "profile"
    else:
        srdb_name = source["id"]
        srdb_origin = "adapter_default"
    if config["kind"] != "housekeeping_packet":
        target["srdb_name"] = srdb_name
        resolutions.append(
            {
                "property": "target.srdb_name",
                "origin": srdb_origin,
                "value": srdb_name,
            }
        )

    if "c_symbol" in config:
        c_symbol = config["c_symbol"]
        c_symbol_origin = "profile"
    else:
        c_symbol = _derive_c_symbol(c_symbol_prefix, source["id"])
        c_symbol_origin = "adapter_default"
    target["c_symbol"] = c_symbol
    resolutions.append(
        {
            "property": "target.c_symbol",
            "origin": c_symbol_origin,
            "value": c_symbol,
        }
    )

    return target, sorted(resolutions, key=lambda item: item["property"])


def _derive_c_symbol(prefix: str, core_id: str) -> str:
    body = re.sub(r"[^A-Za-z0-9_]", "_", core_id).upper()
    body = re.sub(r"_+", "_", body).strip("_")
    if not body:
        raise ValidationInputError(f"cannot derive C symbol from Core id: {core_id}")
    return f"{prefix}{body}"


def _resolve_exclusion(binding: dict[str, Any]) -> dict[str, Any]:
    sources = [
        {"domain": item["domain"], "id": item["id"]}
        for item in binding.get("sources", [])
        if isinstance(item, dict)
    ]
    sources.sort(key=lambda item: (item["domain"], item["id"]))
    return {
        "binding_id": binding["id"],
        "sources": sources,
        "reason": binding["reason"],
    }
