from __future__ import annotations

from pathlib import Path

import pytest

from integration_package.adapter.cli import (
    PROJECT_OPERATION,
    SCENARIO_ROLE,
    VERIFICATION_OPERATION,
    _parse_operation_inputs,
    _validate_operation_bindings,
)
from integration_package.adapter.model import AdapterFailure
from integration_package.adapter.result import failed_result, unavailable_operation_input


def test_g4_parse_one_explicit_scenario_binding() -> None:
    bindings = _parse_operation_inputs([[SCENARIO_ROLE, "scenario.yaml"]])
    assert bindings == {SCENARIO_ROLE: Path("scenario.yaml")}
    _validate_operation_bindings(VERIFICATION_OPERATION, bindings)


def test_g4_duplicate_operation_input_role_fails_closed() -> None:
    with pytest.raises(AdapterFailure) as caught:
        _parse_operation_inputs(
            [
                [SCENARIO_ROLE, "one.yaml"],
                [SCENARIO_ROLE, "two.yaml"],
            ]
        )
    assert caught.value.code == "OFI-OPINPUT-001"
    assert "more than once" in caught.value.message


def test_g4_project_rejects_additional_operation_input() -> None:
    with pytest.raises(AdapterFailure) as caught:
        _validate_operation_bindings(
            PROJECT_OPERATION,
            {SCENARIO_ROLE: Path("scenario.yaml")},
        )
    assert caught.value.code == "OFI-OPINPUT-002"
    assert "declares no additional operation inputs" in caught.value.message


def test_g4_verification_requires_exactly_scenario_role() -> None:
    with pytest.raises(AdapterFailure) as missing:
        _validate_operation_bindings(VERIFICATION_OPERATION, {})
    assert missing.value.code == "OFI-OPINPUT-002"
    assert "missing required roles: scenario" in missing.value.message

    with pytest.raises(AdapterFailure) as unexpected:
        _validate_operation_bindings(
            VERIFICATION_OPERATION,
            {"campaign": Path("campaign.yaml")},
        )
    assert unexpected.value.code == "OFI-OPINPUT-002"
    assert "missing required roles: scenario" in unexpected.value.message
    assert "unexpected roles: campaign" in unexpected.value.message


def test_g4_failed_result_can_retain_unavailable_scenario_provenance() -> None:
    failure = AdapterFailure(
        "OFI-OPINPUT-002",
        "input_compatibility",
        "scenario binding missing",
    )
    result = failed_result(
        VERIFICATION_OPERATION,
        failure,
        operation_inputs=[
            unavailable_operation_input(SCENARIO_ROLE, failure.message)
        ],
    )

    assert result["result"] == "failed"
    assert result["operation"] == {"id": VERIFICATION_OPERATION}
    assert result["inputs"]["operation_inputs"] == [
        {
            "role": "scenario",
            "status": "unavailable",
            "id": None,
            "sha256": None,
            "reason": "scenario binding missing",
        }
    ]
