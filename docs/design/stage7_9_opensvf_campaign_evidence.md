# Stage 7.9: Native OpenSVF Campaign and Verification Evidence

## Objective

Validate that the OrbitFabric-derived OpenOBSW runtime accepted through Stage 7.8 can be exercised through the native OpenSVF Campaign Runner and can produce native machine-readable verification evidence.

Stage 7.9 moves from runtime consumption to verification execution.

## Reference baselines

PoC upstream main:

`8cbd1e0254ef6566d093b774f22817c296b498ed`

OpenOBSW upstream main:

`44ceb71a016f0541ff7a0aa74191e13bafdb59c1`

OpenSVF:

`667d3eadcb0bbd7814ac324b99946c4ed2f11f23`

## Execution chain

OrbitFabric Mission Model

-> Core Integration Input Set

-> Adapter artifact generation

-> target-owned SRDB composition

-> native OpenOBSW host-sim build

-> OpenSVF spacecraft configuration using `OBCEmulatorAdapter` in pipe mode

-> native `CampaignRunner`

-> PoC-owned native OpenSVF `Procedure`

-> TC(17,1)

-> TM(17,2)

-> native procedure verdict

-> native campaign report JSON

## Verification procedure

The first Stage 7.9 procedure intentionally exercises the already-established ping mapping:

`OrbitFabric obc.ping -> OpenOBSW are_you_alive -> TC(17,1) -> TM(17,2)`

The procedure uses the native OpenSVF `ProcedureContext` API:

* `ctx.tc(service=17, subservice=1)`
* `ctx.expect_tm(service=17, subservice=2)`

The procedure requirement identifier is PoC-owned:

`POC-S79-001`

This identifier does not claim projection from an OrbitFabric verification requirement.

## Evidence

Stage 7.9 requires the native OpenSVF campaign report to be written as machine-readable JSON.

The evidence must contain:

* campaign identity
* procedure identity
* declared requirement
* requirement coverage
* procedure verdict
* step-level verdicts
* campaign pass accounting
* execution duration

A successful Stage 7.9 acceptance requires the procedure and campaign to report PASS and `POC-S79-001` to be covered.

## Acceptance criteria

1. PoC, OpenOBSW and OpenSVF references are pinned.
2. The OrbitFabric-derived OpenOBSW host-sim binary is rebuilt from the Stage 7 artifact chain.
3. A PoC-owned OpenSVF spacecraft configuration uses native pipe mode.
4. The configured OBC model is the native `OBCEmulatorAdapter`.
5. The native OpenSVF `CampaignRunner` loads and executes the campaign.
6. The native procedure sends TC(17,1).
7. The native procedure observes TM(17,2).
8. The procedure verdict is PASS.
9. Campaign accounting reports one PASS and no FAIL or ERROR verdicts.
10. `POC-S79-001` is declared and covered.
11. A native machine-readable campaign report JSON is produced.
12. The report contains step-level verification evidence.
13. OpenOBSW repository-owned `srdb/data` remains unchanged.
14. OpenOBSW and OpenSVF source trees are not modified by execution.

## Scope boundary

Stage 7.9 does not:

* modify OrbitFabric Core
* modify OpenOBSW
* modify OpenSVF
* project OrbitFabric scenario semantics into OpenSVF campaign semantics
* claim OrbitFabric-native verification evidence
* introduce onboard scheduling
* exercise periodic housekeeping scheduling
* require YAMCS
* add Studio-specific behavior

The campaign and procedure definitions are PoC-owned integration assets.

## Architectural checkpoint

Stage 7.9 establishes:

OrbitFabric-derived runtime

-> native OpenSVF verification execution

-> native machine-readable verification evidence

It does not yet establish:

OrbitFabric verification semantics

-> explicit verification projection

-> OpenSVF campaign semantics

That mapping remains a separate Stage 7.10 concern.
