#!/usr/bin/env python3
"""Generate the local PoC XTCE/YAMCS MDB through OpenSVF.

This wrapper intentionally lives in the PoC repository.

It does not modify OpenSVF. It loads the generated PoC SRDB file through
OpenSVF's SrdbLoader.load_mission(), calls OpenSVF's generate_xtce(srdb),
validates the minimal PoC XTCE content, and writes a local generated output.

Default output:

  execution/generated/poc_xtce_mdb.xml
"""

from __future__ import annotations

import argparse
from pathlib import Path

from validate_opensvf_srdb_xtce import (
    build_srdb_with_mission_file,
    load_opensvf_generate_xtce,
    validate_parameter,
    validate_xtce,
)


DEFAULT_SRDB = "generated_artifacts/ground_segment/poc_srdb.yaml"
DEFAULT_OUTPUT = "execution/generated/poc_xtce_mdb.xml"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the PoC XTCE/YAMCS MDB through OpenSVF."
    )
    parser.add_argument(
        "--opensvf-repo",
        default="../opensvf",
        help="Path to the OpenSVF repository. Default: ../opensvf",
    )
    parser.add_argument(
        "--srdb",
        default=DEFAULT_SRDB,
        help=f"Path to the generated PoC SRDB YAML file. Default: {DEFAULT_SRDB}",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Path where the generated XTCE/MDB XML is written. Default: {DEFAULT_OUTPUT}",
    )

    args = parser.parse_args()

    opensvf_repo = Path(args.opensvf_repo).resolve()
    srdb_path = Path(args.srdb).resolve()
    output_path = Path(args.output)

    if not srdb_path.is_file():
        raise SystemExit(f"SRDB file not found: {srdb_path}")

    generate_xtce = load_opensvf_generate_xtce(opensvf_repo)
    srdb = build_srdb_with_mission_file(opensvf_repo, srdb_path)

    validate_parameter(srdb)

    xml_text = generate_xtce(srdb)
    validate_xtce(xml_text)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(xml_text, encoding="utf-8", newline="\n")

    print(f"Generated {output_path}")
    print("PoC XTCE/MDB generation through OpenSVF: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
