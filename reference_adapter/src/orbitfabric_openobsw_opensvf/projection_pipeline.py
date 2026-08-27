from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .resolver import resolve_projection as resolve_base_projection
from .validator import ValidationInputError


def resolve_projection(
    *, manifest_path: Path, profile_path: Path, schema_path: Path
) -> dict[str, Any]:
    """Build the complete adapter IR, including target-specific resolved views."""
    resolved = resolve_base_projection(
        manifest_path=manifest_path,
        profile_path=profile_path,
        schema_path=schema_path,
    )
    _resolve_opensvf_telemetry(resolved)
    return resolved


def write_resolved_projection(
    *,
    manifest_path: Path,
    profile_path: Path,
    schema_path: Path,
    output_file: Path,
) -> Path:
    payload = resolve_projection(
        manifest_path=manifest_path,
        profile_path=profile_path,
        schema_path=schema_path,
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_file


def _resolve_opensvf_telemetry(resolved: dict[str, Any]) -> None:
    projections = resolved.get("projections")
    settings = resolved.get("settings")
    if not isinstance(projections, list) or not isinstance(settings, dict):
        raise ValidationInputError("resolved projection is missing projections/settings")
    opensvf_settings = settings.get("opensvf")
    if not isinstance(opensvf_settings, dict):
        raise ValidationInputError("resolved projection is missing OpenSVF settings")
    domain_apids = opensvf_settings.get("domain_apids")
    if not isinstance(domain_apids, dict):
        raise ValidationInputError("resolved OpenSVF domain APIDs must be an object")

    hk_memberships: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for projection in projections:
        if not isinstance(projection, dict) or projection.get("kind") != "housekeeping_packet":
            continue
        target = projection.get("target")
        if not isinstance(target, dict):
            continue
        pus = target.get("pus")
        members = target.get("members")
        if not isinstance(pus, dict) or not isinstance(members, list):
            raise ValidationInputError(
                f"HK projection {projection.get('binding_id')} lacks resolved PUS/members"
            )
        binding_id = str(projection.get("binding_id"))
        for member in members:
            if not isinstance(member, dict) or not isinstance(member.get("core_id"), str):
                raise ValidationInputError("resolved HK member lacks Core identity")
            hk_memberships.setdefault(member["core_id"], []).append((binding_id, pus))

    for projection in projections:
        if not isinstance(projection, dict) or projection.get("kind") != "telemetry_parameter":
            continue
        source_ref = projection.get("sources")
        core_semantics = projection.get("core_semantics")
        target = projection.get("target")
        resolutions = projection.get("resolutions")
        if (
            not isinstance(source_ref, list)
            or len(source_ref) != 1
            or not isinstance(source_ref[0], dict)
            or not isinstance(core_semantics, dict)
            or not isinstance(target, dict)
            or not isinstance(resolutions, list)
        ):
            raise ValidationInputError("telemetry projection is structurally incomplete")

        core_id = source_ref[0].get("id")
        semantic = core_semantics.get("source")
        if not isinstance(core_id, str) or not isinstance(semantic, dict):
            raise ValidationInputError("telemetry projection lacks Core source semantics")

        source = semantic.get("source")
        core_type = semantic.get("type")
        if not isinstance(source, str) or not source:
            raise ValidationInputError(f"telemetry {core_id} has no Core source")
        domain = source.upper()
        apid = domain_apids.get(domain)
        if not isinstance(apid, int) or isinstance(apid, bool):
            raise ValidationInputError(
                f"no OpenSVF APID configured for telemetry domain {domain}"
            )

        memberships = hk_memberships.get(core_id, [])
        if not memberships:
            raise ValidationInputError(
                f"telemetry {core_id} is not materialized by an HK packet with PUS mapping"
            )
        pus_pairs = {
            (item[1].get("service"), item[1].get("subservice")) for item in memberships
        }
        if len(pus_pairs) != 1:
            bindings = ", ".join(sorted(item[0] for item in memberships))
            raise ValidationInputError(
                f"telemetry {core_id} has ambiguous HK PUS mappings via {bindings}"
            )
        service, subservice = next(iter(pus_pairs))
        if not isinstance(service, int) or not isinstance(subservice, int):
            raise ValidationInputError(f"telemetry {core_id} resolved invalid HK PUS mapping")

        numeric_id = target.get("numeric_id")
        if not isinstance(numeric_id, int) or isinstance(numeric_id, bool):
            raise ValidationInputError(f"telemetry {core_id} has no resolved numeric ID")

        dtype, valid_range = _opensvf_type_projection(core_type)
        opensvf = {
            "dtype": dtype,
            "classification": "TM",
            "domain": domain,
            "model_id": source,
            "valid_range": valid_range,
            "pus": {
                "apid": apid,
                "service": service,
                "subservice": subservice,
                "parameter_id": numeric_id,
            },
        }
        target["opensvf"] = opensvf

        resolutions.extend(
            [
                {
                    "property": "target.opensvf.dtype",
                    "origin": "adapter_default",
                    "value": dtype,
                },
                {
                    "property": "target.opensvf.classification",
                    "origin": "adapter_default",
                    "value": "TM",
                },
                {
                    "property": "target.opensvf.domain",
                    "origin": "adapter_default",
                    "value": domain,
                },
                {
                    "property": "target.opensvf.model_id",
                    "origin": "adapter_default",
                    "value": source,
                },
                {
                    "property": "target.opensvf.valid_range",
                    "origin": "adapter_default",
                    "value": valid_range,
                },
                {
                    "property": "target.opensvf.pus.apid",
                    "origin": "profile",
                    "value": apid,
                },
                {
                    "property": "target.opensvf.pus.service",
                    "origin": "profile",
                    "value": service,
                    "source_bindings": sorted(item[0] for item in memberships),
                },
                {
                    "property": "target.opensvf.pus.subservice",
                    "origin": "profile",
                    "value": subservice,
                    "source_bindings": sorted(item[0] for item in memberships),
                },
                {
                    "property": "target.opensvf.pus.parameter_id",
                    "origin": "profile",
                    "value": numeric_id,
                },
            ]
        )
        resolutions.sort(key=lambda item: item["property"])


def _opensvf_type_projection(core_type: Any) -> tuple[str, list[float]]:
    if core_type == "uint16":
        return "int", [0.0, 65535.0]
    raise ValidationInputError(
        f"unsupported Core telemetry type for OpenSVF SRDB: {core_type}"
    )
