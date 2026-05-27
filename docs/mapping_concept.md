# OrbitFabric <-> OpenOBSW / OpenSVF : Integration Concept & Mapping

## 1. Introduction and Scope
This document outlines the conceptual mapping and integration strategy between **OrbitFabric** and the **OpenOBSW / OpenSVF** execution stack. 

The goal of this Proof of Concept (PoC) is to demonstrate a thin vertical slice of an MBSE workflow: using a single source of truth to generate flight-ready C11 artifacts, ground-segment databases, and validate a closed-loop execution.

## 2. High-Level Data Flow
1. **Mission Definition:** Data contracts (Telemetry, Commands, Events) are defined in OrbitFabric Core.
2. **Artifact Generation:** 
   * OrbitFabric exports C header files (`.h`) mapping to OpenOBSW PUS-C structures.
   * OrbitFabric exports an XTCE-compliant database (or SRDB YAML) for OpenSVF/YAMCS.
3. **Execution & Validation:** OpenOBSW (running in Renode or bare-metal STM32) executes the generated contract, communicating via OpenSVF to YAMCS, validating the exact definitions exported in step 2.

## 3. Conceptual Mapping Dictionary

| OrbitFabric Concept | OpenOBSW (Flight Stack - C11) | OpenSVF / YAMCS (Ground Segment) | PUS-C Service Mapping |
| :--- | :--- | :--- | :--- |
| **Telemetry Parameter** | `struct` member / Variable exposed to HAL | XTCE `Parameter` / `SequenceContainer` | Service 3 (Housekeeping) |
| **Command** | `obsw_tc_packet_t` dispatch target | XTCE `MetaCommand` / `ArgumentList` | Service 8 (Function Management) / S17 (Test) |
| **Event / Fault** | Event Trigger function call | YAMCS Event / Alarm | Service 5 (Event Reporting) |
| **Data Types** | C11 Types (`uint8_t`, `float`, etc.) | XTCE Data Encodings | PUS Standard Data Types |
| **Mode / State** | Global State Machine (e.g., Safe, Nominal) | YAMCS System Variables (`/System/Mode`) | Mission Specific |

## 4. The Thin Vertical Slice Definition
To validate the interface without handling edge cases, the initial PoC will implement the following minimal dataset:

### 4.1. Telemetry (TM)
* **Name:** `OBC_Bus_Voltage`
* **Type:** `float` (or `uint16_t` raw ADC value)
* **Behavior:** Sampled at 1Hz.
* **Target:** Automatically packed into a PUS Service 3 TM[3,25] packet by OpenOBSW and decoded by YAMCS.

### 4.2. Telecommand (TC)
* **Name:** `Toggle_Status_LED` or `Ping`
* **Target:** PUS Service 17 (Connection Test) or Service 8 (Function Management).
* **Behavior:** Executed from YAMCS, routed through OpenSVF, processed by OpenOBSW, returning a successful execution report (Service 1 TM[1,1] & TM[1,7]).

### 4.3. Event
* **Name:** `Voltage_Out_Of_Bounds`
* **Trigger:** If `OBC_Bus_Voltage` > Threshold.
* **Target:** OpenOBSW generates a PUS Service 5 TM[5,3] (Warning Event), which triggers an alarm state in YAMCS.

## 5. Way Forward
To close this loop, we need to define the exact format OrbitFabric will export:
1. **For OpenOBSW:** A generated `mission_contract.h` containing the struct definitions for the Housekeeping parameters and the Command ID enums.
2. **For OpenSVF:** An XTCE XML file (or an intermediate YAML file that OpenSVF's current SRDB ingestion tool can read) matching the definitions in `mission_contract.h`.
