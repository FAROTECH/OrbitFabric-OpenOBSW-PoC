from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import yaml

from orbitfabric_openobsw_opensvf.resolver import (
    ProjectionResolutionError,
    resolve_projection,
    write_resolved_projection,
)


SCHEMA = (
    Path(__file__).parents[1]
    / "src/orbitfabric_openobsw_opensvf/schemas/openobsw_opensvf_projection_profile_v0.schema.json"
)


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _make_input_set(tmp_path: Path) -> Path:
    telemetry = [
        {
            "id": "eps.obc.bus_voltage_mv",
            "name": "OBC Bus Voltage",
            "type": "uint16",
            "unit": "mV",
            "source": "EPS",
            "sampling": "1 Hz",
            "criticality": "high",
            "persistence": "store_and_downlink",
            "downlink_priority": "high",
            "limits": {"warning_low": 4700, "critical_low": 4500},
            "enum": None,
            "quality": None,
            "description": None,
        }
    ]
    packets = [
        {
            "id": "obc_hk",
            "name": "OBC Housekeeping",
            "type": "ccsds_like",
            "max_payload_bytes": 64,
            "period": "1 s",
            "telemetry": ["eps.obc.bus_voltage_mv"],
            "description": None,
        }
    ]
    commands = [
        {
            "id": "obc.ping",
            "target": "OBC",
            "description": "Ping OBC",
            "arguments": [],
            "allowed_modes": ["NOMINAL"],
            "preconditions": None,
            "requires_ack": True,
            "timeout_ms": 1000,
            "risk": "low",
            "emits": [],
            "expected_effects": {},
        }
    ]
    events = [
        {
            "id": "eps.voltage_out_of_bounds",
            "source": "EPS",
            "severity": "warning",
            "description": "Voltage out of bounds",
            "downlink_priority": "high",
            "persistence": "store_and_downlink",
        }
    ]
    snapshot = {
        "kind": "orbitfabric.mission_snapshot",
        "snapshot_version": "0.1-candidate",
        "result": "loaded",
        "mission": {"id": "poc-mission", "name": "PoC", "model_version": "0.1.0"},
        "model": {
            "spacecraft": {
                "id": "poc-mission",
                "name": "PoC",
                "class": "demo",
                "form_factor": None,
                "mission_type": None,
                "model_version": "0.1.0",
            },
            "subsystems": [],
            "modes": {},
            "mode_transitions": [],
            "telemetry": telemetry,
            "commands": commands,
            "events": events,
            "faults": [],
            "packets": packets,
            "policies": {},
            "payloads": [],
            "data_products": [],
            "contacts": {},
            "commandability": {},
        },
    }
    entity_index = {
        "kind": "orbitfabric.entity_index",
        "index_version": "0.1",
        "mission": {"id": "poc-mission", "model_version": "0.1.0"},
        "entities": [
            {"domain": "telemetry", "id": "eps.obc.bus_voltage_mv"},
            {"domain": "packets", "id": "obc_hk"},
            {"domain": "commands", "id": "obc.ping"},
            {"domain": "events", "id": "eps.voltage_out_of_bounds"},
        ],
    }
    _write_json(tmp_path / "mission_snapshot.json", snapshot)
    _write_json(tmp_path / "entity_index.json", entity_index)
    _write_json(tmp_path / "relationship_manifest.json", {"kind": "orbitfabric.relationship_manifest"})
    _write_json(tmp_path / "lint_report.json", {"tool": "orbitfabric-lint", "result": "passed"})

    metadata = {
        "mission_snapshot": ("orbitfabric.mission_snapshot", "0.1-candidate"),
        "entity_index": ("orbitfabric.entity_index", "0.1"),
        "relationship_manifest": ("orbitfabric.relationship_manifest", "0.1-candidate"),
        "lint_report": ("orbitfabric-lint", "v1"),
    }
    surfaces = []
    for role, (kind, version) in metadata.items():
        path = tmp_path / f"{role}.json"
        surfaces.append(
            {
                "role": role,
                "requirement": "required",
                "status": "available",
                "kind": kind,
                "format_version": version,
                "path": path.name,
                "sha256": _digest(path),
                "unavailable_reason": None,
            }
        )

    manifest = {
        "kind": "orbitfabric.integration_input_set",
        "input_set_version": "0.1-candidate",
        "input_set_sha256": "a" * 64,
        "orbitfabric_version": "1.x",
        "mission": {"id": "poc-mission", "model_version": "0.1.0"},
        "load_result": "loaded",
        "lint_result": "passed",
        "surfaces": surfaces,
    }
    path = tmp_path / "integration_input_manifest.json"
    _write_json(path, manifest)
    return path


def _profile() -> dict:
    return {
        "kind": "orbitfabric.projection_profile",
        "profile_version": "0.1-candidate",
        "profile": {"id": "test-profile", "version": "0.1.0"},
        "integration": {
            "id": "orbitfabric-openobsw-opensvf",
            "schema_version": "0.1-candidate",
        },
        "settings": {
            "flight_contract": {"c_symbol_prefix": "OF_"},
            "opensvf": {"domain_apids": {"EPS": 0x100}},
        },
        "bindings": [
            {
                "id": "tm.voltage",
                "intent": "project",
                "sources": [{"domain": "telemetry", "id": "eps.obc.bus_voltage_mv"}],
                "config": {"kind": "telemetry_parameter", "numeric_id": 0x4001},
            },
            {
                "id": "hk.obc",
                "intent": "project",
                "sources": [{"domain": "packets", "id": "obc_hk"}],
                "config": {
                    "kind": "housekeeping_packet",
                    "sid": 1,
                    "pus": {"service": 3, "subservice": 25},
                },
            },
            {
                "id": "cmd.ping",
                "intent": "project",
                "sources": [{"domain": "commands", "id": "obc.ping"}],
                "config": {
                    "kind": "command",
                    "numeric_id": 0x1701,
                    "srdb_name": "dhs.obc.ping",
                    "pus": {"service": 17, "subservice": 1},
                    "verification": {
                        "expected_telemetry": [
                            {"role": "acceptance", "service": 1, "subservice": 1}
                        ]
                    },
                },
            },
            {
                "id": "event.voltage",
                "intent": "project",
                "sources": [{"domain": "events", "id": "eps.voltage_out_of_bounds"}],
                "config": {
                    "kind": "event",
                    "numeric_id": 0x5001,
                    "c_symbol": "OF_EVT_VOLTAGE_OOB",
                    "pus": {"service": 5, "subservice": 3},
                },
            },
        ],
    }


def _write_profile(tmp_path: Path, profile: dict) -> Path:
    path = tmp_path / "profile.yaml"
    path.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")
    return path


def _projection(payload: dict, binding_id: str) -> dict:
    return next(item for item in payload["projections"] if item["binding_id"] == binding_id)


def _resolution(projection: dict, property_name: str) -> dict:
    return next(item for item in projection["resolutions"] if item["property"] == property_name)


def test_resolves_core_semantics_defaults_and_profile_values(tmp_path: Path) -> None:
    payload = resolve_projection(
        manifest_path=_make_input_set(tmp_path),
        profile_path=_write_profile(tmp_path, _profile()),
        schema_path=SCHEMA,
    )

    assert payload["kind"] == "orbitfabric.openobsw_opensvf.resolved_projection"
    assert payload["resolved_projection_version"] == "0.1-candidate"
    assert payload["core_input_set"]["input_set_sha256"] == "a" * 64
    assert payload["settings"]["flight_contract"]["contract_name"] == "test-profile"
    assert payload["settings"]["flight_contract"]["contract_version"] == "0.1.0"
    assert [item["binding_id"] for item in payload["projections"]] == [
        "cmd.ping",
        "event.voltage",
        "hk.obc",
        "tm.voltage",
    ]

    telemetry = _projection(payload, "tm.voltage")
    assert telemetry["core_semantics"]["source"]["unit"] == "mV"
    assert telemetry["core_semantics"]["source"]["type"] == "uint16"
    assert telemetry["target"]["numeric_id"] == 0x4001
    assert telemetry["target"]["srdb_name"] == "eps.obc.bus_voltage_mv"
    assert telemetry["target"]["c_symbol"] == "OF_TM_OBC_BUS_VOLTAGE_MV"
    assert telemetry["target"]["c_type"] == "uint16_t"
    assert telemetry["target"]["field_name"] == "obc_bus_voltage_mv"
    assert _resolution(telemetry, "target.numeric_id")["origin"] == "profile"
    assert _resolution(telemetry, "target.srdb_name")["origin"] == "adapter_default"
    assert _resolution(telemetry, "target.c_symbol")["origin"] == "adapter_default"
    assert _resolution(telemetry, "target.c_type")["origin"] == "adapter_default"

    housekeeping = _projection(payload, "hk.obc")
    assert housekeeping["core_semantics"]["source"]["period"] == "1 s"
    assert housekeeping["core_semantics"]["source"]["telemetry"] == [
        "eps.obc.bus_voltage_mv"
    ]
    assert housekeeping["core_semantics"]["telemetry_members"][0]["unit"] == "mV"
    assert housekeeping["target"]["sid"] == 1
    assert housekeeping["target"]["pus"] == {"service": 3, "subservice": 25}
    assert housekeeping["target"]["c_symbol"] == "OF_HK_SET_OBC"
    assert housekeeping["target"]["struct_type"] == "of_hk_obc_t"
    assert housekeeping["target"]["collection_interval_s"] == 1
    assert housekeeping["target"]["members"] == [
        {
            "core_id": "eps.obc.bus_voltage_mv",
            "c_type": "uint16_t",
            "field_name": "obc_bus_voltage_mv",
        }
    ]

    command = _projection(payload, "cmd.ping")
    assert command["core_semantics"]["source"]["requires_ack"] is True
    assert command["target"]["c_symbol"] == "OF_CMD_PING"
    assert command["target"]["srdb_name"] == "dhs.obc.ping"
    assert _resolution(command, "target.srdb_name")["origin"] == "profile"

    event = _projection(payload, "event.voltage")
    assert event["core_semantics"]["source"]["severity"] == "warning"
    assert event["target"]["c_symbol"] == "OF_EVT_VOLTAGE_OOB"
    assert _resolution(event, "target.c_symbol")["origin"] == "profile"


def test_binding_order_does_not_change_resolved_projection_order(tmp_path: Path) -> None:
    manifest_path = _make_input_set(tmp_path)
    profile = _profile()
    first = resolve_projection(
        manifest_path=manifest_path,
        profile_path=_write_profile(tmp_path, profile),
        schema_path=SCHEMA,
    )
    profile["bindings"] = list(reversed(profile["bindings"]))
    second = resolve_projection(
        manifest_path=manifest_path,
        profile_path=_write_profile(tmp_path, profile),
        schema_path=SCHEMA,
    )
    assert first == second


def test_do_not_project_is_preserved_as_explicit_exclusion(tmp_path: Path) -> None:
    profile = _profile()
    profile["bindings"].append(
        {
            "id": "exclude.event",
            "intent": "do_not_project",
            "sources": [{"domain": "events", "id": "eps.voltage_out_of_bounds"}],
            "config": {},
            "reason": "Not materialized in this target profile",
        }
    )
    payload = resolve_projection(
        manifest_path=_make_input_set(tmp_path),
        profile_path=_write_profile(tmp_path, profile),
        schema_path=SCHEMA,
    )
    assert payload["exclusions"] == [
        {
            "binding_id": "exclude.event",
            "sources": [{"domain": "events", "id": "eps.voltage_out_of_bounds"}],
            "reason": "Not materialized in this target profile",
        }
    ]


def test_invalid_profile_cannot_be_resolved(tmp_path: Path) -> None:
    profile = _profile()
    profile["bindings"][0]["sources"][0]["id"] = "eps.missing"
    try:
        resolve_projection(
            manifest_path=_make_input_set(tmp_path),
            profile_path=_write_profile(tmp_path, profile),
            schema_path=SCHEMA,
        )
    except ProjectionResolutionError as exc:
        assert any(item.code == "profile.source" for item in exc.diagnostics)
    else:
        raise AssertionError("expected ProjectionResolutionError")


def test_resolved_projection_json_is_deterministic(tmp_path: Path) -> None:
    manifest_path = _make_input_set(tmp_path)
    profile_path = _write_profile(tmp_path, _profile())
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    write_resolved_projection(
        manifest_path=manifest_path,
        profile_path=profile_path,
        schema_path=SCHEMA,
        output_file=first,
    )
    write_resolved_projection(
        manifest_path=manifest_path,
        profile_path=profile_path,
        schema_path=SCHEMA,
        output_file=second,
    )
    assert first.read_bytes() == second.read_bytes()
