"""Heating/cooling curve endpoints for climate zones A and B.

Read from the input-register table (Modbus function code 0x04), source
sheet "Anlageninformationen" of the manufacturer's register documentation,
addresses 830-837 ("Einheit 1 °C" - whole-degree resolution, no decimal
scale). These are documented read-only: the source table gives no write
function code for them, so - unlike a thermostat's heating-curve UI - they
cannot be tuned over Modbus on this firmware version, only observed.
"""

from __future__ import annotations

from ..data_model import MultibetonComponent, integer


class HeatingCurve(MultibetonComponent):
    """Read-only heating/cooling curve upper and lower bounds, zones A and B."""

    register_space = "input"

    heating_max_zone_a = integer(
        830,
        unit="°C",
        maker_key="Obergrenze Heizkennlinie",
    )
    heating_min_zone_a = integer(
        831,
        unit="°C",
        maker_key="Untergrenze Heizkennlinie",
    )
    cooling_max_zone_a = integer(
        832,
        unit="°C",
        maker_key="Obergrenze Kühlkennlinie",
    )
    cooling_min_zone_a = integer(
        833,
        unit="°C",
        maker_key="Untergrenze Kühlkennlinie",
    )
    heating_max_zone_b = integer(
        834,
        unit="°C",
        maker_key="Obergrenze Heizkennlinie Zone B",
    )
    heating_min_zone_b = integer(
        835,
        unit="°C",
        maker_key="Untergrenze Heizkennlinie Zone B",
    )
    cooling_max_zone_b = integer(
        836,
        unit="°C",
        maker_key="Obergrenze Kühlkennlinie Zone B",
    )
    cooling_min_zone_b = integer(
        837,
        unit="°C",
        maker_key="Untergrenze Kühlkennlinie Zone B",
    )
    # Steigungskennlinien (Kurve 11 Zone A, Kurve 12 Zone B), Adressen 875-882.
    # Diese Kurven sind über Steigung und Offset definiert; die Regelung
    # rechnet daraus die hier lesbaren Grenzen aus.
    slope_heating_max_zone_a = integer(
        875,
        unit="°C",
        maker_key="Obergrenze Steigungskennlinie Heizen Zone A",
        description="Kennlinie 11.",
    )
    slope_heating_min_zone_a = integer(
        876,
        unit="°C",
        maker_key="Untergrenze Steigungskennlinie Heizen Zone A",
        description="Kennlinie 11.",
    )
    slope_cooling_max_zone_a = integer(
        877,
        unit="°C",
        maker_key="Obergrenze Steigungskennlinie Kühlen Zone A",
        description="Kennlinie 11.",
    )
    slope_cooling_min_zone_a = integer(
        878,
        unit="°C",
        maker_key="Untergrenze Steigungskennlinie Kühlen Zone A",
        description="Kennlinie 11.",
    )
    slope_heating_max_zone_b = integer(
        879,
        unit="°C",
        maker_key="Obergrenze Steigungskennlinie Heizen Zone B",
        description="Kennlinie 12.",
    )
    slope_heating_min_zone_b = integer(
        880,
        unit="°C",
        maker_key="Untergrenze Steigungskennlinie Heizen Zone B",
        description="Kennlinie 12.",
    )
    slope_cooling_max_zone_b = integer(
        881,
        unit="°C",
        maker_key="Obergrenze Steigungskennlinie Kühlen Zone B",
        description="Kennlinie 12.",
    )
    slope_cooling_min_zone_b = integer(
        882,
        unit="°C",
        maker_key="Untergrenze Steigungskennlinie Kühlen Zone B",
        description="Kennlinie 12.",
    )
