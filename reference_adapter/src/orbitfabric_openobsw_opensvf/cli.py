from __future__ import annotations

import argparse
from importlib.resources import as_file, files
from pathlib import Path
import sys

from .resolver import ProjectionResolutionError, write_resolved_projection
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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="orbitfabric-openobsw-opensvf")
    subparsers = parser.add_subparsers(dest="command", required=True)

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
    return parser


def _schema_resource():
    return files("orbitfabric_openobsw_opensvf").joinpath(
        "schemas/openobsw_opensvf_projection_profile_v0.schema.json"
    )


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

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

    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
