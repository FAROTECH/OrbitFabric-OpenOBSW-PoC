from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .model import AdapterFailure
from .preflight import run_project
from .result import failed_result, write_result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="orbitfabric-openobsw-opensvf")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--operation", required=True)
    run.add_argument("--input-set-manifest", required=True)
    run.add_argument("--profile", required=True)
    run.add_argument("--output-dir", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    output_dir = Path(args.output_dir)
    operation = args.operation

    if operation != "project":
        failure = AdapterFailure(
            "OFI-OPERATION-001",
            "input_compatibility",
            f"Unsupported operation: {operation}",
        )
        write_result(output_dir, failed_result(operation, failure))
        print(str(failure), file=sys.stderr)
        return 1

    try:
        payload = run_project(
            Path(args.input_set_manifest),
            Path(args.profile),
        )
        result_path = write_result(output_dir, payload)
    except AdapterFailure as exc:
        try:
            write_result(output_dir, failed_result(operation, exc))
        except OSError:
            pass
        print(str(exc), file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Adapter I/O failure: {exc}", file=sys.stderr)
        return 1

    print(f"Integration Result: {result_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
