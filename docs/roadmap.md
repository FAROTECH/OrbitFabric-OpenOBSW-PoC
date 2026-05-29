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

Status: **current**

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

Status: **planned**

Goal:

Generate deterministic PoC artifacts from:

```text
orbitfabric_models/mission/
orbitfabric_models/poc_slice.yaml
```

Target generated artifacts:

```text
generated_artifacts/flight_software/mission_contract.h
generated_artifacts/ground_segment/poc_srdb.yaml
```

Expected adapter behavior:

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

Acceptance criteria:

```text
orbitfabric lint orbitfabric_models/mission/
python tools/generate_poc_artifacts.py
```

The generated files must be stable across repeated runs.

## Stage 3 - OpenSVF SRDB and XTCE/YAMCS Ingestion

Status: **planned**

Goal:

Prove that the generated OpenSVF-compatible SRDB artifact can be consumed by OpenSVF tooling and transformed into a YAMCS-visible MDB.

Target chain:

```text
generated_artifacts/ground_segment/poc_srdb.yaml
-> OpenSVF SRDB loader
-> OpenSVF generate_xtce.py
-> YAMCS MDB
```

Known design point:

OpenSVF currently owns SRDB loading and XTCE generation.

The PoC should not make OrbitFabric Core emit XTCE directly.

Open point:

The exact ingestion path for a generated PoC SRDB file must be validated during implementation. A wrapper or a small OpenSVF-side enhancement may be needed if the current XTCE generation path only loads a fixed SRDB location.

Acceptance criteria:

* generated SRDB YAML validates against OpenSVF expectations;
* XTCE/YAMCS MDB can be produced through OpenSVF tooling;
* OrbitFabric Core remains backend-agnostic.

## Stage 4 - OpenOBSW Contract Consumption

Status: **planned**

Goal:

Use the generated flight-side contract in OpenOBSW without moving runtime logic into generated files.

Target chain:

```text
generated_artifacts/flight_software/mission_contract.h
-> OpenOBSW contract include
-> S17 ping path
-> S3 housekeeping path
-> S5 warning event path
```

Acceptance criteria:

* OpenOBSW can consume the generated contract header.
* The header remains contract-only.
* S17 ping remains implemented by OpenOBSW.
* S3 housekeeping remains implemented by OpenOBSW.
* S5 event reporting remains implemented by OpenOBSW.
* Generated files do not replace OpenOBSW runtime behavior.

## Stage 5 - Closed-Loop Validation

Status: **planned**

Goal:

Run the minimal end-to-end validation chain.

Target validation paths:

```text
YAMCS/OpenSVF -> TC(17,1) ping
OpenOBSW -> TM(17,2) pong

OpenOBSW -> TM(3,25) housekeeping
YAMCS/OpenSVF -> telemetry visibility

OpenOBSW -> TM(5,3) warning event
YAMCS/OpenSVF -> event/alarm visibility
```

Acceptance criteria:

* one command path validated;
* one telemetry path validated;
* one event/fault path validated;
* validation evidence captured;
* outputs are reproducible enough to be documented.

## Stage 6 - Reproducibility and Hardening

Status: **planned**

Goal:

Make the PoC repeatable and easier to run by other contributors.

Potential deliverables:

```text
CI lint check
adapter generation test
golden generated artifacts
execution scripts
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
