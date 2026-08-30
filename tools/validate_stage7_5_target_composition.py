#!/usr/bin/env python3
"""Validate the Stage 7.5 target-owned SRDB composition handoff."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

EXPECTED_OPENOBSW_COMPOSITION_COMMIT = "44ceb71a016f0541ff7a0aa74191e13bafdb59c1"
_XTCE_NS = "http://www.omg.org/space/xtce"


def _git_head(repo: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _load_target_api(openobsw_repo: Path):
    sys.path.insert(0, str((openobsw_repo / "srdb").resolve()))
    try:
        from obsw_srdb import SRDBComposer, SRDBContributionLoader, SRDBLoader
        from obsw_srdb.codegen import generate_header, generate_xtce
    finally:
        sys.path.pop(0)
    return SRDBLoader, SRDBContributionLoader, SRDBComposer, generate_header, generate_xtce


def _compile_generated_header(header: str) -> None:
    with tempfile.TemporaryDirectory(prefix="stage7_5_srdb_") as raw:
        root = Path(raw)
        header_path = root / "srdb_generated.h"
        header_path.write_text(header, encoding="utf-8")
        smoke = """
#include "srdb_generated.h"

int main(void) {
    return (SRDB_PARAM_EPS_OBC_BUS_VOLTAGE_MV == 0x6001U &&
            SRDB_EVENT_EPS_VOLTAGE_OUT_OF_BOUNDS == 0x5001U &&
            SRDB_HK_OBC_HK == 5U &&
            SRDB_TC_ARE_YOU_ALIVE_SVC == 17U &&
            SRDB_TC_ARE_YOU_ALIVE_SUBSVC == 1U) ? 0 : 1;
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
                str(root),
                "-",
            ],
            input=smoke,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "Composed native SRDB generated header failed strict C11 compile:\n"
                + completed.stdout
                + completed.stderr
            )


def _validate_xtce(xtce: str) -> None:
    root = ET.fromstring(xtce)
    parameter_names = {
        item.get("name")
        for item in root.findall(f".//{{{_XTCE_NS}}}Parameter")
    }
    container_names = {
        item.get("name")
        for item in root.findall(f".//{{{_XTCE_NS}}}SequenceContainer")
    }
    parameter_refs = {
        item.get("parameterRef")
        for item in root.findall(f".//{{{_XTCE_NS}}}ParameterRefEntry")
    }

    assert "EPS_OBC_BUS_VOLTAGE_MV" in parameter_names
    assert "TM_3_25_OBC_HK" in container_names
    assert "EPS_OBC_BUS_VOLTAGE_MV" in parameter_refs


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compose the Stage 7.4 contribution through the target-owned obsw-srdb "
            "API and validate native codegen continuity."
        )
    )
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--openobsw-repo", required=True, type=Path)
    args = parser.parse_args()

    bundle = args.bundle.resolve()
    openobsw_repo = args.openobsw_repo.resolve()
    actual_head = _git_head(openobsw_repo)
    if actual_head != EXPECTED_OPENOBSW_COMPOSITION_COMMIT:
        raise SystemExit(
            "OpenOBSW checkout does not match the Stage 7.5 composition reference "
            f"{EXPECTED_OPENOBSW_COMPOSITION_COMMIT}; got {actual_head}"
        )

    (
        SRDBLoader,
        SRDBContributionLoader,
        SRDBComposer,
        generate_header,
        generate_xtce,
    ) = _load_target_api(openobsw_repo)

    base = SRDBLoader.load(openobsw_repo / "srdb" / "data")
    contribution = SRDBContributionLoader.load(bundle / "obsw_srdb_contribution")

    assert len(contribution.parameters) == 1
    assert len(contribution.telecommands) == 0
    assert len(contribution.hk_sets) == 1
    assert len(contribution.events) == 1

    assert base.parameter_by_id(0x6001) is None
    assert base.hk_set_by_id(5) is None
    assert base.event_by_id(0x5001) is None

    composed = SRDBComposer.compose(base, [contribution])

    parameter = composed.parameter_by_id(0x6001)
    assert parameter is not None
    assert parameter.name == "eps_obc_bus_voltage_mv"
    assert parameter.type.value == "uint16"
    assert (parameter.ptc, parameter.pfc) == (1, 16)

    hk = composed.hk_set_by_id(5)
    assert hk is not None
    assert hk.name == "obc_hk"
    assert hk.parameters == ["eps_obc_bus_voltage_mv"]

    event = composed.event_by_id(0x5001)
    assert event is not None
    assert event.name == "eps_voltage_out_of_bounds"
    assert event.severity.value == "MEDIUM"
    assert event.safe_trigger is False

    ping_targets = [
        tc
        for tc in composed.telecommands
        if (tc.apid, tc.service, tc.subservice) == (0x010, 17, 1)
    ]
    assert len(ping_targets) == 1
    assert ping_targets[0].name == "are_you_alive"
    assert all(tc.name != "obc_ping" for tc in composed.telecommands)

    header = generate_header(composed)
    assert "SRDB_PARAM_EPS_OBC_BUS_VOLTAGE_MV" in header
    assert "SRDB_EVENT_EPS_VOLTAGE_OUT_OF_BOUNDS" in header
    assert "SRDB_HK_OBC_HK" in header
    assert "SRDB_TC_ARE_YOU_ALIVE" in header
    _compile_generated_header(header)

    xtce = generate_xtce(composed)
    _validate_xtce(xtce)

    print("Stage 7.5 target composition acceptance: PASS")
    print(f"  bundle: {bundle}")
    print(f"  OpenOBSW composition reference: {EXPECTED_OPENOBSW_COMPOSITION_COMMIT}")
    print("  base + additive contribution -> complete SRDB PASS")
    print("  reused are_you_alive remains unique PASS")
    print("  native obsw-srdb C header codegen + strict C11 PASS")
    print("  native obsw-srdb XTCE codegen continuity PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
