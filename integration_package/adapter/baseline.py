from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io import load_json, sha256_file
from .model import AdapterFailure

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
BASELINE_ROOT = PACKAGE_ROOT / "resources" / "target_baselines"
SUPPORTED_BASELINES = {
    "openobsw-0.7.0-obsw-srdb-0.1.0-reference": BASELINE_ROOT
    / "openobsw-0.7.0-obsw-srdb-0.1.0-reference.json"
}


@dataclass(frozen=True)
class TargetBaseline:
    path: Path
    document: dict[str, Any]
    sha256: str

    @property
    def id(self) -> str:
        return self.document["id"]


def _assert_unique(records: list[dict[str, Any]], key: str, label: str) -> None:
    values = [record.get(key) for record in records]
    if len(values) != len(set(values)):
        raise AdapterFailure(
            "OFI-COMP-BASELINE-002",
            "input_compatibility",
            f"Duplicate {label} in package baseline",
        )


def load_target_baseline(identifier: str) -> TargetBaseline:
    path = SUPPORTED_BASELINES.get(identifier)
    if path is None:
        raise AdapterFailure(
            "OFI-COMP-BASELINE-001",
            "input_compatibility",
            f"Unknown or unsupported target baseline: {identifier}",
        )
    document = load_json(path)
    if (
        document.get("kind") != "orbitfabric.openobsw_opensvf.target_baseline"
        or document.get("baseline_version") != "0.1-candidate"
        or document.get("id") != identifier
    ):
        raise AdapterFailure(
            "OFI-COMP-BASELINE-002",
            "input_compatibility",
            "Package target baseline identity is invalid",
        )

    target = document.get("projection_target", {})
    openobsw = target.get("openobsw", {}) if isinstance(target, dict) else {}
    srdb = target.get("obsw_srdb", {}) if isinstance(target, dict) else {}
    if (
        openobsw.get("version") != "0.7.0"
        or openobsw.get("commit") != "b3b7c3fa9c6edd2a52eef356d113c1eae1b03fec"
    ):
        raise AdapterFailure(
            "OFI-COMP-BASELINE-002",
            "input_compatibility",
            "Unsupported OpenOBSW package baseline",
        )
    if srdb.get("version") != "0.1.0" or srdb.get("source_commit") != openobsw.get("commit"):
        raise AdapterFailure(
            "OFI-COMP-SRDB-001",
            "input_compatibility",
            "Unsupported obsw-srdb package/model baseline",
        )

    compatibility = document.get("project_compatibility", {})
    pus = compatibility.get("pus", {}) if isinstance(compatibility, dict) else {}
    layout = pus.get("tm_layout", {}) if isinstance(pus, dict) else {}
    sec_bytes = layout.get("openobsw_secondary_header_bytes")
    primary_bits = layout.get("obsw_srdb_primary_header_bits")
    app_start = layout.get("obsw_srdb_application_data_start_bit")
    if not all(isinstance(value, int) for value in (sec_bytes, primary_bits, app_start)):
        raise AdapterFailure(
            "OFI-COMP-BASELINE-002",
            "input_compatibility",
            "Package target baseline TM layout is invalid",
        )
    if primary_bits + sec_bytes * 8 != app_start:
        raise AdapterFailure(
            "OFI-COMP-PUS-004",
            "input_compatibility",
            "OpenOBSW TM secondary-header declaration and tested SRDB codegen layout disagree",
        )

    severity_subtypes = pus.get("event_severity_subtypes")
    if severity_subtypes != {"INFO": 1, "LOW": 2, "MEDIUM": 3, "HIGH": 4}:
        raise AdapterFailure(
            "OFI-COMP-BASELINE-002",
            "input_compatibility",
            "Package target baseline event severity mapping is invalid",
        )

    allocations = compatibility.get("occupied_allocations", {})
    if not isinstance(allocations, dict):
        raise AdapterFailure(
            "OFI-COMP-BASELINE-002",
            "input_compatibility",
            "Package baseline allocation registry missing",
        )
    _assert_unique(allocations.get("parameters", []), "id", "parameter ID")
    _assert_unique(allocations.get("parameters", []), "name", "parameter name")
    _assert_unique(allocations.get("events", []), "id", "event ID")
    _assert_unique(allocations.get("events", []), "name", "event name")
    _assert_unique(allocations.get("hk_sets", []), "sid", "HK SID")
    _assert_unique(allocations.get("hk_sets", []), "name", "HK name")

    telecommands = allocations.get("telecommands", [])
    tuples = [
        (item.get("apid"), item.get("service"), item.get("subtype"))
        for item in telecommands
    ]
    if len(tuples) != len(set(tuples)):
        raise AdapterFailure(
            "OFI-COMP-BASELINE-002",
            "input_compatibility",
            "Duplicate telecommand tuple in package baseline",
        )

    return TargetBaseline(path=path, document=document, sha256=sha256_file(path))
