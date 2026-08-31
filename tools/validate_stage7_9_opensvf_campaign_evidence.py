#!/usr/bin/env python3
"""Validate Stage 7.9 native OpenSVF campaign execution and verification evidence."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import validate_stage7_7_host_sim_runtime as stage77


EXPECTED_POC_BASE_COMMIT = "8cbd1e0254ef6566d093b774f22817c296b498ed"
EXPECTED_OPENOBSW_COMMIT = "44ceb71a016f0541ff7a0aa74191e13bafdb59c1"
EXPECTED_OPENSVF_COMMIT = "667d3eadcb0bbd7814ac324b99946c4ed2f11f23"

EXPECTED_CAMPAIGN = "OrbitFabric Stage 7.9 Native OpenSVF Verification"
EXPECTED_PROCEDURE = "OF-STAGE7-9-PING"
EXPECTED_REQUIREMENT = "POC-S79-001"

CAMPAIGN_ASSETS = (
    Path("execution/campaigns/stage7_9_native_campaign.yaml"),
    Path("execution/opensvf/stage7_9_spacecraft.yaml"),
    Path("execution/procedures/stage7_9_ping_procedure.py"),
)


def _git_status(repo: Path) -> str:
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def _git_is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "merge-base",
            "--is-ancestor",
            ancestor,
            descendant,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def _load_campaign_runner(opensvf_repo: Path):
    opensvf_src = str((opensvf_repo / "src").resolve())
    if opensvf_src not in sys.path:
        sys.path.insert(0, opensvf_src)

    from svf.campaign.campaign_runner import CampaignRunner

    return CampaignRunner


def _copy_campaign_assets(poc_repo: Path, workspace: Path) -> None:
    for relative in CAMPAIGN_ASSETS:
        source = poc_repo / relative
        if not source.is_file():
            raise RuntimeError(f"Stage 7.9 campaign asset not found: {source}")

        destination = workspace / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build the OrbitFabric-derived OpenOBSW host simulator, execute it "
            "through the native OpenSVF CampaignRunner, and validate the native "
            "machine-readable campaign evidence."
        )
    )
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--openobsw-repo", required=True, type=Path)
    parser.add_argument("--opensvf-repo", required=True, type=Path)
    parser.add_argument(
        "--evidence-output",
        type=Path,
        default=Path("/tmp/orbitfabric_stage7_9_campaign_report.json"),
    )
    args = parser.parse_args()

    poc_repo = Path(__file__).resolve().parents[1]
    bundle = args.bundle.resolve()
    openobsw_repo = args.openobsw_repo.resolve()
    opensvf_repo = args.opensvf_repo.resolve()
    evidence_output = args.evidence_output.resolve()

    poc_head = stage77._git_head(poc_repo)
    if not _git_is_ancestor(
        poc_repo,
        EXPECTED_POC_BASE_COMMIT,
        poc_head,
    ):
        raise SystemExit(
            "PoC checkout is not based on the merged Stage 7.5-7.8 reference "
            f"{EXPECTED_POC_BASE_COMMIT}; got {poc_head}"
        )

    actual_openobsw = stage77._git_head(openobsw_repo)
    if actual_openobsw != EXPECTED_OPENOBSW_COMMIT:
        raise SystemExit(
            "OpenOBSW checkout does not match the Stage 7.9 reference "
            f"{EXPECTED_OPENOBSW_COMMIT}; got {actual_openobsw}"
        )

    actual_opensvf = stage77._git_head(opensvf_repo)
    if actual_opensvf != EXPECTED_OPENSVF_COMMIT:
        raise SystemExit(
            "OpenSVF checkout does not match the Stage 7.9 reference "
            f"{EXPECTED_OPENSVF_COMMIT}; got {actual_opensvf}"
        )

    contract_dir = bundle / "flight_software"
    contract_path = contract_dir / "mission_contract.h"
    contribution_dir = bundle / "obsw_srdb_contribution"

    if not contract_path.is_file():
        raise SystemExit(f"Stage 7.4 flight contract not found: {contract_path}")

    if not contribution_dir.is_dir():
        raise SystemExit(
            f"Stage 7.4 SRDB contribution not found: {contribution_dir}"
        )

    before_srdb = stage77._source_fingerprints(openobsw_repo)
    before_openobsw_status = _git_status(openobsw_repo)
    before_opensvf_status = _git_status(opensvf_repo)

    (
        SRDBLoader,
        SRDBContributionLoader,
        SRDBComposer,
        SRDBMaterializer,
    ) = stage77._load_target_api(openobsw_repo)

    base = SRDBLoader.load(openobsw_repo / "srdb" / "data")
    contribution = SRDBContributionLoader.load(contribution_dir)
    composed = SRDBComposer.compose(base, [contribution])

    CampaignRunner = _load_campaign_runner(opensvf_repo)

    evidence_output.parent.mkdir(parents=True, exist_ok=True)
    if evidence_output.exists():
        evidence_output.unlink()

    with tempfile.TemporaryDirectory(
        prefix="stage7_9_opensvf_campaign_"
    ) as raw:
        root = Path(raw)
        assembled_dir = root / "assembled_srdb"
        build_dir = root / "build"
        campaign_workspace = root / "campaign_workspace"

        SRDBMaterializer.write(composed, assembled_dir)

        reloaded = SRDBLoader.load(assembled_dir)
        assert reloaded == composed
        assert reloaded.parameter_by_id(0x6001).name == "eps_obc_bus_voltage_mv"
        assert reloaded.hk_set_by_id(5).name == "obc_hk"
        assert (
            reloaded.event_by_id(0x5001).name
            == "eps_voltage_out_of_bounds"
        )

        stage77._run(
            [
                "cmake",
                "-S",
                str(openobsw_repo),
                "-B",
                str(build_dir),
                "-DOBSW_BUILD_TESTS=OFF",
                "-DOBSW_BUILD_SIM=ON",
                "-DOBSW_ENABLE_ORBITFABRIC_CONTRACT=ON",
                f"-DORBITFABRIC_CONTRACT_DIR={contract_dir}",
                f"-DSRDB_DATA_DIR={assembled_dir}",
                f"-DPython3_EXECUTABLE={sys.executable}",
            ],
            label="OpenOBSW host-sim configure for Stage 7.9 campaign",
        )

        stage77._run(
            [
                "cmake",
                "--build",
                str(build_dir),
                "--target",
                "obsw_sim",
            ],
            label="OpenOBSW host-sim build for Stage 7.9 campaign",
        )

        sim_binary = build_dir / "sim" / "obsw_sim"
        assert sim_binary.is_file()

        _copy_campaign_assets(poc_repo, campaign_workspace)

        runtime_binary = campaign_workspace / "bin" / "obsw_sim"
        runtime_binary.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(sim_binary, runtime_binary)

        assert runtime_binary.is_file()
        assert os.access(runtime_binary, os.X_OK)

        campaign_path = (
            campaign_workspace
            / "execution"
            / "campaigns"
            / "stage7_9_native_campaign.yaml"
        )

        runner = CampaignRunner.from_yaml(campaign_path)

        assert runner._campaign_name == EXPECTED_CAMPAIGN
        assert runner._declared_requirements == [EXPECTED_REQUIREMENT]
        assert len(runner._procedures) == 1
        assert (
            runner._procedures[0].__name__
            == "A01_OrbitFabricPingVerification"
        )

        previous_cwd = Path.cwd()
        try:
            os.chdir(campaign_workspace)
            report = runner.run(output_path=evidence_output)
        finally:
            os.chdir(previous_cwd)

        assert report.campaign_name == EXPECTED_CAMPAIGN
        assert report.n_procedures == 1
        assert report.n_pass == 1
        assert report.n_fail == 0
        assert report.n_error == 0
        assert report.n_inconclusive == 0
        assert report.pass_rate == 1.0
        assert report.declared_requirements == [EXPECTED_REQUIREMENT]
        assert report.uncovered_requirements == []

        assert len(report.results) == 1
        procedure_result = report.results[0]

        assert procedure_result.procedure_id == EXPECTED_PROCEDURE
        assert procedure_result.requirement == EXPECTED_REQUIREMENT
        assert procedure_result.verdict.value == "PASS"
        assert procedure_result.error is None

        assert len(procedure_result.steps) == 4
        assert all(
            step.verdict.value == "PASS"
            for step in procedure_result.steps
        )

        assert evidence_output.is_file()

        evidence = json.loads(
            evidence_output.read_text(encoding="utf-8")
        )

        assert evidence["campaign"] == EXPECTED_CAMPAIGN
        assert evidence["n_procedures"] == 1
        assert evidence["pass_rate"] == 1.0
        assert evidence["declared_requirements"] == [EXPECTED_REQUIREMENT]
        assert evidence["uncovered_requirements"] == []

        assert len(evidence["results"]) == 1
        evidence_result = evidence["results"][0]

        assert evidence_result["id"] == EXPECTED_PROCEDURE
        assert evidence_result["requirement"] == EXPECTED_REQUIREMENT
        assert evidence_result["verdict"] == "PASS"
        assert evidence_result["error"] is None

        evidence_steps = evidence_result["steps"]
        assert len(evidence_steps) == 4
        assert all(step["verdict"] == "PASS" for step in evidence_steps)

    after_srdb = stage77._source_fingerprints(openobsw_repo)
    after_openobsw_status = _git_status(openobsw_repo)
    after_opensvf_status = _git_status(opensvf_repo)

    assert (
        after_srdb == before_srdb
    ), "OpenOBSW srdb/data was mutated by the Stage 7.9 workflow"

    assert (
        after_openobsw_status == before_openobsw_status
    ), "OpenOBSW working tree changed during Stage 7.9 execution"

    assert (
        after_opensvf_status == before_opensvf_status
    ), "OpenSVF working tree changed during Stage 7.9 execution"

    print("Stage 7.9 OpenSVF campaign evidence acceptance: PASS")
    print(f"  bundle: {bundle}")
    print(f"  PoC base reference: {EXPECTED_POC_BASE_COMMIT}")
    print(f"  OpenOBSW reference: {EXPECTED_OPENOBSW_COMMIT}")
    print(f"  OpenSVF reference: {EXPECTED_OPENSVF_COMMIT}")
    print("  OrbitFabric artifacts -> full OpenOBSW host-sim build PASS")
    print("  native OpenSVF CampaignRunner execution PASS")
    print("  native Procedure TC(17,1) -> TM(17,2) verification PASS")
    print("  POC-S79-001 requirement coverage PASS")
    print("  native campaign PASS verdict PASS")
    print("  step-level machine-readable evidence PASS")
    print(f"  campaign report JSON: {evidence_output}")
    print("  OpenOBSW srdb/data remained byte-identical PASS")
    print("  OpenOBSW and OpenSVF working trees remained unchanged PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())