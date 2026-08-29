from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .io import load_json, load_yaml, sha256_file
from .model import AdapterFailure, INTEGRATION_ID, PROFILE_SCHEMA_VERSION, PROFILE_VERSION

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA_PATH = PACKAGE_ROOT / "schemas" / "profile-0.1.schema.json"


@dataclass(frozen=True)
class ProjectionProfile:
    path: Path
    document: dict[str, Any]
    sha256: str

    @property
    def id(self) -> str:
        return self.document["profile"]["id"]

    @property
    def version(self) -> str:
        return self.document["profile"]["version"]

    @property
    def schema_version(self) -> str:
        return self.document["integration"]["schema_version"]

    @property
    def bindings(self) -> list[dict[str, Any]]:
        return self.document["bindings"]


def _assert_local_refs(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "$ref" and isinstance(child, str) and not child.startswith("#/"):
                raise AdapterFailure(
                    "OFI-PROFILE-SCHEMA-001",
                    "profile_schema",
                    f"Remote or non-local JSON Schema $ref is forbidden: {child}",
                )
            _assert_local_refs(child)
    elif isinstance(value, list):
        for child in value:
            _assert_local_refs(child)


def _source(binding: dict[str, Any]) -> tuple[str, str] | None:
    sources = binding.get("sources")
    if not isinstance(sources, list) or len(sources) != 1 or not isinstance(sources[0], dict):
        return None
    domain = sources[0].get("domain")
    identifier = sources[0].get("id")
    if isinstance(domain, str) and isinstance(identifier, str):
        return (domain, identifier)
    return None


def _semantic_errors(profile: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    bindings = profile.get("bindings")
    if not isinstance(bindings, list):
        return errors

    ids: set[str] = set()
    symbols: set[str] = set()
    parameter_ids: set[int] = set()
    command_ids: set[int] = set()
    event_ids: set[int] = set()
    hk_sids: set[int] = set()
    tc_tuples: set[tuple[int, int, int]] = set()
    projected_tm: set[tuple[str, str]] = set()

    settings = profile.get("settings", {})
    severity_map = settings.get("obsw_srdb", {}).get("event_severity_map", {}) if isinstance(settings, dict) else {}
    order = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
    values = [severity_map.get(key) for key in ("info", "warning", "error", "critical")]
    if all(value in order for value in values):
        numeric = [order[value] for value in values]
        if numeric != sorted(numeric):
            errors.append("settings.obsw_srdb.event_severity_map must be non-decreasing")

    for binding in bindings:
        if not isinstance(binding, dict):
            continue
        binding_id = binding.get("id")
        if isinstance(binding_id, str):
            if binding_id in ids:
                errors.append(f"duplicate binding id {binding_id}")
            ids.add(binding_id)
        source = _source(binding)
        if binding.get("intent") == "project" and source and source[0] == "telemetry":
            projected_tm.add(source)

    default_tc_apid = settings.get("pus", {}).get("tc_apid") if isinstance(settings, dict) else None

    for binding in bindings:
        if not isinstance(binding, dict) or binding.get("intent") != "project":
            continue
        source = _source(binding)
        if source is None:
            continue
        domain = source[0]
        config = binding.get("config") if isinstance(binding.get("config"), dict) else {}
        flight = config.get("flight_contract") if isinstance(config.get("flight_contract"), dict) else {}
        srdb = config.get("obsw_srdb") if isinstance(config.get("obsw_srdb"), dict) else {}
        pus = config.get("pus") if isinstance(config.get("pus"), dict) else {}

        symbol = flight.get("c_symbol")
        if isinstance(symbol, str):
            if symbol in symbols:
                errors.append(f"duplicate target C symbol {symbol}")
            symbols.add(symbol)

        if domain == "telemetry":
            parameter_id = srdb.get("parameter_id")
            if isinstance(parameter_id, int):
                if parameter_id in parameter_ids:
                    errors.append(f"duplicate obsw-srdb parameter ID {parameter_id}")
                parameter_ids.add(parameter_id)
            if pus or "event_id" in srdb or "hk_set" in srdb or "command_id" in flight:
                errors.append(f"illegal telemetry target configuration in {binding.get('id')}")

        elif domain == "commands":
            command_id = flight.get("command_id")
            if isinstance(command_id, int):
                if command_id in command_ids:
                    errors.append(f"duplicate flight-contract command ID {command_id}")
                command_ids.add(command_id)
            if srdb or not pus:
                errors.append(f"illegal command target configuration in {binding.get('id')}")
            if pus:
                apid = pus.get("apid", default_tc_apid)
                service = pus.get("service")
                subtype = pus.get("subtype")
                if all(isinstance(value, int) for value in (apid, service, subtype)):
                    key = (apid, service, subtype)
                    if key in tc_tuples:
                        errors.append(f"duplicate PUS TC tuple {key}")
                    tc_tuples.add(key)

        elif domain == "events":
            event_id = srdb.get("event_id")
            if isinstance(event_id, int):
                if event_id in event_ids:
                    errors.append(f"duplicate obsw-srdb event ID {event_id}")
                event_ids.add(event_id)
            if pus or "parameter_id" in srdb or "hk_set" in srdb or "command_id" in flight or "expected_responses" in config:
                errors.append(f"illegal event target configuration in {binding.get('id')}")

        elif domain == "packets":
            hk_set = srdb.get("hk_set")
            if isinstance(hk_set, dict):
                sid = hk_set.get("sid")
                if isinstance(sid, int):
                    if sid in hk_sids:
                        errors.append(f"duplicate obsw-srdb HK SID {sid}")
                    hk_sids.add(sid)
                fields = hk_set.get("fields")
                if isinstance(fields, list):
                    seen_fields: set[tuple[str, str]] = set()
                    for field in fields:
                        if not isinstance(field, dict):
                            continue
                        key = (field.get("domain"), field.get("id"))
                        if key in seen_fields:
                            errors.append(f"duplicate HK field {key} in {binding.get('id')}")
                        seen_fields.add(key)
                        if key not in projected_tm:
                            errors.append(f"HK field {key} has no projected telemetry binding")
            if pus or "parameter_id" in srdb or "event_id" in srdb or "command_id" in flight or "expected_responses" in config:
                errors.append(f"illegal packet target configuration in {binding.get('id')}")

    return errors


def load_projection_profile(profile_path: Path, *, schema_path: Path = DEFAULT_SCHEMA_PATH) -> ProjectionProfile:
    profile_path = profile_path.resolve()
    schema_path = schema_path.resolve()
    profile = load_yaml(profile_path)
    schema = load_json(schema_path)
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        raise AdapterFailure(
            "OFI-PROFILE-SCHEMA-001",
            "profile_schema",
            f"Package Projection Profile schema is invalid: {exc}",
        ) from exc
    _assert_local_refs(schema)
    errors = sorted(Draft202012Validator(schema).iter_errors(profile), key=lambda item: list(item.absolute_path))
    if errors:
        first = errors[0]
        path = ".".join(str(part) for part in first.absolute_path) or "<root>"
        raise AdapterFailure(
            "OFI-PROFILE-SCHEMA-001",
            "profile_schema",
            f"Projection Profile schema validation failed at {path}: {first.message}",
        )

    if profile.get("kind") != "orbitfabric.projection_profile" or profile.get("profile_version") != PROFILE_VERSION:
        raise AdapterFailure("OFI-PROFILE-SCHEMA-001", "profile_schema", "Unsupported Projection Profile envelope")
    integration = profile.get("integration")
    if not isinstance(integration, dict) or integration.get("id") != INTEGRATION_ID or integration.get("schema_version") != PROFILE_SCHEMA_VERSION:
        raise AdapterFailure("OFI-PROFILE-SCHEMA-001", "profile_schema", "Projection Profile integration/schema identity mismatch")

    semantic_errors = _semantic_errors(profile)
    if semantic_errors:
        raise AdapterFailure(
            "OFI-PROFILE-SEMANTIC-001",
            "projection_validation",
            semantic_errors[0],
        )

    return ProjectionProfile(path=profile_path, document=profile, sha256=sha256_file(profile_path))
