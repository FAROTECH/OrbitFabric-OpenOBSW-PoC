from __future__ import annotations

from hashlib import sha256
from importlib.resources import as_file, files
import json
from pathlib import Path

from orbitfabric_openobsw_opensvf.runner import run_operation
from test_resolved_projection import SCHEMA, _make_input_set, _profile, _write_profile


def _resource(name: str):
    return files("orbitfabric_openobsw_opensvf").joinpath(name)


def _input_set(tmp_path: Path) -> Path:
    root = tmp_path / "input"
    root.mkdir(parents=True)
    return _make_input_set(root)


def _target_triples(targets: list[dict]) -> set[tuple[str, str, str]]:
    return {
        (target["namespace"], target["kind"], target["id"])
        for target in targets
    }


def test_static_package_manifest_matches_packaged_schema() -> None:
    with as_file(_resource("integration_package.json")) as manifest_path:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["kind"] == "orbitfabric.integration_package"
    assert manifest["manifest_version"] == "0.1-candidate"
    assert manifest["execution"] == {
        "protocol": "orbitfabric.adapter_cli.v0",
        "argv_prefix": ["orbitfabric-openobsw-opensvf"],
    }
    assert manifest["capabilities"] == [
        "profile_validation",
        "projection",
        "artifact_generation",
        "traceability",
    ]
    assert manifest["operations"] == [
        {"id": "project", "capabilities": manifest["capabilities"]}
    ]

    schema_record = manifest["profile_schemas"][0]
    with as_file(_resource(schema_record["path"])) as schema_path:
        actual = sha256(schema_path.read_bytes()).hexdigest()
    assert schema_record["sha256"] == actual


def test_project_run_writes_coherent_result_last_bundle(tmp_path: Path) -> None:
    manifest_path = _input_set(tmp_path)
    profile_path = _write_profile(tmp_path, _profile())
    output_dir = tmp_path / "result"

    status, result_path = run_operation(
        operation_id="project",
        manifest_path=manifest_path,
        profile_path=profile_path,
        output_dir=output_dir,
        schema_path=SCHEMA,
    )
    assert status == 0
    assert result_path == output_dir / "integration_result.json"
    assert result_path.is_file()

    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["kind"] == "orbitfabric.integration_result"
    assert result["result_version"] == "0.1-candidate"
    assert result["result"] == "succeeded"
    assert result["operation"] == {"id": "project"}
    assert result["capabilities"] == [
        "profile_validation",
        "projection",
        "artifact_generation",
        "traceability",
    ]
    assert result["inputs"]["core_input_set"]["status"] == "available"
    assert result["inputs"]["profile"]["status"] == "available"
    assert result["mission"]["status"] == "available"

    artifacts = {item["id"]: item for item in result["artifacts"]}
    assert artifacts["flight.mission_contract"]["status"] == "generated"
    assert artifacts["ground.opensvf_srdb"]["status"] == "generated"
    for artifact in artifacts.values():
        path = output_dir / artifact["path"]
        assert path.is_file()
        assert sha256(path.read_bytes()).hexdigest() == artifact["sha256"]
        assert not Path(artifact["path"]).is_absolute()
        assert ".." not in Path(artifact["path"]).parts

    mappings = {item["id"]: item for item in result["mappings"]}
    telemetry = mappings["mapping.tm.voltage"]
    assert _target_triples(telemetry["targets"]) == {
        ("openobsw", "contract_symbol", "OF_TM_OBC_BUS_VOLTAGE_MV"),
        ("opensvf", "srdb_parameter", "eps.obc.bus_voltage_mv"),
    }

    coverage = result["coverage"]
    assert coverage["status"] == "complete"
    assert coverage["scope"]["domains"] == ["commands", "events", "packets", "telemetry"]
    assert len(coverage["records"]) == 4
    assert all(record["state"] == "projected" for record in coverage["records"])
    assert coverage["summary"] == {"projected": 4}
    assert result["diagnostics"] == []
    assert result["evidence"] == []
    assert result["external_tools"] == []


def test_project_validation_failure_writes_failed_result(tmp_path: Path) -> None:
    manifest_path = _input_set(tmp_path)
    profile = _profile()
    profile["bindings"][0]["sources"][0]["id"] = "eps.missing"
    profile_path = _write_profile(tmp_path, profile)
    output_dir = tmp_path / "failed"

    status, result_path = run_operation(
        operation_id="project",
        manifest_path=manifest_path,
        profile_path=profile_path,
        output_dir=output_dir,
        schema_path=SCHEMA,
    )
    assert status != 0
    assert result_path is not None and result_path.is_file()
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["result"] == "failed"
    assert result["capabilities"] == ["profile_validation"]
    assert result["inputs"]["core_input_set"]["status"] == "available"
    assert result["inputs"]["profile"]["status"] == "available"
    assert result["mission"]["status"] == "available"
    assert result["integration"]["schema_version"] == "0.1-candidate"
    assert any(item["code"] == "profile.source" for item in result["diagnostics"])
    assert all(item["owner"] == "integration" for item in result["diagnostics"])
    assert result["coverage"]["status"] == "unavailable"
    assert all(item["status"] == "not_generated" for item in result["artifacts"])
    assert not (output_dir / "artifacts/flight/mission_contract.h").exists()
    assert not (output_dir / "artifacts/ground/poc_srdb.yaml").exists()


def test_unsupported_operation_is_machine_readable_failure(tmp_path: Path) -> None:
    manifest_path = _input_set(tmp_path)
    profile_path = _write_profile(tmp_path, _profile())
    output_dir = tmp_path / "unsupported"

    status, result_path = run_operation(
        operation_id="something-else",
        manifest_path=manifest_path,
        profile_path=profile_path,
        output_dir=output_dir,
        schema_path=SCHEMA,
    )
    assert status != 0
    assert result_path is not None
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["result"] == "failed"
    assert result["capabilities"] == []
    assert result["operation"] == {"id": "something-else"}
    assert result["diagnostics"][0]["code"] == "operation.unsupported"


def test_profile_read_failure_does_not_erase_available_core_provenance(tmp_path: Path) -> None:
    manifest_path = _input_set(tmp_path)
    missing_profile = tmp_path / "missing-profile.yaml"
    output_dir = tmp_path / "failed"

    status, result_path = run_operation(
        operation_id="project",
        manifest_path=manifest_path,
        profile_path=missing_profile,
        output_dir=output_dir,
        schema_path=SCHEMA,
    )
    assert status != 0
    assert result_path is not None
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["inputs"]["core_input_set"]["status"] == "available"
    assert result["mission"]["status"] == "available"
    assert result["inputs"]["profile"]["status"] == "unavailable"
    assert result["integration"]["schema_version"] is None


def test_existing_result_marker_is_removed_before_new_attempt(tmp_path: Path) -> None:
    manifest_path = _input_set(tmp_path)
    profile = _profile()
    profile["bindings"][0]["sources"][0]["id"] = "eps.missing"
    profile_path = _write_profile(tmp_path, profile)
    output_dir = tmp_path / "result"
    output_dir.mkdir(parents=True)
    (output_dir / "integration_result.json").write_text('{"result":"succeeded"}\n')
    old_artifact = output_dir / "artifacts/flight/mission_contract.h"
    old_artifact.parent.mkdir(parents=True)
    old_artifact.write_text("stale")

    status, result_path = run_operation(
        operation_id="project",
        manifest_path=manifest_path,
        profile_path=profile_path,
        output_dir=output_dir,
        schema_path=SCHEMA,
    )
    assert status != 0
    assert result_path is not None
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["result"] == "failed"
    assert not old_artifact.exists()
