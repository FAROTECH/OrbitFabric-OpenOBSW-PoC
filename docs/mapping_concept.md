# OrbitFabric <-> OpenOBSW / OpenSVF : Integration Concept & Mapping

## 1. Introduction and Scope
This document outlines the conceptual mapping and integration strategy between **OrbitFabric** and the **OpenOBSW / OpenSVF** execution stack. 

The goal of this Proof of Concept (PoC) is to demonstrate a thin vertical slice of an MBSE workflow: using a single source of truth to generate flight-ready C11 artifacts, ground-segment databases, and validate a closed-loop execution.

## 2. High-Level Data Flow
1. **Mission Definition:** Data contracts (Telemetry, Commands, Events) are defined in OrbitFabric Core (`orbitfabric_models/`).
2. **Artifact Generation (via PoC adapter):**
   * **Flight side:** OrbitFabric generates `mission_contract.h` — a C11 contract header containing stable IDs (enums), housekeeping payload structs, and command argument structs. No runtime logic, no PUS framing, no transport.
   * **Ground side:** OrbitFabric generates an SRDB YAML. OpenSVF's existing `generate_xtce.py` tooling then produces the YAMCS XTCE MDB from that YAML. OrbitFabric Core does not emit XTCE directly.
3. **Execution:** OpenOBSW (Renode or host simulation first; STM32 bare-metal once the contract boundary is stable) consumes `mission_contract.h` and runs the contracted telemetry, command, and event logic.
4. **Validation:** OpenSVF drives the closed-loop campaign; YAMCS receives TM, issues TC, and triggers alarms based on the SRDB-derived XTCE MDB.

## 3. Conceptual Mapping Dictionary

| OrbitFabric Concept | OpenOBSW (Flight Stack - C11) | OpenSVF / YAMCS (Ground Segment) | PUS-C Service Mapping |
| :--- | :--- | :--- | :--- |
| **Telemetry Parameter** | `struct` member / Variable exposed to HAL | XTCE `Parameter` / `SequenceContainer` | Service 3 (Housekeeping) |
| **Command** | `obsw_tc_packet_t` dispatch target | XTCE `MetaCommand` / `ArgumentList` | Service 8 (Function Management) / S17 (Test) |
| **Event / Fault** | Event Trigger function call | YAMCS Event / Alarm | Service 5 (Event Reporting) |
| **Data Types** | C11 Types (`uint8_t`, `float`, etc.) | XTCE Data Encodings | PUS Standard Data Types |
| **Mode / State** | Context-scoped FSM (state carried via context pointer, e.g., Safe, Nominal) | YAMCS System Variables (`/System/Mode`) | Mission Specific |

## 4. The Thin Vertical Slice Definition
To validate the interface without handling edge cases, the initial PoC will implement the following minimal dataset:

### 4.1. Telemetry (TM)
* **Contract name:** `obc_bus_voltage_mv`
* **Type:** `uint16_t` — raw millivolts. Engineering conversion (scaling, units, limits) lives in the SRDB/YAMCS layer, not in the flight header.
* **Behavior:** Sampled at 1 Hz, packed into a PUS Service 3 TM[3,25] housekeeping report (HK set `obc_hk`, SID `0x01`).
* **SRDB canonical name:** `eps.obc.bus_voltage_mv`

### 4.2. Telecommand (TC)
* **Contract name:** `ping`
* **Target:** PUS Service 17 TC[17,1] (Connection Test). Chosen for the first slice for its minimal dispatch complexity.
* **Behavior:** Issued from YAMCS, routed through OpenSVF, processed by OpenOBSW. Expected response chain: TM[1,1] (acceptance) → TM[1,7] (execution complete) → TM[17,2] (connection test response).
* **SRDB canonical name:** `dhs.obc.ping`
* **Note:** `toggle_status_led` / Service 8 (Function Management) is the natural next command once the S17 path is proven.

### 4.3. Event
* **Contract name:** `voltage_out_of_bounds`
* **Trigger:** `obc_bus_voltage_mv` exceeds threshold (placeholder: 3500 mV — to be confirmed).
* **Target:** OpenOBSW generates PUS Service 5 TM[5,3] (Warning Event), which triggers a YAMCS alarm state.
* **SRDB canonical name:** `eps.obc.voltage_out_of_bounds`

## 5. Way Forward

Settled decisions (from [issue #1](https://github.com/lipofefeyt/OrbitFabric-OpenOBSW-PoC/issues/1)):

| Decision | Resolution |
|:---|:---|
| `mission_contract.h` role | Contract-only header: IDs (enums), HK payload struct, command argument structs. No runtime logic, no PUS framing. |
| C prefix | `OF_` |
| Ground artifact path | OrbitFabric → SRDB YAML → OpenSVF `generate_xtce.py` → YAMCS XTCE MDB |
| First execution target | OpenOBSW host simulation or Renode; STM32 bare-metal deferred |
| OrbitFabric entry point | OrbitFabric Core (`github.com/FAROTECH/orbitfabric`); Studio is not a PoC dependency |

**Pending (blocking `mission_contract.h` generation):**
- Confirmation from OrbitFabric Core on whether the proposed ID ranges (`0x4001` / `0x1701` / `0x5001`) match an existing convention or need to be redefined.

**Next steps once IDs are confirmed:**
1. Generate `generated_artifacts/flight_software/mission_contract.h` from `orbitfabric_models/poc_slice.yaml`.
2. Generate `generated_artifacts/ground_segment/poc_srdb.yaml` and run OpenSVF's `generate_xtce.py` to produce the YAMCS MDB.
3. Wire `obc_bus_voltage_mv` into OpenOBSW's S3 HK report and the `ping` dispatcher into S17.
4. Run the OpenSVF closed-loop campaign against the Renode/host-sim target.
