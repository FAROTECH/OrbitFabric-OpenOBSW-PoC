from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .io import load_json, sha256_file
from .model import AdapterFailure


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA_PATH = (
    PACKAGE_ROOT / "schemas" / "verification-projection-plan-0.1.schema.json"
)


def _failure(message: str, *, code: str = "OFI-VPROJ-PLAN-001") -> AdapterFailure:
    return AdapterFailure(
        code,
        "verification_projection",
        message,
    )


def _assert_local_refs(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "$ref" and isinstance(child, str) and not child.startswith("#/"):
                raise _failure(
                    f"Remote or non-local JSON Schema $ref is forbidden: {child}"
                )
            _assert_local_refs(child)
    elif isinstance(value, list):
        for child in value:
            _assert_local_refs(child)


def _load_schema(schema_path: Path) -> dict[str, Any]:
    schema = load_json(schema_path.resolve())
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        raise _failure(f"Verification Projection Plan schema is invalid: {exc}") from exc
    _assert_local_refs(schema)
    return schema


def validate_verification_projection_plan(
    payload: dict[str, Any],
    *,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
) -> None:
    """Validate plan structure and cross-record v0 semantic invariants."""

    schema = _load_schema(schema_path)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(payload),
        key=lambda item: list(item.absolute_path),
    )
    if errors:
        first = errors[0]
        path = ".".join(str(part) for part in first.absolute_path) or "<root>"
        raise _failure(
            f"Verification Projection Plan schema validation failed at "
            f"{path}: {first.message}"
        )

    _validate_semantics(payload)


def _validate_semantics(payload: dict[str, Any]) -> None:
    atoms = payload["atoms"]
    operations = payload["operations"]
    accounting = payload["accounting"]

    atom_ids = [item["id"] for item in atoms]
    if len(atom_ids) != len(set(atom_ids)):
        raise _failure("Verification Projection Plan contains duplicate atom IDs")

    operation_ids = [item["id"] for item in operations]
    if len(operation_ids) != len(set(operation_ids)):
        raise _failure("Verification Projection Plan contains duplicate operation IDs")

    expected_orders = list(range(len(operations)))
    actual_orders = [item["order"] for item in operations]
    if actual_orders != expected_orders:
        raise _failure(
            "Verification Projection Plan operation ordering must be contiguous "
            f"and list-ordered from 0; got {actual_orders}"
        )

    dispositions = {
        "projected": sum(1 for atom in atoms if atom["disposition"] == "projected"),
        "not_projected": sum(
            1 for atom in atoms if atom["disposition"] == "not_projected"
        ),
        "blocked": sum(1 for atom in atoms if atom["disposition"] == "blocked"),
    }
    roles = {
        "action": sum(1 for atom in atoms if atom["role"] == "action"),
        "expectation": sum(1 for atom in atoms if atom["role"] == "expectation"),
    }
    projected_roles = {
        "action": sum(
            1
            for atom in atoms
            if atom["role"] == "action" and atom["disposition"] == "projected"
        ),
        "expectation": sum(
            1
            for atom in atoms
            if atom["role"] == "expectation"
            and atom["disposition"] == "projected"
        ),
    }
    obligation_count = sum(
        1 for operation in operations if operation["operation"] == "expect_pus_tm"
    )

    expected_accounting = {
        "source_atoms": len(atoms),
        "projected_atoms": dispositions["projected"],
        "not_projected_atoms": dispositions["not_projected"],
        "blocked_atoms": dispositions["blocked"],
        "source_actions": roles["action"],
        "source_expectations": roles["expectation"],
        "projected_source_actions": projected_roles["action"],
        "projected_source_expectations": projected_roles["expectation"],
        "profile_verification_obligations": obligation_count,
    }
    for key, expected in expected_accounting.items():
        if accounting[key] != expected:
            raise _failure(
                f"Verification Projection Plan accounting mismatch for {key}: "
                f"declared {accounting[key]}, computed {expected}"
            )

    if (
        accounting["source_atoms"]
        != accounting["projected_atoms"]
        + accounting["not_projected_atoms"]
        + accounting["blocked_atoms"]
    ):
        raise _failure(
            "Verification Projection Plan source atom accounting does not reconcile"
        )

    if accounting["blocked_atoms"] > 0 and payload["status"] != "blocked":
        raise _failure("A plan with blocked atoms must have status=blocked")

    if accounting["blocked_atoms"] == 0 and payload["status"] != "executable_subset":
        raise _failure(
            "A v0 plan with no blocked atoms must have status=executable_subset"
        )

    atom_by_id = {item["id"]: item for item in atoms}
    operation_by_id = {item["id"]: item for item in operations}

    for atom in atoms:
        refs = atom["operation_ids"]
        if len(refs) != len(set(refs)):
            raise _failure(f"Atom {atom['id']} contains duplicate operation references")

        if atom["disposition"] != "projected" and refs:
            raise _failure(
                f"Non-projected atom {atom['id']} must not own executable operations"
            )

        for operation_id in refs:
            operation = operation_by_id.get(operation_id)
            if operation is None:
                raise _failure(
                    f"Atom {atom['id']} references unknown operation {operation_id}"
                )
            if operation["source_atom_id"] != atom["id"]:
                raise _failure(
                    f"Operation {operation_id} source_atom_id does not match "
                    f"owning atom {atom['id']}"
                )

        if atom["disposition"] == "projected" and atom["kind"] == "command":
            source = atom["source"]
            if not isinstance(source, dict) or source.get("domain") != "commands":
                raise _failure(
                    f"Projected command atom {atom['id']} must resolve a Core "
                    "commands entity"
                )
            if atom["binding_id"] is None:
                raise _failure(
                    f"Projected command atom {atom['id']} must record a Profile binding"
                )
            owned = [operation_by_id[item] for item in refs]
            tc_ops = [item for item in owned if item["operation"] == "pus_tc"]
            if len(tc_ops) != 1:
                raise _failure(
                    f"Projected command atom {atom['id']} must own exactly one "
                    "pus_tc operation"
                )
            if tc_ops[0]["origin"] != "profile_mapping":
                raise _failure(
                    f"Projected command atom {atom['id']} PUS TC must originate "
                    "from profile_mapping"
                )

        if atom["disposition"] == "projected" and atom["role"] == "expectation":
            raise _failure(
                "Stage 7.10 v0 does not admit projected OrbitFabric expectation atoms"
            )

        if atom["disposition"] == "projected" and atom["kind"] == "scenario_metadata":
            if refs:
                raise _failure(
                    "Projected scenario metadata is provenance-only and cannot "
                    "own executable operations"
                )

    for operation in operations:
        atom = atom_by_id.get(operation["source_atom_id"])
        if atom is None:
            raise _failure(
                f"Operation {operation['id']} references unknown source atom "
                f"{operation['source_atom_id']}"
            )
        if atom["disposition"] != "projected":
            raise _failure(
                f"Operation {operation['id']} references non-projected atom "
                f"{atom['id']}"
            )
        if operation["id"] not in atom["operation_ids"]:
            raise _failure(
                f"Operation {operation['id']} is not declared by source atom "
                f"{atom['id']}"
            )
        if atom["binding_id"] != operation["binding_id"]:
            raise _failure(
                f"Operation {operation['id']} binding {operation['binding_id']} "
                f"does not match atom binding {atom['binding_id']}"
            )
        if (
            operation["operation"] == "expect_pus_tm"
            and operation["origin"] != "profile_expected_response"
        ):
            raise _failure(
                f"Operation {operation['id']} target TM obligation must originate "
                "from profile_expected_response"
            )


def validate_verification_projection_provenance(
    payload: dict[str, Any],
    *,
    scenario_path: Path,
    core: Any,
    profile: Any,
) -> None:
    """Validate exact consumed-input provenance and Profile-derived operations."""

    validate_verification_projection_plan(payload)

    scenario_path = scenario_path.resolve()
    if payload["source"]["scenario_sha256"] != sha256_file(scenario_path):
        raise _failure(
            "Scenario SHA-256 provenance does not match consumed scenario bytes",
            code="OFI-VPROJ-PROVENANCE-001",
        )

    core_manifest = core.manifest
    core_record = payload["core_input"]
    expected_core = {
        "kind": core_manifest["kind"],
        "input_set_version": core_manifest["input_set_version"],
        "input_set_sha256": core.sha256,
        "mission_id": core.mission["id"],
        "model_version": core.mission["model_version"],
    }
    for key, expected in expected_core.items():
        if core_record[key] != expected:
            raise _failure(
                f"Core input provenance mismatch for {key}: "
                f"declared {core_record[key]!r}, consumed {expected!r}",
                code="OFI-VPROJ-PROVENANCE-001",
            )

    orbitfabric_version = core_manifest.get("orbitfabric_version")
    if payload["source"]["orbitfabric_version"] != orbitfabric_version:
        raise _failure(
            "OrbitFabric producer version provenance does not match Core input set",
            code="OFI-VPROJ-PROVENANCE-001",
        )

    profile_record = payload["profile"]
    expected_profile = {
        "kind": profile.document["kind"],
        "profile_version": profile.document["profile_version"],
        "id": profile.id,
        "version": profile.version,
        "sha256": profile.sha256,
    }
    for key, expected in expected_profile.items():
        if profile_record[key] != expected:
            raise _failure(
                f"Projection Profile provenance mismatch for {key}: "
                f"declared {profile_record[key]!r}, consumed {expected!r}",
                code="OFI-VPROJ-PROVENANCE-001",
            )

    _validate_profile_operations(payload, profile)


def _validate_profile_operations(payload: dict[str, Any], profile: Any) -> None:
    project_bindings = {
        binding["id"]: binding
        for binding in profile.bindings
        if binding.get("intent") == "project"
    }
    default_apid = profile.document["settings"]["pus"]["tc_apid"]
    operations = {item["id"]: item for item in payload["operations"]}

    total_expected_responses = 0

    for atom in payload["atoms"]:
        if atom["disposition"] != "projected" or atom["kind"] != "command":
            continue

        binding_id = atom["binding_id"]
        binding = project_bindings.get(binding_id)
        if binding is None:
            raise _failure(
                f"Projected command atom {atom['id']} references unavailable "
                f"project binding {binding_id!r}",
                code="OFI-VPROJ-PROVENANCE-001",
            )

        source = binding["sources"]
        if len(source) != 1 or source[0] != atom["source"]:
            raise _failure(
                f"Projected command atom {atom['id']} source does not match "
                f"Profile binding {binding_id}",
                code="OFI-VPROJ-PROVENANCE-001",
            )

        config = binding["config"]
        pus = config["pus"]
        expected_tc = {
            "apid": pus.get("apid", default_apid),
            "service": pus["service"],
            "subtype": pus["subtype"],
            "data_hex": "",
        }

        owned = [operations[item] for item in atom["operation_ids"]]
        tc_ops = [item for item in owned if item["operation"] == "pus_tc"]
        if tc_ops[0]["resolved"] != expected_tc:
            raise _failure(
                f"Projected command atom {atom['id']} PUS TC resolution does not "
                f"match Profile binding {binding_id}",
                code="OFI-VPROJ-PROVENANCE-001",
            )

        declared_responses = config.get("expected_responses", [])
        actual_responses = [
            item["resolved"]
            for item in owned
            if item["operation"] == "expect_pus_tm"
        ]
        expected_responses = [
            {"service": item["service"], "subtype": item["subtype"]}
            for item in declared_responses
        ]
        if actual_responses != expected_responses:
            raise _failure(
                f"Projected command atom {atom['id']} target verification "
                f"obligations do not match Profile expected_responses",
                code="OFI-VPROJ-PROVENANCE-001",
            )
        total_expected_responses += len(expected_responses)

    if (
        payload["accounting"]["profile_verification_obligations"]
        != total_expected_responses
    ):
        raise _failure(
            "Plan Profile verification obligation accounting does not match "
            "consumed Profile expected_responses",
            code="OFI-VPROJ-PROVENANCE-001",
        )


def verification_projection_plan_bytes(payload: dict[str, Any]) -> bytes:
    """Return deterministic UTF-8 plan bytes after validation."""

    validate_verification_projection_plan(payload)
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_verification_projection_plan(
    path: Path,
    payload: dict[str, Any],
) -> Path:
    """Write a validated plan using the PoC deterministic JSON policy."""

    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(verification_projection_plan_bytes(payload))
    return path


def load_verification_projection_plan(
    path: Path,
    *,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
) -> dict[str, Any]:
    payload = load_json(path.resolve())
    validate_verification_projection_plan(payload, schema_path=schema_path)
    return payload
