from __future__ import annotations

from typing import Any

from .artifact_support import mapping_by_binding, projected_bindings, resolution_values, target
from .core_input import CoreInputSet
from .model import AdapterFailure
from .profile import ProjectionProfile

_C_TYPES = {
    "uint8": "uint8_t",
    "uint16": "uint16_t",
    "uint32": "uint32_t",
    "int8": "int8_t",
    "int16": "int16_t",
    "int32": "int32_t",
    "float32": "float",
}


def render_flight_contract(
    core: CoreInputSet,
    profile: ProjectionProfile,
    mappings: list[dict[str, Any]],
    resolutions: list[dict[str, Any]],
) -> str:
    """Render the contract-only C header from already validated projection records."""
    by_binding = mapping_by_binding(mappings)
    values = resolution_values(resolutions)

    lines = [
        "/*",
        " * GENERATED FILE. DO NOT EDIT.",
        " *",
        " * OrbitFabric OpenOBSW/OpenSVF Integration Adapter output.",
        f" * Mission: {core.mission['id']} ({core.mission['model_version']})",
        f" * Projection Profile: {profile.id} ({profile.version})",
        " *",
        " * Contract-only artifact: no PUS framing, transport, scheduling,",
        " * dispatch, runtime behavior or dynamic allocation is generated here.",
        " */",
        "",
        "#ifndef OF_MISSION_CONTRACT_H",
        "#define OF_MISSION_CONTRACT_H",
        "",
        "#include <stdint.h>",
        "",
        f'#define OF_MISSION_ID "{core.mission["id"]}"',
        f'#define OF_MISSION_MODEL_VERSION "{core.mission["model_version"]}"',
        f'#define OF_PROJECTION_PROFILE_ID "{profile.id}"',
        f'#define OF_PROJECTION_PROFILE_VERSION "{profile.version}"',
        "",
    ]

    telemetry: list[tuple[str, int]] = []
    commands: list[tuple[str, int]] = []
    events: list[tuple[str, int]] = []
    packets: list[tuple[str, int]] = []

    for binding in projected_bindings(profile):
        binding_id = binding["id"]
        mapping = by_binding[binding_id]
        domain = binding["sources"][0]["domain"]
        symbol = target(mapping, "openobsw", "contract_symbol")
        if domain == "telemetry":
            telemetry.append((symbol, int(values[f"resolution.{binding_id}.parameter_id"])))
        elif domain == "commands":
            commands.append((symbol, int(values[f"resolution.{binding_id}.command_id"])))
        elif domain == "events":
            events.append((symbol, int(values[f"resolution.{binding_id}.event_id"])))
        elif domain == "packets":
            packets.append((symbol, int(values[f"resolution.{binding_id}.sid"])))

    def enum_block(type_name: str, invalid: str, records: list[tuple[str, int]]) -> None:
        lines.extend(["typedef enum {", f"    {invalid} = 0,"])
        for index, (symbol, value) in enumerate(records):
            comma = "," if index < len(records) - 1 else ""
            lines.append(f"    {symbol} = 0x{value:04X}{comma}")
        lines.extend([f"}} {type_name};", ""])

    enum_block("of_tm_id_t", "OF_TM_INVALID", telemetry)
    enum_block("of_cmd_id_t", "OF_CMD_INVALID", commands)
    enum_block("of_event_id_t", "OF_EVENT_INVALID", events)
    enum_block("of_hk_set_id_t", "OF_HK_SET_INVALID", packets)

    for binding in projected_bindings(profile):
        binding_id = binding["id"]
        if binding["sources"][0]["domain"] != "packets":
            continue
        symbol = target(by_binding[binding_id], "openobsw", "contract_symbol")
        interval = int(values[f"resolution.{binding_id}.default_interval_ticks"])
        lines.append(f"#define {symbol}_DEFAULT_INTERVAL_TICKS {interval}u")
    if packets:
        lines.append("")

    telemetry_binding_by_target: dict[str, str] = {}
    for binding in projected_bindings(profile):
        binding_id = binding["id"]
        if binding["sources"][0]["domain"] == "telemetry":
            parameter = target(by_binding[binding_id], "obsw-srdb", "parameter")
            telemetry_binding_by_target[parameter] = binding_id

    for binding in projected_bindings(profile):
        binding_id = binding["id"]
        if binding["sources"][0]["domain"] != "packets":
            continue

        hk_name = target(by_binding[binding_id], "obsw-srdb", "hk_set")
        fields = values[f"resolution.{binding_id}.fields"]
        if not isinstance(fields, list) or not all(isinstance(item, str) for item in fields):
            raise AdapterFailure(
                "OFI-ARTIFACT-HK-001",
                "artifact_generation",
                f"Resolved HK fields are invalid for {binding_id}",
                profile_bindings=[binding_id],
            )

        lines.append("typedef struct {")
        for field in fields:
            telemetry_binding = telemetry_binding_by_target.get(field)
            if telemetry_binding is None:
                raise AdapterFailure(
                    "OFI-ARTIFACT-HK-001",
                    "artifact_generation",
                    f"Resolved HK field {field} has no projected telemetry binding",
                    profile_bindings=[binding_id],
                )
            target_type = values[f"resolution.{telemetry_binding}.target_type"]
            type_name = target_type.get("type") if isinstance(target_type, dict) else None
            c_type = _C_TYPES.get(type_name)
            if c_type is None:
                raise AdapterFailure(
                    "OFI-ARTIFACT-C-TYPE-001",
                    "artifact_generation",
                    f"No C representation for resolved target type {type_name!r}",
                    profile_bindings=[telemetry_binding],
                )
            lines.append(f"    {c_type} {field};")
        lines.extend([f"}} of_hk_{hk_name}_t;", ""])

    lines.extend(["#endif /* OF_MISSION_CONTRACT_H */", ""])
    return "\n".join(lines)
