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


S5_EVENT_PARAMETER_XML = """      <Parameter name="of_event_id" parameterTypeRef="uint16">
        <LongDescription>OrbitFabric event identifier carried in PUS Service 5 event reports. Stage 6.11 projects OF_EVENT_VOLTAGE_OUT_OF_BOUNDS = 0x5001 for eps.voltage_out_of_bounds.</LongDescription>
      </Parameter>
"""


S5_TM_5_3_CONTAINER_XML = """
      <!-- TM(5,3) Event report - warning / medium severity -->
      <SequenceContainer name="TM_5_3_Event">
        <LongDescription>PUS Service 5 warning event report for OF_EVENT_VOLTAGE_OUT_OF_BOUNDS = 0x5001 / eps.voltage_out_of_bounds.</LongDescription>
        <BaseContainer containerRef="PUS_Packet">
          <RestrictionCriteria>
            <ComparisonList>
              <Comparison parameterRef="pus_svc"    value="5" comparisonOperator="=="/>
              <Comparison parameterRef="pus_subsvc" value="3" comparisonOperator="=="/>
            </ComparisonList>
          </RestrictionCriteria>
        </BaseContainer>
        <EntryList>
          <ParameterRefEntry parameterRef="of_event_id">
            <LocationInContainerInBits referenceLocation="containerStart">
              <FixedValue>88</FixedValue>
            </LocationInContainerInBits>
          </ParameterRefEntry>
        </EntryList>
      </SequenceContainer>
"""


def project_stage6_11_s5_event_mdb(xml_text: str) -> str:
    """Project the local PoC PUS Service 5 event marker into the MDB."""
    if "TM_5_3_Event" in xml_text:
        return xml_text

    parameter_anchor = '      <Parameter name="eps_obc_bus_voltage_mv" parameterTypeRef="int32">\n'
    if parameter_anchor not in xml_text:
        raise SystemExit("Cannot project Stage 6.11 MDB event parameter: telemetry anchor not found")

    xml_text = xml_text.replace(
        parameter_anchor,
        S5_EVENT_PARAMETER_XML + parameter_anchor,
        1,
    )

    container_anchor = "      <!-- TM(17,2) Are-You-Alive response -->\n"
    if container_anchor not in xml_text:
        raise SystemExit("Cannot project Stage 6.11 MDB event container: container anchor not found")

    xml_text = xml_text.replace(
        container_anchor,
        S5_TM_5_3_CONTAINER_XML + "\n" + container_anchor,
        1,
    )

    return xml_text


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

    xml_text = project_stage6_11_s5_event_mdb(xml_text)
    validate_xtce(xml_text)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(xml_text, encoding="utf-8", newline="\n")

    print(f"Generated {output_path}")
    print("PoC XTCE/MDB generation through OpenSVF: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
