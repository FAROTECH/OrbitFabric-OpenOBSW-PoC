#!/usr/bin/env python3
"""Run native OpenSVF verification from artifacts produced through the G4 CLI boundary."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

import validate_stage7_7_host_sim_runtime as stage77
from validate_stage7_10f_final_runtime_acceptance import (
    EXPECTED_OPENOBSW_COMMIT,
    EXPECTED_OPENSVF_COMMIT,
    EXPECTED_OPERATION_IDS,
    EXPECTED_SCENARIO_ID,
    _assert_report_traceability,
    _copy_runtime_binary,
    _find_obsw,
)


def _git_status(repo: Path) -> str:
    return stage77._run(
        ["git", "-C", str(repo), "status", "--porcelain=v1", "--untracked-files=all"],
        label=f"git status {repo}",
    ).stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-output", required=True, type=Path)
    parser.add_argument("--verification-output", required=True, type=Path)
    parser.add_argument("--openobsw-repo", required=True, type=Path)
    parser.add_argument("--opensvf-repo", required=True, type=Path)
    parser.add_argument("--campaign-evidence", required=True, type=Path)
    args = parser.parse_args()

    project_output = args.project_output.resolve()
    verification_output = args.verification_output.resolve()
    openobsw_repo = args.openobsw_repo.resolve()
    opensvf_repo = args.opensvf_repo.resolve()
    campaign_evidence = args.campaign_evidence.resolve()

    if stage77._git_head(openobsw_repo) != EXPECTED_OPENOBSW_COMMIT:
        raise SystemExit("OpenOBSW checkout does not match the Stage 7.10 reference")
    if stage77._git_head(opensvf_repo) != EXPECTED_OPENSVF_COMMIT:
        raise SystemExit("OpenSVF checkout does not match the Stage 7.10 reference")

    project_result = json.loads(
        (project_output / "integration_result.json").read_text(encoding="utf-8")
    )
    verification_result = json.loads(
        (verification_output / "integration_result.json").read_text(encoding="utf-8")
    )
    plan_path = (
        verification_output
        / "verification_projection"
        / "verification_projection_plan.json"
    )
    runtime_bundle = verification_output / "verification_projection" / "opensvf"
    materialization_path = runtime_bundle / "materialization_manifest.json"
    campaign_path = runtime_bundle / "campaigns" / "verification_projection_campaign.yaml"

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    materialization = json.loads(materialization_path.read_text(encoding="utf-8"))

    assert project_result["result"] == "succeeded"
    assert project_result["operation"] == {"id": "project"}
    assert verification_result["result"] == "succeeded"
    assert verification_result["operation"] == {"id": "verification_projection"}
    assert project_result["inputs"]["core_input_set"]["sha256"] == (
        verification_result["inputs"]["core_input_set"]["sha256"]
    )
    assert project_result["inputs"]["profile"]["sha256"] == (
        verification_result["inputs"]["profile"]["sha256"]
    )

    consumed = verification_result["inputs"]["operation_inputs"]
    assert len(consumed) == 1
    assert consumed[0]["role"] == "scenario"
    assert consumed[0]["status"] == "available"
    assert consumed[0]["id"] == EXPECTED_SCENARIO_ID
    assert consumed[0]["sha256"] == plan["source"]["scenario_sha256"]
    assert [item["id"] for item in plan["operations"]] == EXPECTED_OPERATION_IDS
    assert [item["plan_operation_id"] for item in materialization["operation_trace"]] == (
        EXPECTED_OPERATION_IDS
    )

    before_openobsw = _git_status(openobsw_repo)
    before_opensvf = _git_status(opensvf_repo)
    before_srdb = stage77._source_fingerprints(openobsw_repo)

    for source_root in (opensvf_repo / "src", Path(__file__).resolve().parents[1]):
        value = str(source_root.resolve())
        if value not in sys.path:
            sys.path.insert(0, value)
    from svf.campaign.campaign_runner import CampaignRunner

    SRDBLoader, SRDBContributionLoader, SRDBComposer, SRDBMaterializer = (
        stage77._load_target_api(openobsw_repo)
    )

    with tempfile.TemporaryDirectory(prefix="orbitfabric_g4_native_") as directory:
        root = Path(directory)
        assembled_srdb = root / "assembled_srdb"
        build_dir = root / "openobsw_build"

        base = SRDBLoader.load(openobsw_repo / "srdb" / "data")
        contribution = SRDBContributionLoader.load(
            project_output / "obsw_srdb_contribution"
        )
        composed = SRDBComposer.compose(base, [contribution])
        SRDBMaterializer.write(composed, assembled_srdb)
        assert SRDBLoader.load(assembled_srdb) == composed

        contract_dir = project_output / "flight_software"
        assert (contract_dir / "mission_contract.h").is_file()

        stage77._run(
            [
                "cmake",
                "-S",
                str(openobsw_repo),
                "-B",
                str(build_dir),
                "-G",
                "Ninja",
                "-DCMAKE_BUILD_TYPE=Release",
                "-DOBSW_BUILD_TESTS=OFF",
                "-DOBSW_BUILD_SIM=ON",
                "-DOBSW_ENABLE_ORBITFABRIC_CONTRACT=ON",
                f"-DORBITFABRIC_CONTRACT_DIR={contract_dir}",
                f"-DSRDB_DATA_DIR={assembled_srdb}",
                f"-DPython3_EXECUTABLE={sys.executable}",
            ],
            label="OpenOBSW G4 native configure",
        )
        stage77._run(
            ["cmake", "--build", str(build_dir), "--target", "obsw_sim"],
            label="OpenOBSW G4 native build",
        )
        sim_binary = _find_obsw(build_dir)
        runtime_binary = _copy_runtime_binary(sim_binary, runtime_bundle)

        spacecraft = yaml.safe_load(
            (runtime_bundle / materialization["spacecraft"]["path"]).read_text(
                encoding="utf-8"
            )
        )
        configured_binary = (
            (runtime_bundle / materialization["spacecraft"]["path"]).parent
            / spacecraft["obsw"]["binary"]
        ).resolve()
        assert configured_binary == runtime_binary.resolve()

        campaign_evidence.parent.mkdir(parents=True, exist_ok=True)
        if campaign_evidence.exists():
            campaign_evidence.unlink()
        runner = CampaignRunner.from_yaml(campaign_path)
        previous_cwd = Path.cwd()
        try:
            os.chdir(runtime_bundle)
            report = runner.run(output_path=campaign_evidence)
        finally:
            os.chdir(previous_cwd)

    evidence = json.loads(campaign_evidence.read_text(encoding="utf-8"))
    _assert_report_traceability(
        report=report,
        evidence=evidence,
        plan=plan,
        materialization_manifest=materialization,
    )

    assert stage77._source_fingerprints(openobsw_repo) == before_srdb
    assert _git_status(openobsw_repo) == before_openobsw
    assert _git_status(opensvf_repo) == before_opensvf

    print("G4 operation-input native OpenSVF acceptance: PASS")
    print("  installed G4 project output -> OpenOBSW build PASS")
    print("  installed G4 verification_projection output -> OpenSVF campaign PASS")
    print("  exact Scenario consumed provenance -> plan -> campaign PASS")
    print("  op-0001 .. op-0004 native traceability PASS")
    print("  target source trees remained unchanged PASS")
    print(f"  campaign evidence: {campaign_evidence}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
