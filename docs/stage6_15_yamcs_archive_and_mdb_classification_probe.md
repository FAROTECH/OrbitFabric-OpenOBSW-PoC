# Stage 6.15 - YAMCS Archive and MDB Classification Probe

## Purpose

Stage 6.15 combines the next two YAMCS visibility steps into one local runtime probe:

```text
Stage 6.14 bridge-compatible producer
-> YAMCS tm-in TcpTmDataLink
-> YAMCS packet archive API
-> representative raw TM packet visibility
-> MDB leaf-container classification evidence
```

This stage intentionally accelerates the previous plan by combining packet archive visibility and packet classification evidence into one reviewable stage.

## API surface used

The stage uses the YAMCS packet archive API:

```text
GET /api/archive/{instance}/packets
```

For the `opensvf` instance, the validator checks that representative raw packet bytes are present in archived packet records.

The stage also uses the YAMCS MDB containers API:

```text
GET /api/mdb/{instance}/containers
```

For the `opensvf` instance, the validator checks that the generated MDB exposes:

```text
TM_3_25_HK
TM_5_3_Event
```

## Runtime setup

The stage reuses the Stage 6.14 bridge-compatible TM producer, but runs it with a longer packet stream:

```text
cycles: 25
delay: 0.20 s
linger: 20.0 s
```

The producer sends representative packets for:

```text
TM(3,25) - housekeeping side
TM(5,3)  - event side, with event ID 0x5001
```

The packets use the same PUS-C secondary header version byte (`0x20`) as Stage 6.12.

## Pass criteria

The validator requires all of the following:

```text
YAMCS tm-in status OK
YAMCS tm-in dataInCount >= 2
MDB container TM_3_25_HK visible through API
MDB container TM_5_3_Event visible through API
Representative raw TM(3,25) packet archived
Representative raw TM(5,3) packet archived
Packet archive name classified as TM_3_25_HK
Packet archive name classified as TM_5_3_Event
```

If YAMCS receives and archives packets but only exposes a base packet/container name, this validator fails intentionally and prints the observed archive names, links and packet sizes. That failure is useful evidence for the next investigation.

## Claims

This stage claims only:

```text
YAMCS TcpTmDataLink packet consumption: true
YAMCS packet archive raw packet visibility: true
YAMCS MDB container definitions visible via API: true
YAMCS MDB packet classification observed via archive name: true
```

## Explicit non-claims

This stage does not claim live OpenSVF YamcsBridge execution.

This stage does not claim live OpenOBSW packet generation.

This stage does not claim closed-loop runtime execution.

This stage does not claim YAMCS parameter/event API extraction.

This stage does not claim production deployment hardening.
