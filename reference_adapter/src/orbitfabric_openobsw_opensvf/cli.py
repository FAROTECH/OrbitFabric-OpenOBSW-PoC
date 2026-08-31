from __future__ import annotations

import argparse
from importlib.resources import as_file, files
from pathlib import Path
import sys

from .flight_contract import FlightContractError, materialize_flight_contract
from .opensvf_srdb import OpenSvfSrdbError, materialize_opensvf_srdb
from .projection_pipeline import write_resolved_projection
from .resolver import ProjectionResolutionError
from .runner import run_operation
from .validator import ValidationInputError, validate_profile


def _add_common_projection_inputs(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--input-set-manifest",
        required=True,
        type=Path,
        help="Path to integration_input_manifest.json",
    )
    parser.add_argument(
        "--profile",
        required=True,
        type=Path,
        help="Path to the OpenOBSW/OpenSVF Projection Profile YAML",
    )


def _add_resolved_input(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--resolved-projection",
        required=True,
        type=Path,
        help="Path to adapter-owned resolved_projection.json",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output artifact path",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="orbitfabric-openobsw-opensvf")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser(
        "run",
        help="Execute an advertised integration operation using orbitfabric.adapter_cli.v0",
    )
    run.add_argument("--operation", required=True, help="Advertised integration operation ID")
    _add_common_projection_inputs(run)
    run.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Root directory for the Integration Result bundle",
    )

    validate = subparsers.add_parser(
        "validate-profile",
        help="Validate a Projection Profile against a coherent Core Integration Input Set",
    )
    _add_common_projection_inputs(validate)

    resolve = subparsers.add_parser(
        "resolve-projection",
        help="Resolve validated Core semantics and Profile target intent into adapter IR",
    )
    _add_common_projection_inputs(resolve)
    resolve.add_argument(
        "--json",
        required=True,
        type=Path,
        dest="json_output",
        help="Write the resolved projection model to this JSON file",
    )

    flight = subparsers.add_parser(
        "generate-flight-contract",
        help="Materialize mission_contract.h from a resolved projection model",
    )
    _add_resolved_input(flight)

    srdb = subparsers.add_parser(
        "generate-opensvf-srdb",
        help="Materialize OpenSVF SRDB YAML from a resolved projection model",
    )
    _add_resolved_input(srdb)
    return parser


def _schema_resource():
    return files("orbitfabric_openobsw_opensvf").joinpath(
        "schemas/openobsw_opensvf_projection_profile_v0.schema.json"
    )


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "run":
        with as_file(_schema_resource()) as schema_path:
            status, result_path = run_operation(
                operation_id=args.operation,
                manifest_path=args.input_set_manifest,
                profile_path=args.profile,
                output_dir=args.output_dir,
                schema_path=schema_path,
            )
        if result_path is not None:
            print(f"Integration Result: {result_path}")
        if status == 0:
            print("Integration operation: PASS")
        else:
            print("Integration operation: FAIL", file=sys.stderr)
        return status

    if args.command == "validate-profile":
        try:
            with as_file(_schema_resource()) as schema_path:
                result = validate_profile(
                    manifest_path=args.input_set_manifest,
                    profile_path=args.profile,
                    schema_path=schema_path,
                )
        except ValidationInputError as exc:
            print(f"ERROR input: {exc}", file=sys.stderr)
            return 2

        if result.ok:
            print("Projection Profile validation: PASS")
            return 0
        for diagnostic in result.diagnostics:
            print(f"ERROR {diagnostic.code}: {diagnostic.message}", file=sys.stderr)
        print(
            f"Projection Profile validation: FAIL ({len(result.diagnostics)} diagnostic(s))",
            file=sys.stderr,
        )
        return 1

    if args.command == "resolve-projection":
        try:
            with as_file(_schema_resource()) as schema_path:
                written = write_resolved_projection(
                    manifest_path=args.input_set_manifest,
                    profile_path=args.profile,
                    schema_path=schema_path,
                    output_file=args.json_output,
                )
        except ProjectionResolutionError as exc:
            for diagnostic in exc.diagnostics:
                print(f"ERROR {diagnostic.code}: {diagnostic.message}", file=sys.stderr)
            print(
                f"Projection resolution: FAIL ({len(exc.diagnostics)} diagnostic(s))",
                file=sys.stderr,
            )
            return 1
        except ValidationInputError as exc:
            print(f"ERROR input: {exc}", file=sys.stderr)
            return 2

        print(f"Resolved projection written to: {written}")
        print("Projection resolution: PASS")
        return 0

    if args.command == "generate-flight-contract":
        try:
            written = materialize_flight_contract(
                resolved_projection_file=args.resolved_projection,
                output_file=args.output,
            )
        except FlightContractError as exc:
            print(f"ERROR flight-contract: {exc}", file=sys.stderr)
            return 2
        print(f"Flight contract written to: {written}")
        print("Flight contract materialization: PASS")
        return 0

    if args.command == "generate-opensvf-srdb":
        try:
            written = materialize_opensvf_srdb(
                resolved_projection_file=args.resolved_projection,
                output_file=args.output,
            )
        except OpenSvfSrdbError as exc:
            print(f"ERROR opensvf-srdb: {exc}", file=sys.stderr)
            return 2
        print(f"OpenSVF SRDB written to: {written}")
        print("OpenSVF SRDB materialization: PASS")
        return 0

    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
