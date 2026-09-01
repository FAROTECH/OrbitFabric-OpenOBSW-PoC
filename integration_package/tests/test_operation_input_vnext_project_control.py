from __future__ import annotations

import json
import tempfile
from pathlib import Path

from integration_package.adapter.model import ADAPTER_VERSION, RESULT_VERSION, AdapterFailure
from integration_package.adapter.preflight import run_project
from integration_package.adapter.result import failed_result
from integration_package.tests.test_adapter_slice1 import PROFILE_PATH, REPO_ROOT, _build_input_set


def test_lab_vnext_manifest_retains_zero_input_project() -> None:
    package = json.loads(
        (REPO_ROOT / "integration_package" / "integration_package.json").read_text(
            encoding="utf-8"
        )
    )

    assert package["kind"] == "orbitfabric.integration_package"
    assert package["manifest_version"] == "0.2-lab"
    assert package["adapter"]["version"] == ADAPTER_VERSION == "0.2.0.dev2"
    assert package["execution"]["protocol"] == "orbitfabric.adapter_cli.vnext-lab"
    assert package["result_compatibility"] == {
        "result_versions": ["0.2-lab"],
        "default_result_version": "0.2-lab",
    }

    operations = {item["id"]: item for item in package["operations"]}
    assert set(operations) == {"project", "verification_projection"}
    assert operations["project"]["input_requirements"] == []
    assert operations["verification_projection"]["input_requirements"] == [
        {"role": "scenario"}
    ]


def test_lab_vnext_project_result_retains_zero_operation_inputs() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        manifest = _build_input_set(root)
        output = root / "bundle"

        result = run_project(manifest, PROFILE_PATH, output_dir=output)

    assert result["result"] == "succeeded"
    assert result["result_version"] == RESULT_VERSION == "0.2-lab"
    assert result["adapter"]["version"] == ADAPTER_VERSION
    assert result["operation"] == {"id": "project"}
    assert result["inputs"]["operation_inputs"] == []
    assert result["inputs"]["core_input_set"]["status"] == "available"
    assert result["inputs"]["profile"]["status"] == "available"
    assert result["coverage"]["status"] == "complete"
    assert result["artifacts"]
    assert result["mappings"]


def test_lab_vnext_failed_project_result_has_explicit_empty_operation_inputs() -> None:
    failure = AdapterFailure(
        "OFI-LAB-001",
        "input_compatibility",
        "synthetic control failure",
    )

    result = failed_result("project", failure)

    assert result["result"] == "failed"
    assert result["result_version"] == "0.2-lab"
    assert result["inputs"]["operation_inputs"] == []
