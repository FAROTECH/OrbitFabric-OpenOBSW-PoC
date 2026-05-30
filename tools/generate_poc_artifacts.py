#!/usr/bin/env python3
"""Generate deterministic PoC adapter artifacts.

This generator consumes:
  - orbitfabric_models/mission/
  - orbitfabric_models/poc_slice.yaml

and writes:
  - generated_artifacts/flight_software/mission_contract.h
  - generated_artifacts/ground_segment/poc_srdb.yaml

The generated C header is contract-only. It intentionally contains no
runtime logic, no PUS framing, no transport, no scheduling and no dynamic
allocation.
"""

import io
import os

try:
    import yaml
except ImportError:
    raise SystemExit(
        "PyYAML is required to run this generator. "
        "Install it in the active Python environment and retry."
    )

try:
    string_types = (basestring,)  # type: ignore[name-defined]
except NameError:  # pragma: no cover - Python 3 path
    string_types = (str,)

try:
    integer_types = (int, long)  # type: ignore[name-defined]
except NameError:  # pragma: no cover - Python 3 path
    integer_types = (int,)


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
MISSION_DIR = os.path.join(REPO_ROOT, "orbitfabric_models", "mission")
POC_SLICE_PATH = os.path.join(REPO_ROOT, "orbitfabric_models", "poc_slice.yaml")

FLIGHT_OUTPUT = os.path.join(
    REPO_ROOT,
    "generated_artifacts",
    "flight_software",
    "mission_contract.h",
)
GROUND_OUTPUT = os.path.join(
    REPO_ROOT,
    "generated_artifacts",
    "ground_segment",
    "poc_srdb.yaml",
)


REQUIRED_MISSION_FILES = [
    "spacecraft.yaml",
    "subsystems.yaml",
    "modes.yaml",
    "telemetry.yaml",
    "commands.yaml",
    "events.yaml",
    "faults.yaml",
    "packets.yaml",
    "policies.yaml",
]


def repo_relative(path):
    return os.path.relpath(path, REPO_ROOT)


def load_yaml(path):
    if not os.path.exists(path):
        raise SystemExit("Required input file not found: {0}".format(path))

    with io.open(path, "r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)

    if not isinstance(data, dict):
        raise SystemExit("Invalid YAML document in {0}".format(path))

    return data


def load_mission_model(mission_dir):
    model = {}
    for filename in REQUIRED_MISSION_FILES:
        model.update(load_yaml(os.path.join(mission_dir, filename)))

    return model


def as_list(value, field_name):
    if not isinstance(value, list):
        raise SystemExit("Expected list for field: {0}".format(field_name))

    for item in value:
        if not isinstance(item, dict):
            raise SystemExit(
                "Expected mapping entries in field: {0}".format(field_name)
            )

    return value


def require_mapping(data, key):
    value = data.get(key)
    if not isinstance(value, dict):
        raise SystemExit("Missing or invalid mapping: {0}".format(key))
    return value


def require_scalar(data, key):
    if key not in data:
        raise SystemExit("Missing required field: {0}".format(key))
    value = data[key]
    if isinstance(value, (dict, list)):
        raise SystemExit("Expected scalar field: {0}".format(key))
    return value


def format_c_integer(value):
    if isinstance(value, integer_types):
        return "0x{0:04X}".format(value)
    if isinstance(value, string_types):
        return value
    raise SystemExit("Expected integer-compatible value, got: {0!r}".format(value))


def format_c_unsigned(value):
    if not isinstance(value, integer_types):
        raise SystemExit("Expected integer value, got: {0!r}".format(value))
    return "{0}u".format(value)


def find_by_id(entries, identifier):
    for entry in entries:
        if entry.get("id") == identifier:
            return entry
    raise SystemExit("Mission Model identifier not found: {0}".format(identifier))


def find_by_leaf_id(entries, leaf, kind):
    matches = []
    for entry in entries:
        entry_id = entry.get("id")
        if isinstance(entry_id, string_types) and entry_id.split(".")[-1] == leaf:
            matches.append(entry)

    if len(matches) != 1:
        raise SystemExit(
            "Expected exactly one {0} matching leaf id '{1}', found {2}".format(
                kind,
                leaf,
                len(matches),
            )
        )

    return matches[0]


def c_struct_type_for_hk_set(name):
    base = name[:-3] if name.endswith("_hk") else name
    return "of_hk_{0}_t".format(base)


def validate_inputs(mission_model, poc_slice):
    telemetry_model = as_list(mission_model.get("telemetry"), "mission.telemetry")
    commands_model = as_list(mission_model.get("commands"), "mission.commands")
    events_model = as_list(mission_model.get("events"), "mission.events")
    packets_model = as_list(mission_model.get("packets"), "mission.packets")

    telemetry_map = as_list(poc_slice.get("telemetry"), "poc_slice.telemetry")
    commands_map = as_list(poc_slice.get("commands"), "poc_slice.commands")
    events_map = as_list(poc_slice.get("events"), "poc_slice.events")
    hk_sets_map = as_list(
        poc_slice.get("housekeeping_sets"),
        "poc_slice.housekeeping_sets",
    )

    telemetry_by_srdb_name = {}
    for item in telemetry_map:
        telemetry_by_srdb_name[require_scalar(item, "srdb_name")] = item

    for item in telemetry_map:
        semantic = find_by_id(telemetry_model, str(require_scalar(item, "srdb_name")))

        if item.get("unit") != semantic.get("unit"):
            raise SystemExit(
                "Telemetry unit mismatch for {0}: {1} != {2}".format(
                    semantic["id"],
                    item.get("unit"),
                    semantic.get("unit"),
                )
            )

        if item.get("c_type") != "uint16_t":
            raise SystemExit(
                "The first PoC adapter only supports uint16_t telemetry fields"
            )

    for hk_set in hk_sets_map:
        hk_name = str(require_scalar(hk_set, "name"))
        find_by_id(packets_model, hk_name)

        parameters = hk_set.get("parameters")
        if not isinstance(parameters, list):
            raise SystemExit("Missing parameter list for HK set: {0}".format(hk_name))

        for parameter in parameters:
            if parameter not in telemetry_by_srdb_name:
                raise SystemExit(
                    "HK set {0} references unknown telemetry: {1}".format(
                        hk_name,
                        parameter,
                    )
                )

    for command in commands_map:
        semantic = find_by_leaf_id(
            commands_model,
            str(require_scalar(command, "name")),
            "command",
        )
        command["semantic_id"] = semantic["id"]

    for event in events_map:
        semantic = find_by_leaf_id(
            events_model,
            str(require_scalar(event, "name")),
            "event",
        )
        event["semantic_id"] = semantic["id"]

        trigger = require_mapping(event, "trigger")
        parameter = str(require_scalar(trigger, "parameter"))
        if parameter not in telemetry_by_srdb_name:
            raise SystemExit(
                "Event {0} references unknown trigger parameter: {1}".format(
                    event["name"],
                    parameter,
                )
            )

    return {
        "telemetry_model": telemetry_model,
        "commands_model": commands_model,
        "events_model": events_model,
        "packets_model": packets_model,
        "telemetry_map": telemetry_map,
        "commands_map": commands_map,
        "events_map": events_map,
        "hk_sets_map": hk_sets_map,
    }


def render_header(poc_slice, validated):
    contract = require_mapping(poc_slice, "contract")
    telemetry = validated["telemetry_map"]
    commands = validated["commands_map"]
    events = validated["events_map"]
    hk_sets = validated["hk_sets_map"]

    lines = [
        "/*",
        " * GENERATED FILE. DO NOT EDIT.",
        " *",
        " * Generated by:",
        " *   python tools/generate_poc_artifacts.py",
        " *",
        " * Inputs:",
        " *   orbitfabric_models/mission/",
        " *   orbitfabric_models/poc_slice.yaml",
        " *",
        " * This file is contract-only.",
        " * It contains no runtime logic, no PUS framing, no transport,",
        " * no scheduling and no dynamic allocation.",
        " */",
        "",
        "#ifndef OF_MISSION_CONTRACT_H",
        "#define OF_MISSION_CONTRACT_H",
        "",
        "#include <stdint.h>",
        "",
        "#define OF_CONTRACT_NAME \"{0}\"".format(contract["name"]),
        "#define OF_CONTRACT_VERSION \"{0}\"".format(contract["version"]),
        "",
        "typedef enum {",
        "    OF_TM_INVALID = 0,",
    ]

    for item in telemetry:
        lines.append("    {0} = {1}".format(item["of_id"], format_c_integer(item["of_id_value"])))
    lines.extend(["} of_tm_id_t;", "", "typedef enum {", "    OF_CMD_INVALID = 0,"])

    for item in commands:
        lines.append("    {0} = {1}".format(item["of_id"], format_c_integer(item["of_id_value"])))
    lines.extend(["} of_cmd_id_t;", "", "typedef enum {", "    OF_EVENT_INVALID = 0,"])

    for item in events:
        lines.append("    {0} = {1}".format(item["of_id"], format_c_integer(item["of_id_value"])))
    lines.extend(["} of_event_id_t;", "", "typedef enum {", "    OF_HK_SET_INVALID = 0,"])

    for item in hk_sets:
        lines.append("    {0} = {1}".format(item["of_id"], format_c_integer(item["sid"])))
    lines.extend(["} of_hk_set_id_t;", ""])

    telemetry_by_srdb_name = {}
    for item in telemetry:
        telemetry_by_srdb_name[item["srdb_name"]] = item

    for hk_set in hk_sets:
        interval = format_c_unsigned(hk_set["collection_interval_s"])
        lines.append("#define {0}_COLLECTION_INTERVAL_S {1}".format(hk_set["of_id"], interval))
    lines.append("")

    for hk_set in hk_sets:
        lines.append("typedef struct {")
        for parameter in hk_set["parameters"]:
            telemetry_item = telemetry_by_srdb_name[parameter]
            lines.append("    {0} {1};".format(telemetry_item["c_type"], telemetry_item["name"]))
        lines.append("}} {0};".format(c_struct_type_for_hk_set(hk_set["name"])))
        lines.append("")

    lines.extend(["#endif /* OF_MISSION_CONTRACT_H */", ""])
    return "\n".join(lines)


def render_srdb(poc_slice, validated):
    contract = require_mapping(poc_slice, "contract")
    telemetry = validated["telemetry_map"]
    commands = validated["commands_map"]
    events = validated["events_map"]
    hk_sets = validated["hk_sets_map"]

    telemetry_model_by_id = {}
    for item in validated["telemetry_model"]:
        telemetry_model_by_id[item["id"]] = item

    lines = [
        "# GENERATED FILE. DO NOT EDIT.",
        "#",
        "# Generated by:",
        "#   python tools/generate_poc_artifacts.py",
        "#",
        "# Inputs:",
        "#   orbitfabric_models/mission/",
        "#   orbitfabric_models/poc_slice.yaml",
        "#",
        "# This file is the first PoC SRDB projection for OpenSVF/YAMCS ingestion.",
        "",
        "database:",
        "  name: {0}".format(contract["name"]),
        "  version: \"{0}\"".format(contract["version"]),
        "",
        "parameters:",
    ]

    for item in telemetry:
        semantic = telemetry_model_by_id[item["srdb_name"]]
        lines.extend([
            "  - name: {0}".format(item["srdb_name"]),
            "    semantic_id: {0}".format(semantic["id"]),
            "    description: {0}".format(semantic["description"]),
            "    type: {0}".format(semantic["type"]),
            "    c_type: {0}".format(item["c_type"]),
            "    unit: {0}".format(item["unit"]),
            "    source: {0}".format(semantic["source"]),
            "    pus:",
            "      service: {0}".format(item["pus_service"]),
            "      subtype: {0}".format(item["pus_subtype"]),
            "    housekeeping:",
            "      set: {0}".format(item["hk_set"]),
            "      sample_rate_hz: {0}".format(item["sample_rate_hz"]),
            "    limits:",
            "      warning_high: {0}".format(semantic["limits"]["warning_high"]),
        ])

    lines.extend(["", "housekeeping:"])
    for item in hk_sets:
        lines.extend([
            "  - name: {0}".format(item["name"]),
            "    of_id: {0}".format(item["of_id"]),
            "    sid: {0}".format(format_c_integer(item["sid"])),
            "    collection_interval_s: {0}".format(item["collection_interval_s"]),
            "    parameters:",
        ])
        for parameter in item["parameters"]:
            lines.append("      - {0}".format(parameter))

    lines.extend(["", "commands:"])
    for item in commands:
        lines.extend([
            "  - name: {0}".format(item["srdb_name"]),
            "    semantic_id: {0}".format(item["semantic_id"]),
            "    of_id: {0}".format(item["of_id"]),
            "    of_id_value: {0}".format(format_c_integer(item["of_id_value"])),
            "    pus:",
            "      service: {0}".format(item["pus_service"]),
            "      subtype: {0}".format(item["pus_subtype"]),
            "    arguments: []",
            "    expected_responses:",
        ])
        for response in item["expected_responses"]:
            lines.append("      - \"{0}\"".format(response))

    lines.extend(["", "events:"])
    for item in events:
        trigger = item["trigger"]
        lines.extend([
            "  - name: {0}".format(item["srdb_name"]),
            "    semantic_id: {0}".format(item["semantic_id"]),
            "    of_id: {0}".format(item["of_id"]),
            "    of_id_value: {0}".format(format_c_integer(item["of_id_value"])),
            "    severity: {0}".format(item["severity"]),
            "    pus:",
            "      service: {0}".format(item["pus_service"]),
            "      subtype: {0}".format(item["pus_subtype"]),
            "    trigger:",
            "      parameter: {0}".format(trigger["parameter"]),
            "      condition: \"{0}\"".format(trigger["condition"]),
            "      threshold_mv: {0}".format(trigger["threshold_mv"]),
        ])

    lines.append("")
    return "\n".join(lines)


def write_text(path, content):
    parent = os.path.dirname(path)
    if not os.path.isdir(parent):
        os.makedirs(parent)

    with io.open(path, "w", encoding="utf-8", newline="\n") as stream:
        stream.write(content)


def main():
    mission_model = load_mission_model(MISSION_DIR)
    poc_slice = load_yaml(POC_SLICE_PATH)
    validated = validate_inputs(mission_model, poc_slice)

    write_text(FLIGHT_OUTPUT, render_header(poc_slice, validated))
    write_text(GROUND_OUTPUT, render_srdb(poc_slice, validated))

    print("Generated {0}".format(repo_relative(FLIGHT_OUTPUT)))
    print("Generated {0}".format(repo_relative(GROUND_OUTPUT)))


if __name__ == "__main__":
    main()
