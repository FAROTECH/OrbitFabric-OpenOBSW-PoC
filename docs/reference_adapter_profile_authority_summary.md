# Reference Adapter Profile Authority Summary

The candidate OpenOBSW/OpenSVF Projection Profile preserves the following authority split:

```text
Core
  semantic IDs
  telemetry type/unit/limits/sampling
  packet membership/period
  command arguments/modes/effects
  event severity
  fault condition/recovery

Profile
  stable target numeric allocations
  PUS service/subservice projection
  HK SID
  target naming overrides
  flight symbol naming policy
  OpenSVF APID allocations when externally significant
  optional verification-facing protocol expectations

Adapter
  deterministic target names/symbols when not overridden
  Core-type -> target-type projection
  source-domain -> OpenSVF-domain convention
  semantic validation and collision checks
  generated artifacts, mappings, coverage and provenance

OpenOBSW/OpenSVF/YAMCS
  native runtime/verification behavior
```

This summary is explanatory only; the normative candidate details remain in `docs/openobsw_opensvf_projection_profile_v0.md` and the accompanying schema.
