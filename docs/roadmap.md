# PoC and Reference Integration Roadmap

This roadmap preserves the detailed stage-by-stage engineering history of the OrbitFabric <-> OpenOBSW/OpenSVF integration while recording the current Reference Adapter baseline.

## Current Authoritative Checkpoint

```text
Original thin PoC evidence baseline
    achieved through Stage 6.20

Reference Integration extraction
    validated through Stage 7.10

Reference Adapter
    orbitfabric-openobsw-opensvf 0.1.0

Public Adapter operation
    project

Generic external contracts
    remain 0.1-candidate
```

The PoC evidence baseline and Reference Adapter baseline are frozen engineering checkpoints.

They do not claim final production packaging, final repository topology, stable generic discovery/orchestration contracts, hardware/HIL validation, or complete scenario projection coverage.

See [`reference_integration_baseline_v0_1.md`](reference_integration_baseline_v0_1.md) for the exact frozen boundary.

## How to Read Historical Status Text

The detailed Stage 0-6 entries below are preserved as engineering history.

Statements such as `pending`, `prepared locally`, or `still open` describe the state when that stage was written. They are not the current repository status when a later stage explicitly closed the same path.

The current authoritative closure is Stage 6.20 for the original PoC and Stage 7.10 for the Reference Integration extraction.

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

Status: **completed for local PoC generation; later YAMCS runtime closure is recorded in Stage 6**

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

Status: **completed by the later Stage 6 runtime closure**

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

Open at this historical checkpoint, and later closed by Stage 6:

* runtime validation of `TM(3,25)` housekeeping telemetry;
* runtime validation of the `TM(5,3)` warning event/fault path;
* YAMCS runtime visibility.

## Stage 6 - OpenSVF Runtime Bridge Discovery and Hardening

Status: **completed through Stage 6.20**

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

### Stage 6.12 - YAMCS Contract Packet Visibility Probe

Status: **local PoC-side representative packet probe implemented, YAMCS classification evidence still pending**

Reference:

```text
docs/stage6_12_yamcs_contract_packet_visibility_probe.md
tools/validate_stage6_12_yamcs_contract_packet_visibility_probe.py
```

Goal:

Validate the YAMCS candidate packet input boundary for both sides of the original vertical slice before adding live OpenSVF/YamcsBridge machinery:

```text
Representative TM(3,25)
-> YAMCS candidate TCP TM input
-> generated MDB contract
-> TM_3_25_HK packet visibility readiness

Representative TM(5,3)
-> YAMCS candidate TCP TM input
-> generated MDB contract
-> TM_5_3_Event packet visibility readiness
-> of_event_id = 0x5001 packet field readiness
```

Rationale:

Stage 6.11 projected the selected PUS Service 5 warning event into the generated local YAMCS MDB. Stage 6.12 adds a small PoC-side representative packet probe that validates the contract packet bytes and attempts to write them toward the currently exposed YAMCS TCP boundary.

Validation boundary:

```text
generated XTCE/MDB
-> PUS_Packet offsets
-> TM_3_25_HK restrictions
-> TM_5_3_Event restrictions
-> representative packet bytes
-> optional TCP send to YAMCS candidate port 10015
```

When the YAMCS candidate is not running, the validator still passes with:

```text
Packet injection attempted: false
```

When the YAMCS candidate is running and the exposed TCP boundary accepts the probe connection, the validator can report:

```text
Packet injection attempted: true
```

Stage 6.12 does not modify OpenSVF, OpenOBSW, or OrbitFabric Core. It does not claim live OpenSVF/YamcsBridge execution, live OpenOBSW packet generation, YAMCS `TcpTmDataLink` packet consumption, YAMCS MDB classification observed via API, parameter/event visibility via API, or closed-loop runtime execution.


### Stage 6.13 - YAMCS TM Link Topology Discovery

Status: **local topology discovery implemented, YAMCS packet classification evidence still pending**

Reference:

```text
docs/stage6_13_yamcs_tm_link_topology_discovery.md
tools/validate_stage6_13_yamcs_tm_link_topology_discovery.py
```

Goal:

Clarify the actual TM/TC topology required before making YAMCS packet-consumption or classification claims:

```text
OpenSVF YamcsBridge
-> TCP server on 127.0.0.1:10015
-> raw PUS TM packets

YAMCS TcpTmDataLink
-> TCP client to 127.0.0.1:10015
-> consumes TM from the bridge

YAMCS UdpTcDataLink
-> sends TC to OpenSVF UDP server on 127.0.0.1:10025
```

Rationale:

Stage 6.12 validated representative packet construction and tightened the TCP boundary wording. Stage 6.13 records that the real YAMCS TM link is client-side and requires the OpenSVF `YamcsBridge` or a bridge-compatible TM producer on the other side of port 10015.

Validation boundary:

```text
OpenSVF requirements
-> OpenSVF YamcsBridge implementation
-> OpenSVF YamcsBridge integration tests
-> OpenSVF YAMCS configuration
-> PoC YAMCS configuration
-> optional YAMCS link API observation
-> OpenSVF sibling repo soft-skip when absent
```

Stage 6.13 does not modify OpenSVF, OpenOBSW, or OrbitFabric Core. It does not claim live OpenSVF/YamcsBridge execution, live OpenOBSW packet generation, YAMCS packet consumption, YAMCS MDB classification, parameter/event visibility, or closed-loop runtime execution.


### Stage 6.14 - YAMCS Bridge-Compatible TM Producer Smoke

Status: **local runtime link-consumption smoke implemented, MDB classification evidence still pending**

Reference:

```text
docs/stage6_14_yamcs_bridge_compatible_tm_producer.md
tools/validate_stage6_14_yamcs_bridge_compatible_tm_producer.py
execution/yamcs/stage6_14_bridge_tm_producer.py
execution/yamcs/docker-compose.stage6_14.bridge-producer.yml
```

Goal:

Validate the Stage 6.13 topology with a bridge-compatible producer:

```text
bridge-compatible producer
-> TCP server on 127.0.0.1:10015

YAMCS TcpTmDataLink
-> TCP client
-> status OK
-> dataInCount >= 2
```

This stage demonstrates YAMCS `TcpTmDataLink` packet consumption through the correct bridge-compatible direction. It does not run the real OpenSVF `YamcsBridge`, does not run live OpenOBSW packet generation, does not claim MDB packet classification, and does not claim parameter/event visibility through the YAMCS API.


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

### Stage 6.15 - YAMCS Archive and MDB Classification Probe

Status: local stacked branch / pending PR #23 merge.

Goal:

```text
Stage 6.14 bridge-compatible producer
-> YAMCS tm-in TcpTmDataLink
-> YAMCS packet archive API
-> representative raw TM packet visibility
-> MDB leaf-container classification evidence
```

This stage intentionally combines the packet archive visibility and MDB packet classification evidence steps. It still does not claim live OpenSVF YamcsBridge execution, live OpenOBSW packet generation, parameter/event API extraction, or closed-loop runtime execution.

### Stage 6.16 - Real OpenSVF YamcsBridge TM Path Probe

Status: local stacked branch / pending PR #23 merge.

Goal:

```text
real OpenSVF YamcsBridge
-> YAMCS tm-in TcpTmDataLink
-> YAMCS packet archive API
-> MDB packet classification evidence
```

This stage replaces the Stage 6.14/6.15 bridge-compatible producer with the real OpenSVF YamcsBridge while still sending representative packets. It does not claim live OpenOBSW packet generation, OpenSVF campaign closed-loop execution, YAMCS TC command path execution, parameter/event API extraction, or production hardening.

### Stage 6.17 - Live OpenOBSW HK TM to YAMCS Path Probe

Status: **prepared locally**

Stage 6.17 validates the first live OpenOBSW-generated housekeeping telemetry path into YAMCS.

```text
Linux-built OpenOBSW obsw_sim
-> OpenSVF OBCEmulatorAdapter pipe mode
-> OBCEmulatorAdapter live TM parsing
-> existing OBCEmulatorAdapter._yamcs_bridge TM hook
-> real OpenSVF YamcsBridge
-> YAMCS tm-in TcpTmDataLink
-> YAMCS packet archive
-> MDB packet classification
```

This stage moves beyond representative packet generation. It builds `obsw_sim` as a Linux ELF executable inside the Docker runtime, runs it through the real OpenSVF adapter path, and validates that live `TM(3,25)` generated by OpenOBSW reaches the YAMCS packet archive and is classified as `TM_3_25_HK`.

The validator preserves the PoC soft-skip rule for optional sibling repositories. PoC-local artifacts are always validated, but the live runtime probe is skipped with an explicit `NOTICE` when `../opensvf` or `../openobsw` is absent.

This stage does not claim YAMCS TC command path execution, live event/fault runtime generation, full OpenSVF/OpenOBSW/YAMCS closed-loop campaign execution, hardware target execution, or production deployment hardening.

---

## Stage 6.18 - Live OpenOBSW Event TM to YAMCS

Status: **completed**

Closed the selected live event path:

```text
eps.voltage_out_of_bounds
-> OpenOBSW event materialization
-> TM(5,3)
-> real OpenSVF YamcsBridge
-> YAMCS packet archive / MDB classification
```

This stage strengthened the earlier event-readiness and MDB-projection work with live OpenOBSW-generated telemetry.

## Stage 6.19 - YAMCS-Originated TC Direction Closure

Status: **completed**

Closed the opposite command direction:

```text
YAMCS TC(17,1)
-> OpenSVF
-> OpenOBSW
-> TM(1,1)
-> TM(17,2)
-> TM(1,7)
-> YAMCS
```

This completed the representative ground-originated telecommand loop without moving command-execution semantics out of OpenOBSW or command-release semantics out of YAMCS.

## Stage 6.20 - Final PoC Integration Evidence Matrix

Status: **completed**

Stage 6.20 consolidated the selected thin slice:

```text
Telemetry
eps.obc.bus_voltage_mv
-> OpenOBSW TM(3,25)
-> OpenSVF YamcsBridge
-> YAMCS archive / MDB classification

Command
YAMCS TC(17,1)
-> OpenSVF
-> OpenOBSW
-> TM(1,1), TM(17,2), TM(1,7)
-> YAMCS

Event
eps.voltage_out_of_bounds
-> OpenOBSW TM(5,3)
-> OpenSVF YamcsBridge
-> YAMCS archive / MDB classification
```

The original PoC goal is therefore closed at representative integration-evidence level.

This does not imply production qualification, hardware-target execution, HIL validation, or operational deployment hardening.

---

# Stage 7 - Reference Integration Extraction

Status: **reference baseline achieved through Stage 7.10**

Stage 7 extracted a durable integration boundary from the proven PoC rather than continuing to broaden Stage 6 by default.

The architectural shift is:

```text
historical PoC input
Mission Model YAML + poc_slice.yaml
        |
        v
PoC-specific generators
```

to:

```text
Core Integration Input Set
        +
Projection Profile
        |
        v
out-of-process Integration Package / Adapter
        |
        +-> OpenOBSW-facing contract
        +-> obsw-srdb contribution
        +-> Integration Result
        |
        v
target-owned composition and downstream runtime
```

Detailed extraction rationale is preserved in [`stage7_reference_integration_extraction.md`](stage7_reference_integration_extraction.md).

## Stage 7 progression

| Stage | Status | Outcome |
|---|---|---|
| 7.0 | completed | extraction baseline and ownership framing |
| 7.1 | completed | Projection Profile schema and target allocation boundary |
| 7.2 | completed | compatibility-preflight contract |
| 7.3 | completed | executable Adapter resolution/preflight slice |
| 7.4 | completed | deterministic OpenOBSW-facing contract, SRDB contribution, and Integration Result |
| 7.5 | completed | target-owned SRDB composition |
| 7.6 | completed | external assembled-SRDB build/codegen consumption |
| 7.7 | completed | OpenOBSW host-sim build/runtime from projected integration artifacts |
| 7.8 | completed | native OpenSVF runtime consumption |
| 7.9 | completed | native OpenSVF campaign execution and evidence |
| 7.10 | completed | explicit verification projection and final dual-branch runtime acceptance |

## Stage 7.10 closure

One authoritative Core Integration Input Set and one Projection Profile were exercised through two downstream evidence branches:

```text
flight/runtime branch

Core Integration Input Set + Profile
-> Adapter project
-> OpenOBSW-facing contract + SRDB contribution
-> target-owned composition
-> OpenOBSW runtime
```

```text
verification branch

Core Integration Input Set + Profile + scenario
-> Verification Projection Plan
-> OpenSVF procedure materialization
-> OpenOBSW runtime built from the projected contract and composed target SRDB
-> native OpenSVF CampaignReport
```

Final native campaign acceptance:

```text
PASS: 1
FAIL: 0
ERROR: 0
INCONCLUSIVE: 0
Pass rate: 100.0%
```

The verification extension is validated but intentionally not advertised as a first-class Adapter `0.1.0` public operation.

---

# Reference Adapter 0.1.0 Baseline

Status: **frozen reference implementation baseline**

```text
Adapter
    orbitfabric-openobsw-opensvf 0.1.0

Public operation
    project

Generic external contracts
    0.1-candidate
```

Adapter `0.1.0` does not stabilize the generic Projection Profile, Integration Package, or Integration Result contracts.

Future productionization and integration-architecture evolution are explicit new workstreams rather than unfinished PoC closure.
