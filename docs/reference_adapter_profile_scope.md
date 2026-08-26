# Initial Reference Profile Scope

The first OpenOBSW/OpenSVF Projection Profile candidate intentionally covers only the durable projection kinds already evidenced by the PoC:

- telemetry parameter;
- housekeeping packet;
- command;
- event.

Other Core semantic domains remain valid future inputs to the generic framework but are not yet claimed as projectable by this reference schema.

In particular:

- fault conditions and recovery remain Core semantic context;
- modes/states are not yet projected by this schema;
- arrays/structured values are not yet claimed;
- `do_not_project` remains available for explicit authored exclusion across arbitrary Core domains.

This narrow scope is deliberate: the first schema should prove correct authority separation before expanding representativeness.
