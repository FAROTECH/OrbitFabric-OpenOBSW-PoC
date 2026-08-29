from __future__ import annotations

from typing import Any

from .baseline import TargetBaseline
from .core_input import CoreInputSet
from .model import AdapterFailure
from .profile import ProjectionProfile
from .target import (
    allocation_maps,
    argument_contract_compatible,
    check_numeric_and_name,
    message_set,
    require_message,
    target_name,
    target_ref,
)


def binding_source(binding: dict[str, Any]) -> tuple[str, str]:
    source = binding["sources"][0]
    return (source["domain"], source["id"])


def source_ref(source: tuple[str, str]) -> dict[str, str]:
    return {"domain": source[0], "id": source[1]}


def mapping_record(binding: dict[str, Any], targets: list[dict[str, str]]) -> dict[str, Any]:
    source = binding_source(binding)
    return {
        "id": f"mapping.{binding['id']}",
        "sources": [source_ref(source)],
        "profile_bindings": [binding["id"]],
        "targets": targets,
    }


def resolution_record(
    *,
    identifier: str,
    mapping: str,
    binding: str,
    source: tuple[str, str],
    property_name: str,
    value: Any,
    origin: str,
) -> dict[str, Any]:
    return {
        "id": identifier,
        "mapping": mapping,
        "binding": binding,
        "sources": [source_ref(source)],
        "property": property_name,
        "value": value,
        "origin": origin,
    }


def resolve_core_bindings(core: CoreInputSet, profile: ProjectionProfile) -> dict[str, dict[str, Any]]:
    resolved: dict[str, dict[str, Any]] = {}
    for binding in profile.bindings:
        if binding.get("intent") != "project":
            continue
        source = binding_source(binding)
        core.resolve_source(*source)
        resolved[binding["id"]] = {
            "binding": binding,
            "source": source,
            "semantic": core.semantic_object(*source),
        }
    return resolved


def resolve_projection(
    core: CoreInputSet,
    profile: ProjectionProfile,
    baseline: TargetBaseline,
    resolved: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rules = baseline.document["adapter_projection_rules"]
    compatibility = baseline.document["project_compatibility"]
    pus_baseline = compatibility["pus"]
    type_map = rules["core_scalar_to_obsw_srdb"]
    messages = message_set(baseline)
    settings_pus = profile.document["settings"]["pus"]

    if settings_pus["tm_apid"] != pus_baseline["tm_apid"]:
        raise AdapterFailure(
            "OFI-COMP-PUS-001",
            "input_compatibility",
            f"Profile TM APID {settings_pus['tm_apid']} is incompatible with selected baseline TM APID {pus_baseline['tm_apid']}",
        )

    mappings: list[dict[str, Any]] = []
    resolutions: list[dict[str, Any]] = []
    projected_tm_targets = _project_telemetry(
        profile,
        baseline,
        resolved,
        settings_pus,
        type_map,
        mappings,
        resolutions,
    )
    _project_packets(
        core,
        profile,
        baseline,
        resolved,
        rules,
        pus_baseline,
        messages,
        projected_tm_targets,
        mappings,
        resolutions,
    )
    _project_commands(
        profile,
        baseline,
        resolved,
        settings_pus,
        type_map,
        messages,
        mappings,
        resolutions,
    )
    _project_events(
        profile,
        baseline,
        resolved,
        rules,
        pus_baseline,
        messages,
        mappings,
        resolutions,
    )

    expected = len([item for item in profile.bindings if item.get("intent") == "project"])
    if len(mappings) != expected:
        raise AdapterFailure(
            "OFI-PROJ-SRDB-001",
            "projection_validation",
            "Resolved projection mapping set is internally inconsistent",
        )
    mappings.sort(key=lambda item: item["id"])
    resolutions.sort(key=lambda item: item["id"])
    return mappings, resolutions


def _project_telemetry(
    profile: ProjectionProfile,
    baseline: TargetBaseline,
    resolved: dict[str, dict[str, Any]],
    settings_pus: dict[str, Any],
    type_map: dict[str, Any],
    mappings: list[dict[str, Any]],
    resolutions: list[dict[str, Any]],
) -> dict[tuple[str, str], str]:
    projected: dict[tuple[str, str], str] = {}
    for binding in profile.bindings:
        if binding.get("intent") != "project" or binding_source(binding)[0] != "telemetry":
            continue
        source = binding_source(binding)
        semantic = resolved[binding["id"]]["semantic"]
        target_type = type_map.get(semantic.get("type"))
        if target_type is None:
            raise AdapterFailure(
                "OFI-PROJ-TYPE-001",
                "projection_validation",
                f"Core telemetry type {semantic.get('type')!r} has no supported obsw-srdb representation",
                sources=[source_ref(source)],
                profile_bindings=[binding["id"]],
            )
        name = target_name(source[1])
        parameter_id = binding["config"]["obsw_srdb"]["parameter_id"]
        by_id, by_name = allocation_maps(baseline, "parameters", "id")
        check_numeric_and_name(
            numeric_value=parameter_id,
            target_name_value=name,
            by_id=by_id,
            by_name=by_name,
            numeric_code="OFI-COMP-ALLOC-001",
            binding=binding["id"],
            label="parameter",
        )
        mapping_id = f"mapping.{binding['id']}"
        mappings.append(
            mapping_record(
                binding,
                [
                    target_ref("openobsw", "contract_symbol", binding["config"]["flight_contract"]["c_symbol"]),
                    target_ref("obsw-srdb", "parameter", name),
                ],
            )
        )
        projected[source] = name
        resolutions.extend(
            [
                resolution_record(identifier=f"resolution.{binding['id']}.tm_apid", mapping=mapping_id, binding=binding["id"], source=source, property_name="tm_apid", value=settings_pus["tm_apid"], origin="profile"),
                resolution_record(identifier=f"resolution.{binding['id']}.parameter_id", mapping=mapping_id, binding=binding["id"], source=source, property_name="obsw_srdb.parameter_id", value=parameter_id, origin="profile"),
                resolution_record(identifier=f"resolution.{binding['id']}.target_type", mapping=mapping_id, binding=binding["id"], source=source, property_name="obsw_srdb.type", value=target_type, origin="core"),
            ]
        )
    return projected


def _project_packets(
    core: CoreInputSet,
    profile: ProjectionProfile,
    baseline: TargetBaseline,
    resolved: dict[str, dict[str, Any]],
    rules: dict[str, Any],
    pus_baseline: dict[str, Any],
    messages: set[tuple[str, int, int]],
    projected_tm_targets: dict[tuple[str, str], str],
    mappings: list[dict[str, Any]],
    resolutions: list[dict[str, Any]],
) -> None:
    for binding in profile.bindings:
        if binding.get("intent") != "project" or binding_source(binding)[0] != "packets":
            continue
        source = binding_source(binding)
        semantic = resolved[binding["id"]]["semantic"]
        name = target_name(source[1])
        hk_config = binding["config"]["obsw_srdb"]["hk_set"]
        sid = hk_config["sid"]
        by_id, by_name = allocation_maps(baseline, "hk_sets", "sid")
        check_numeric_and_name(
            numeric_value=sid,
            target_name_value=name,
            by_id=by_id,
            by_name=by_name,
            numeric_code="OFI-COMP-ALLOC-003",
            binding=binding["id"],
            label="HK set",
        )
        packet_members = semantic.get("telemetry")
        if not isinstance(packet_members, list):
            raise AdapterFailure(
                "OFI-PROJ-HK-001",
                "projection_validation",
                "Core packet telemetry membership is unavailable",
                sources=[source_ref(source)],
                profile_bindings=[binding["id"]],
            )
        fields: list[str] = []
        for field in hk_config["fields"]:
            field_source = (field["domain"], field["id"])
            core.resolve_source(*field_source)
            if field_source[1] not in packet_members:
                raise AdapterFailure(
                    "OFI-PROJ-HK-001",
                    "projection_validation",
                    f"HK field {field_source[1]} is not a member of Core packet {source[1]}",
                    sources=[source_ref(field_source), source_ref(source)],
                    profile_bindings=[binding["id"]],
                )
            target_field = projected_tm_targets.get(field_source)
            if target_field is None:
                raise AdapterFailure(
                    "OFI-PROJ-HK-002",
                    "projection_validation",
                    f"HK field {field_source[1]} has no projected telemetry target representation",
                    sources=[source_ref(field_source)],
                    profile_bindings=[binding["id"]],
                )
            fields.append(target_field)
        require_message(messages, "TM", 3, 25, binding=binding["id"])
        mapping_id = f"mapping.{binding['id']}"
        mappings.append(
            mapping_record(
                binding,
                [
                    target_ref("openobsw", "contract_symbol", binding["config"]["flight_contract"]["c_symbol"]),
                    target_ref("obsw-srdb", "hk_set", name),
                ],
            )
        )
        resolutions.extend(
            [
                resolution_record(identifier=f"resolution.{binding['id']}.sid", mapping=mapping_id, binding=binding["id"], source=source, property_name="obsw_srdb.hk_set.sid", value=sid, origin="profile"),
                resolution_record(identifier=f"resolution.{binding['id']}.fields", mapping=mapping_id, binding=binding["id"], source=source, property_name="obsw_srdb.hk_set.fields", value=fields, origin="profile"),
                resolution_record(identifier=f"resolution.{binding['id']}.default_interval_ticks", mapping=mapping_id, binding=binding["id"], source=source, property_name="obsw_srdb.default_interval_ticks", value=rules["new_hk_default_interval_ticks"], origin="adapter_default"),
                resolution_record(identifier=f"resolution.{binding['id']}.tm_layout", mapping=mapping_id, binding=binding["id"], source=source, property_name="obsw_srdb.application_data_start_bit", value=pus_baseline["tm_layout"]["obsw_srdb_application_data_start_bit"], origin="adapter_default"),
            ]
        )


def _project_commands(
    profile: ProjectionProfile,
    baseline: TargetBaseline,
    resolved: dict[str, dict[str, Any]],
    settings_pus: dict[str, Any],
    type_map: dict[str, Any],
    messages: set[tuple[str, int, int]],
    mappings: list[dict[str, Any]],
    resolutions: list[dict[str, Any]],
) -> None:
    compatibility = baseline.document["project_compatibility"]
    route_policy = compatibility["pus"]["openobsw_contract_route_apid_policy"]
    telecommands = compatibility["occupied_allocations"]["telecommands"]
    for binding in profile.bindings:
        if binding.get("intent") != "project" or binding_source(binding)[0] != "commands":
            continue
        source = binding_source(binding)
        semantic = resolved[binding["id"]]["semantic"]
        pus = binding["config"]["pus"]
        apid = pus.get("apid", settings_pus["tc_apid"])
        service = pus["service"]
        subtype = pus["subtype"]
        require_message(messages, "TC", service, subtype, binding=binding["id"])
        if route_policy.get("kind") == "fixed" and route_policy.get("value") != apid:
            raise AdapterFailure(
                "OFI-COMP-PUS-003",
                "input_compatibility",
                f"Target TC APID {apid} is incompatible with OpenOBSW route policy",
                profile_bindings=[binding["id"]],
            )
        for response in binding["config"].get("expected_responses", []):
            require_message(messages, "TM", response["service"], response["subtype"], binding=binding["id"])

        existing = [
            item
            for item in telecommands
            if (item["apid"], item["service"], item["subtype"]) == (apid, service, subtype)
        ]
        if len(existing) > 1:
            raise AdapterFailure(
                "OFI-COMP-BASELINE-002",
                "input_compatibility",
                "Baseline contains duplicate target TC tuple",
            )
        if existing:
            target_tc = existing[0]
            if not argument_contract_compatible(
                semantic.get("arguments", []),
                target_tc.get("parameters", []),
                type_map,
            ):
                raise AdapterFailure(
                    "OFI-COMP-TC-001",
                    "input_compatibility",
                    "Existing target telecommand tuple has incompatible argument contract",
                    sources=[source_ref(source)],
                    profile_bindings=[binding["id"]],
                    targets=[target_ref("obsw-srdb", "telecommand", target_tc["name"])],
                )
            action = "reuse_existing"
            name = target_tc["name"]
        else:
            name = target_name(source[1])
            if any(item["name"] == name for item in telecommands):
                raise AdapterFailure(
                    "OFI-COMP-NAME-001",
                    "input_compatibility",
                    f"Projected telecommand name {name!r} collides with baseline target",
                    profile_bindings=[binding["id"]],
                )
            action = "contribute_new"

        mapping_id = f"mapping.{binding['id']}"
        mappings.append(
            mapping_record(
                binding,
                [
                    target_ref("openobsw", "contract_symbol", binding["config"]["flight_contract"]["c_symbol"]),
                    target_ref("obsw-srdb", "telecommand", name),
                ],
            )
        )
        resolutions.extend(
            [
                resolution_record(identifier=f"resolution.{binding['id']}.command_id", mapping=mapping_id, binding=binding["id"], source=source, property_name="flight_contract.command_id", value=binding["config"]["flight_contract"]["command_id"], origin="profile"),
                resolution_record(identifier=f"resolution.{binding['id']}.tc_apid", mapping=mapping_id, binding=binding["id"], source=source, property_name="pus.tc_apid", value=apid, origin="profile"),
                resolution_record(identifier=f"resolution.{binding['id']}.target_action", mapping=mapping_id, binding=binding["id"], source=source, property_name="obsw_srdb.telecommand_action", value=action, origin="adapter_default"),
                resolution_record(identifier=f"resolution.{binding['id']}.target_name", mapping=mapping_id, binding=binding["id"], source=source, property_name="obsw_srdb.telecommand_name", value=name, origin="adapter_default"),
            ]
        )


def _project_events(
    profile: ProjectionProfile,
    baseline: TargetBaseline,
    resolved: dict[str, dict[str, Any]],
    rules: dict[str, Any],
    pus_baseline: dict[str, Any],
    messages: set[tuple[str, int, int]],
    mappings: list[dict[str, Any]],
    resolutions: list[dict[str, Any]],
) -> None:
    severity_subtypes = pus_baseline["event_severity_subtypes"]
    severity_map = profile.document["settings"]["obsw_srdb"]["event_severity_map"]
    for binding in profile.bindings:
        if binding.get("intent") != "project" or binding_source(binding)[0] != "events":
            continue
        source = binding_source(binding)
        semantic = resolved[binding["id"]]["semantic"]
        target_severity = severity_map.get(semantic.get("severity"))
        if target_severity not in severity_subtypes:
            raise AdapterFailure(
                "OFI-PROJ-SEVERITY-001",
                "projection_validation",
                f"Core event severity {semantic.get('severity')!r} cannot be projected through configured target map",
                sources=[source_ref(source)],
                profile_bindings=[binding["id"]],
            )
        subtype = severity_subtypes[target_severity]
        require_message(messages, "TM", 5, subtype, binding=binding["id"])
        event_id = binding["config"]["obsw_srdb"]["event_id"]
        name = target_name(source[1])
        by_id, by_name = allocation_maps(baseline, "events", "id")
        check_numeric_and_name(
            numeric_value=event_id,
            target_name_value=name,
            by_id=by_id,
            by_name=by_name,
            numeric_code="OFI-COMP-ALLOC-002",
            binding=binding["id"],
            label="event",
        )
        mapping_id = f"mapping.{binding['id']}"
        mappings.append(
            mapping_record(
                binding,
                [
                    target_ref("openobsw", "contract_symbol", binding["config"]["flight_contract"]["c_symbol"]),
                    target_ref("obsw-srdb", "event", name),
                ],
            )
        )
        resolutions.extend(
            [
                resolution_record(identifier=f"resolution.{binding['id']}.event_id", mapping=mapping_id, binding=binding["id"], source=source, property_name="obsw_srdb.event_id", value=event_id, origin="profile"),
                resolution_record(identifier=f"resolution.{binding['id']}.severity", mapping=mapping_id, binding=binding["id"], source=source, property_name="obsw_srdb.severity", value=target_severity, origin="profile"),
                resolution_record(identifier=f"resolution.{binding['id']}.pus_subtype", mapping=mapping_id, binding=binding["id"], source=source, property_name="pus.tm_event_subtype", value=subtype, origin="adapter_default"),
                resolution_record(identifier=f"resolution.{binding['id']}.safe_trigger", mapping=mapping_id, binding=binding["id"], source=source, property_name="obsw_srdb.safe_trigger", value=rules["new_event_safe_trigger"], origin="adapter_default"),
            ]
        )
