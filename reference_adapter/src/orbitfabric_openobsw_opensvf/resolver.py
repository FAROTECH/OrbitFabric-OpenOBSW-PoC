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
    *, manifest_path: Path, profile_path: Path, schema_path: Path
) -> dict[str, Any]:
    """Resolve Core-owned semantics plus Profile intent into adapter-owned IR."""
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
        else:
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
    manifest_path: Path, manifest: dict[str, Any]
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


def _index_snapshot_entities(
    model: dict[str, Any],
) -> dict[tuple[str, str], dict[str, Any]]:
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


def _resolve_settings(
    profile: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    authored = profile.get("settings")
    authored = authored if isinstance(authored, dict) else {}
    flight = authored.get("flight_contract")
    flight = flight if isinstance(flight, dict) else {}
    opensvf = authored.get("opensvf")
    opensvf = opensvf if isinstance(opensvf, dict) else {}

    if "c_symbol_prefix" in flight:
        prefix = flight["c_symbol_prefix"]
        prefix_origin = "profile"
    else:
        prefix = DEFAULT_C_SYMBOL_PREFIX
        prefix_origin = "adapter_default"

    profile_identity = profile["profile"]
    flight_settings = {
        "c_symbol_prefix": prefix,
        "contract_name": profile_identity["id"],
        "contract_version": profile_identity["version"],
    }
    domain_apids = opensvf.get("domain_apids", {})
    domain_apids = domain_apids if isinstance(domain_apids, dict) else {}
    settings = {
        "flight_contract": flight_settings,
        "opensvf": {"domain_apids": dict(sorted(domain_apids.items()))},
    }
    resolutions = [
        {
            "property": "settings.flight_contract.c_symbol_prefix",
            "origin": prefix_origin,
            "value": prefix,
        },
        {
            "property": "settings.flight_contract.contract_name",
            "origin": "adapter_default",
            "value": profile_identity["id"],
        },
        {
            "property": "settings.flight_contract.contract_version",
            "origin": "adapter_default",
            "value": profile_identity["version"],
        },
    ]
    for domain, apid in sorted(domain_apids.items()):
        resolutions.append(
            {
                "property": f"settings.opensvf.domain_apids.{domain}",
                "origin": "profile",
                "value": apid,
            }
        )
    return settings, sorted(resolutions, key=lambda item: item["property"])


def _resolve_binding(
    *,
    binding: dict[str, Any],
    core_entities: dict[tuple[str, str], dict[str, Any]],
    model: dict[str, Any],
    settings: dict[str, Any],
) -> dict[str, Any]:
    source = binding["sources"][0]
    ref = (source["domain"], source["id"])
    semantic = core_entities.get(ref)
    if semantic is None:
        raise ValidationInputError(
            f"validated source disappeared from Mission Snapshot: {ref[0]}/{ref[1]}"
        )

    config = binding["config"]
    target, resolutions = _resolve_target(
        source=source,
        semantic=semantic,
        config=config,
        c_symbol_prefix=settings["flight_contract"]["c_symbol_prefix"],
    )
    core_semantics: dict[str, Any] = {"origin": "core", "source": semantic}

    if config["kind"] == "housekeeping_packet":
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
        target_members = []
        for member_id in member_ids:
            member = telemetry_index.get(member_id)
            if member is None:
                raise ValidationInputError(
                    f"packet {source['id']} references missing telemetry {member_id}"
                )
            members.append(member)
            c_type = _c_type_for_core_type(member.get("type"))
            field_name = _c_field_name(member_id)
            target_members.append(
                {"core_id": member_id, "c_type": c_type, "field_name": field_name}
            )
            resolutions.extend(
                [
                    {
                        "property": f"target.members.{member_id}.c_type",
                        "origin": "adapter_default",
                        "value": c_type,
                    },
                    {
                        "property": f"target.members.{member_id}.field_name",
                        "origin": "adapter_default",
                        "value": field_name,
                    },
                ]
            )
        core_semantics["telemetry_members"] = members
        target["members"] = target_members

    return {
        "binding_id": binding["id"],
        "kind": config["kind"],
        "sources": [{"domain": source["domain"], "id": source["id"]}],
        "core_semantics": core_semantics,
        "target": target,
        "resolutions": sorted(resolutions, key=lambda item: item["property"]),
    }


def _resolve_target(
    *,
    source: dict[str, Any],
    semantic: dict[str, Any],
    config: dict[str, Any],
    c_symbol_prefix: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    kind = config["kind"]
    target: dict[str, Any] = {"kind": kind}
    resolutions: list[dict[str, Any]] = [
        {"property": "target.kind", "origin": "profile", "value": kind}
    ]

    for name in ("numeric_id", "sid", "pus", "verification"):
        if name in config:
            target[name] = config[name]
            resolutions.append(
                {"property": f"target.{name}", "origin": "profile", "value": config[name]}
            )

    if kind != "housekeeping_packet":
        srdb_name = config.get("srdb_name", source["id"])
        target["srdb_name"] = srdb_name
        resolutions.append(
            {
                "property": "target.srdb_name",
                "origin": "profile" if "srdb_name" in config else "adapter_default",
                "value": srdb_name,
            }
        )

    c_symbol = config.get("c_symbol")
    if c_symbol is None:
        c_symbol = _derive_c_symbol(c_symbol_prefix, kind, source["id"])
        c_symbol_origin = "adapter_default"
    else:
        c_symbol_origin = "profile"
    target["c_symbol"] = c_symbol
    resolutions.append(
        {"property": "target.c_symbol", "origin": c_symbol_origin, "value": c_symbol}
    )

    if kind == "telemetry_parameter":
        c_type = _c_type_for_core_type(semantic.get("type"))
        field_name = _c_field_name(source["id"])
        target["c_type"] = c_type
        target["field_name"] = field_name
        resolutions.extend(
            [
                {
                    "property": "target.c_type",
                    "origin": "adapter_default",
                    "value": c_type,
                },
                {
                    "property": "target.field_name",
                    "origin": "adapter_default",
                    "value": field_name,
                },
            ]
        )
    elif kind == "housekeeping_packet":
        struct_type = _hk_struct_type(source["id"])
        interval_s = _period_to_seconds(semantic.get("period"))
        target["struct_type"] = struct_type
        target["collection_interval_s"] = interval_s
        resolutions.extend(
            [
                {
                    "property": "target.struct_type",
                    "origin": "adapter_default",
                    "value": struct_type,
                },
                {
                    "property": "target.collection_interval_s",
                    "origin": "adapter_default",
                    "value": interval_s,
                },
            ]
        )

    return target, resolutions


def _derive_c_symbol(prefix: str, kind: str, core_id: str) -> str:
    if kind == "telemetry_parameter":
        role = "TM_"
        body = _drop_domain_segment(core_id)
    elif kind == "command":
        role = "CMD_"
        body = core_id.split(".")[-1]
    elif kind == "event":
        role = "EVENT_"
        body = core_id.split(".")[-1]
    elif kind == "housekeeping_packet":
        role = "HK_SET_"
        body = core_id[:-3] if core_id.endswith("_hk") else core_id
    else:
        raise ValidationInputError(f"unsupported projection kind for C symbol: {kind}")
    normalized = re.sub(r"[^A-Za-z0-9_]", "_", body).upper()
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if not normalized:
        raise ValidationInputError(f"cannot derive C symbol from Core id: {core_id}")
    return f"{prefix}{role}{normalized}"


def _drop_domain_segment(core_id: str) -> str:
    parts = core_id.split(".")
    return ".".join(parts[1:]) if len(parts) >= 3 else core_id


def _c_field_name(core_id: str) -> str:
    body = _drop_domain_segment(core_id)
    normalized = re.sub(r"[^A-Za-z0-9_]", "_", body).lower()
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if not normalized or normalized[0].isdigit():
        raise ValidationInputError(f"cannot derive C field name from Core id: {core_id}")
    return normalized


def _c_type_for_core_type(core_type: Any) -> str:
    mapping = {"uint16": "uint16_t"}
    try:
        return mapping[core_type]
    except (KeyError, TypeError) as exc:
        raise ValidationInputError(
            f"unsupported Core telemetry type for C flight contract: {core_type}"
        ) from exc


def _hk_struct_type(packet_id: str) -> str:
    base = packet_id[:-3] if packet_id.endswith("_hk") else packet_id
    normalized = re.sub(r"[^A-Za-z0-9_]", "_", base).lower()
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if not normalized:
        raise ValidationInputError(f"cannot derive HK C struct type from packet id: {packet_id}")
    return f"of_hk_{normalized}_t"


def _period_to_seconds(period: Any) -> int:
    if not isinstance(period, str):
        raise ValidationInputError("housekeeping packet period is required for flight contract")
    match = re.fullmatch(r"\s*(\d+)\s*s\s*", period)
    if match is None:
        raise ValidationInputError(
            f"unsupported housekeeping period for C flight contract: {period}"
        )
    value = int(match.group(1))
    if value <= 0:
        raise ValidationInputError("housekeeping collection interval must be positive")
    return value


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
