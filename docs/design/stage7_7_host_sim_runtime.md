# Stage 7.7 — Full OpenOBSW host-sim build and runtime consumption

## Goal

Cross the first real OpenOBSW runtime boundary while preserving the ownership rules established by Stages 7.4–7.6.

The acceptance flow is:

```text
OrbitFabric Stage 7.4 bundle
        |
        +-- flight_software/mission_contract.h
        |
        `-- obsw_srdb_contribution/
                |
                v
        target-owned SRDB composition
                |
                v
        target-owned complete SRDB materialization
                |
                v
        OpenOBSW CMake configure
          SRDB_DATA_DIR=<external assembled SRDB>
          ORBITFABRIC_CONTRACT_DIR=<generated contract directory>
          OBSW_ENABLE_ORBITFABRIC_CONTRACT=ON
                |
                v
        full obsw_sim build
                |
                +-- TC(17,1) ping runtime smoke
                `-- TC(8,1) OrbitFabric event runtime smoke
```

## Boundary

This stage does not add another OpenOBSW target change. The Stage 7.6 target reference already provides the two build inputs required by the existing host simulator:

- external complete SRDB via `SRDB_DATA_DIR`;
- generated OrbitFabric flight contract via `ORBITFABRIC_CONTRACT_DIR`.

The existing host-sim CMake target links `obsw_srdb_generated` and conditionally compiles the existing OrbitFabric contract adapter when `OBSW_ENABLE_ORBITFABRIC_CONTRACT=ON`.

## Acceptance claims

A passing Stage 7.7 gate proves:

1. the Stage 7.4 additive SRDB contribution can be composed and materialized through target-owned APIs;
2. the full OpenOBSW host-sim target builds from that external complete SRDB;
3. the same binary compiles against the Stage 7.4 generated `mission_contract.h`;
4. the existing `obc.ping` mapping is exercised at runtime as TC(17,1) and produces TM(17,2), with normal PUS verification reports;
5. the generated OrbitFabric event contract ID `0x5001` is exercised by the existing host-sim S8 hook and appears in TM(5,3);
6. the native `srdb/data` source directory remains unchanged.

## Non-goals

This stage does not claim:

- OpenSVF execution;
- YAMCS integration;
- hardware execution;
- generic runtime generation from arbitrary OrbitFabric commands/events;
- replacement of OpenOBSW routing or service implementation;
- runtime verification beyond the two explicit host-sim smoke paths.

The host-sim S8 event trigger remains a test hook. Its purpose here is to prove that a generated OrbitFabric event contract is present in, compiled into and observable from the real OpenOBSW runtime path.

## Next boundary

After this gate, the next meaningful integration seam is OpenSVF consumption of the same externally assembled target definition and OpenOBSW host-sim runtime, rather than another static artifact step.
