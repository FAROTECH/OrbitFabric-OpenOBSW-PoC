from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import yaml

from orbitfabric_openobsw_opensvf.validator import validate_profile


SCHEMA = (
    Path(__file__).parents[1]
    / "src/orbitfabric_openobsw_opensvf/schemas/openobsw_opensvf_projection_profile_v0.schema.json"
)
REFERENCE_SCHEMA = Path(__file__).parents[2] / "schemas/openobsw_opensvf_projection_profile_v0.schema.json"


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _make_input_set(tmp_path: Path) -> Path:
    entity_index = {
        "kind": "orbitfabric.entity_index",
        "index_version": "0.1",
        "mission": {"id": "poc-mission", "model_version": "0.1.0"},
        "entities": [
            {"domain": "telemetry", "id": "eps.obc.bus_voltage_mv"},
            {"domain": "telemetry", "id": "eps.obc.bus_current_ma"},
            {"domain": "packets", "id": "obc_hk"},
            {"domain": "commands", "id": "obc.ping"},
            {"domain": "events", "id": "eps.voltage_out_of_bounds"},
        ],
    }
    _write_json(tmp_path / "entity_index.json", entity_index)
    _write_json(tmp_path / "mission_snapshot.json", {"kind": "orbitfabric.mission_snapshot"})
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
        "orbitfabric_version": "1.x",
        "mission": {"id": "poc-mission", "model_version": "0.1.0"},
        "load_result": "loaded",
        "lint_result": "passed",
        "surfaces": surfaces,
    }
    path = tmp_path / "integration_input_manifest.json"
    _write_json(path, manifest)
    return path


def _profile(bindings: list[dict] | None = None) -> dict:
    return {
        "kind": "orbitfabric.projection_profile",
        "profile_version": "0.1-candidate",
        "profile": {"id": "test-profile", "version": "0.1.0"},
        "integration": {
            "id": "orbitfabric-openobsw-opensvf",
            "schema_version": "0.1-candidate",
        },
        "settings": {"flight_contract": {"c_symbol_prefix": "OF_"}},
        "bindings": bindings
        if bindings is not None
        else [
            {
                "id": "tm.voltage",
                "intent": "project",
                "sources": [{"domain": "telemetry", "id": "eps.obc.bus_voltage_mv"}],
                "config": {"kind": "telemetry_parameter", "numeric_id": 0x4001},
            }
        ],
    }


def _write_profile(tmp_path: Path, value: dict) -> Path:
    path = tmp_path / "profile.yaml"
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    return path


def test_reference_and_packaged_schemas_are_equivalent() -> None:
    assert json.loads(SCHEMA.read_text()) == json.loads(REFERENCE_SCHEMA.read_text())


def test_valid_profile_passes(tmp_path: Path) -> None:
    result = validate_profile(
        manifest_path=_make_input_set(tmp_path),
        profile_path=_write_profile(tmp_path, _profile()),
        schema_path=SCHEMA,
    )
    assert result.ok
    assert result.diagnostics == ()


def test_unresolved_core_source_is_rejected(tmp_path: Path) -> None:
    profile = _profile()
    profile["bindings"][0]["sources"][0]["id"] = "eps.missing"
    result = validate_profile(
        manifest_path=_make_input_set(tmp_path),
        profile_path=_write_profile(tmp_path, profile),
        schema_path=SCHEMA,
    )
    assert not result.ok
    assert any(d.code == "profile.source" for d in result.diagnostics)


def test_surface_digest_mismatch_is_rejected(tmp_path: Path) -> None:
    manifest_path = _make_input_set(tmp_path)
    manifest = json.loads(manifest_path.read_text())
    next(item for item in manifest["surfaces"] if item["role"] == "entity_index")["sha256"] = "0" * 64
    _write_json(manifest_path, manifest)

    result = validate_profile(
        manifest_path=manifest_path,
        profile_path=_write_profile(tmp_path, _profile()),
        schema_path=SCHEMA,
    )
    assert not result.ok
    assert any(d.code == "input.surface_digest" for d in result.diagnostics)


def test_duplicate_numeric_id_within_projection_kind_is_rejected(tmp_path: Path) -> None:
    bindings = [
        {
            "id": "tm.voltage",
            "intent": "project",
            "sources": [{"domain": "telemetry", "id": "eps.obc.bus_voltage_mv"}],
            "config": {"kind": "telemetry_parameter", "numeric_id": 0x4001},
        },
        {
            "id": "tm.current",
            "intent": "project",
            "sources": [{"domain": "telemetry", "id": "eps.obc.bus_current_ma"}],
            "config": {"kind": "telemetry_parameter", "numeric_id": 0x4001},
        },
    ]
    result = validate_profile(
        manifest_path=_make_input_set(tmp_path),
        profile_path=_write_profile(tmp_path, _profile(bindings)),
        schema_path=SCHEMA,
    )
    assert not result.ok
    assert any(d.code == "profile.numeric_id" for d in result.diagnostics)


def test_core_semantic_duplication_is_rejected_by_schema(tmp_path: Path) -> None:
    profile = _profile()
    profile["bindings"][0]["config"]["unit"] = "mV"
    result = validate_profile(
        manifest_path=_make_input_set(tmp_path),
        profile_path=_write_profile(tmp_path, profile),
        schema_path=SCHEMA,
    )
    assert not result.ok
    assert any(d.code == "profile.schema" for d in result.diagnostics)
