#!/usr/bin/env python3
"""Stage 7.10e OpenSVF materialization acceptance."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


EXPECTED_ORBITFABRIC_COMMIT = "b1aa95408710f697b0ee144a7b41f2376395e01f"
EXPECTED_OPENSVF_COMMIT = "667d3eadcb0bbd7814ac324b99946c4ed2f11f23"

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


def _git_head(repo: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


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


class _FakeContext:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def tc(
        self,
        service: int,
        subservice: int,
        data: bytes = b"",
        apid: int | None = None,
    ) -> None:
        self.calls.append(("tc", service, subservice, data, apid))

    def expect_tm(
        self,
        service: int,
        subservice: int,
        timeout: float = 5.0,
    ) -> None:
        self.calls.append(("tm", service, subservice, timeout))


def _run_unit_tests() -> None:
    suite = unittest.defaultTestLoader.loadTestsFromName(
        "integration_package.tests.test_opensvf_materializer"
    )
    result = unittest.TextTestRunner(verbosity=0).run(suite)
    if not result.wasSuccessful():
        raise AssertionError("Stage 7.10e unit tests failed")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate deterministic Verification Projection Plan to OpenSVF "
            "materialization without executing the OBSW runtime."
        )
    )
    parser.add_argument("--orbitfabric-repo", required=True, type=Path)
    parser.add_argument("--opensvf-repo", required=True, type=Path)
    args = parser.parse_args()

    orbitfabric_repo = args.orbitfabric_repo.resolve()
    opensvf_repo = args.opensvf_repo.resolve()

    if _git_head(orbitfabric_repo) != EXPECTED_ORBITFABRIC_COMMIT:
        raise SystemExit("OrbitFabric checkout does not match Stage 7.10 baseline")
    if _git_head(opensvf_repo) != EXPECTED_OPENSVF_COMMIT:
        raise SystemExit("OpenSVF checkout does not match Stage 7.10 baseline")

    before_core = _git_status(orbitfabric_repo)
    before_svf = _git_status(opensvf_repo)

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

    from integration_package.adapter.opensvf_materializer import (
        CAMPAIGN_REL,
        MANIFEST_REL,
        PROCEDURE_REL,
        SPACECRAFT_REL,
        materialize_opensvf_plan,
    )
    from integration_package.adapter.verification_plan import (
        write_verification_projection_plan,
    )
    from integration_package.adapter.verification_projector import (
        project_verification_scenario,
    )

    with tempfile.TemporaryDirectory(prefix="stage7_10e_") as directory:
        root = Path(directory)

        input_set_dir = root / "core_input"
        result = write_integration_input_set(MISSION_DIR, input_set_dir)
        assert result.succeeded

        plan = project_verification_scenario(
            SCENARIO_PATH,
            result.manifest_path,
            PROFILE_PATH,
        )
        plan_path = root / "verification_projection_plan.json"
        write_verification_projection_plan(plan_path, plan)

        first = root / "bundle_first"
        second = root / "bundle_second"

        manifest = materialize_opensvf_plan(
            plan_path,
            SPACECRAFT_TEMPLATE,
            first,
        )
        materialize_opensvf_plan(
            plan_path,
            SPACECRAFT_TEMPLATE,
            second,
        )

        for relative in (
            PROCEDURE_REL,
            CAMPAIGN_REL,
            SPACECRAFT_REL,
            MANIFEST_REL,
        ):
            assert (first / relative).read_bytes() == (second / relative).read_bytes()

        procedure_text = (first / PROCEDURE_REL).read_text(encoding="utf-8")
        assert "apid=0x010" in procedure_text
        assert "apid=0x001" not in procedure_text
        assert "ctx.wait(" not in procedure_text
        assert "schedule_tc(" not in procedure_text

        for operation_id in ("op-0001", "op-0002", "op-0003", "op-0004"):
            assert operation_id in procedure_text

        assert (
            SPACECRAFT_TEMPLATE.read_bytes()
            == (first / SPACECRAFT_REL).read_bytes()
        )

        materialized_spacecraft = first / SPACECRAFT_REL
        spacecraft_payload = json.loads(
            json.dumps(
                __import__("yaml").safe_load(
                    materialized_spacecraft.read_text(encoding="utf-8")
                )
            )
        )
        runtime_binary = spacecraft_payload["obsw"]["binary"]
        assert runtime_binary == "../bin/obsw_sim"
        assert (
            materialized_spacecraft.parent / runtime_binary
        ).resolve() == (first / "bin" / "obsw_sim").resolve()

        runner = CampaignRunner.from_yaml(first / CAMPAIGN_REL)
        procedures = runner._procedures
        assert len(procedures) == 1

        procedure = procedures[0]()
        context = _FakeContext()
        procedure.run(context)

        assert context.calls == [
            ("tc", 17, 1, b"", 16),
            ("tm", 1, 1, 5.0),
            ("tm", 17, 2, 5.0),
            ("tm", 1, 7, 5.0),
        ]

        assert [step.step_name.split(":", 1)[0] for step in procedure._steps] == [
            "op-0001",
            "op-0002",
            "op-0003",
            "op-0004",
        ]

        stored_manifest = json.loads(
            (first / MANIFEST_REL).read_text(encoding="utf-8")
        )
        assert stored_manifest == manifest
        assert [
            item["plan_operation_id"]
            for item in stored_manifest["operation_trace"]
        ] == ["op-0001", "op-0002", "op-0003", "op-0004"]

        assert stored_manifest["execution_policy"] == {
            "tm_expectation_timeout_s": 5.0,
            "scenario_time_interpretation": "provenance_only",
        }

    _run_unit_tests()

    assert _git_status(orbitfabric_repo) == before_core
    assert _git_status(opensvf_repo) == before_svf

    print("Stage 7.10e OpenSVF materializer acceptance: PASS")
    print(f"  OrbitFabric reference: {EXPECTED_ORBITFABRIC_COMMIT}")
    print(f"  OpenSVF reference: {EXPECTED_OPENSVF_COMMIT}")
    print("  real Stage 7.10d plan production PASS")
    print("  executable_subset gate PASS")
    print("  deterministic OpenSVF bundle materialization PASS")
    print("  spacecraft template byte-copy PASS")
    print("  spacecraft runtime binary path resolves inside bundle PASS")
    print("  plan APID 0x010 -> generated ctx.tc APID 0x010 PASS")
    print("  plan TC(17,1) -> generated ctx.tc PASS")
    print("  3 plan TM obligations -> generated ctx.expect_tm PASS")
    print("  plan operation IDs -> native OpenSVF step names PASS")
    print("  scenario time remains provenance-only PASS")
    print("  CampaignRunner.from_yaml native procedure discovery PASS")
    print("  generated procedure dry execution against native class PASS")
    print("  materialization manifest traceability PASS")
    print("  repeated materialization byte stability PASS")
    print("  OrbitFabric and OpenSVF working trees remained unchanged PASS")
    print("  Stage 7.10e unit test suite PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
