"""System temperature sensors and the heating-curve operating point.

Read from the input-register table (Modbus function code 0x04), source
sheet "Analogwerte" of the manufacturer's register documentation.
"""

from __future__ import annotations

from ..data_model import MultibetonComponent, gauge

# Sensor-absent/fault sentinel values documented on the "Analogwerte" sheet
# for every analog input, by their signed decimal meaning: -32700 = sensor
# not present, -32701 = sensor fault, -32702 = sensor open circuit,
# -32703 = sensor short circuit.
#
# A field's `nan` set is matched against the *raw* (unsigned 16-bit) register
# pattern before sign-folding (see modbus_connection.model.fields.NumberField
# .decode), so the signed sentinel values above must be converted to their
# two's-complement raw word form here - passing the negative decimals
# directly would never match and the sentinel would silently decode as a
# large negative temperature/pressure instead of ``None``.
_SENSOR_FAULT_SIGNED_CODES = (-32700, -32701, -32702, -32703)
SENSOR_FAULT_CODES = tuple(code & 0xFFFF for code in _SENSOR_FAULT_SIGNED_CODES)


class Sensors(MultibetonComponent):
    """System temperature sensors and the heating-curve operating point.

    The compressor-circuit values of each module live on
    :class:`~multibeton_modbus.subsystems.module.Module`. The curve flow
    temperatures 1342-1345 are listed per module as well; they are read
    from module 0# here because the curve is a property of the system.
    """

    register_space = "input"

    curve_flow_temp_zone_a = gauge(
        1342,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Kennlinien-Vorlauftemperatur Zone A",
        description=(
            "Vorlauf-Solltemperatur, die die gewählte Heiz-/Kühlkennlinie "
            "für Zone A beim aktuellen Arbeitspunkt fordert."
        ),
    )
    curve_flow_temp_zone_a_corrected = gauge(
        1343,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Korrigierte Kennlinien-Vorlauftemperatur Zone A",
        description="Wie curve_flow_temp_zone_a, nach Anwendung der Korrekturen.",
    )
    curve_flow_temp_zone_b = gauge(
        1344,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Kennlinien-Vorlauftemperatur Zone B",
    )
    curve_flow_temp_zone_b_corrected = gauge(
        1345,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Korrigierte Kennlinien-Vorlauftemperatur Zone B",
    )
    room_temp = gauge(
        3348,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Raumtemperatur",
        description="System resource column, not per-module.",
    )
    ambient_temp = gauge(
        3350,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Umgebungstemperatur",
        description="Outdoor temperature.",
    )
    dhw_tank_temp = gauge(
        3351,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Temperatur Warmwasserspeicher",
    )
    system_flow_temp = gauge(
        3353,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Gesamt-Vorlauftemperatur System",
    )
    solar_temp = gauge(
        3354,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Solartemperatur",
    )
    buffer_top_temp = gauge(
        3355,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Temperatur Pufferspeicher oben",
    )
    buffer_bottom_temp = gauge(
        3356,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Temperatur Pufferspeicher unten",
    )
    climate_flow_temp = gauge(
        3357,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Gesamt-Vorlauftemperatur Klimabetrieb",
    )
    floor_heating_flow_temp = gauge(
        3362,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Vorlauftemperatur Fußbodenheizung",
    )
    mean_ambient_temp = gauge(
        3377,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Mittlere Umgebungstemperatur",
        description=(
            "Gemittelter Außenwert der Regelung. Nicht zu verwechseln mit "
            "SystemStatus.curve_ambient_temp, die die Kennlinie auswertet. "
            "An der Anlage stand er zeitweise vier Grad über dem Rohwert "
            "von ambient_temp, zu einem anderen Zeitpunkt gleichauf - über "
            "welchen Zeitraum gemittelt wird, sagt die Tabelle nicht."
        ),
    )
    return_temp_zone_a = gauge(
        3376,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Rücklauftemperatur Zone A",
        description=(
            "Return-water temperature for climate zone A - pairs with "
            "climate_flow_temp/floor_heating_flow_temp for a flow/return "
            "reading. Documented on the 'Analogwerte' sheet's system-resource "
            "column (source label 'A区进水温度')."
        ),
    )
