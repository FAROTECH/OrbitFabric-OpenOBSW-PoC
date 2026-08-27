from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
import yaml


EXPECTED_INPUT_SET_KIND = "orbitfabric.integration_input_set"
EXPECTED_INPUT_SET_VERSION = "0.1-candidate"
EXPECTED_ENTITY_INDEX_KIND = "orbitfabric.entity_index"
REQUIRED_SURFACE_ROLES = {
    "mission_snapshot",
    "entity_index",
    "relationship_manifest",
    "lint_report",
}
SUPPORTED_PROJECT_KINDS = {
    "telemetry_parameter",
    "housekeeping_packet",
    "command",
    "event",
}


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    diagnostics: tuple[Diagnostic, ...]

    @property
    def ok(self) -> bool:
        return not self.diagnostics


class ValidationInputError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationInputError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationInputError(f"expected JSON object in {path}")
    return value


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValidationInputError(f"cannot read YAML {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationInputError(f"expected YAML mapping in {path}")
    return value


def _sha256(path: Path) -> str:
    digest = sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ValidationInputError(f"cannot hash {path}: {exc}") from exc
    return digest.hexdigest()


def _contained_path(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    root_resolved = root.resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ValidationInputError(
            f"surface path escapes Integration Input Set root: {relative}"
        ) from exc
    return candidate


def _validate_input_set(
    manifest_path: Path,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    manifest = _read_json(manifest_path)

    if manifest.get("kind") != EXPECTED_INPUT_SET_KIND:
        diagnostics.append(Diagnostic("input.kind", "unsupported Integration Input Set kind"))
    if manifest.get("input_set_version") != EXPECTED_INPUT_SET_VERSION:
        diagnostics.append(
            Diagnostic("input.version", "unsupported Integration Input Set version")
        )
    if manifest.get("load_result") != "loaded":
        diagnostics.append(Diagnostic("input.load", "Core Mission Model was not loaded"))
    if manifest.get("lint_result") not in {"passed", "passed_with_warnings"}:
        diagnostics.append(
            Diagnostic("input.lint", "Core lint result blocks projection validation")
        )

    surfaces = manifest.get("surfaces")
    if not isinstance(surfaces, list):
        diagnostics.append(Diagnostic("input.surfaces", "surfaces must be an array"))
        return manifest, {}, diagnostics

    by_role: dict[str, dict[str, Any]] = {}
    for item in surfaces:
        if not isinstance(item, dict) or not isinstance(item.get("role"), str):
            diagnostics.append(Diagnostic("input.surface", "invalid surface record"))
            continue
        role = item["role"]
        if role in by_role:
            diagnostics.append(Diagnostic("input.surface_role", f"duplicate surface role: {role}"))
            continue
        by_role[role] = item

    root = manifest_path.parent
    for role in sorted(REQUIRED_SURFACE_ROLES):
        item = by_role.get(role)
        if item is None:
            diagnostics.append(Diagnostic("input.required_surface", f"missing required surface: {role}"))
            continue
        if item.get("requirement") != "required":
            diagnostics.append(
                Diagnostic("input.surface_requirement", f"surface {role} is not declared required")
            )
        if item.get("status") != "available":
            diagnostics.append(
                Diagnostic("input.surface_status", f"required surface {role} is unavailable")
            )
            continue
        relative = item.get("path")
        expected_digest = item.get("sha256")
        if not isinstance(relative, str) or not relative:
            diagnostics.append(Diagnostic("input.surface_path", f"surface {role} has no path"))
            continue
        if not isinstance(expected_digest, str) or len(expected_digest) != 64:
            diagnostics.append(Diagnostic("input.surface_digest", f"surface {role} has invalid SHA-256"))
            continue
        try:
            path = _contained_path(root, relative)
            actual_digest = _sha256(path)
        except ValidationInputError as exc:
            diagnostics.append(Diagnostic("input.surface_file", str(exc)))
            continue
        if actual_digest.lower() != expected_digest.lower():
            diagnostics.append(Diagnostic("input.surface_digest", f"SHA-256 mismatch for {role}"))

    return manifest, by_role, diagnostics


def _load_entity_index(
    manifest_path: Path,
    manifest: dict[str, Any],
    surfaces: dict[str, dict[str, Any]],
    diagnostics: list[Diagnostic],
) -> set[tuple[str, str]]:
    item = surfaces.get("entity_index")
    if item is None or item.get("status") != "available" or not isinstance(item.get("path"), str):
        return set()

    try:
        path = _contained_path(manifest_path.parent, item["path"])
        index = _read_json(path)
    except ValidationInputError as exc:
        diagnostics.append(Diagnostic("entity_index.read", str(exc)))
        return set()

    if index.get("kind") != EXPECTED_ENTITY_INDEX_KIND:
        diagnostics.append(Diagnostic("entity_index.kind", "unexpected Entity Index kind"))
    if index.get("index_version") != item.get("format_version"):
        diagnostics.append(
            Diagnostic("entity_index.version", "Entity Index format version does not match manifest")
        )

    manifest_mission = manifest.get("mission") if isinstance(manifest.get("mission"), dict) else {}
    index_mission = index.get("mission") if isinstance(index.get("mission"), dict) else {}
    for key in ("id", "model_version"):
        if manifest_mission.get(key) != index_mission.get(key):
            diagnostics.append(
                Diagnostic("entity_index.mission", f"Entity Index mission {key} does not match manifest")
            )

    entities = index.get("entities")
    if not isinstance(entities, list):
        diagnostics.append(Diagnostic("entity_index.entities", "Entity Index entities must be an array"))
        return set()

    refs: set[tuple[str, str]] = set()
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        domain = entity.get("domain")
        entity_id = entity.get("id")
        if isinstance(domain, str) and isinstance(entity_id, str):
            refs.add((domain, entity_id))
    return refs


def _validate_profile_semantics(
    profile: dict[str, Any], entity_refs: set[tuple[str, str]]
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    bindings = profile.get("bindings")
    if not isinstance(bindings, list):
        return diagnostics

    binding_ids: set[str] = set()
    explicit_c_symbols: dict[str, str] = {}
    numeric_ids: dict[tuple[str, int], str] = {}

    for binding in bindings:
        if not isinstance(binding, dict):
            continue
        binding_id = binding.get("id")
        if isinstance(binding_id, str):
            if binding_id in binding_ids:
                diagnostics.append(Diagnostic("profile.binding_id", f"duplicate binding id: {binding_id}"))
            binding_ids.add(binding_id)
        else:
            binding_id = "<unknown>"

        seen_sources: set[tuple[str, str]] = set()
        sources = binding.get("sources")
        if isinstance(sources, list):
            for source in sources:
                if not isinstance(source, dict):
                    continue
                domain = source.get("domain")
                entity_id = source.get("id")
                if not isinstance(domain, str) or not isinstance(entity_id, str):
                    continue
                ref = (domain, entity_id)
                if ref in seen_sources:
                    diagnostics.append(
                        Diagnostic("profile.source", f"duplicate source {domain}/{entity_id} in {binding_id}")
                    )
                seen_sources.add(ref)
                if ref not in entity_refs:
                    diagnostics.append(
                        Diagnostic("profile.source", f"unresolved Core source: {domain}/{entity_id}")
                    )

        if binding.get("intent") != "project":
            continue
        config = binding.get("config")
        if not isinstance(config, dict):
            continue
        kind = config.get("kind")
        if kind not in SUPPORTED_PROJECT_KINDS:
            diagnostics.append(Diagnostic("profile.kind", f"unsupported projection kind: {kind}"))
            continue

        c_symbol = config.get("c_symbol")
        if isinstance(c_symbol, str):
            previous = explicit_c_symbols.get(c_symbol)
            if previous is not None:
                diagnostics.append(
                    Diagnostic("profile.c_symbol", f"C symbol {c_symbol} used by {previous} and {binding_id}")
                )
            else:
                explicit_c_symbols[c_symbol] = str(binding_id)

        numeric_id = config.get("numeric_id")
        if isinstance(numeric_id, int):
            key = (kind, numeric_id)
            previous = numeric_ids.get(key)
            if previous is not None:
                diagnostics.append(
                    Diagnostic(
                        "profile.numeric_id",
                        f"numeric_id {numeric_id} for {kind} used by {previous} and {binding_id}",
                    )
                )
            else:
                numeric_ids[key] = str(binding_id)

    return diagnostics


def validate_profile(
    *, manifest_path: Path, profile_path: Path, schema_path: Path
) -> ValidationResult:
    diagnostics: list[Diagnostic] = []

    manifest, surfaces, input_diagnostics = _validate_input_set(manifest_path)
    diagnostics.extend(input_diagnostics)

    profile = _read_yaml(profile_path)
    schema = _read_json(schema_path)
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:  # jsonschema raises several schema-specific subclasses
        raise ValidationInputError(f"invalid packaged Projection Profile schema: {exc}") from exc

    validator = Draft202012Validator(schema)
    schema_errors = sorted(validator.iter_errors(profile), key=lambda error: list(error.absolute_path))
    for error in schema_errors:
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        diagnostics.append(Diagnostic("profile.schema", f"{location}: {error.message}"))

    if not schema_errors:
        entity_refs = _load_entity_index(manifest_path, manifest, surfaces, diagnostics)
        diagnostics.extend(_validate_profile_semantics(profile, entity_refs))

    return ValidationResult(tuple(diagnostics))
