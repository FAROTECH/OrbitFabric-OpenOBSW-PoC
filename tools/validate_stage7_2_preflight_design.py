#!/usr/bin/env python3
"""Validate the Stage 7.2 compatibility-preflight design resources."""

from __future__ import print_function

import hashlib
import json
import os
import re
import sys


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
BASELINE_PATH = os.path.join(
    REPO_ROOT,
    "docs",
    "design",
    "stage7_2_reference_target_baseline.example.json",
)
CASES_PATH = os.path.join(
    REPO_ROOT,
    "docs",
    "design",
    "stage7_2_preflight_cases.json",
)
DESIGN_PATH = os.path.join(REPO_ROOT, "docs", "stage7_2_compatibility_preflight_design.md")
PROPOSAL_PATH = os.path.join(
    REPO_ROOT,
    "docs",
    "design",
    "obsw_srdb_composition_boundary_proposal.md",
)


class DesignError(Exception):
    pass


def load_json(path):
    with open(path, "r", encoding="utf-8") as stream:
        return json.load(stream)


def load_text(path):
    with open(path, "r", encoding="utf-8") as stream:
        return stream.read()


def require(condition, message):
    if not condition:
        raise DesignError(message)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_no_typographic_dash(path, text):
    require("\u2013" not in text, "Typographic en dash found in {0}".format(path))
    require("\u2014" not in text, "Typographic em dash found in {0}".format(path))


def assert_unique(values, label):
    values = list(values)
    require(len(values) == len(set(values)), "Duplicate {0}".format(label))


def validate_baseline(baseline):
    require(
        baseline.get("kind") == "orbitfabric.openobsw_opensvf.target_baseline_design",
        "Unexpected baseline kind",
    )
    require(baseline.get("baseline_version") == "0.1-candidate", "Unexpected baseline version")
    require(baseline.get("status") == "design_only", "Baseline must remain design_only")
    require(
        baseline.get("id") == "openobsw-0.7.0-obsw-srdb-0.1.0-reference",
        "Unexpected baseline ID",
    )

    projection_target = baseline.get("projection_target", {})
    openobsw = projection_target.get("openobsw", {})
    obsw_srdb = projection_target.get("obsw_srdb", {})
    require(openobsw.get("version") == "0.7.0", "Unexpected OpenOBSW baseline version")
    require(obsw_srdb.get("version") == "0.1.0", "Unexpected obsw-srdb baseline version")
    require(
        openobsw.get("commit") == "b3b7c3fa9c6edd2a52eef356d113c1eae1b03fec",
        "Unexpected OpenOBSW baseline commit",
    )
    require(
        obsw_srdb.get("source_commit") == openobsw.get("commit"),
        "obsw-srdb baseline must be pinned to the same audited OpenOBSW commit",
    )

    contract = baseline.get("project_contract", {})
    require(contract.get("operation") == "project", "Baseline operation must be project")
    require(
        contract.get("handoff_mode") == "obsw_srdb_contribution_bundle",
        "Project must use contribution-bundle handoff",
    )
    require(
        contract.get("target_application") == "not_in_operation_scope",
        "Target application must stay outside project",
    )
    require(
        contract.get("complete_srdb_claim_allowed") is False,
        "Project must not claim a complete SRDB",
    )

    compatibility = baseline.get("project_compatibility", {})
    handoff = compatibility.get("srdb_handoff", {})
    contribution = handoff.get("contribution_bundle", {})
    composition = handoff.get("native_target_composition", {})

    require(contribution.get("supported") is True, "Contribution handoff must be supported")
    require(
        contribution.get("project_requirement") == "required",
        "Contribution handoff must be required for project",
    )
    require(contribution.get("complete_database") is False, "Contribution must not be complete DB")
    require(contribution.get("applied_to_target") is False, "Contribution must not claim application")
    require(
        contribution.get("semantic_manifest") == "integration_result.json",
        "Integration Result must remain semantic manifest",
    )

    require(
        composition.get("supported_by_audited_baseline") is False,
        "Audited baseline unexpectedly claims native composition",
    )
    require(
        composition.get("project_requirement") == "not_applicable",
        "Native target composition must not block project",
    )

    pus = compatibility.get("pus", {})
    tm_apid = pus.get("tm_apid", {}).get("value")
    tc_apid = pus.get("tc_reference_apid", {}).get("value")
    require(isinstance(tm_apid, int) and 0 <= tm_apid <= 0x7FE, "Invalid TM APID")
    require(isinstance(tc_apid, int) and 0 <= tc_apid <= 0x7FE, "Invalid TC APID")

    layout = pus.get("tm_layout", {})
    sec_bytes = layout.get("openobsw_secondary_header_bytes")
    primary_bits = layout.get("obsw_srdb_primary_header_bits")
    app_start = layout.get("obsw_srdb_application_data_start_bit")
    require(
        isinstance(sec_bytes, int)
        and isinstance(primary_bits, int)
        and isinstance(app_start, int),
        "TM layout values must be integers",
    )
    require(
        primary_bits + sec_bytes * 8 == app_start,
        "OpenOBSW secondary header and obsw-srdb application offset disagree in baseline",
    )

    messages = compatibility.get("exact_message_capabilities", [])
    message_keys = []
    for record in messages:
        key = (record.get("direction"), record.get("service"), record.get("subtype"))
        require(key[0] in ("TM", "TC"), "Invalid PUS direction")
        require(isinstance(key[1], int) and 0 <= key[1] <= 255, "Invalid PUS service")
        require(isinstance(key[2], int) and 0 <= key[2] <= 255, "Invalid PUS subtype")
        message_keys.append(key)
    assert_unique(message_keys, "exact PUS capability tuple")

    required_messages = {
        ("TC", 17, 1),
        ("TM", 1, 1),
        ("TM", 1, 7),
        ("TM", 17, 2),
        ("TM", 3, 25),
        ("TM", 5, 3),
    }
    require(required_messages.issubset(set(message_keys)), "Canonical exact PUS capability missing")

    allocations = compatibility.get("occupied_allocations", {})
    for category, id_key in (("parameters", "id"), ("events", "id"), ("hk_sets", "sid")):
        records = allocations.get(category, [])
        assert_unique((record.get(id_key) for record in records), "{0} numeric allocation".format(category))
        assert_unique((record.get("name") for record in records), "{0} target name".format(category))

    telecommands = allocations.get("telecommands", [])
    tc_keys = [
        (record.get("apid"), record.get("service"), record.get("subtype"))
        for record in telecommands
    ]
    assert_unique(tc_keys, "baseline telecommand tuple")
    assert_unique((record.get("name") for record in telecommands), "baseline telecommand name")

    type_map = baseline.get("adapter_projection_rules", {}).get("core_scalar_to_obsw_srdb", {})
    expected_types = {"uint8", "uint16", "uint32", "int8", "int16", "int32", "float32"}
    require(set(type_map) == expected_types, "Unexpected first-slice Core scalar mapping set")

    for runtime_name, record in baseline.get("runtime_context", {}).items():
        require(
            record.get("project_requirement") == "not_applicable",
            "Runtime context {0} must not block project".format(runtime_name),
        )

    provenance = baseline.get("provenance", [])
    require(provenance, "Baseline provenance must not be empty")
    paths = {record.get("path") for record in provenance}
    required_paths = {
        "CMakeLists.txt",
        "srdb/pyproject.toml",
        "srdb/obsw_srdb/model.py",
        "srdb/obsw_srdb/loader.py",
        "srdb/obsw_srdb/codegen.py",
        "include/obsw/pus/pus_tm.h",
        "src/pus/s3.c",
        "src/pus/s5.c",
        "src/pus/s17.c",
        "srdb/data/spacecraft.yaml",
        "srdb/data/parameters.yaml",
        "srdb/data/events.yaml",
        "srdb/data/hk_sets.yaml",
        "srdb/data/telecommands.yaml",
        "sim/orbitfabric_contract_adapter.c",
        "pyproject.toml",
    }
    require(required_paths.issubset(paths), "Pinned baseline provenance is incomplete")

    for record in provenance:
        require(isinstance(record.get("repository"), str) and record["repository"], "Invalid provenance repository")
        require(isinstance(record.get("commit"), str) and len(record["commit"]) == 40, "Invalid provenance commit")
        require(isinstance(record.get("git_blob"), str) and len(record["git_blob"]) == 40, "Invalid provenance blob")
        require(isinstance(record.get("facts"), list) and record["facts"], "Provenance facts must be non-empty")


def validate_cases(cases, design_text):
    require(
        cases.get("kind") == "orbitfabric.openobsw_opensvf.preflight_design_cases",
        "Unexpected preflight-cases kind",
    )
    require(cases.get("cases_version") == "0.1-candidate", "Unexpected cases version")
    require(cases.get("status") == "design_only", "Cases must remain design_only")
    require(cases.get("operation") == "project", "Cases operation must be project")

    records = cases.get("cases", [])
    require(records, "No Stage 7.2 preflight cases")
    ids = [record.get("id") for record in records]
    require(all(isinstance(value, str) and value for value in ids), "Every case needs a non-empty ID")
    assert_unique(ids, "preflight case ID")

    by_id = {record["id"]: record for record in records}
    canonical = by_id.get("canonical_current_upstream", {}).get("expected", {})
    require(canonical.get("required_preflight") == "passed", "Canonical project must pass")
    require(canonical.get("artifact_generation_allowed") is True, "Canonical artifacts must be allowed")
    require(
        canonical.get("native_target_application") == "not_applicable",
        "Canonical project must not require target application",
    )

    no_merge = by_id.get("native_merge_api_absent_is_not_project_blocker", {}).get("expected", {})
    require(no_merge.get("required_preflight") == "passed", "Missing merge API must not fail project")
    require(no_merge.get("artifact_generation_allowed") is True, "Missing merge API must allow project artifacts")

    contribution_claim = by_id.get("contribution_must_not_claim_complete_srdb", {}).get("expected", {})
    require(
        contribution_claim.get("diagnostic") == "OFI-PROJ-SRDB-001",
        "Complete-SRDB misclaim must use contribution diagnostic",
    )

    diagnostic_codes = set()
    for record in records:
        diagnostic = record.get("expected", {}).get("diagnostic")
        if diagnostic is not None:
            require(isinstance(diagnostic, str) and diagnostic, "Invalid diagnostic code in cases")
            diagnostic_codes.add(diagnostic)

    design_codes = set(re.findall(r"\bOFI-[A-Z0-9-]+\b", design_text))
    missing = diagnostic_codes - design_codes
    require(not missing, "Case diagnostics absent from design catalog: {0}".format(sorted(missing)))

    retired = "OFI-COMP-SRDB-002"
    require(retired not in diagnostic_codes, "Retired native-merge blocker still used by cases")
    require(retired not in design_codes, "Retired native-merge blocker still present in design")


def validate_proposal(text):
    require("not a prerequisite" in text, "Proposal must state that upstream composition is optional")
    require(
        "proceed without OpenOBSW changes" in text,
        "Proposal must preserve Stage 7.2 no-upstream-change path",
    )
    require("additive-only" in text, "Proposal must define safe initial additive semantics")
    require("OrbitFabric-private merge semantics" in text, "Proposal must reject private merge semantics")


def main():
    paths = [BASELINE_PATH, CASES_PATH, DESIGN_PATH, PROPOSAL_PATH]
    for path in paths:
        if not os.path.exists(path):
            raise DesignError("Missing Stage 7.2 design file: {0}".format(path))

    baseline = load_json(BASELINE_PATH)
    cases = load_json(CASES_PATH)
    design_text = load_text(DESIGN_PATH)
    proposal_text = load_text(PROPOSAL_PATH)

    for path, text in ((DESIGN_PATH, design_text), (PROPOSAL_PATH, proposal_text)):
        assert_no_typographic_dash(path, text)

    validate_baseline(baseline)
    validate_cases(cases, design_text)
    validate_proposal(proposal_text)

    all_text = design_text + "\n" + proposal_text + "\n" + json.dumps(baseline) + json.dumps(cases)
    require("OFI-COMP-SRDB-002" not in all_text, "Retired native SRDB merge blocker remains in design resources")
    require("native_srdb_assembly" not in all_text, "Legacy native_srdb_assembly vocabulary remains")

    print("Baseline SHA-256: {0}".format(sha256(BASELINE_PATH)))
    print("Cases SHA-256: {0}".format(sha256(CASES_PATH)))
    print("Design SHA-256: {0}".format(sha256(DESIGN_PATH)))
    print("Proposal SHA-256: {0}".format(sha256(PROPOSAL_PATH)))
    print("Preflight design cases: {0}".format(len(cases["cases"])))
    print("Stage 7.2 compatibility preflight design validation: PASS")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except DesignError as exc:
        print("Stage 7.2 compatibility preflight design validation: FAIL")
        print("  - {0}".format(exc))
        sys.exit(1)
