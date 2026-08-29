#!/usr/bin/env python3
"""Validate the Stage 7.1 OpenOBSW/OpenSVF Projection Profile schema."""

from __future__ import print_function

import copy
import hashlib
import io
import json
import os
import sys

try:
    import yaml
except ImportError:
    raise SystemExit("PyYAML is required. Install requirements-stage7.txt and retry.")

try:
    from jsonschema import Draft202012Validator
except ImportError:
    raise SystemExit("jsonschema is required. Install requirements-stage7.txt and retry.")

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SCHEMA_PATH = os.path.join(REPO_ROOT, "integration_package", "schemas", "profile-0.1.schema.json")
PROFILE_PATH = os.path.join(REPO_ROOT, "projection_profiles", "poc_openobsw_opensvf.yaml")
CASES_PATH = os.path.join(REPO_ROOT, "integration_package", "tests", "profile_schema_cases.json")


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def construct_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError("Duplicate YAML mapping key: {0}".format(key))
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_mapping,
)


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as stream:
        value = yaml.load(stream, Loader=UniqueKeyLoader)
    if not isinstance(value, dict):
        raise ValueError("Expected YAML mapping document: {0}".format(path))
    return value


def load_json(path):
    with open(path, "r", encoding="utf-8") as stream:
        return json.load(stream)


def resolve_parent(document, path):
    current = document
    for element in path[:-1]:
        current = current[element]
    return current, path[-1]


def apply_mutation(document, mutation):
    parent, leaf = resolve_parent(document, mutation["path"])
    if mutation["op"] == "set":
        parent[leaf] = copy.deepcopy(mutation["value"])
        return
    if mutation["op"] == "delete":
        del parent[leaf]
        return
    raise ValueError("Unsupported mutation op: {0}".format(mutation["op"]))


def error_text(error):
    path = ".".join(str(part) for part in error.absolute_path) or "<root>"
    return "{0}: {1}".format(path, error.message)


def binding_source(binding):
    if not isinstance(binding, dict):
        return None
    sources = binding.get("sources")
    if not isinstance(sources, list) or len(sources) != 1:
        return None
    source = sources[0]
    if not isinstance(source, dict):
        return None
    domain = source.get("domain")
    identifier = source.get("id")
    if not isinstance(domain, str) or not isinstance(identifier, str):
        return None
    return (domain, identifier)


def binding_domain(binding):
    source = binding_source(binding)
    return source[0] if source else None


def append_duplicate(errors, path, label, value):
    errors.append("{0}: duplicate {1} {2}".format(path, label, value))


def resolved_tc_apid(profile, binding):
    config = binding.get("config") if isinstance(binding, dict) else None
    if isinstance(config, dict):
        pus = config.get("pus")
        if isinstance(pus, dict) and pus.get("apid") is not None:
            return pus.get("apid")
    settings = profile.get("settings")
    if not isinstance(settings, dict):
        return None
    pus_settings = settings.get("pus")
    if not isinstance(pus_settings, dict):
        return None
    return pus_settings.get("tc_apid")


def severity_projection_errors(profile):
    errors = []
    settings = profile.get("settings")
    if not isinstance(settings, dict):
        return errors
    srdb = settings.get("obsw_srdb")
    if not isinstance(srdb, dict):
        return errors
    mapping = srdb.get("event_severity_map")
    if not isinstance(mapping, dict):
        return errors

    target_order = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
    core_order = ("info", "warning", "error", "critical")
    resolved = []
    for key in core_order:
        value = mapping.get(key)
        if value not in target_order:
            return errors
        resolved.append(target_order[value])

    if resolved != sorted(resolved):
        errors.append(
            "settings.obsw_srdb.event_severity_map: target severity projection must be non-decreasing"
        )
    return errors


def profile_contract_errors(profile, validator):
    errors = [error_text(error) for error in validator.iter_errors(profile)]
    errors.extend(severity_projection_errors(profile))

    bindings = profile.get("bindings", [])
    if not isinstance(bindings, list):
        return errors

    ids = []
    c_symbols = set()
    parameter_ids = set()
    command_ids = set()
    event_ids = set()
    housekeeping_sids = set()
    command_tuples = set()
    projected_telemetry_sources = set()

    for binding in bindings:
        if not isinstance(binding, dict):
            continue
        if binding.get("id") is not None:
            ids.append(binding.get("id"))
        if binding.get("intent") == "project" and binding_domain(binding) == "telemetry":
            source = binding_source(binding)
            if source is not None:
                projected_telemetry_sources.add(source)

    if len(ids) != len(set(ids)):
        errors.append("bindings: Projection Profile binding IDs must be unique")

    for index, binding in enumerate(bindings):
        if not isinstance(binding, dict) or binding.get("intent") != "project":
            continue

        domain = binding_domain(binding)
        config = binding.get("config")
        if not isinstance(config, dict):
            continue

        flight = config.get("flight_contract")
        if not isinstance(flight, dict):
            flight = {}

        pus = config.get("pus")
        if not isinstance(pus, dict):
            pus = {}

        srdb = config.get("obsw_srdb")
        if not isinstance(srdb, dict):
            srdb = {}

        c_symbol = flight.get("c_symbol")
        if c_symbol is not None:
            if c_symbol in c_symbols:
                append_duplicate(
                    errors,
                    "bindings.{0}.config.flight_contract.c_symbol".format(index),
                    "target C symbol",
                    c_symbol,
                )
            else:
                c_symbols.add(c_symbol)

        parameter_id = srdb.get("parameter_id")
        event_id = srdb.get("event_id")
        hk_set = srdb.get("hk_set")
        command_id = flight.get("command_id")

        if domain == "telemetry":
            if pus:
                errors.append(
                    "bindings.{0}.config.pus: telemetry PUS placement is owned by packet/HK projection".format(index)
                )
            if event_id is not None or hk_set is not None:
                errors.append(
                    "bindings.{0}.config.obsw_srdb: telemetry bindings may only allocate parameter_id".format(index)
                )
            if command_id is not None:
                errors.append(
                    "bindings.{0}.config.flight_contract.command_id: only valid for command bindings".format(index)
                )

        elif domain == "commands":
            if srdb:
                errors.append(
                    "bindings.{0}.config.obsw_srdb: command target identity is resolved from PUS tuple in the first schema".format(index)
                )
            if not pus:
                errors.append(
                    "bindings.{0}.config.pus: command binding requires a PUS TC mapping".format(index)
                )

        elif domain == "events":
            if pus:
                errors.append(
                    "bindings.{0}.config.pus: event subtype is derived from Core severity through settings.obsw_srdb.event_severity_map".format(index)
                )
            if parameter_id is not None or hk_set is not None:
                errors.append(
                    "bindings.{0}.config.obsw_srdb: event bindings may only allocate event_id".format(index)
                )
            if command_id is not None:
                errors.append(
                    "bindings.{0}.config.flight_contract.command_id: only valid for command bindings".format(index)
                )
            if "expected_responses" in config:
                errors.append(
                    "bindings.{0}.config.expected_responses: only valid for command bindings".format(index)
                )

        elif domain == "packets":
            if pus:
                errors.append(
                    "bindings.{0}.config.pus: HK packet PUS service/subtype is target-fixed by obsw-srdb HK semantics".format(index)
                )
            if parameter_id is not None or event_id is not None:
                errors.append(
                    "bindings.{0}.config.obsw_srdb: packet bindings may only configure hk_set".format(index)
                )
            if command_id is not None:
                errors.append(
                    "bindings.{0}.config.flight_contract.command_id: only valid for command bindings".format(index)
                )
            if "expected_responses" in config:
                errors.append(
                    "bindings.{0}.config.expected_responses: only valid for command bindings".format(index)
                )

        if domain != "commands" and "expected_responses" in config:
            errors.append(
                "bindings.{0}.config.expected_responses: only valid for command bindings".format(index)
            )

        if domain == "telemetry" and parameter_id is not None:
            if parameter_id in parameter_ids:
                append_duplicate(
                    errors,
                    "bindings.{0}.config.obsw_srdb.parameter_id".format(index),
                    "obsw-srdb parameter ID",
                    parameter_id,
                )
            else:
                parameter_ids.add(parameter_id)

        if domain == "commands" and command_id is not None:
            if command_id in command_ids:
                append_duplicate(
                    errors,
                    "bindings.{0}.config.flight_contract.command_id".format(index),
                    "flight-contract command ID",
                    command_id,
                )
            else:
                command_ids.add(command_id)

        if domain == "events" and event_id is not None:
            if event_id in event_ids:
                append_duplicate(
                    errors,
                    "bindings.{0}.config.obsw_srdb.event_id".format(index),
                    "obsw-srdb event ID",
                    event_id,
                )
            else:
                event_ids.add(event_id)

        if domain == "packets" and isinstance(hk_set, dict):
            sid = hk_set.get("sid")
            if sid is not None:
                if sid in housekeeping_sids:
                    append_duplicate(
                        errors,
                        "bindings.{0}.config.obsw_srdb.hk_set.sid".format(index),
                        "obsw-srdb HK SID",
                        sid,
                    )
                else:
                    housekeeping_sids.add(sid)

            fields = hk_set.get("fields")
            if isinstance(fields, list):
                for field_index, field_source in enumerate(fields):
                    if not isinstance(field_source, dict):
                        continue
                    key = (field_source.get("domain"), field_source.get("id"))
                    if key not in projected_telemetry_sources:
                        errors.append(
                            "bindings.{0}.config.obsw_srdb.hk_set.fields.{1}: "
                            "HK field must reference a projected telemetry binding source".format(
                                index, field_index
                            )
                        )

        if domain == "commands" and pus:
            apid = resolved_tc_apid(profile, binding)
            service = pus.get("service")
            subtype = pus.get("subtype")
            if apid is not None and service is not None and subtype is not None:
                key = (apid, service, subtype)
                if key in command_tuples:
                    append_duplicate(
                        errors,
                        "bindings.{0}.config.pus".format(index),
                        "PUS TC tuple",
                        key,
                    )
                else:
                    command_tuples.add(key)

    return errors


def assert_offline_refs(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "$ref" and isinstance(child, str) and not child.startswith("#/"):
                raise ValueError("Remote or non-local $ref is forbidden: {0}".format(child))
            assert_offline_refs(child)
    elif isinstance(value, list):
        for child in value:
            assert_offline_refs(child)


def assert_duplicate_keys_rejected():
    duplicate = "kind: orbitfabric.projection_profile\nkind: duplicate\n"
    try:
        yaml.load(io.StringIO(duplicate), Loader=UniqueKeyLoader)
    except ValueError:
        return
    raise ValueError("Strict YAML loader failed to reject duplicate mapping keys")


def main():
    assert_duplicate_keys_rejected()

    schema = load_json(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    assert_offline_refs(schema)
    validator = Draft202012Validator(schema)

    profile = load_yaml(PROFILE_PATH)
    canonical_errors = profile_contract_errors(profile, validator)
    if canonical_errors:
        print("Canonical Projection Profile failed Stage 7.1 validation:")
        for error in canonical_errors:
            print("  - {0}".format(error))
        return 1

    with open(SCHEMA_PATH, "rb") as stream:
        schema_sha256 = hashlib.sha256(stream.read()).hexdigest()
    print("Schema SHA-256: {0}".format(schema_sha256))

    cases = load_json(CASES_PATH).get("cases", [])
    if not cases:
        raise ValueError("No Stage 7.1 schema test cases defined")

    failed = []
    for case in cases:
        candidate = copy.deepcopy(profile)
        for mutation in case.get("mutations", []):
            apply_mutation(candidate, mutation)

        errors = profile_contract_errors(candidate, validator)
        actual_valid = not errors
        expected_valid = bool(case["expected_valid"])
        if actual_valid != expected_valid:
            failed.append((case["name"], errors))
            continue
        print("PASS {0}: {1}".format(case["name"], "valid" if actual_valid else "rejected"))

    if failed:
        print("\nStage 7.1 schema test failures:")
        for name, errors in failed:
            print("  - {0}".format(name))
            for error in errors[:5]:
                print("      {0}".format(error))
        return 1

    print("Stage 7.1 Projection Profile schema validation: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
