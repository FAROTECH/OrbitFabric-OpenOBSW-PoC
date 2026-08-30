#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

EXPECTED_OPENOBSW_COMMIT = "b3b7c3fa9c6edd2a52eef356d113c1eae1b03fec"
EXPECTED_RESULT_KIND = "orbitfabric.integration_result"
EXPECTED_RESULT_VERSION = "0.1-candidate"
EXPECTED_CONTRIBUTION_KIND = "orbitfabric.openobsw_opensvf.obsw_srdb_contribution"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _read_yaml_list(path: Path, key: str) -> list[dict[str, Any]]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get(key), list):
        raise ValueError(f"Expected YAML mapping with {key!r} list: {path}")
    if not all(isinstance(item, dict) for item in value[key]):
        raise ValueError(f"Expected object records in {path}")
    return value[key]


def _git_head(repo: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _load_target_models(openobsw_repo: Path) -> Any:
    sys.path.insert(0, str((openobsw_repo / "srdb").resolve()))
    try:
        return importlib.import_module("obsw_srdb.model")
    finally:
        sys.path.pop(0)


def _validate_result(bundle: Path) -> dict[str, Any]:
    result = _read_json(bundle / "integration_result.json")
    assert result["kind"] == EXPECTED_RESULT_KIND
    assert result["result_version"] == EXPECTED_RESULT_VERSION
    assert result["result"] == "succeeded"
    assert result["capabilities"] == [
        "profile_validation",
        "projection",
        "artifact_generation",
        "traceability",
    ]
    assert result["diagnostics"] == []
    assert result["coverage"]["status"] == "complete"
    assert result["coverage"]["summary"] == {"not_projected": 1, "projected": 4}
    assert len(result["mappings"]) == 4
    assert "dhs.obc.ping" not in json.dumps(result, sort_keys=True)

    for artifact in result["artifacts"]:
        assert artifact["status"] == "generated"
        relative = Path(artifact["path"])
        assert not relative.is_absolute()
        assert ".." not in relative.parts
        path = bundle / relative
        assert path.is_file(), path
        assert artifact["sha256"] == _sha256(path)
    return result


def _validate_contribution(bundle: Path, models: Any) -> None:
    root = bundle / "obsw_srdb_contribution"
    manifest = _read_json(root / "contribution_manifest.json")
    assert manifest["kind"] == EXPECTED_CONTRIBUTION_KIND
    assert manifest["contribution_version"] == "0.1-candidate"
    assert manifest["mode"] == "additive"
    assert manifest["complete_srdb"] is False
    assert manifest["target"]["obsw_srdb"]["version"] == "0.1.0"
    assert manifest["target"]["obsw_srdb"]["source_commit"] == EXPECTED_OPENOBSW_COMMIT

    declared_roles = {record["role"] for record in manifest["files"]}
    assert declared_roles == {"parameters", "telecommands", "hk_sets", "events"}
    for record in manifest["files"]:
        path = root / record["path"]
        assert path.is_file(), path
        assert record["sha256"] == _sha256(path)

    parameters = _read_yaml_list(root / "parameters.yaml", "parameters")
    telecommands = _read_yaml_list(root / "telecommands.yaml", "telecommands")
    hk_sets = _read_yaml_list(root / "hk_sets.yaml", "hk_sets")
    events = _read_yaml_list(root / "events.yaml", "events")

    for record in parameters:
        models.Parameter(**record)
    for record in telecommands:
        models.Telecommand(**record)
    for record in hk_sets:
        models.HKSet(**record)
    for record in events:
        models.Event(**record)

    contributed_parameter_names = {record["name"] for record in parameters}
    for hk_set in hk_sets:
        missing = set(hk_set["parameters"]) - contributed_parameter_names
        assert not missing, f"HK contribution has unresolved parameter refs: {sorted(missing)}"

    assert telecommands == []
    assert manifest["reused_targets"] == [
        {
            "binding": "cmd.ping",
            "source": {"domain": "commands", "id": "obc.ping"},
            "namespace": "obsw-srdb",
            "kind": "telecommand",
            "id": "are_you_alive",
            "reason": (
                "Exact compatible target telecommand already exists "
                "in the selected baseline."
            ),
        }
    ]


def _validate_c11(bundle: Path) -> None:
    include_dir = bundle / "flight_software"
    header = include_dir / "mission_contract.h"
    assert header.is_file()
    smoke = """
#include "mission_contract.h"

int main(void) {
    of_hk_obc_hk_t hk = {0};
    hk.eps_obc_bus_voltage_mv = 0u;
    return (OF_TM_OBC_BUS_VOLTAGE_MV == 0x6001 &&
            OF_CMD_PING == 0x1701 &&
            OF_EVENT_VOLTAGE_OUT_OF_BOUNDS == 0x5001 &&
            OF_HK_SET_OBC == 0x0005 &&
            OF_HK_SET_OBC_DEFAULT_INTERVAL_TICKS == 0u) ? 0 : 1;
}
"""
    completed = subprocess.run(
        [
            "cc",
            "-x",
            "c",
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-fsyntax-only",
            "-I",
            str(include_dir),
            "-",
        ],
        input=smoke,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "Generated flight contract failed strict C11 compile:\n"
            + completed.stdout
            + completed.stderr
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Stage 7.4 artifacts against the pinned real OpenOBSW/obsw-srdb target."
    )
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--openobsw-repo", required=True, type=Path)
    args = parser.parse_args()

    bundle = args.bundle.resolve()
    openobsw_repo = args.openobsw_repo.resolve()
    if _git_head(openobsw_repo) != EXPECTED_OPENOBSW_COMMIT:
        raise SystemExit(
            "OpenOBSW checkout does not match the pinned Stage 7.4 baseline "
            f"{EXPECTED_OPENOBSW_COMMIT}"
        )

    models = _load_target_models(openobsw_repo)
    _validate_result(bundle)
    _validate_contribution(bundle, models)
    _validate_c11(bundle)

    print("Stage 7.4 artifact acceptance: PASS")
    print(f"  bundle: {bundle}")
    print(f"  OpenOBSW: {EXPECTED_OPENOBSW_COMMIT}")
    print("  obsw-srdb: 0.1.0 native model validation PASS")
    print("  mission_contract.h strict C11 compile PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
