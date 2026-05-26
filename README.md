# OrbitFabric ↔ OpenOBSW : MBSE Vertical Slice PoC

## 🚀 The Vision
This repository is a Proof of Concept (PoC) demonstrating a full Model-Based Systems Engineering (MBSE) pipeline for spacecraft software validation. It acts as a bridge between:
*   **[OrbitFabric](lien_vers_orbitfabric):** The model-first Mission Data Contract framework (The Single Source of Truth).
*   **[OpenOBSW](lien_vers_votre_repo) & OpenSVF:** The flight-grade C11 execution stack and simulation ground segment.

## 🎯 The Goal: The "Thin Vertical Slice"
Instead of building a massive system, this PoC focuses on a minimal, end-to-end data flow:
1. Define a data contract in OrbitFabric (1 Telemetry, 1 Command, 1 Event).
2. Generate C definitions (`.h`) for the flight software and XTCE databases for the ground segment.
3. Execute the contract on OpenOBSW (via Renode/STM32).
4. Validate the loop in YAMCS via OpenSVF.

## 📂 Repository Structure
*   `/docs`: System engineering documents mapping the concepts.
*   `/orbitfabric_models`: The raw mission models (The Contract).
*   `/generated_artifacts`: The code and databases generated from the models.
*   `/execution`: Scripts to run the closed-loop validation campaign.

## 🛠️ Current Status
* [x] Define high-level mapping concepts (See `/docs/mapping_concept.md`)
* [ ] Define the minimal OrbitFabric model
* [ ] Generate artifacts
* [ ] Execute the validation campaign
