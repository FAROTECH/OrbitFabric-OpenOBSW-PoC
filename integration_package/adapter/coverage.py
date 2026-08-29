from __future__ import annotations

from collections import Counter
from typing import Any

from .core_input import CoreInputSet
from .profile import ProjectionProfile


def _source(binding: dict[str, Any]) -> tuple[str, str]:
    source = binding["sources"][0]
    return (source["domain"], source["id"])


def _source_ref(source: tuple[str, str]) -> dict[str, str]:
    return {"domain": source[0], "id": source[1]}


def build_coverage(
    core: CoreInputSet,
    profile: ProjectionProfile,
    mappings: list[dict[str, Any]],
) -> dict[str, Any]:
    mapping_by_source: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for mapping in mappings:
        for source in mapping["sources"]:
            mapping_by_source.setdefault((source["domain"], source["id"]), []).append(mapping)

    binding_by_source: dict[tuple[str, str], list[str]] = {}
    scope_domains: set[str] = set()
    for binding in profile.bindings:
        if binding.get("intent") != "project":
            continue
        source = _source(binding)
        scope_domains.add(source[0])
        binding_by_source.setdefault(source, []).append(binding["id"])

    records: list[dict[str, Any]] = []
    for source_key in sorted(core.entities):
        if source_key[0] not in scope_domains:
            continue
        source_mappings = mapping_by_source.get(source_key, [])
        if source_mappings:
            state = "projected"
            reason = None
        else:
            state = "not_projected"
            reason = "No Projection Profile binding projects this Core entity in the current operation."
        records.append(
            {
                "source": _source_ref(source_key),
                "state": state,
                "mappings": [item["id"] for item in source_mappings],
                "profile_bindings": binding_by_source.get(source_key, []),
                "diagnostics": [],
                "reason": reason,
            }
        )

    counts = Counter(item["state"] for item in records)
    return {
        "status": "complete",
        "scope": {"domains": sorted(scope_domains)},
        "reason": None,
        "summary": {key: counts[key] for key in sorted(counts)},
        "records": records,
    }
