"""Relay outputs and digital inputs of the system board.

Read from the input-register table (Modbus function code 0x04), source
sheet "IO Wort (FC04)" of the manufacturer's register documentation. Two
words carry the whole plant's hydraulic switching state: 3331 what the
system board has energized, 3334 what the installation reports back.

These are **plant-wide, not per module**. The manufacturer's terminal list
(service manual, "Port description of main board") wires every field
sensor, valve, pump, external heat source and the SG-Ready terminals to
the master's main board; a slave's board carries only its own refrigerant
circuit. So unlike :mod:`.module_io` there is no stride here - a cascade
of eight reads the same two addresses a single unit does.

The controller also offers write commands for these outputs (64047-64067).
The register table files them under "manueller Testbetrieb" and they are
deliberately not modeled: forcing a pump against a closed valve is a way
to wreck a plant, not a dashboard feature.
"""

from __future__ import annotations

from ..data_model import MultibetonComponent, flags, gauge, integer
from ..enums import SystemInputs, SystemRelays
from .sensors import SENSOR_FAULT_CODES


class SystemIO(MultibetonComponent):
    """The plant's shared relay outputs and digital inputs."""

    register_space = "input"

    relay_outputs = flags(
        3331,
        SystemRelays,
        maker_key="Relaisausgänge System",
        description=(
            "B0: Abtauanzeige | B1: Störungsanzeige | B2: externe Wärmequelle | "
            "B3: 3-Wege-Magnetventil 1 | B4: 3-Wege-Magnetventil 3 | "
            "B5: 3-Wege-Magnetventil 2 | B6: Speicher-Heizstab | B7: Mischventil | "
            "B8: Zirkulationspumpe Rücklauf | B9: Solarpumpe | B10: Mischpumpe | "
            "B11: externe Umwälzpumpe | B12: Zellen-Umwälzpumpe"
        ),
    )
    digital_inputs = flags(
        3334,
        SystemInputs,
        maker_key="Digitaleingänge System",
        description=(
            "B1: Fernbedienungsschalter | B3: Schalter Kühlen | "
            "B4: Schalter Heizen | B5: Schalter Warmwasserbereitung | "
            "B8: Rückmeldung Speicher-Heizstab | B9: Thermostatsignal C | "
            "B10: Thermostatsignal H | B11: Solarsignal | "
            "B12: Smart-Grid-Signal SG | B13: Smart-Grid-Signal EVU"
        ),
    )
    # The table names these three but gives neither a scale nor a value
    # list. Observed on a running plant: 446 / 447 / 446 while bit B5 of
    # relay_outputs said valve 2 was the only energized one, so they are
    # not a plain 0/1 mirror of those bits. Kept as the raw reading until
    # the manufacturer explains the encoding.
    valve_1_status = integer(
        3363,
        maker_key="Status 3-Wege-Magnetventil 1",
        description="Kodierung der Werte noch nicht geklärt.",
    )
    valve_2_status = integer(
        3364,
        maker_key="Status 3-Wege-Magnetventil 2",
        description="Kodierung der Werte noch nicht geklärt.",
    )
    valve_3_status = integer(
        3365,
        maker_key="Status 3-Wege-Magnetventil 3",
        description="Kodierung der Werte noch nicht geklärt.",
    )
    # Only populated where zone B has a mixing valve fitted; without one
    # both read the "Fühler nicht vorhanden" sentinel, so they carry the
    # same nan handling as a temperature.
    mixing_valve_target_opening = gauge(
        3373,
        0.001,
        nan=SENSOR_FAULT_CODES,
        maker_key="Sollöffnung Mischventil Zone B",
        description="Skalierung laut Tabelle 0,001; Anzeigeeinheit nicht benannt.",
    )
    mixing_valve_opening = gauge(
        3374,
        0.001,
        nan=SENSOR_FAULT_CODES,
        maker_key="Aktuelle Öffnung Mischventil Zone B",
        description="Skalierung laut Tabelle 0,001; Anzeigeeinheit nicht benannt.",
    )
