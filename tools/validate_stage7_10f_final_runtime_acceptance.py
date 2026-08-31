#!/usr/bin/env python3
"""Stage 7.10f final runtime acceptance for verification projection."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

import validate_stage7_7_host_sim_runtime as stage77


EXPECTED_POC_BASE_COMMIT = "f51ef00de850600bd319319f8a917febb5ad6d41"
EXPECTED_ORBITFABRIC_COMMIT = "b1aa95408710f697b0ee144a7b41f2376395e01f"
EXPECTED_OPENOBSW_COMMIT = "44ceb71a016f0541ff7a0aa74191e13bafdb59c1"
EXPECTED_OPENSVF_COMMIT = "667d3eadcb0bbd7814ac324b99946c4ed2f11f23"

EXPECTED_SCENARIO_ID = "stage7_10_ping_verification"
EXPECTED_OPERATION_IDS = ["op-0001", "op-0002", "op-0003", "op-0004"]

REPO_ROOT = Path(__file__).resolve().parents[1]
MISSION_DIR = REPO_ROOT / "orbitfabric_models" / "mission"
SCENARIO_PATH = (
    REPO_ROOT
    / "orbitfabric_models"
    / "scenarios"
    / "stage7_10_ping_verification.yaml"
)
PROFILE_PATH = REPO_ROOT / "projection_profiles" / "poc_openobsw_opensvf.yaml"
SPACECRAFT_TEMPLATE = (
    REPO_ROOT / "execution" / "opensvf" / "stage7_10_spacecraft.yaml"
)


def _git_status(repo: Path) -> str:
    return subprocess.run(
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
    ).stdout


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


def _load_native_apis(
    orbitfabric_repo: Path,
    opensvf_repo: Path,
) -> tuple[object, object]:
    for source_root in (
        orbitfabric_repo / "src",
        opensvf_repo / "src",
        REPO_ROOT,
    ):
        value = str(source_root.resolve())
        if value not in sys.path:
            sys.path.insert(0, value)

    from orbitfabric.export.integration_input_set import write_integration_input_set
    from svf.campaign.campaign_runner import CampaignRunner

    return write_integration_input_set, CampaignRunner


def _find_obsw_sim(build_dir: Path) -> Path:
    preferred = build_dir / "sim" / "obsw_sim"
    if preferred.is_file():
        return preferred.resolve()

    candidates = sorted(
        (path.resolve() for path in build_dir.rglob("obsw_sim") if path.is_file()),
        key=lambda item: item.as_posix(),
    )
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise RuntimeError(
            f"OpenOBSW build completed but obsw_sim was not found under {build_dir}"
        )
    raise RuntimeError(
        "OpenOBSW build produced multiple unexpected obsw_sim candidates: "
        + ", ".join(str(path) for path in candidates)
    )


def _copy_runtime_binary(sim_binary: Path, runtime_bundle: Path) -> Path:
    destination = runtime_bundle / "bin" / sim_binary.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(sim_binary, destination)
    if os.name != "nt":
        destination.chmod(destination.stat().st_mode | 0o111)
    return destination


def _assert_report_traceability(
    *,
    report: object,
    evidence: dict,
    plan: dict,
    materialization_manifest: dict,
) -> None:
    assert report.n_procedures == 1
    assert report.n_pass == 1
    assert report.n_fail == 0
    assert report.n_error == 0
    assert report.n_inconclusive == 0
    assert report.pass_rate == 1.0
    assert report.declared_requirements == []
    assert report.uncovered_requirements == []

    assert len(report.results) == 1
    result = report.results[0]
    assert result.verdict.value == "PASS"
    assert result.error is None
    assert result.requirement == ""
    assert len(result.steps) == 4
    assert all(step.verdict.value == "PASS" for step in result.steps)

    report_step_ids = [
        step.step_name.split(":", 1)[0]
        for step in result.steps
    ]
    assert report_step_ids == EXPECTED_OPERATION_IDS

    plan_operation_ids = [item["id"] for item in plan["operations"]]
    assert plan_operation_ids == EXPECTED_OPERATION_IDS

    manifest_operation_ids = [
        item["plan_operation_id"]
        for item in materialization_manifest["operation_trace"]
    ]
    assert manifest_operation_ids == EXPECTED_OPERATION_IDS

    assert evidence["n_procedures"] == 1
    assert evidence["pass_rate"] == 1.0
    assert evidence["declared_requirements"] == []
    assert evidence["uncovered_requirements"] == []
    assert len(evidence["results"]) == 1

    evidence_result = evidence["results"][0]
    assert evidence_result["verdict"] == "PASS"
    assert evidence_result["error"] is None
    assert evidence_result["requirement"] == ""

    evidence_steps = evidence_result["steps"]
    assert len(evidence_steps) == 4
    assert all(step["verdict"] == "PASS" for step in evidence_steps)
    evidence_step_ids = [
        step["name"].split(":", 1)[0]
        for step in evidence_steps
    ]
    assert evidence_step_ids == EXPECTED_OPERATION_IDS


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Regenerate the OrbitFabric flight and verification projections from "
            "one Core Integration Input Set, build the OrbitFabric-derived "
            "OpenOBSW host simulator, execute the generated OpenSVF campaign, "
            "and validate native step-level runtime evidence."
        )
    )
    parser.add_argument("--orbitfabric-repo", required=True, type=Path)
    parser.add_argument("--openobsw-repo", required=True, type=Path)
    parser.add_argument("--opensvf-repo", required=True, type=Path)
    parser.add_argument(
        "--evidence-output",
        type=Path,
        default=Path(tempfile.gettempdir())
        / "orbitfabric_stage7_10_campaign_report.json",
    )
    args = parser.parse_args()

    if os.name == "nt":
        raise SystemExit(
            "Stage 7.10f runtime acceptance must run in a downstream-supported "
            "Linux/WSL2 environment. Stages 7.10a-e remain host-platform independent."
        )

    orbitfabric_repo = args.orbitfabric_repo.resolve()
    openobsw_repo = args.openobsw_repo.resolve()
    opensvf_repo = args.opensvf_repo.resolve()
    evidence_output = args.evidence_output.resolve()

    poc_head = stage77._git_head(REPO_ROOT)
    if not _git_is_ancestor(REPO_ROOT, EXPECTED_POC_BASE_COMMIT, poc_head):
        raise SystemExit(
            "PoC checkout is not based on the merged Stage 7.9 reference "
            f"{EXPECTED_POC_BASE_COMMIT}; got {poc_head}"
        )

    if stage77._git_head(orbitfabric_repo) != EXPECTED_ORBITFABRIC_COMMIT:
        raise SystemExit("OrbitFabric checkout does not match Stage 7.10 baseline")
    if stage77._git_head(openobsw_repo) != EXPECTED_OPENOBSW_COMMIT:
        raise SystemExit("OpenOBSW checkout does not match Stage 7.10 baseline")
    if stage77._git_head(opensvf_repo) != EXPECTED_OPENSVF_COMMIT:
        raise SystemExit("OpenSVF checkout does not match Stage 7.10 baseline")

    before_poc_status = _git_status(REPO_ROOT)
    before_core_status = _git_status(orbitfabric_repo)
    before_openobsw_status = _git_status(openobsw_repo)
    before_opensvf_status = _git_status(opensvf_repo)
    before_srdb = stage77._source_fingerprints(openobsw_repo)

    write_integration_input_set, CampaignRunner = _load_native_apis(
        orbitfabric_repo,
        opensvf_repo,
    )

    from integration_package.adapter.opensvf_materializer import (
        CAMPAIGN_REL,
        MANIFEST_REL,
        materialize_opensvf_plan,
    )
    from integration_package.adapter.preflight import run_project
    from integration_package.adapter.verification_plan import (
        write_verification_projection_plan,
    )
    from integration_package.adapter.verification_projector import (
        project_verification_scenario,
    )

    (
        SRDBLoader,
        SRDBContributionLoader,
        SRDBComposer,
        SRDBMaterializer,
    ) = stage77._load_target_api(openobsw_repo)

    evidence_output.parent.mkdir(parents=True, exist_ok=True)
    if evidence_output.exists():
        evidence_output.unlink()

    with tempfile.TemporaryDirectory(prefix="stage7_10f_runtime_") as directory:
        root = Path(directory)
        input_set_dir = root / "core_input"
        flight_projection_dir = root / "flight_projection"
        assembled_srdb_dir = root / "assembled_srdb"
        build_dir = root / "openobsw_build"
        runtime_bundle = root / "runtime_bundle"

        # One authoritative Core Integration Input Set feeds both downstream branches.
        input_result = write_integration_input_set(MISSION_DIR, input_set_dir)
        assert input_result.succeeded

        flight_result = run_project(
            input_result.manifest_path,
            PROFILE_PATH,
            output_dir=flight_projection_dir,
        )
        assert flight_result["result"] == "succeeded"

        plan = project_verification_scenario(
            SCENARIO_PATH,
            input_result.manifest_path,
            PROFILE_PATH,
        )
        assert plan["status"] == "executable_subset"
        assert plan["source"]["scenario_id"] == EXPECTED_SCENARIO_ID
        assert [item["id"] for item in plan["operations"]] == EXPECTED_OPERATION_IDS

        # Both branches must prove they consumed the exact same Core input and Profile.
        core_sha = plan["core_input"]["input_set_sha256"]
        profile_sha = plan["profile"]["sha256"]
        assert (
            flight_result["inputs"]["core_input_set"]["sha256"]
            == core_sha
        )
        assert flight_result["inputs"]["profile"]["sha256"] == profile_sha

        plan_path = root / "verification_projection_plan.json"
        write_verification_projection_plan(plan_path, plan)

        # Compose the target-owned OpenOBSW SRDB using the freshly generated contribution.
        base = SRDBLoader.load(openobsw_repo / "srdb" / "data")
        contribution = SRDBContributionLoader.load(
            flight_projection_dir / "obsw_srdb_contribution"
        )
        composed = SRDBComposer.compose(base, [contribution])
        SRDBMaterializer.write(composed, assembled_srdb_dir)
        assert SRDBLoader.load(assembled_srdb_dir) == composed

        contract_dir = flight_projection_dir / "flight_software"
        contract_path = contract_dir / "mission_contract.h"
        assert contract_path.is_file()

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
                f"-DSRDB_DATA_DIR={assembled_srdb_dir}",
                f"-DPython3_EXECUTABLE={sys.executable}",
            ],
            label="OpenOBSW host-sim configure for Stage 7.10f",
        )

        stage77._run(
            [
                "cmake",
                "--build",
                str(build_dir),
                "--target",
                "obsw_sim",
            ],
            label="OpenOBSW host-sim build for Stage 7.10f",
        )

        sim_binary = _find_obsw_sim(build_dir)

        materialization_manifest = materialize_opensvf_plan(
            plan_path,
            SPACECRAFT_TEMPLATE,
            runtime_bundle,
        )

        runtime_binary = _copy_runtime_binary(sim_binary, runtime_bundle)
        assert runtime_binary.is_file()

        materialized_spacecraft = (
            runtime_bundle / materialization_manifest["spacecraft"]["path"]
        )
        spacecraft_payload = yaml.safe_load(
            materialized_spacecraft.read_text(encoding="utf-8")
        )
        configured_binary = (
            materialized_spacecraft.parent
            / spacecraft_payload["obsw"]["binary"]
        ).resolve()
        assert configured_binary == runtime_binary.resolve()

        assert materialization_manifest["source_plan"]["scenario_id"] == (
            EXPECTED_SCENARIO_ID
        )
        assert [
            item["plan_operation_id"]
            for item in materialization_manifest["operation_trace"]
        ] == EXPECTED_OPERATION_IDS

        campaign_path = runtime_bundle / CAMPAIGN_REL
        runner = CampaignRunner.from_yaml(campaign_path)
        assert len(runner._procedures) == 1
        assert runner._declared_requirements == []

        previous_cwd = Path.cwd()
        try:
            os.chdir(runtime_bundle)
            report = runner.run(output_path=evidence_output)
        finally:
            os.chdir(previous_cwd)

        assert evidence_output.is_file()
        evidence = json.loads(evidence_output.read_text(encoding="utf-8"))

        _assert_report_traceability(
            report=report,
            evidence=evidence,
            plan=plan,
            materialization_manifest=materialization_manifest,
        )

        manifest_on_disk = json.loads(
            (runtime_bundle / MANIFEST_REL).read_text(encoding="utf-8")
        )
        assert manifest_on_disk == materialization_manifest

    after_srdb = stage77._source_fingerprints(openobsw_repo)
    after_poc_status = _git_status(REPO_ROOT)
    after_core_status = _git_status(orbitfabric_repo)
    after_openobsw_status = _git_status(openobsw_repo)
    after_opensvf_status = _git_status(opensvf_repo)

    assert after_srdb == before_srdb, (
        "OpenOBSW srdb/data changed during Stage 7.10f"
    )
    assert after_poc_status == before_poc_status, (
        "PoC working tree changed during Stage 7.10f"
    )
    assert after_core_status == before_core_status, (
        "OrbitFabric working tree changed during Stage 7.10f"
    )
    assert after_openobsw_status == before_openobsw_status, (
        "OpenOBSW working tree changed during Stage 7.10f"
    )
    assert after_opensvf_status == before_opensvf_status, (
        "OpenSVF working tree changed during Stage 7.10f"
    )

    print("Stage 7.10f final runtime acceptance: PASS")
    print(f"  PoC base reference: {EXPECTED_POC_BASE_COMMIT}")
    print(f"  OrbitFabric reference: {EXPECTED_ORBITFABRIC_COMMIT}")
    print(f"  OpenOBSW reference: {EXPECTED_OPENOBSW_COMMIT}")
    print(f"  OpenSVF reference: {EXPECTED_OPENSVF_COMMIT}")
    print("  one Core Integration Input Set -> both downstream branches PASS")
    print("  one Projection Profile -> both downstream branches PASS")
    print("  flight contract + SRDB contribution regeneration PASS")
    print("  verification projection plan regeneration PASS")
    print("  target-owned SRDB composition/materialization PASS")
    print("  full OrbitFabric-derived OpenOBSW obsw_sim build PASS")
    print(f"  runtime simulator: {sim_binary}")
    print("  generated OpenSVF campaign/procedure materialization PASS")
    print("  runtime spacecraft -> packaged obsw_sim path resolution PASS")
    print("  plan APID 0x010 -> native runtime TC(17,1) PASS")
    print("  native TM(1,1) obligation PASS")
    print("  native TM(17,2) obligation PASS")
    print("  native TM(1,7) obligation PASS")
    print("  op-0001 .. op-0004 native CampaignReport traceability PASS")
    print("  native campaign PASS verdict PASS")
    print("  no OrbitFabric requirement semantics invented PASS")
    print("  scenario time remained provenance-only PASS")
    print(f"  native campaign report JSON: {evidence_output}")
    print("  OpenOBSW srdb/data remained byte-identical PASS")
    print("  PoC/Core/OpenOBSW/OpenSVF working trees remained unchanged PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
