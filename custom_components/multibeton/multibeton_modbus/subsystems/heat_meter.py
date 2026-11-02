"""Optional vortex-type heat/cold quantity meter ("Wirbel-Wärmemengenzähler").

Read from the input-register table (Modbus function code 0x04), source
sheet "Lesen-Schreiben", addresses 5510-5533. This is an optional accessory
meter, not present on every installation - if none is fitted, expect these
registers to read 0 or a fixed sentinel rather than an exception.

UNSCALED - READ THIS BEFORE TRUSTING A NUMBER FROM THIS COMPONENT:
Every measured value here (flow, power, cumulative heat/cold quantity,
pressure) is paired in the source documentation with its own "Einheit"
(unit/scale) register - a classic industrial flow-computer pattern where a
code in that register selects both the physical unit and the decimal scale
of the value next to it (e.g. "kWh vs. MWh", "x1 vs. x0.1"). The
documentation available when this library was written names each pairing
but never gives the actual code table (what each numeric "Einheit" value
means), so this module exposes every measured field as its *raw* decoded
integer plus its raw, undecoded "*_unit_code" sibling where one exists -
deliberately not scaled to kWh/l/h/bar, because guessing the scale would
risk presenting a confidently wrong number as real data.

Before using ``heat_cumulative_raw`` (the register most people want - the
device's own cumulative heat-quantity counter) for anything, read it
alongside ``heat_cumulative_unit_code`` against a real controller and
compare to a known-good reading (e.g. the unit's own display, if it has
one) to work out the scale empirically, then encode that as a proper
``gauge()``/``uint32(..., scale=...)`` field here once confirmed.
"""

from __future__ import annotations

from ..data_model import MultibetonComponent, integer, uint32


class HeatMeter(MultibetonComponent):
    """Optional heat/cold-quantity meter - raw, unscaled values.

    See the module docstring: nothing here is scaled to an engineering
    unit yet, because the "Einheit" scale-code registers this device pairs
    with each value are undocumented in the source material.
    """

    register_space = "input"

    flow_instant_raw = uint32(
        5510,
        maker_key="Momentandurchfluss",
        description="Raw, unscaled. See module docstring.",
    )
    flow_instant_unit_code = integer(
        5512,
        maker_key="Einheit Momentandurchfluss",
        description="Undecoded scale/unit code for flow_instant_raw.",
    )
    power_instant_raw = uint32(
        5513,
        maker_key="Leistung",
        description="Raw, unscaled. See module docstring.",
    )
    power_instant_unit_code = integer(
        5515,
        maker_key="Einheit Leistung",
        description="Undecoded scale/unit code for power_instant_raw.",
    )
    flow_cumulative_raw = uint32(
        5516,
        maker_key="Durchfluss kumuliert",
        description="Raw, unscaled. See module docstring.",
    )
    flow_cumulative_unit_code = integer(
        5518,
        maker_key="Einheit Durchfluss kumuliert",
        description="Undecoded scale/unit code for flow_cumulative_raw.",
    )
    heat_cumulative_raw = uint32(
        5519,
        maker_key="Wärmemenge kumuliert",
        description=(
            "Raw, unscaled cumulative heat quantity - the register most "
            "likely wanted as a kWh energy counter. See module docstring "
            "before trusting a value from this field."
        ),
    )
    heat_cumulative_unit_code = integer(
        5521,
        maker_key="Einheit Wärmemenge kumuliert",
        description="Undecoded scale/unit code for heat_cumulative_raw.",
    )
    cold_cumulative_raw = uint32(
        5522,
        maker_key="Kältemenge kumuliert",
        description="Raw, unscaled. See module docstring.",
    )
    cold_cumulative_unit_code = integer(
        5524,
        maker_key="Einheit Kältemenge kumuliert",
        description="Undecoded scale/unit code for cold_cumulative_raw.",
    )
    flow_temp_raw = uint32(
        5525,
        maker_key="Vorlauftemperatur",
        description=(
            "The meter's own flow-temperature reading, raw/unscaled - a "
            "second, independent sensor from Sensors.system_flow_temp."
        ),
    )
    return_temp_raw = uint32(
        5527,
        maker_key="Rücklauftemperatur",
        description="The meter's own return-temperature reading, raw/unscaled.",
    )
    status = integer(
        5529,
        maker_key="Status",
    )
    runtime_with_flow_raw = uint32(
        5530,
        maker_key="Betriebszeit (mit Durchfluss)",
        description="Raw, unscaled. See module docstring.",
    )
    pressure_raw = integer(
        5532,
        maker_key="Druck",
        description="Raw, unscaled. See module docstring.",
    )
    pressure_unit_code = integer(
        5533,
        maker_key="Einheit Druck",
        description="Undecoded scale/unit code for pressure_raw.",
    )
