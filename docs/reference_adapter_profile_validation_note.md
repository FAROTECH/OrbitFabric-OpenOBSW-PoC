# OpenOBSW/OpenSVF Projection Profile Candidate Validation Note

Status: local design validation record

Validated artifacts:

- `schemas/openobsw_opensvf_projection_profile_v0.schema.json`
- `orbitfabric_models/profiles/openobsw_opensvf_poc_v0.yaml`

Validation performed against JSON Schema Draft 2020-12 semantics.

## Positive checks

- schema JSON parses successfully;
- `Draft202012Validator.check_schema` accepts the schema;
- the candidate PoC Projection Profile validates successfully against the schema.

## Negative checks

The following intentionally invalid mutations were verified to be rejected:

1. adding `unit: mV` to the telemetry binding config;
   - expected rejection because unit remains Core-owned semantic state;
2. changing the housekeeping binding source domain from `packets` to `telemetry`;
   - expected rejection because housekeeping materialization is anchored to the Core packet entity;
3. setting a PUS service value outside the permitted integer range;
   - expected structural rejection.

## Validation boundary

These checks prove structural schema behavior only.

They do not replace adapter semantic validation for:

- Core Entity Index resolution;
- binding-ID uniqueness;
- numeric allocation/SID/APID collisions;
- target name legality/uniqueness;
- Core type representability;
- OpenOBSW/OpenSVF/YAMCS compatibility;
- packet/member consistency;
- verification capability support.

Those checks belong to the reference Integration Adapter implementation and its regression suite.
