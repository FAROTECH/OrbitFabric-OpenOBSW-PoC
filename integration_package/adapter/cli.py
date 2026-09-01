from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .artifacts import reset_project_outputs
from .model import AdapterFailure
from .preflight import (
    _reset_verification_outputs,
    run_project,
    run_verification_projection,
)
from .result import failed_result, unavailable_operation_input, write_result


PROJECT_OPERATION = "project"
VERIFICATION_OPERATION = "verification_projection"
SCENARIO_ROLE = "scenario"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="orbitfabric-openobsw-opensvf")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--operation", required=True)
    run.add_argument("--input-set-manifest", required=True)
    run.add_argument("--profile", required=True)
    run.add_argument(
        "--operation-input",
        action="append",
        nargs=2,
        metavar=("ROLE", "PATH"),
        default=[],
        help=(
            "Operation-input v1 binding. Repeat as "
            "--operation-input ROLE PATH."
        ),
    )
    run.add_argument("--output-dir", required=True)
    return parser


def _parse_operation_inputs(raw: list[list[str]]) -> dict[str, Path]:
    bindings: dict[str, Path] = {}
    for role_value, path_value in raw:
        role = role_value.strip()
        if not role:
            raise AdapterFailure(
                "OFI-OPINPUT-001",
                "input_compatibility",
                "Operation input role must be a non-empty string.",
            )
        if role in bindings:
            raise AdapterFailure(
                "OFI-OPINPUT-001",
                "input_compatibility",
                f"Operation input role {role!r} is bound more than once.",
            )
        if not path_value.strip():
            raise AdapterFailure(
                "OFI-OPINPUT-001",
                "input_compatibility",
                f"Operation input role {role!r} has an empty resource path.",
            )
        bindings[role] = Path(path_value)
    return bindings


def _binding_failure_provenance(operation: str, message: str) -> list[dict]:
    if operation == VERIFICATION_OPERATION:
        return [unavailable_operation_input(SCENARIO_ROLE, message)]
    return []


def _validate_operation_bindings(
    operation: str,
    bindings: dict[str, Path],
) -> None:
    if operation == PROJECT_OPERATION:
        if bindings:
            raise AdapterFailure(
                "OFI-OPINPUT-002",
                "input_compatibility",
                "Operation 'project' declares no additional operation inputs.",
            )
        return

    if operation == VERIFICATION_OPERATION:
        actual = set(bindings)
        expected = {SCENARIO_ROLE}
        if actual != expected:
            missing = sorted(expected - actual)
            unexpected = sorted(actual - expected)
            details: list[str] = []
            if missing:
                details.append(f"missing required roles: {', '.join(missing)}")
            if unexpected:
                details.append(f"unexpected roles: {', '.join(unexpected)}")
            raise AdapterFailure(
                "OFI-OPINPUT-002",
                "input_compatibility",
                "Operation 'verification_projection' requires exactly one "
                "'scenario' binding; " + "; ".join(details),
            )
        return

    raise AdapterFailure(
        "OFI-OPERATION-001",
        "input_compatibility",
        f"Unsupported operation: {operation}",
    )


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    output_dir = Path(args.output_dir)
    operation = args.operation

    try:
        reset_project_outputs(output_dir)
        _reset_verification_outputs(output_dir)
    except (AdapterFailure, OSError) as exc:
        print(f"Adapter output reset failure: {exc}", file=sys.stderr)
        return 1

    try:
        bindings = _parse_operation_inputs(args.operation_input)
        _validate_operation_bindings(operation, bindings)
    except AdapterFailure as exc:
        write_result(
            output_dir,
            failed_result(
                operation,
                exc,
                operation_inputs=_binding_failure_provenance(operation, exc.message),
            ),
        )
        print(str(exc), file=sys.stderr)
        return 1

    try:
        if operation == PROJECT_OPERATION:
            payload = run_project(
                Path(args.input_set_manifest),
                Path(args.profile),
                output_dir=output_dir,
            )
        else:
            payload = run_verification_projection(
                Path(args.input_set_manifest),
                Path(args.profile),
                bindings[SCENARIO_ROLE],
                output_dir=output_dir,
            )
        result_path = write_result(output_dir, payload)
    except AdapterFailure as exc:
        try:
            write_result(
                output_dir,
                failed_result(
                    operation,
                    exc,
                    operation_inputs=_binding_failure_provenance(operation, exc.message),
                ),
            )
        except OSError:
            pass
        print(str(exc), file=sys.stderr)
        return 1
    except OSError as exc:
        failure = AdapterFailure(
            "OFI-IO-001",
            "execution",
            f"Adapter I/O failure: {exc}",
        )
        try:
            write_result(
                output_dir,
                failed_result(
                    operation,
                    failure,
                    operation_inputs=_binding_failure_provenance(operation, failure.message),
                ),
            )
        except OSError:
            pass
        print(str(failure), file=sys.stderr)
        return 1

    print(f"Integration Result: {result_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
