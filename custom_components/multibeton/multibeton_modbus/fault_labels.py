"""The manufacturer's German plain-text label of every modeled fault bit.

The fault words are read as ``IntFlag`` values (see
:mod:`multibeton_modbus.enums`), whose member names are English identifiers
chosen for the code. The register table documents each bit under a German
name instead, and that name is what the controller's own display shows and
what a service technician looks up. :func:`fault_label` maps one to the
other, so a caller can report "Störung Drucksensor J5" rather than
``PRESSURE_SENSOR_J5_FAULT``.

Labels are taken verbatim from sheet "Stoerungen Wort (FC04)" of
``docs/Multibeton_Registertabelle_DE_flach.xlsx``, column "Beschreibung",
which lists them per bit as ``B<n>: <Text>``. They exist in German only -
the manufacturer documents no English wording - so this module stays
untranslated rather than inventing one.

The labels are keyed by flag class and then by bit value, not by the flag
member itself: ``IntFlag`` members compare and hash as plain integers, so
one flat mapping would silently collapse every bit 0 of every fault word
into a single entry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .enums import (
    CompressorFaults1,
    SystemFaults1,
    SystemFaults6,
    UnitFaults1,
    UnitFaults2,
)

if TYPE_CHECKING:
    from enum import IntFlag

__all__ = ["FAULT_LABELS", "fault_label"]

#: Every modeled fault bit under the German name the register table gives it.
FAULT_LABELS: dict[type[IntFlag], dict[int, str]] = {
    CompressorFaults1: {  # Verdichterstörungen 1
        CompressorFaults1.LOW_PRESSURE.value: "Verdichter Niederdruck",
        CompressorFaults1.HIGH_PRESSURE.value: "Verdichter Hochdruck",
        CompressorFaults1.FIN_TEMP_FAULT.value: "Störung Lamellentemperatur",
        CompressorFaults1.DISCHARGE_TEMP_FAULT.value: "Störung Heißgastemperatur",
        CompressorFaults1.DISCHARGE_TEMP_TOO_HIGH.value: "Heißgastemperatur zu hoch",
        CompressorFaults1.PRESSURE_SENSOR_J5_FAULT.value: "Störung Drucksensor J5",
        CompressorFaults1.PRESSURE_SENSOR_J6_FAULT.value: "Störung Drucksensor J6",
        CompressorFaults1.LOW_PRESSURE_TOO_LOW.value: (
            "Niederdruck (Drucksensor) zu niedrig"
        ),
        CompressorFaults1.HIGH_PRESSURE_TOO_HIGH.value: (
            "Hochdruck (Drucksensor) zu hoch"
        ),
        CompressorFaults1.SUCTION_TEMP_FAULT.value: "Störung Sauggastemperatur",
        CompressorFaults1.AFTER_VALVE_TEMP_FAULT.value: (
            "Störung Temperatur nach Ventil"
        ),
        CompressorFaults1.SUCTION_TEMP_TOO_LOW.value: "Sauggastemperatur zu niedrig",
        CompressorFaults1.EMERGENCY_DEFROST_TOO_FREQUENT.value: "Notabtauung zu häufig",
        CompressorFaults1.SUCTION_DISCHARGE_DIFF_IMPLAUSIBLE.value: (
            "Temperaturdifferenz Saug-/Heißgas unplausibel"
        ),
    },
    UnitFaults1: {  # Einheitenstörungen 1
        UnitFaults1.AMBIENT_TEMP_FAULT.value: "Störung Umgebungstemperatur",
        UnitFaults1.COMMUNICATION_FAULT.value: "Kommunikationsstörung",
        UnitFaults1.EEPROM_DATA_ERROR.value: "EEPROM-Datenfehler",
        UnitFaults1.AUX_HEATER_OVERLOAD.value: "Überlast Zusatzheizstab",
        UnitFaults1.PHE_FLOW_TEMP_TOO_LOW.value: (
            "Vorlauftemperatur Plattenwärmetauscher zu niedrig"
        ),
        UnitFaults1.PHE_FLOW_TEMP_TOO_HIGH.value: (
            "Vorlauftemperatur Plattenwärmetauscher zu hoch"
        ),
        UnitFaults1.PHE_FLOW_TEMP_FAULT.value: (
            "Störung Vorlauftemperatur Plattenwärmetauscher"
        ),
        UnitFaults1.FLOW_TOO_LOW.value: "Zu geringer Durchfluss",
        UnitFaults1.PHASE_LOSS_PROTECTION.value: "Phasenausfallschutz",
        UnitFaults1.PHE_RETURN_TEMP_FAULT.value: (
            "Störung Rücklauftemperatur Plattenwärmetauscher"
        ),
        UnitFaults1.SYSTEM_FLOW_TEMP_FAULT.value: "Störung Gesamt-Vorlauftemperatur",
        UnitFaults1.PHASE_SEQUENCE_PROTECTION.value: "Phasenfolgeschutz",
        UnitFaults1.PHE_FLOW_RETURN_DIFF_TOO_LARGE.value: (
            "Temperaturdifferenz Vor-/Rücklauf Plattenwärmetauscher zu groß"
        ),
        UnitFaults1.PHE_FLOW_RETURN_DIFF_IMPLAUSIBLE.value: (
            "Temperaturdifferenz Vor-/Rücklauf Plattenwärmetauscher unplausibel"
        ),
        UnitFaults1.INVERTER_PUMP_WARNING.value: "Warnung Inverter-Umwälzpumpe",
    },
    UnitFaults2: {  # Einheitenstörungen 2
        UnitFaults2.COMMUNICATION_ERROR.value: "Kommunikationsfehler",
        UnitFaults2.INDOOR_OUTDOOR_COMM_FAULT.value: (
            "Kommunikationsstörung Innen-/Außengerät"
        ),
        UnitFaults2.PROTOCOL_VERSION_TOO_LOW.value: "Protokollversion zu niedrig",
        UnitFaults2.INVERTER_PUMP_FAULT.value: "Störung Inverter-Umwälzpumpe",
        UnitFaults2.TYPE_SETTING_ERROR.value: "Fehlerhafte Typeneinstellung",
        UnitFaults2.R290_SENSOR_FAULT.value: "Störung R290-Sensor",
        UnitFaults2.R290_LEAK.value: "R290-Leckage",
        UnitFaults2.FLOW_SENSOR_FAULT.value: "Störung Durchflusssensor",
        UnitFaults2.WATER_PRESSURE_SENSOR_FAULT.value: "Störung Wasserdrucksensor",
        UnitFaults2.INDOOR_OUTDOOR_COMM_ERROR.value: (
            "Kommunikationsfehler Innen-/Außengerät"
        ),
        UnitFaults2.LED_BAR_COMM_FAULT.value: "Kommunikationsstörung LED-Leiste",
        UnitFaults2.HEAT_METER_COMM_FAULT.value: (
            "Kommunikationsstörung Wirbel-Wärmemengenzähler"
        ),
        UnitFaults2.ENERGY_METER_COMM_FAULT.value: "Kommunikationsfehler Stromzähler",
    },
    SystemFaults1: {  # Systemstörungen 1
        SystemFaults1.PHASE_SEQUENCE_PROTECTION.value: "Phasenfolgeschutz",
        SystemFaults1.EEPROM_DATA_ERROR.value: "EEPROM-Datenfehler",
        SystemFaults1.CELL_TEMP_1_FAULT.value: "Störung Zellentemperatur 1",
        SystemFaults1.CELL_TEMP_2_FAULT.value: "Störung Zellentemperatur 2",
        SystemFaults1.SYSTEM_MAINTENANCE_DATA_ERROR.value: "Datenfehler Systemwartung",
        SystemFaults1.PHASE_LOSS_PROTECTION.value: "Phasenausfallschutz",
        SystemFaults1.TANK_HEATER_OVERLOAD.value: "Überlast Speicher-Heizstab",
        SystemFaults1.DHW_TANK_TEMP_FAULT.value: (
            "Störung Temperatur Warmwasserspeicher"
        ),
        SystemFaults1.SYSTEM_FLOW_TEMP_FAULT.value: (
            "Störung Gesamt-Vorlauftemperatur System"
        ),
        SystemFaults1.FLOOR_HEATING_FLOW_TEMP_FAULT.value: (
            "Störung Vorlauftemperatur Fußbodenheizung"
        ),
    },
    SystemFaults6: {  # Systemstörungen 6
        SystemFaults6.BUFFER_TOP_TEMP_FAULT.value: (
            "Störung Temperatur Pufferspeicher oben"
        ),
        SystemFaults6.BUFFER_BOTTOM_TEMP_FAULT.value: (
            "Störung Temperatur Pufferspeicher unten"
        ),
        SystemFaults6.SOLAR_TEMP_FAULT.value: "Störung Solartemperatur",
        SystemFaults6.WIRED_REMOTE_COMM_FAULT.value: (
            "Kommunikationsstörung Kabelfernbedienung"
        ),
        SystemFaults6.CLIMATE_FLOW_TEMP_FAULT.value: (
            "Störung Gesamt-Vorlauftemperatur Klimabetrieb"
        ),
        SystemFaults6.ROOM_TEMP_FAULT.value: "Störung Raumtemperatur",
        SystemFaults6.SYSTEM_LOCKED_FREQUENT_STARTS.value: (
            "Anlagensperre wegen häufiger Starts"
        ),
        SystemFaults6.ZONE_A_RETURN_TEMP_FAULT.value: (
            "Störung Rücklauftemperatur Zone A"
        ),
    },
}


def fault_label(flag: IntFlag) -> str:
    """Return the German label of ``flag``, or its member name if unmapped."""
    labels = FAULT_LABELS.get(type(flag))
    if labels is not None:
        label = labels.get(flag.value)
        if label is not None:
            return label
    return flag.name or str(flag)
