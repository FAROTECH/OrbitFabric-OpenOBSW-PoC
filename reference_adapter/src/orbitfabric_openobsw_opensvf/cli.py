from __future__ import annotations

import argparse
from importlib.resources import files
from pathlib import Path
import sys

from .validator import ValidationInputError, validate_profile


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="orbitfabric-openobsw-opensvf")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser(
        "validate-profile",
        help="Validate a Projection Profile against a coherent Core Integration Input Set",
    )
    validate.add_argument(
        "--input-set-manifest",
        required=True,
        type=Path,
        help="Path to integration_input_manifest.json",
    )
    validate.add_argument(
        "--profile",
        required=True,
        type=Path,
        help="Path to the OpenOBSW/OpenSVF Projection Profile YAML",
    )
    return parser


def _packaged_schema_path() -> Path:
    resource = files("orbitfabric_openobsw_opensvf").joinpath(
        "schemas/openobsw_opensvf_projection_profile_v0.schema.json"
    )
    return Path(str(resource))


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "validate-profile":
        try:
            result = validate_profile(
                manifest_path=args.input_set_manifest,
                profile_path=args.profile,
                schema_path=_packaged_schema_path(),
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

    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
