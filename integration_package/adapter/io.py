from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from .model import AdapterFailure


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader: UniqueKeyLoader, node: yaml.Node, deep: bool = False) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"Duplicate YAML mapping key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AdapterFailure(
            "OFI-INPUT-DOCUMENT-001",
            "input_compatibility",
            f"Cannot read JSON document {path}: {exc}",
        ) from exc
    if not isinstance(value, dict):
        raise AdapterFailure(
            "OFI-INPUT-DOCUMENT-001",
            "input_compatibility",
            f"Expected JSON object document: {path}",
        )
    return value


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as stream:
            value = yaml.load(stream, Loader=UniqueKeyLoader)
    except (OSError, UnicodeError, yaml.YAMLError, ValueError) as exc:
        raise AdapterFailure(
            "OFI-PROFILE-DOCUMENT-001",
            "profile_schema",
            f"Cannot parse Projection Profile {path}: {exc}",
        ) from exc
    if not isinstance(value, dict):
        raise AdapterFailure(
            "OFI-PROFILE-DOCUMENT-001",
            "profile_schema",
            f"Expected YAML mapping document: {path}",
        )
    return value


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise AdapterFailure(
            "OFI-INPUT-DOCUMENT-001",
            "input_compatibility",
            f"Cannot hash file {path}: {exc}",
        ) from exc
    return digest.hexdigest()


def resolve_contained_file(root: Path, relative: str, *, code: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise AdapterFailure(code, "input_compatibility", "Portable path must be a non-empty string")
    candidate = Path(relative)
    if candidate.is_absolute():
        raise AdapterFailure(code, "input_compatibility", f"Absolute portable path is forbidden: {relative}")
    root_resolved = root.resolve()
    resolved = (root_resolved / candidate).resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise AdapterFailure(code, "input_compatibility", f"Portable path escapes its bundle root: {relative}") from exc
    return resolved


def canonical_input_set_sha256(manifest: dict[str, Any]) -> str:
    try:
        import rfc8785
    except ImportError as exc:  # pragma: no cover - environment/configuration failure
        raise AdapterFailure(
            "OFI-COMP-AUTH-001",
            "input_compatibility",
            "rfc8785 is required to verify Core input_set_sha256",
        ) from exc

    surfaces = []
    try:
        for record in sorted(manifest["surfaces"], key=lambda item: item["role"]):
            surfaces.append(
                {
                    "role": record["role"],
                    "requirement": record["requirement"],
                    "status": record["status"],
                    "kind": record["kind"],
                    "format_version": record["format_version"],
                    "sha256": record["sha256"],
                    "unavailable_reason": record["unavailable_reason"],
                }
            )
        payload = {
            "kind": manifest["kind"],
            "input_set_version": manifest["input_set_version"],
            "orbitfabric_version": manifest["orbitfabric_version"],
            "mission": manifest["mission"],
            "load_result": manifest["load_result"],
            "lint_result": manifest["lint_result"],
            "surfaces": surfaces,
        }
    except (KeyError, TypeError) as exc:
        raise AdapterFailure(
            "OFI-INPUT-MANIFEST-001",
            "input_compatibility",
            f"Core Integration Input Manifest is structurally incomplete: {exc}",
        ) from exc
    return hashlib.sha256(rfc8785.dumps(payload)).hexdigest()
