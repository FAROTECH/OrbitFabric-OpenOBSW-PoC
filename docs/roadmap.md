# PoC Roadmap

This roadmap defines the public execution plan for the OrbitFabric ↔ OpenOBSW/OpenSVF Proof of Concept.

The roadmap is intentionally staged.

Each stage should be small, reviewable, and independently useful.

## Stage 0 - Core-Compatible Source Model

Status: **completed**

Goal:

Establish a minimal OrbitFabric Core-compatible source model for the PoC.

Deliverables:

```text
orbitfabric_models/mission/
orbitfabric_models/poc_slice.yaml
docs/mapping_concept.md
```

The Core Mission Model includes:

* one spacecraft definition;
* two subsystems;
* three modes;
* one telemetry parameter;
* one command;
* two semantic events;
* one fault;
* one housekeeping packet;
* required policies.

Validation:

```bash
orbitfabric lint orbitfabric_models/mission/
```

Expected result:

```text
PASSED
0 errors
0 warnings
```

## Stage 1 - Documentation Alignment

Status: **completed**

Goal:

Align the repository documentation after the Core Mission Model has been merged.

Deliverables:

```text
README.md
docs/mapping_concept.md
docs/integration_vision.md
docs/roadmap.md
docs/development_workflow.md
```

Acceptance criteria:

* The Core Mission Model is clearly distinguished from the PoC mapping/allocation layer.
* The adapter boundary is documented.
* The public roadmap is documented.
* The collaborator workflow is documented.
* No generated artifacts are introduced yet.
* No OpenOBSW/OpenSVF wiring is changed yet.

## Stage 2 - PoC Adapter Generation Prototype

Status: **completed**

Goal:

Generate deterministic PoC artifacts from:

```text
orbitfabric_models/mission/
orbitfabric_models/poc_slice.yaml
```

Generated artifacts:

```text
generated_artifacts/flight_software/mission_contract.h
generated_artifacts/ground_segment/poc_srdb.yaml
```

Adapter behavior:

* validate/read the OrbitFabric Core Mission Model;
* consume the PoC mapping/allocation layer;
* generate a contract-only C11 header;
* generate OpenSVF-compatible SRDB YAML;
* keep generation deterministic.

`mission_contract.h` constraints:

* no runtime logic;
* no PUS framing;
* no transport logic;
* no scheduling;
* no dynamic allocation;
* fixed-width C types only;
* deterministic `OF_` naming.

Validation:

```text
orbitfabric lint orbitfabric_models/mission/
python tools/generate_poc_artifacts.py
```

The generated files must be stable across repeated runs.

## Stage 3 - OpenSVF SRDB and XTCE/YAMCS MDB Wrapper

Status: **completed for local PoC generation, YAMCS runtime still pending**

Goal:

Prove that the generated OpenSVF-compatible SRDB artifact can be consumed by OpenSVF tooling and transformed into a local XTCE/YAMCS MDB artifact without modifying OpenSVF proper.

Validated local chain:

```text
generated_artifacts/ground_segment/poc_srdb.yaml
-> PoC-side OpenSVF wrapper
-> OpenSVF SRDB loading path
-> OpenSVF XTCE generation
-> execution/generated/poc_xtce_mdb.xml
```

Known design point:

OpenSVF currently owns SRDB loading and XTCE generation.

The PoC should not make OrbitFabric Core emit XTCE directly.

Acceptance criteria:

* generated SRDB YAML validates against OpenSVF expectations;
* XTCE/YAMCS MDB can be produced through PoC-side OpenSVF wrapper tooling;
* OrbitFabric Core remains backend-agnostic;
* generated execution output remains local and ignored by git.

Remaining work:

* run or expose the generated MDB through a real YAMCS runtime path.

## Stage 4 - OpenOBSW Contract Consumption Boundary

Status: **exercised through runtime smoke, OpenOBSW proper remains external to this repo**

Goal:

Use the generated flight-side contract in the OpenOBSW integration boundary without moving runtime logic into generated files.

Target chain:

```text
generated_artifacts/flight_software/mission_contract.h
-> OrbitFabric-enabled OpenOBSW host simulator
-> S17 ping path
-> S3 housekeeping path
-> S5 warning event path
```

Current baseline:

* the generated contract header exists in this repository;
* it remains contract-only;
* the Stage 6.3 runtime smoke exercises the OrbitFabric-enabled OpenOBSW host simulator through OpenSVF pipe mode;
* OpenOBSW proper changes are outside this repository and are not duplicated here.

Acceptance criteria:

* OpenOBSW can consume the generated contract header.
* The header remains contract-only.
* S17 ping remains implemented by OpenOBSW.
* S3 housekeeping remains implemented by OpenOBSW.
* S5 event reporting remains implemented by OpenOBSW.
* Generated files do not replace OpenOBSW runtime behavior.

## Stage 5 - Closed-Loop Validation

Status: **partially completed**

Goal:

Run the minimal end-to-end validation chain.

Target validation paths:

```text
OpenSVF -> TC(17,1) ping
OpenOBSW -> TM(1,1), TM(17,2), TM(1,7)

OpenOBSW -> TM(3,25) housekeeping
OpenSVF/YAMCS -> telemetry visibility

OpenOBSW -> TM(5,3) warning event
OpenSVF/YAMCS -> event/alarm visibility
```

Completed:

* the PUS ping command path is validated by Stage 6.3 using OpenSVF campaign tooling and pipe mode;
* machine-readable campaign evidence can be generated locally.

Still open:

* runtime validation of `TM(3,25)` housekeeping telemetry;
* runtime validation of the `TM(5,3)` warning event/fault path;
* YAMCS runtime visibility.

## Stage 6 - OpenSVF Runtime Bridge Discovery and Hardening

Status: **in progress**

Goal:

Make the PoC repeatable and progressively closer to a real OpenSVF/YAMCS validation workflow, without adding architecture prematurely.

### Stage 6.1 - OpenSVF Pipe Mode Discovery

Status: **completed**

Finding:

OpenSVF already provides pipe mode and `SpacecraftLoader` support sufficient to attempt a PoC-side runtime wrapper before introducing any custom bridge process.

Reference:

```text
docs/stage6_1_opensvf_pipe_mode_discovery.md
```

### Stage 6.2 - OpenSVF Bridge Readiness Wrapper

Status: **completed**

Finding:

The PoC-side OpenSVF wrapper can describe the expected OpenOBSW host simulator pipe-mode path while keeping external SRDB/XTCE/YAMCS handling outside unsupported `spacecraft.yaml` fields.

Reference:

```text
docs/stage6_2_opensvf_bridge_readiness.md
```

### Stage 6.3 - OpenSVF Runtime Smoke

Status: **completed**

Validated runtime path:

```text
OpenSVF campaign runner
-> SpacecraftLoader
-> OBCEmulatorAdapter
-> pipe mode
-> OrbitFabric-enabled OpenOBSW obsw_sim
-> PUS TC(17,1)
-> PUS TM(1,1)
-> PUS TM(17,2)
-> PUS TM(1,7)
```

Critical runtime finding:

```yaml
simulation:
  realtime: true
```

is required for campaign procedures that observe telemetry in wall-clock time.

Reference:

```text
docs/stage6_3_opensvf_runtime_smoke.md
```

### Stage 6.4 - Documentation and Roadmap Baseline Sync

Status: **current**

Goal:

Bring the top-level documentation back in line with the actual merged PoC baseline after Stage 6.3.

Scope:

* update the README current baseline;
* update this roadmap;
* update the mapping concept immediate next steps;
* do not change runtime behavior;
* do not modify OpenSVF proper;
* do not modify OpenOBSW proper.

## Candidate Next Technical Stages

### Candidate Stage 6.5A - HK Telemetry Runtime Smoke

Goal:

Validate the generated telemetry/HK path at runtime.

Target path:

```text
eps.obc.bus_voltage_mv
-> generated SRDB parameter
-> TM(3,25)
-> OpenSVF runtime observation
```

Rationale:

The generated SRDB currently covers the PoC telemetry parameter. The next high-value runtime proof is to observe the housekeeping telemetry path, not only the ping command path.

### Candidate Stage 6.5B - SRDB Package and Clean Runtime Environment

Goal:

Decide whether the non-blocking Stage 6.3 warning:

```text
obsw-srdb package not installed — cannot verify SRDB version handshake
```

should be resolved through packaging/setup work.

Rationale:

Stage 6.3 proves the ping loop works despite the warning. A later stage may still need a clean SRDB/version-handshake environment for stronger reproducibility.

### Candidate Stage 6.6 - YAMCS Runtime Visibility

Goal:

Run or expose the generated MDB through a YAMCS-visible runtime path.

Rationale:

The PoC has local XTCE/MDB generation support, but YAMCS runtime execution is not yet demonstrated.

### Candidate Stage 6.7 - Event/Fault Runtime Path

Goal:

Validate the event/fault path:

```text
eps.voltage_out_of_bounds
-> fault/event materialization
-> TM(5,3)
-> OpenSVF/YAMCS event or alarm visibility
```

Rationale:

The semantic event/fault exists in the Mission Model and mapping layer, but it has not yet been closed in runtime evidence.

## Reproducibility and Hardening Backlog

Potential deliverables:

```text
CI lint check
adapter generation test
golden generated artifacts check
runtime smoke script
optional Docker/devcontainer support
optional Renode/YAMCS runner
```

Guiding rule:

Docker or compose-based orchestration becomes useful after the adapter, generated artifacts, and execution loop are clear.

It should not drive the architecture prematurely.

## Out of Scope for the Initial PoC

The initial PoC does not attempt to:

* model a complete spacecraft mission;
* turn OrbitFabric into a flight software framework;
* make OrbitFabric Core depend on OpenOBSW or OpenSVF;
* make OrbitFabric Core emit XTCE directly;
* replace OpenSVF's SRDB/XTCE/YAMCS responsibilities;
* replace OpenOBSW runtime behavior;
* introduce OrbitFabric Studio as a runtime dependency.
