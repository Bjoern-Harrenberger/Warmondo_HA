"""Electrical power drawn and thermal power delivered.

Read from the input-register table (Modbus function code 0x04). The three
5500-block rows sit on the "Lesen-Schreiben" sheet but are documented
read-only; the 3367-3372 block sits on the "Analogwerte" sheet and carries
that sheet's sensor sentinels.

Registers 3367-3372 pair an electrical input with the thermal output it
produced, separately for cooling, heating and domestic hot water. That
pairing is what makes an efficiency figure possible at all: the plant-wide
``power_consumption`` cannot be divided by a capacity, because it also
covers the mode the plant is not currently running in.
"""

from __future__ import annotations

from ..data_model import MultibetonComponent, gauge, integer
from .sensors import SENSOR_FAULT_CODES


class Power(MultibetonComponent):
    """Electrical power drawn and thermal power delivered."""

    register_space = "input"

    power_consumption = integer(
        5500,
        unit="W",
        maker_key="Aktuelle Leistungsaufnahme der Anlage",
        description=(
            "Tatsächliche Leistungsaufnahme der Anlage, ohne Zusatzheizstab "
            "und Speicher-Heizstab"
        ),
    )
    aux_heater_power = integer(
        5501,
        unit="W",
        maker_key="Aktuelle Leistung Zusatzheizstab",
    )
    aux_heater_power_configured = integer(
        5502,
        unit="W",
        maker_key="Konfigurierte Leistung Zusatzheizstab",
    )

    # -- electrical input per operating mode ---------------------------------
    cooling_power_input = gauge(
        3367,
        0.01,
        unit="kW",
        nan=SENSOR_FAULT_CODES,
        maker_key="Kühlleistungsaufnahme",
        description="Elektrische Leistungsaufnahme im Kühlbetrieb.",
    )
    heating_power_input = gauge(
        3368,
        0.01,
        unit="kW",
        nan=SENSOR_FAULT_CODES,
        maker_key="Heizleistungsaufnahme",
        description="Elektrische Leistungsaufnahme im Heizbetrieb.",
    )
    dhw_power_input = gauge(
        3369,
        0.01,
        unit="kW",
        nan=SENSOR_FAULT_CODES,
        maker_key="Leistungsaufnahme Warmwasserbereitung",
        description="Elektrische Leistungsaufnahme bei der Warmwasserbereitung.",
    )

    # -- thermal output per operating mode -----------------------------------
    cooling_capacity = gauge(
        3370,
        0.01,
        unit="kW",
        nan=SENSOR_FAULT_CODES,
        maker_key="Kälteleistung",
        description="Abgegebene Kälteleistung im Kühlbetrieb.",
    )
    heating_capacity = gauge(
        3371,
        0.01,
        unit="kW",
        nan=SENSOR_FAULT_CODES,
        maker_key="Heizleistung",
        description="Abgegebene Heizleistung im Heizbetrieb.",
    )
    dhw_capacity = gauge(
        3372,
        0.01,
        unit="kW",
        nan=SENSOR_FAULT_CODES,
        maker_key="Heizleistung Warmwasser",
        description="Abgegebene Heizleistung bei der Warmwasserbereitung.",
    )
