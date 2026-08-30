# Stage 7.8 — OpenSVF runtime consumption

## Objective

Demonstrate that the OpenOBSW host-sim binary produced from the OrbitFabric-derived
contract and composed SRDB can be consumed directly by the pinned OpenSVF runtime
through its native `OBCEmulatorAdapter`.

This stage must not add OrbitFabric-specific behavior to OpenSVF.

## Reference baselines

- OpenOBSW build/runtime reference:
  `44ceb71a016f0541ff7a0aa74191e13bafdb59c1`
- OpenSVF reference:
  `667d3eadcb0bbd7814ac324b99946c4ed2f11f23`

## Input chain

```text
OrbitFabric Mission Model
        ↓
Core Integration Input Set
        ↓
Projection Profile
        ↓
Adapter project
        ├── mission_contract.h
        └── additive obsw-srdb contribution
                 ↓
          SRDBComposer
                 ↓
          SRDBMaterializer
                 ↓
          complete external SRDB
                 ↓
          OpenOBSW CMake build
                 ↓
             obsw_sim
                 ↓
       OpenSVF OBCEmulatorAdapter
                 ↓
       native simulation ticks / TC-TM
```

## Acceptance boundary

The Stage 7.8 validator shall:

1. require the exact pinned OpenOBSW and OpenSVF commits;
2. compose and materialize the Stage 7.4 contribution using target-owned APIs;
3. build the complete OpenOBSW `obsw_sim` with:
   - external `SRDB_DATA_DIR`;
   - generated `mission_contract.h`;
   - `OBSW_ENABLE_ORBITFABRIC_CONTRACT=ON`;
4. import `OBCEmulatorAdapter` from the pinned OpenSVF checkout without modifying it;
5. start the generated `obsw_sim` through the adapter's normal pipe transport;
6. execute native OpenSVF simulation ticks;
7. verify the adapter completes synchronization and publishes readiness each tick;
8. verify OBC time advances through the OpenSVF-visible port;
9. verify an OpenSVF mode command is consumed through the real TC path;
10. verify OpenOBSW source SRDB files remain byte-identical.

## Non-goals

This stage does not:

- patch OpenSVF;
- introduce an OrbitFabric-specific OpenSVF plugin;
- generate OpenSVF campaign semantics from OrbitFabric;
- claim verification coverage or mission validation;
- integrate YAMCS;
- change the OpenSVF SRDB model;
- change OrbitFabric Core or the Projection Profile contract.

## Meaning of success

A PASS means the downstream runtime chain has crossed both target boundaries:

```text
OrbitFabric-derived artifacts
    -> native OpenOBSW build/runtime
    -> native OpenSVF binary adapter/runtime
```

It does not yet mean that OpenSVF campaigns or verification procedures are
generated from OrbitFabric mission semantics.
