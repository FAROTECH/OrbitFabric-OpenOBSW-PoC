#!/usr/bin/env python3
"""Validate the generated PoC SRDB against the OpenSVF SRDB and XTCE path.

This script intentionally does not modify OpenSVF.

It validates that:

1. generated_artifacts/ground_segment/poc_srdb.yaml can be loaded through
   OpenSVF's SrdbLoader.load_mission().
2. The resulting SRDB object can be passed to OpenSVF's generate_xtce(srdb).
3. The generated XTCE/YAMCS MDB XML contains the PoC telemetry parameter.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


POC_PARAMETER_NAME = "eps.obc.bus_voltage_mv"
POC_PARAMETER_XTCE_NAME = "eps_obc_bus_voltage_mv"


def load_opensvf_generate_xtce(opensvf_repo: Path):
    opensvf_src = opensvf_repo / "src"
    generate_xtce_path = opensvf_repo / "tools" / "generate_xtce.py"

    if not opensvf_src.is_dir():
        raise SystemExit(f"OpenSVF src directory not found: {opensvf_src}")

    if not generate_xtce_path.is_file():
        raise SystemExit(f"OpenSVF generate_xtce.py not found: {generate_xtce_path}")

    sys.path.insert(0, str(opensvf_src))

    spec = importlib.util.spec_from_file_location(
        "opensvf_generate_xtce",
        generate_xtce_path,
    )
    if spec is None or spec.loader is None:
        raise SystemExit(f"Unable to import {generate_xtce_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "generate_xtce"):
        raise SystemExit("OpenSVF generate_xtce.py does not expose generate_xtce(srdb)")

    return module.generate_xtce


def build_srdb_with_mission_file(opensvf_repo: Path, srdb_path: Path):
    opensvf_src = opensvf_repo / "src"
    sys.path.insert(0, str(opensvf_src))

    from svf.srdb.loader import SrdbLoader

    loader = SrdbLoader()
    loader.load_mission(srdb_path)
    return loader.build()


def validate_parameter(srdb) -> None:
    param = srdb.require(POC_PARAMETER_NAME)

    assert param.description
    assert param.unit == "mV"
    assert param.dtype.value == "int"
    assert param.classification.value == "TM"
    assert param.domain.value == "EPS"
    assert param.model_id == "eps"
    assert param.valid_range == (0.0, 65535.0)

    assert param.pus is not None
    assert param.pus.apid == 0x100
    assert param.pus.service == 3
    assert param.pus.subservice == 25
    assert param.pus.parameter_id == 0x4001


def validate_xtce(xml_text: str) -> None:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise SystemExit(f"Generated XTCE is not valid XML: {exc}") from exc

    ns = {"xtce": "http://www.omg.org/spec/XTCE/20180204"}

    parameter = root.find(
        f".//xtce:Parameter[@name='{POC_PARAMETER_XTCE_NAME}']",
        ns,
    )
    if parameter is None:
        raise SystemExit(
            "Generated XTCE does not contain parameter "
            f"{POC_PARAMETER_XTCE_NAME}"
        )

    hk_container = root.find(
        ".//xtce:SequenceContainer[@name='TM_3_25_HK']",
        ns,
    )
    if hk_container is None:
        raise SystemExit("Generated XTCE does not contain TM_3_25_HK container")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate PoC SRDB ingestion through OpenSVF and XTCE generation."
    )
    parser.add_argument(
        "--opensvf-repo",
        default="../opensvf",
        help="Path to the OpenSVF repository. Default: ../opensvf",
    )
    parser.add_argument(
        "--srdb",
        default="generated_artifacts/ground_segment/poc_srdb.yaml",
        help="Path to the generated PoC SRDB YAML file.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path where the generated XTCE XML should be written.",
    )

    args = parser.parse_args()

    opensvf_repo = Path(args.opensvf_repo).resolve()
    srdb_path = Path(args.srdb).resolve()

    if not srdb_path.is_file():
        raise SystemExit(f"SRDB file not found: {srdb_path}")

    generate_xtce = load_opensvf_generate_xtce(opensvf_repo)
    srdb = build_srdb_with_mission_file(opensvf_repo, srdb_path)

    validate_parameter(srdb)

    xml_text = generate_xtce(srdb)
    validate_xtce(xml_text)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(xml_text, encoding="utf-8", newline="\n")

    print("OpenSVF SRDB to XTCE validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
