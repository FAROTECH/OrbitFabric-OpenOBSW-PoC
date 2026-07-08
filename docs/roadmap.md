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

Status: **completed on main**

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

### Stage 6.5 - HK Telemetry Runtime Smoke

Status:

Merged on `main` through PR #16.

Goal:

Validate the first OpenSVF-observed OpenOBSW housekeeping telemetry path at runtime.

Validated path:

```text
OpenSVF campaign runner
-> OpenSVF SpacecraftLoader
-> OpenSVF OBCEmulatorAdapter
-> OpenSVF pipe mode
-> OrbitFabric-enabled OpenOBSW obsw_sim
-> OpenOBSW sensor tick
-> OpenOBSW PUS Service 3 housekeeping tick
-> TM(3,25)
-> OpenSVF runtime observation
-> OpenSVF ParameterStore DHS OBC HK visibility
```

Outcome:

Stage 6.5 validates that `TM(3,25)` is observable through the public OpenSVF campaign API and that `dhs.obc.obt` becomes visible in the OpenSVF `ParameterStore`.

Boundary:

This stage validates the existing DHS OBC HK runtime path consumed by OpenSVF. It does not yet validate the full OrbitFabric housekeeping contract path for `eps.obc.bus_voltage_mv`.

Review note:

The Stage 6.5 validator intentionally guards against `TC(3,5)` usage. This preserves the design decision that Stage 6.5 observes auto-enabled housekeeping rather than configuring a housekeeping set. Any future stage that configures a custom HK set must explicitly remove or replace that constraint.

Reference:

```text
docs/stage6_5_hk_telemetry_runtime_smoke.md
```

### Stage 6.6 - Roadmap Closure and SRDB Runtime Environment Triage

Status:

Completed on main through PR #17.

Goal:

Close the roadmap state after the Stage 6.5 merge and triage the remaining non-blocking SRDB package/version-handshake warning before choosing the next technical runtime stage.

Known warning:

```text
obsw-srdb package not installed - cannot verify SRDB version handshake
```

Rationale:

Stage 6.3 and Stage 6.5 both prove useful runtime paths despite the warning. The warning should still be made explicit because later YAMCS runtime visibility, stronger MDB reproducibility, or cleaner OpenSVF/OpenOBSW environment setup may depend on a clearer SRDB package/version-handshake story.

Scope:

* update the roadmap to reflect that Stage 6.5 is merged on main;
* record the SRDB warning as a deliberate follow-up item, not as an accidental leftover;
* preserve the Stage 6.5 boundary around auto-enabled HK observation versus HK set configuration;
* do not modify runtime behavior;
* do not modify OpenSVF proper;
* do not modify OpenOBSW proper;
* do not claim YAMCS runtime execution.

Reference:

```text
docs/stage6_6_srdb_runtime_environment_triage.md
```

### Stage 6.7 - SRDB Runtime Environment Probe

Status:

Local stacked branch: `stage6.7/srdb-version-handshake-probe`.

Goal:

Turn the Stage 6.6 SRDB warning triage into a reproducible local environment check.

Finding:

OpenOBSW already carries an installable Python package under:

```text
../openobsw/srdb
```

The OpenSVF runtime warning appears when the OpenSVF Python environment cannot import the `obsw-srdb` package. Installing the OpenOBSW SRDB package into the OpenSVF virtual environment makes `obsw_srdb` importable and allows the Stage 6.5 HK runtime smoke to run without the previous package-not-installed warning.

Local environment setup:

```bash
../opensvf/.venv/bin/python -m pip install -e ../openobsw/srdb
```

Validation:

```bash
../opensvf/.venv/bin/python tools/validate_stage6_7_srdb_runtime_environment.py --run-campaign
```

Boundary:

Stage 6.7 does not modify OpenSVF, OpenOBSW, YAMCS, or runtime behavior. It only makes the clean local SRDB package/runtime environment requirement explicit and testable from the PoC workspace.

Reference:

```text
docs/stage6_7_srdb_runtime_environment_probe.md
```

### Stage 6.8 - YAMCS/MDB Runtime Visibility Readiness

Status: **local readiness path implemented, full YAMCS runtime execution still pending**

Reference:

```text
docs/stage6_8_yamcs_runtime_visibility_readiness.md
tools/validate_stage6_8_yamcs_runtime_visibility.py
```

Goal:

Expose the generated XTCE/MDB artifact as a clean runtime-facing handoff point
for the next YAMCS visibility step.

Rationale:

The PoC already has local XTCE/MDB generation support. Stage 6.8 makes the
runtime-facing MDB handoff explicit and testable before introducing a real YAMCS
launch, import or Docker-based runtime workflow.

Validation boundary:

```text
execution/opensvf/poc_runtime_inputs.yaml
-> generated_xtce_mdb.path
-> execution/generated/poc_xtce_mdb.xml
-> XTCE XML parse
-> eps_obc_bus_voltage_mv
-> TM_3_25_HK
-> yamcs_runtime_execution remains false
```

Stage 6.8 does not launch YAMCS, does not modify OpenSVF or OpenOBSW, and does
not claim closed-loop YAMCS runtime execution. It prepares the next YAMCS import
or launch step while preserving the current architectural boundary.

### Stage 6.9 - Docker-based YAMCS Runtime Candidate

Status: **local PoC-side runtime candidate implemented, closed-loop TM/TC still pending**

Reference:

    docs/stage6_9_yamcs_docker_runtime_candidate.md
    tools/validate_stage6_9_yamcs_docker_runtime_candidate.py
    execution/yamcs/

Goal:

Run the generated XTCE/MDB artifact through a concrete YAMCS-visible runtime
candidate without modifying OpenSVF or OpenOBSW.

Rationale:

Stage 6.8 validates that the runtime-facing MDB handoff exists and is testable.
Stage 6.9 provides a PoC-side Docker/YAMCS candidate derived from the OpenSVF
YAMCS runtime pattern.

Validation boundary:

    execution/generated/poc_xtce_mdb.xml
    -> Docker volume mount
    -> /yamcs/mdb/poc_xtce_mdb.xml
    -> YAMCS 5.12.6 container
    -> XTCE MDB import
    -> HTTP API readiness on port 8090

The candidate preserves the OpenSVF-like YAMCS boundary:

    TM TCP: 10015
    TC UDP: 10025
    PusPacketPreprocessor
    StreamTmPacketProvider
    StreamTcCommandReleaser

Stage 6.9 does not claim live OpenSVF/YamcsBridge execution, live OpenOBSW
telemetry delivery into YAMCS, or closed-loop TC/TM execution.

### Stage 6.10 - Event/Fault Runtime Path Readiness

Status: **local readiness path implemented, live runtime evidence still pending**

Reference:

```text
docs/stage6_10_event_fault_runtime_path_readiness.md
tools/validate_stage6_10_event_fault_runtime_path_readiness.py
```

Goal:

Validate the current readiness state of the event/fault path:

```text
eps.voltage_out_of_bounds
-> fault/event materialization
-> TM(5,3)
-> OpenSVF/YAMCS event or alarm visibility
```

Rationale:

The semantic event/fault exists in the Mission Model and mapping layer. OpenOBSW
already exposes PUS Service 5 event reporting capability and OpenSVF already
exposes YAMCS bridge and PUS Service 5 support. Stage 6.10 records and validates
that readiness boundary without claiming that the live event/fault runtime path
is closed.

Validation boundary:

```text
orbitfabric_models/mission/events.yaml
-> eps.voltage_out_of_bounds

orbitfabric_models/mission/faults.yaml
-> eps.voltage_out_of_bounds_fault
-> emits eps.voltage_out_of_bounds

orbitfabric_models/poc_slice.yaml
-> OF_EVENT_VOLTAGE_OUT_OF_BOUNDS
-> event ID 0x5001
-> PUS Service 5 subtype 3

generated_artifacts/flight_software/mission_contract.h
-> OF_EVENT_VOLTAGE_OUT_OF_BOUNDS = 0x5001

../openobsw
-> PUS Service 5 capability
-> OBSW_S5_MEDIUM = 3
-> obsw_s5_report()

../opensvf
-> YamcsBridge TM TCP 10015
-> YamcsBridge TC UDP 10025
-> PUS Service 5 helper

execution/yamcs/
-> OpenSVF-like YAMCS TM/TC boundary
```

Stage 6.10 does not claim live OpenSVF/YamcsBridge execution, live OpenOBSW
event delivery into YAMCS, or closed-loop event/fault runtime execution.

### Stage 6.11 - YAMCS PUS Service 5 Event MDB Projection

Status: **local PoC-side MDB projection implemented, live event/fault runtime evidence still pending**

Reference:

```text
docs/stage6_11_yamcs_s5_event_mdb_projection.md
tools/validate_stage6_11_yamcs_s5_event_mdb_projection.py
tools/generate_poc_xtce_mdb.py
```

Goal:

Close the Stage 6.10 MDB visibility gap for the selected PoC event/fault path:

```text
eps.voltage_out_of_bounds
-> OF_EVENT_VOLTAGE_OUT_OF_BOUNDS = 0x5001
-> PUS Service 5 subtype 3
-> TM(5,3)
-> TM_5_3_Event
```

Rationale:

Stage 6.10 validated the event/fault readiness boundary. Stage 6.11 projects the selected PUS Service 5 warning event into the local YAMCS MDB so that YAMCS can import a concrete `TM_5_3_Event` sequence container.

Validation boundary:

```text
OpenSVF base XTCE/MDB generation
-> PoC-side MDB projection in tools/generate_poc_xtce_mdb.py
-> of_event_id
-> TM_5_3_Event
-> Generated MDB TM(5,3) marker: present
-> YAMCS Docker runtime import smoke
```

Stage 6.11 does not modify OpenSVF, OpenOBSW, or OrbitFabric Core. It does not claim live OpenSVF/YamcsBridge execution, live OpenOBSW event delivery into YAMCS, YAMCS alarm triggering, or closed-loop event/fault runtime execution.

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
