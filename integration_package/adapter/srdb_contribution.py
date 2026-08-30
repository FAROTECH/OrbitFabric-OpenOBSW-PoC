from __future__ import annotations

from typing import Any

from .artifact_support import mapping_by_binding, projected_bindings, resolution_values, target
from .baseline import TargetBaseline
from .model import AdapterFailure
from .profile import ProjectionProfile


def _limits(semantic: dict[str, Any], baseline: TargetBaseline) -> dict[str, Any] | None:
    source_limits = semantic.get("limits")
    if not isinstance(source_limits, dict):
        return None
    mapping = baseline.document["adapter_projection_rules"]["telemetry_limit_mapping"]
    projected = {
        target_key: source_limits[source_key]
        for source_key, target_key in mapping.items()
        if source_key in source_limits and source_limits[source_key] is not None
    }
    return projected or None


def build_srdb_contribution(
    profile: ProjectionProfile,
    baseline: TargetBaseline,
    resolved: dict[str, dict[str, Any]],
    mappings: list[dict[str, Any]],
    resolutions: list[dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    """Build target-native additive obsw-srdb records without claiming a complete SRDB."""
    by_binding = mapping_by_binding(mappings)
    values = resolution_values(resolutions)
    semantics = {binding_id: item["semantic"] for binding_id, item in resolved.items()}

    records: dict[str, list[dict[str, Any]]] = {
        "parameters": [],
        "telecommands": [],
        "hk_sets": [],
        "events": [],
    }
    reused_targets: list[dict[str, Any]] = []

    for binding in projected_bindings(profile):
        binding_id = binding["id"]
        source = binding["sources"][0]
        domain = source["domain"]
        semantic = semantics[binding_id]
        mapping = by_binding[binding_id]

        if domain == "telemetry":
            target_type = values[f"resolution.{binding_id}.target_type"]
            record: dict[str, Any] = {
                "id": int(values[f"resolution.{binding_id}.parameter_id"]),
                "name": target(mapping, "obsw-srdb", "parameter"),
                "description": semantic.get("description") or source["id"],
                "type": target_type["type"],
                "ptc": int(target_type["ptc"]),
                "pfc": int(target_type["pfc"]),
            }
            if isinstance(semantic.get("source"), str):
                record["subsystem"] = semantic["source"]
            if isinstance(semantic.get("unit"), str):
                record["unit"] = semantic["unit"]
            limits = _limits(semantic, baseline)
            if limits:
                record["limits"] = limits
            records["parameters"].append(record)

        elif domain == "packets":
            records["hk_sets"].append(
                {
                    "id": int(values[f"resolution.{binding_id}.sid"]),
                    "name": target(mapping, "obsw-srdb", "hk_set"),
                    "description": semantic.get("description") or source["id"],
                    "parameters": list(values[f"resolution.{binding_id}.fields"]),
                    "default_interval_ticks": int(
                        values[f"resolution.{binding_id}.default_interval_ticks"]
                    ),
                }
            )

        elif domain == "events":
            records["events"].append(
                {
                    "id": int(values[f"resolution.{binding_id}.event_id"]),
                    "name": target(mapping, "obsw-srdb", "event"),
                    "severity": values[f"resolution.{binding_id}.severity"],
                    "description": semantic.get("description") or source["id"],
                    "safe_trigger": bool(values[f"resolution.{binding_id}.safe_trigger"]),
                    "auxiliary_data": [],
                }
            )

        elif domain == "commands":
            action = values[f"resolution.{binding_id}.target_action"]
            target_name = values[f"resolution.{binding_id}.target_name"]
            if action == "reuse_existing":
                reused_targets.append(
                    {
                        "binding": binding_id,
                        "source": {"domain": domain, "id": source["id"]},
                        "namespace": "obsw-srdb",
                        "kind": "telecommand",
                        "id": target_name,
                        "reason": (
                            "Exact compatible target telecommand already exists "
                            "in the selected baseline."
                        ),
                    }
                )
            elif action == "contribute_new":
                pus = binding["config"]["pus"]
                type_map = baseline.document["adapter_projection_rules"][
                    "core_scalar_to_obsw_srdb"
                ]
                parameters: list[dict[str, Any]] = []
                for argument in semantic.get("arguments", []):
                    target_type = type_map.get(argument.get("type"))
                    if target_type is None:
                        raise AdapterFailure(
                            "OFI-PROJ-TYPE-001",
                            "artifact_generation",
                            (
                                "Core command argument type "
                                f"{argument.get('type')!r} has no supported "
                                "obsw-srdb representation"
                            ),
                            profile_bindings=[binding_id],
                        )
                    parameter = {
                        "name": argument["name"],
                        "type": target_type["type"],
                    }
                    if isinstance(argument.get("description"), str):
                        parameter["description"] = argument["description"]
                    parameters.append(parameter)
                records["telecommands"].append(
                    {
                        "name": target_name,
                        "description": semantic.get("description") or source["id"],
                        "apid": int(values[f"resolution.{binding_id}.tc_apid"]),
                        "service": int(pus["service"]),
                        "subservice": int(pus["subtype"]),
                        "parameters": parameters,
                    }
                )
            else:
                raise AdapterFailure(
                    "OFI-ARTIFACT-TC-001",
                    "artifact_generation",
                    f"Unsupported resolved telecommand action {action!r}",
                    profile_bindings=[binding_id],
                )

    for items in records.values():
        items.sort(key=lambda item: (item.get("id", -1), item.get("name", "")))
    reused_targets.sort(key=lambda item: (item["binding"], item["id"]))
    return records, reused_targets
