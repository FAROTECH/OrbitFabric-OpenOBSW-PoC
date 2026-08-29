from __future__ import annotations

import re
from typing import Any

from .baseline import TargetBaseline
from .model import AdapterFailure


def target_name(identifier: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "_", identifier).strip("_").lower()
    value = re.sub(r"_+", "_", value)
    if not value:
        raise AdapterFailure(
            "OFI-COMP-AUTH-001",
            "projection_validation",
            f"Cannot derive target name from Core id {identifier!r}",
        )
    return value


def target_ref(namespace: str, kind: str, identifier: str) -> dict[str, str]:
    return {"namespace": namespace, "kind": kind, "id": identifier}


def message_set(baseline: TargetBaseline) -> set[tuple[str, int, int]]:
    records = baseline.document["project_compatibility"]["exact_message_capabilities"]
    return {(item["direction"], item["service"], item["subtype"]) for item in records}


def require_message(
    messages: set[tuple[str, int, int]],
    direction: str,
    service: int,
    subtype: int,
    *,
    binding: str,
) -> None:
    if (direction, service, subtype) not in messages:
        raise AdapterFailure(
            "OFI-COMP-PUS-002",
            "input_compatibility",
            f"Exact required PUS message is unsupported: {direction}({service},{subtype})",
            profile_bindings=[binding],
        )


def allocation_maps(
    baseline: TargetBaseline,
    category: str,
    id_key: str,
) -> tuple[dict[int, str], dict[str, int]]:
    records = baseline.document["project_compatibility"]["occupied_allocations"][category]
    return (
        {item[id_key]: item["name"] for item in records},
        {item["name"]: item[id_key] for item in records},
    )


def check_numeric_and_name(
    *,
    numeric_value: int,
    target_name_value: str,
    by_id: dict[int, str],
    by_name: dict[str, int],
    numeric_code: str,
    binding: str,
    label: str,
) -> None:
    if numeric_value in by_id:
        raise AdapterFailure(
            numeric_code,
            "input_compatibility",
            f"{label} allocation {numeric_value} collides with baseline target {by_id[numeric_value]}",
            profile_bindings=[binding],
        )
    if target_name_value in by_name:
        raise AdapterFailure(
            "OFI-COMP-NAME-001",
            "input_compatibility",
            f"Deterministic target name {target_name_value!r} collides with baseline {label} allocation {by_name[target_name_value]}",
            profile_bindings=[binding],
        )


def argument_contract_compatible(
    core_arguments: Any,
    target_parameters: Any,
    type_map: dict[str, Any],
) -> bool:
    if not isinstance(core_arguments, list) or not isinstance(target_parameters, list):
        return False
    if len(core_arguments) != len(target_parameters):
        return False
    for core_arg, target_arg in zip(core_arguments, target_parameters):
        if not isinstance(core_arg, dict) or not isinstance(target_arg, dict):
            return False
        projected = type_map.get(core_arg.get("type"))
        if projected is None:
            return False
        if core_arg.get("name") != target_arg.get("name"):
            return False
        if projected.get("type") != target_arg.get("type"):
            return False
    return True
