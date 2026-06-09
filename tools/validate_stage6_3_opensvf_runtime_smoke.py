#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]

DOC = ROOT / "docs/stage6_3_opensvf_runtime_smoke.md"
CAMPAIGN = ROOT / "execution/campaigns/poc_runtime_ping_smoke.yaml"
SPACECRAFT = ROOT / "execution/opensvf/poc_spacecraft_runtime_smoke.yaml"
PROCEDURE = ROOT / "execution/procedures/poc_runtime_ping_smoke.py"
GITIGNORE = ROOT / ".gitignore"
OPTIONAL_EVIDENCE = ROOT / "execution/evidence/poc_runtime_ping_smoke_report.json"


def fail(message: str) -> None:
    print(f"Stage 6.3 validation: FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def require_file(path: Path) -> None:
    if not path.is_file():
        fail(f"missing file: {path.relative_to(ROOT)}")


def load_yaml(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text())
    except Exception as exc:
        fail(f"cannot parse YAML {path.relative_to(ROOT)}: {exc}")

    if not isinstance(data, dict):
        fail(f"YAML root must be a mapping: {path.relative_to(ROOT)}")

    return data


def validate_gitignore() -> None:
    text = GITIGNORE.read_text() if GITIGNORE.exists() else ""

    if "results/" not in text:
        fail(".gitignore must ignore OpenSVF local results/ output")

    evidence_patterns = [
        "execution/evidence/*.json",
        "execution/evidence/",
        "poc_runtime_ping_smoke_report.json",
    ]

    if not any(pattern in text for pattern in evidence_patterns):
        fail(".gitignore must ignore generated execution evidence JSON outputs")


def validate_campaign() -> None:
    campaign = load_yaml(CAMPAIGN)

    if campaign.get("campaign") != "Stage 6.3 OpenSVF Runtime Ping Smoke":
        fail("campaign name mismatch")

    spacecraft_ref = campaign.get("spacecraft")
    if spacecraft_ref != "../opensvf/poc_spacecraft_runtime_smoke.yaml":
        fail("campaign must reference ../opensvf/poc_spacecraft_runtime_smoke.yaml")

    procedures = campaign.get("procedures")
    if procedures != ["../procedures/poc_runtime_ping_smoke.py"]:
        fail("campaign must reference ../procedures/poc_runtime_ping_smoke.py")

    requirements = campaign.get("requirements")
    if requirements != ["OF-STAGE6-3-RUNTIME-SMOKE"]:
        fail("campaign requirements mismatch")


def validate_spacecraft() -> None:
    spacecraft = load_yaml(SPACECRAFT)

    simulation = spacecraft.get("simulation")
    if not isinstance(simulation, dict):
        fail("spacecraft must define simulation mapping")

    if simulation.get("realtime") is not True:
        fail("Stage 6.3 runtime smoke requires simulation.realtime: true")

    dt = simulation.get("dt")
    if not isinstance(dt, (int, float)) or dt <= 0:
        fail("simulation.dt must be a positive number")

    stop_time = simulation.get("stop_time")
    if not isinstance(stop_time, (int, float)) or stop_time < 5.0:
        fail("simulation.stop_time must be at least 5.0 seconds")

    obsw = spacecraft.get("obsw")
    if not isinstance(obsw, dict):
        fail("spacecraft must define obsw mapping")

    if obsw.get("type") != "pipe":
        fail("Stage 6.3 must use OpenSVF pipe mode")

    binary = str(obsw.get("binary", ""))
    if "build_stage4_orbitfabric/sim/obsw_sim" not in binary:
        fail("obsw.binary must point to the OrbitFabric-enabled OpenOBSW obsw_sim")

    forbidden_keys = {"srdb", "xtce", "mdb", "yamcs"}
    present_forbidden = forbidden_keys.intersection(obsw.keys())
    if present_forbidden:
        fail(f"obsw contains unsupported keys: {sorted(present_forbidden)}")


def validate_procedure() -> None:
    text = PROCEDURE.read_text()

    required_fragments = [
        "class A01_PusPingClosedLoopSmoke",
        'id = "OF-STAGE6-3-PING-SMOKE"',
        'requirement = "OF-STAGE6-3-RUNTIME-SMOKE"',
        "ctx.tc(17, 1, apid=0x001)",
        "ctx.expect_tm(1, 1",
        "ctx.expect_tm(17, 2",
        "ctx.expect_tm(1, 7",
    ]

    for fragment in required_fragments:
        if fragment not in text:
            fail(f"procedure missing required fragment: {fragment}")

    forbidden_fragments = [
        "LEGACY_TC_17_1",
        "HilAdapter",
        "ctx._master",
        "model.receive_tc",
        "ctx._log_event",
    ]

    for fragment in forbidden_fragments:
        if fragment in text:
            fail(f"procedure must use public API only; found forbidden fragment: {fragment}")


def validate_doc() -> None:
    text = DOC.read_text()

    required_fragments = [
        "Stage 6.3 OpenSVF Runtime Smoke",
        "simulation:",
        "realtime: true",
        "ctx.tc(17, 1, apid=0x001)",
        "TM(1,1)",
        "TM(17,2)",
        "TM(1,7)",
        "does not include",
        "custom bridge",
    ]

    for fragment in required_fragments:
        if fragment not in text:
            fail(f"document missing required fragment: {fragment}")


def validate_optional_evidence() -> None:
    if not OPTIONAL_EVIDENCE.exists():
        print("Stage 6.3 validation: optional evidence JSON not present, skipping evidence content check")
        return

    try:
        data = json.loads(OPTIONAL_EVIDENCE.read_text())
    except Exception as exc:
        fail(f"optional evidence JSON is invalid: {exc}")

    if data.get("campaign") != "Stage 6.3 OpenSVF Runtime Ping Smoke":
        fail("optional evidence campaign name mismatch")

    if data.get("pass_rate") != 1.0:
        fail("optional evidence must show pass_rate 1.0 when present")

    results = data.get("results")
    if not isinstance(results, list) or len(results) != 1:
        fail("optional evidence must contain exactly one procedure result")

    result = results[0]
    if result.get("id") != "OF-STAGE6-3-PING-SMOKE":
        fail("optional evidence procedure id mismatch")

    if result.get("verdict") != "PASS":
        fail("optional evidence procedure verdict must be PASS")


def main() -> int:
    for path in [DOC, CAMPAIGN, SPACECRAFT, PROCEDURE, GITIGNORE]:
        require_file(path)

    validate_gitignore()
    validate_campaign()
    validate_spacecraft()
    validate_procedure()
    validate_doc()
    validate_optional_evidence()

    print("Stage 6.3 OpenSVF runtime smoke validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
