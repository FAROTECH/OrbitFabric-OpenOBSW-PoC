from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from orbitfabric_openobsw_opensvf.flight_contract import (
    FlightContractError,
    render_flight_contract,
    write_flight_contract,
)


def _resolved() -> dict:
    return {
        "kind": "orbitfabric.openobsw_opensvf.resolved_projection",
        "resolved_projection_version": "0.1-candidate",
        "settings": {
            "flight_contract": {
                "c_symbol_prefix": "OF_",
                "contract_name": "poc-openobsw-opensvf",
                "contract_version": "0.1.0",
            }
        },
        "projections": [
            {
                "binding_id": "tm.obc_bus_voltage",
                "kind": "telemetry_parameter",
                "target": {
                    "kind": "telemetry_parameter",
                    "numeric_id": 0x4001,
                    "c_symbol": "OF_TM_OBC_BUS_VOLTAGE_MV",
                    "c_type": "uint16_t",
                    "field_name": "obc_bus_voltage_mv",
                },
            },
            {
                "binding_id": "cmd.ping",
                "kind": "command",
                "target": {
                    "kind": "command",
                    "numeric_id": 0x1701,
                    "c_symbol": "OF_CMD_PING",
                },
            },
            {
                "binding_id": "event.voltage_out_of_bounds",
                "kind": "event",
                "target": {
                    "kind": "event",
                    "numeric_id": 0x5001,
                    "c_symbol": "OF_EVENT_VOLTAGE_OUT_OF_BOUNDS",
                },
            },
            {
                "binding_id": "hk.obc",
                "kind": "housekeeping_packet",
                "target": {
                    "kind": "housekeeping_packet",
                    "sid": 1,
                    "c_symbol": "OF_HK_SET_OBC",
                    "collection_interval_s": 1,
                    "struct_type": "of_hk_obc_t",
                    "members": [
                        {
                            "core_id": "eps.obc.bus_voltage_mv",
                            "c_type": "uint16_t",
                            "field_name": "obc_bus_voltage_mv",
                        }
                    ],
                },
            },
        ],
    }


def test_render_flight_contract_materializes_only_resolved_values() -> None:
    header = render_flight_contract(_resolved())
    assert '#define OF_CONTRACT_NAME "poc-openobsw-opensvf"' in header
    assert '#define OF_CONTRACT_VERSION "0.1.0"' in header
    assert "OF_TM_OBC_BUS_VOLTAGE_MV = 0x4001" in header
    assert "OF_CMD_PING = 0x1701" in header
    assert "OF_EVENT_VOLTAGE_OUT_OF_BOUNDS = 0x5001" in header
    assert "OF_HK_SET_OBC = 0x0001" in header
    assert "#define OF_HK_SET_OBC_COLLECTION_INTERVAL_S 1u" in header
    assert "uint16_t obc_bus_voltage_mv;" in header
    assert "} of_hk_obc_t;" in header
    assert "Mission Snapshot" not in header
    assert "Projection Profile" not in header


def test_materializer_does_not_invent_missing_target_representation() -> None:
    resolved = _resolved()
    del resolved["projections"][0]["target"]["c_symbol"]
    try:
        render_flight_contract(resolved)
    except FlightContractError as exc:
        assert "c_symbol" in str(exc)
    else:
        raise AssertionError("expected FlightContractError")


def test_projection_input_order_does_not_change_header() -> None:
    resolved = _resolved()
    first = render_flight_contract(resolved)
    reversed_input = deepcopy(resolved)
    reversed_input["projections"] = list(reversed(reversed_input["projections"]))
    assert render_flight_contract(reversed_input) == first


def test_write_flight_contract_is_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first.h"
    second = tmp_path / "second.h"
    write_flight_contract(_resolved(), first)
    write_flight_contract(_resolved(), second)
    assert first.read_bytes() == second.read_bytes()
