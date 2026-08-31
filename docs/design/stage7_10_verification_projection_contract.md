# Stage 7.10: Explicit Verification Projection Contract

## Objective

Stage 7.10 defines the first explicit semantic boundary between OrbitFabric scenario intent and native OpenSVF verification execution.

The goal is not to translate OrbitFabric scenario YAML mechanically into OpenSVF Python.

The goal is to define a deterministic, reviewable and provenance-preserving verification projection contract that states:

- which OrbitFabric-authored scenario semantics are being projected;
- which target-specific verification obligations come from the Projection Profile;
- how each projected item maps to an OpenSVF-native primitive;
- which source semantics are intentionally not projected;
- which cases must fail closed because projection would require a semantic guess.

The resulting architecture is:

```text
OrbitFabric scenario YAML
        |
        |  Core-authored scenario intent
        v
Verification Projection
        ^
        |
Core Integration Input Set
        |
        |  Core entity identity and semantics
        |
Projection Profile
        |
        |  target mapping + verification-facing target obligations
        v
Verification Projection Plan
        |
        v
OpenSVF campaign / procedure materialization
        |
        v
native OpenSVF runtime verification
        |
        v
traceable target verification evidence
```

Stage 7.10 must preserve the distinction between source semantics and target verification configuration.

---

## Reference baselines

The first Stage 7.10 contract is designed against:

```text
OrbitFabric Core
b1aa95408710f697b0ee144a7b41f2376395e01f
v1.2.0

OrbitFabric-OpenOBSW-PoC
f51ef00de850600bd319319f8a917febb5ad6d41

OpenOBSW
44ceb71a016f0541ff7a0aa74191e13bafdb59c1

OpenSVF
667d3eadcb0bbd7814ac324b99946c4ed2f11f23
```

Projection Profile:

```text
poc-openobsw-opensvf
profile version 0.3.0
generic profile contract 0.1-candidate
```

---

## 1. Existing semantic boundaries

OrbitFabric scenarios are a stable host-side input contract.

Their source of truth is:

```text
Mission Model
+
scenario YAML
```

Scenario expectations are declarative host-side checks.

They must not silently become:

```text
flight runtime behavior
ground automation
onboard scheduling
command-dispatch implementation
plugin execution
```

The Mission Model remains the semantic authority for mission entities.

The Core Integration Input Set remains the required structured boundary for downstream Mission Data Contract entity resolution.

The Projection Profile remains authored target-specific configuration.

OpenSVF owns its native campaign, procedure and runtime-verification semantics.

Stage 7.10 must not move semantic authority across these boundaries.

---

## 2. OrbitFabric scenario semantic inventory

The OrbitFabric v1.2.0 scenario model contains four conceptual families.

### 2.1 Metadata

```text
scenario.id
scenario.name
scenario.description
```

These identify and describe the authored scenario.

They may be propagated as provenance and human-readable labels.

They do not define target runtime behavior.

### 2.2 Initial state

```text
initial_state.mode
initial_state.telemetry
```

These are host-side scenario initialization semantics.

Stage 7.10 v0 does not project them into OpenSVF spacecraft initialization.

Doing so would require an explicit mapping between Core state semantics and OpenSVF model inputs.

### 2.3 Stimulus / action semantics

```text
command
args
inject.telemetry
inject.value
```

These describe host-side scenario stimuli.

A stimulus is only projectable when the integration can resolve it through an explicit target mapping without changing Core meaning.

### 2.4 Expectation semantics

Current Core expectation families include:

```text
mode
event
command
command_status
telemetry
payload_lifecycle
data_flow
scenario_status
```

Each expectation family must be assessed independently.

No expectation type is projectable merely because OpenSVF exposes a similarly named primitive.

---

## 3. Semantic authority chain

The Stage 7.10 authority chain is:

```text
1. OrbitFabric Mission Model
   owns mission semantics

2. OrbitFabric scenario
   owns authored host-side scenario intent

3. Projection Profile
   owns target-specific representation choices and
   verification-facing target obligations

4. Integration Package
   owns deterministic projection rules and diagnostics

5. Verification Projection Plan
   records the resolved projection and provenance

6. OpenSVF
   owns native procedure execution and target verification evidence
```

A downstream projection may preserve or represent Core semantics.

It may not redefine them.

---

## 4. Critical non-equivalences

Stage 7.10 explicitly rejects semantic shortcuts.

### 4.1 Core command acceptance is not PUS acceptance telemetry

OrbitFabric:

```text
expect:
  command_status: ACCEPTED
```

means that the Core host-side command router accepted the scenario command.

OpenSVF:

```text
expect TM(1,1)
```

means that the target runtime emitted a PUS acceptance-success report.

These are related concepts but they are not the same semantic assertion.

Stage 7.10 v0 must not map one to the other implicitly.

### 4.2 Scenario time is not onboard scheduling

OrbitFabric:

```text
t: 5
```

is scenario host-side timeline information.

It must not silently become:

```text
OpenSVF ctx.wait(...)
PUS Service 11 scheduling
OBT scheduling
real-time execution timing
```

Stage 7.10 v0 preserves scenario time as provenance and ordering metadata only.

Any future execution-time mapping requires an explicit reviewed policy.

### 4.3 Core telemetry expectation is not automatically an OpenSVF parameter assertion

A Core telemetry ID and an OpenSVF ParameterStore key are different identities.

Projection requires an explicit target-observation mapping.

String similarity is forbidden as a mapping rule.

### 4.4 Core event expectation is not only a PUS service/subservice match

A Core event has mission identity.

Observing only:

```text
TM(5,x)
```

is insufficient when several events may share the same PUS event subtype.

A faithful projection requires enough target evidence to identify the projected event.

### 4.5 Data-flow evidence is not runtime evidence

OrbitFabric `data_flow` expectation semantics are host-side Mission Data Contract continuity evidence.

They must not be translated into runtime storage, downlink, RF, contact or ground-operations assertions.

---

## 5. Verification Projection inputs

A Stage 7.10 projection consumes four explicit inputs.

### Required

```text
1. validated OrbitFabric scenario YAML
2. matching Core Integration Input Set
3. compatible Projection Profile
4. Integration Package implementation/schema
```

The scenario is the authored scenario-intent source.

The Core Integration Input Set is used to resolve Mission Data Contract entity identity and semantics.

The Projection Profile supplies target-specific choices.

The Integration Package supplies projection policy and validation.

### Forbidden fallbacks

The projector must not:

```text
guess target mapping from textual IDs
read Mission Model YAML as a fallback for Integration Input Set semantics
parse terminal logs
infer mapping from generated C symbols
infer OpenSVF keys from Core IDs
infer PUS semantics from numeric coincidence
```

---

## 6. Projection atom model

The projector decomposes source scenario content into explicit semantic atoms.

Representative atom kinds:

```text
scenario_metadata
initial_mode
initial_telemetry
command
command_argument
telemetry_injection
expect_mode
expect_event
expect_command
expect_command_status
expect_telemetry
expect_payload_lifecycle
expect_data_flow
expect_scenario_status
```

Every source atom receives exactly one disposition.

### `projected`

The atom has a faithful explicit mapping.

### `not_projected`

The atom is intentionally outside the supported projection subset.

A non-empty reason is mandatory.

### `blocked`

Projection would require a semantic guess, an unresolved source entity, an incompatible binding, missing required target configuration, or another unsafe assumption.

A blocked atom makes the executable projection invalid.

No atom may disappear silently.

---

## 7. Stage 7.10 v0 support matrix

| OrbitFabric source semantic | v0 disposition | Rationale |
|---|---|---|
| scenario metadata | projected as provenance | No runtime semantic claim |
| initial mode | not_projected | No explicit Core-mode -> OpenSVF initialization contract |
| initial telemetry | not_projected | No explicit Core-telemetry -> OpenSVF initialization contract |
| command with empty args | projected when command binding has explicit PUS mapping | Existing reference mapping is target-owned and validated |
| command with non-empty args | blocked | Argument encoding projection is not yet defined |
| telemetry injection | not_projected | No explicit target injection mapping yet |
| expect_mode | not_projected | No explicit target observation mapping |
| expect_event | not_projected | PUS subtype alone is not sufficient event identity |
| expect_command | not_projected | Host dispatch-history semantics differ from runtime evidence |
| expect_command_status | not_projected | Core host acceptance is not PUS acceptance telemetry |
| expect_telemetry | not_projected | No explicit Core telemetry -> OpenSVF ParameterStore observation mapping |
| expect_payload_lifecycle | not_projected | No target lifecycle observation contract |
| expect_data_flow | not_projected | Contract-level host evidence, not runtime evidence |
| expect_scenario_status | not_projected | Aggregate Core scenario result, not a target observation |

This matrix is intentionally conservative.

Stage 7.10 succeeds by making the boundary explicit, not by maximizing the number of translated fields.

---

## 8. First reference projection: `obc.ping`

The first Stage 7.10 executable slice uses the already proven command mapping:

```text
Core command entity
commands:obc.ping
```

Projection Profile binding:

```text
binding: cmd.ping
intent: project
PUS TC: (17,1)
```

The Profile also declares target verification obligations:

```text
TM(1,1)
TM(17,2)
TM(1,7)
```

The resolved provenance is:

```text
Core scenario command action
        |
        | source origin = orbitfabric_scenario
        v
commands:obc.ping
        |
        | resolved through Core Integration Input Set
        v
Profile binding cmd.ping
        |
        | target action origin = profile target mapping
        v
PUS TC(17,1)
        |
        | target verification obligation origin =
        | profile expected_responses
        v
TM(1,1)
TM(17,2)
TM(1,7)
```

The three TM expectations are not promoted into OrbitFabric scenario semantics.

They remain target-specific verification obligations.

---

## 9. Verification Projection Plan

Stage 7.10 introduces a PoC-owned derived artifact:

```text
verification_projection_plan.json
```

This is not a new Core surface.

It is an Integration Package result artifact.

The plan records at least:

```text
kind
plan_version

source:
  scenario identity
  scenario SHA-256
  OrbitFabric version

core_input:
  Integration Input Set identity
  input_set_sha256

profile:
  profile id
  profile version
  profile SHA-256

integration:
  integration id
  schema version
  adapter/package version

projection:
  source atom accounting
  projected atom accounting
  not-projected atom accounting
  blocked atom accounting

operations:
  ordered resolved verification operations

diagnostics:
  explicit projection diagnostics
```

Each resolved operation records provenance.

Representative command operation:

```json
{
  "operation": "pus_tc",
  "source": {
    "scenario_step": 0,
    "scenario_t": 0,
    "domain": "commands",
    "id": "obc.ping"
  },
  "binding_id": "cmd.ping",
  "origin": "profile_mapping",
  "resolved": {
    "apid": 16,
    "service": 17,
    "subtype": 1
  }
}
```

Representative target verification obligation:

```json
{
  "operation": "expect_pus_tm",
  "source": {
    "domain": "commands",
    "id": "obc.ping"
  },
  "binding_id": "cmd.ping",
  "origin": "profile_expected_response",
  "resolved": {
    "service": 17,
    "subtype": 2
  }
}
```

The exact JSON schema is Integration Package-owned.

---

## 10. Coverage and executable status

Projection coverage is explicit.

The plan must separately report:

```text
source action count
source expectation count
projected source action count
projected source expectation count
not-projected source atom count
blocked source atom count
profile verification obligation count
```

A plan may exist even when some atoms are `not_projected`.

However the plan must expose its scope honestly.

Suggested status values:

```text
executable_subset
blocked
```

`executable_subset` means:

```text
all operations selected for this supported projection subset
are fully and faithfully resolved;
unsupported source semantics remain explicitly recorded
as not_projected.
```

It does not mean:

```text
the complete OrbitFabric scenario semantics were reproduced in OpenSVF.
```

`blocked` means at least one semantic atom required for the selected projection cannot be resolved safely.

---

## 11. Fail-closed rules

Stage 7.10 must fail closed when:

```text
scenario is invalid
Core Integration Input Set is incompatible
scenario source entity cannot be resolved
Profile source binding is missing for a selected projected action
Profile binding intent is do_not_project
PUS mapping is incomplete
command arguments are present without an explicit encoder
multiple bindings create ambiguous target action semantics
Profile verification obligation is malformed
projection would require identity inference
projection would require semantic equivalence inference
```

Unsupported-but-known semantics may be recorded as `not_projected`.

Ambiguous semantics must be `blocked`.

---

## 12. OpenSVF materialization

The Verification Projection Plan is the semantic handoff.

OpenSVF campaign/procedure generation is a separate materialization step.

For the first reference slice:

```text
pus_tc
    -> ctx.tc(...)

expect_pus_tm
    -> ctx.expect_tm(...)
```

The generated procedure must not recover semantics by rereading the original scenario or Profile.

It consumes the resolved plan.

This preserves:

```text
source interpretation
!=
target execution materialization
```

and gives one inspectable artifact between the two.

---

## 13. Evidence provenance

The Stage 7.10 evidence chain is:

```text
OrbitFabric scenario
        |
        v
Verification Projection Plan
        |
        v
generated OpenSVF campaign/procedure
        |
        v
native OpenSVF CampaignReport
```

The acceptance validator must be able to prove:

```text
which scenario was consumed
which Core input set was consumed
which Projection Profile was consumed
which source command produced each target TC
which Profile obligation produced each target TM expectation
which OpenSVF procedure executed the resolved plan
which native verdict resulted
```

Stage 7.10 must not label OpenSVF target evidence as if it were the original Core simulation evidence.

They are related through explicit provenance, not semantic identity.

---

## 14. Stage 7.10 acceptance criteria

The first Stage 7.10 slice is accepted when:

1. The four repository baselines are pinned.
2. A valid OrbitFabric scenario is consumed as explicit scenario intent.
3. The matching Core Integration Input Set is validated.
4. The Projection Profile is validated.
5. Every relevant scenario semantic atom receives an explicit disposition.
6. No source semantic atom is silently dropped.
7. `obc.ping` resolves through Core identity `commands:obc.ping`.
8. `obc.ping` resolves through Profile binding `cmd.ping`.
9. The resolved target action is PUS TC(17,1).
10. Profile `expected_responses` produce three target verification obligations.
11. Those obligations retain `profile_expected_response` provenance.
12. Core `command_status` semantics are not inferred from PUS verification reports.
13. Scenario `t` is not converted into onboard scheduling.
14. A deterministic machine-readable Verification Projection Plan is produced.
15. The plan records source, Core-input and Profile SHA-256 provenance.
16. OpenSVF campaign/procedure materialization consumes the resolved plan.
17. Native OpenSVF execution sends TC(17,1).
18. Native OpenSVF execution observes TM(1,1), TM(17,2) and TM(1,7).
19. The native procedure verdict is PASS.
20. Native machine-readable OpenSVF evidence is produced.
21. The validator proves traceability from source scenario command to native target evidence.
22. OpenOBSW repository-owned `srdb/data` remains byte-identical.
23. OpenOBSW and OpenSVF working trees remain unchanged.
24. OrbitFabric Core, OpenOBSW and OpenSVF require no production-code modification for this slice.

---

## 15. Explicit non-goals

Stage 7.10 v0 does not:

```text
modify OrbitFabric scenario semantics
add OpenSVF semantics to Core
claim full scenario semantic equivalence
map Core command_status to PUS acceptance
map scenario time to onboard scheduling
map scenario time to PUS Service 11
project telemetry expectations by string matching
project event expectations from PUS subtype alone
project data-flow evidence into runtime operations
project payload lifecycle semantics
project Core scenario_status into target evidence
introduce live ground commanding
introduce flight scheduling
modify OpenOBSW
modify OpenSVF
introduce Studio-specific semantic authority
```

---

## 16. Implementation sequence

Implementation should proceed in separate acceptance slices.

### 7.10a - Contract and semantic inventory

Freeze this document and the support/disposition matrix.

No executable production projection yet.

### 7.10b - Deterministic Verification Projection Plan

Implement:

```text
validated scenario
+
Core Integration Input Set
+
Projection Profile
    ->
verification_projection_plan.json
```

Validate provenance, atom accounting and fail-closed behavior.

### 7.10c - OpenSVF materialization

Generate PoC-owned OpenSVF campaign/procedure assets from the resolved plan.

No semantic rereading in the materializer.

### 7.10d - Native acceptance

Execute the generated materialization through the native OpenSVF CampaignRunner and verify traceable machine-readable evidence.

---

## 17. Architectural checkpoint

Stage 7.9 established:

```text
OrbitFabric-derived runtime
-> native OpenSVF verification execution
-> machine-readable target evidence
```

Stage 7.10 establishes:

```text
OrbitFabric-authored scenario intent
        +
Core Mission Data Contract identity
        +
Profile-authored target verification configuration
        |
        v
explicit verification projection
        |
        v
traceable OpenSVF verification execution
```

The critical property is not automatic translation.

It is explicit semantic provenance.

No source meaning is silently upgraded, weakened, replaced or inferred.
