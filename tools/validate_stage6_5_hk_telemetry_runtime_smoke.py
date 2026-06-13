#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]

DOC = ROOT / "docs/stage6_5_hk_telemetry_runtime_smoke.md"
CAMPAIGN = ROOT / "execution/campaigns/poc_runtime_hk_smoke.yaml"
SPACECRAFT = ROOT / "execution/opensvf/poc_spacecraft_runtime_smoke.yaml"
PROCEDURE = ROOT / "execution/procedures/poc_runtime_hk_smoke.py"
OPTIONAL_EVIDENCE = ROOT / "execution/evidence/poc_runtime_hk_smoke_report.json"


def fail(message: str) -> None:
    print(f"Stage 6.5 validation: FAIL: {message}", file=sys.stderr)
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


def validate_campaign() -> None:
    campaign = load_yaml(CAMPAIGN)

    if campaign.get("campaign") != "Stage 6.5 OpenSVF HK Telemetry Runtime Smoke":
        fail("campaign name mismatch")

    if campaign.get("spacecraft") != "../opensvf/poc_spacecraft_runtime_smoke.yaml":
        fail("campaign must reuse ../opensvf/poc_spacecraft_runtime_smoke.yaml")

    if campaign.get("procedures") != ["../procedures/poc_runtime_hk_smoke.py"]:
        fail("campaign must reference ../procedures/poc_runtime_hk_smoke.py")

    if campaign.get("requirements") != ["OF-STAGE6-5-HK-RUNTIME-SMOKE"]:
        fail("campaign requirements mismatch")


def validate_spacecraft() -> None:
    spacecraft = load_yaml(SPACECRAFT)

    simulation = spacecraft.get("simulation")
    if not isinstance(simulation, dict):
        fail("spacecraft must define simulation mapping")

    if simulation.get("realtime") is not True:
        fail("Stage 6.5 runtime smoke requires simulation.realtime: true")

    stop_time = simulation.get("stop_time")
    if not isinstance(stop_time, (int, float)) or stop_time < 10.0:
        fail("simulation.stop_time must be at least 10.0 seconds for HK observation")

    obsw = spacecraft.get("obsw")
    if not isinstance(obsw, dict):
        fail("spacecraft must define obsw mapping")

    if obsw.get("type") != "pipe":
        fail("Stage 6.5 must use OpenSVF pipe mode")

    binary = str(obsw.get("binary", ""))
    if "build_stage4_orbitfabric/sim/obsw_sim" not in binary:
        fail("obsw.binary must point to the OrbitFabric-enabled OpenOBSW obsw_sim")


def validate_procedure() -> None:
    text = PROCEDURE.read_text()

    required_fragments = [
        "class A01_HkTelemetryRuntimeSmoke",
        'id = "OF-STAGE6-5-HK-SMOKE"',
        'requirement = "OF-STAGE6-5-HK-RUNTIME-SMOKE"',
        "ctx.expect_tm(3, 25",
        'store.read("dhs.obc.obt")',
        'ctx.assert_parameter("dhs.obc.obt", greater_than=0.0)',
    ]

    for fragment in required_fragments:
        if fragment not in text:
            fail(f"procedure missing required fragment: {fragment}")

    forbidden_fragments = [
        "ctx._master",
        "ctx._store",
        "ctx._log_event",
        "HilAdapter",
        "OBCEmulatorAdapter",
        "model.receive_tc",
    ]

    for fragment in forbidden_fragments:
        if fragment in text:
            fail(f"procedure must use public API only; found forbidden fragment: {fragment}")

    if "ctx.tc(3, 5" in text or "ctx.tc(3,5" in text:
        fail("Stage 6.5 smoke must observe auto-enabled HK, not enable HK via TC(3,5)")


def validate_doc() -> None:
    text = DOC.read_text()

    required_fragments = [
        "Stage 6.5 OpenSVF HK Telemetry Runtime Smoke",
        "OpenSVF OBCEmulatorAdapter",
        "OpenOBSW PUS Service 3 housekeeping tick",
        "TM(3,25)",
        "ctx.expect_tm(3, 25",
        "dhs.obc.obt",
        "ParameterStore",
        "Stage 6.5 does not include:",
        "full OrbitFabric housekeeping telemetry contract runtime validation",
        "eps.obc.bus_voltage_mv",
        "SRDB package/version-handshake cleanup",
        "obsw-srdb package not installed",
    ]

    for fragment in required_fragments:
        if fragment not in text:
            fail(f"document missing required fragment: {fragment}")


def validate_optional_evidence() -> None:
    if not OPTIONAL_EVIDENCE.exists():
        print("Stage 6.5 validation: optional evidence JSON not present, skipping evidence content check")
        return

    try:
        data = json.loads(OPTIONAL_EVIDENCE.read_text())
    except Exception as exc:
        fail(f"optional evidence JSON is invalid: {exc}")

    if data.get("campaign") != "Stage 6.5 OpenSVF HK Telemetry Runtime Smoke":
        fail("optional evidence campaign name mismatch")

    if data.get("pass_rate") != 1.0:
        fail("optional evidence must show pass_rate 1.0 when present")

    results = data.get("results")
    if not isinstance(results, list) or len(results) != 1:
        fail("optional evidence must contain exactly one procedure result")

    result = results[0]
    if result.get("id") != "OF-STAGE6-5-HK-SMOKE":
        fail("optional evidence procedure id mismatch")

    if result.get("verdict") != "PASS":
        fail("optional evidence procedure verdict must be PASS")


def main() -> int:
    for path in [DOC, CAMPAIGN, SPACECRAFT, PROCEDURE]:
        require_file(path)

    validate_campaign()
    validate_spacecraft()
    validate_procedure()
    validate_doc()
    validate_optional_evidence()

    print("Stage 6.5 HK telemetry runtime smoke validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
