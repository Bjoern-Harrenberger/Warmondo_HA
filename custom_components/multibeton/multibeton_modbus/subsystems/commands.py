"""Read-back-capable on/off style controls.

Read and written through the holding-register table (Modbus function code
0x03 to read, 0x06 or 0x10 to write), source sheet "Benutzerbefehle
Lesen-Schreiben". These registers are preferred over the write-only coil
table documented for the same commands, since a holding register reflects
the controller's applied state on the next read while a coil does not.
"""

from __future__ import annotations

from ..data_model import MultibetonComponent, boolean


class Commands(MultibetonComponent):
    """Read-back-capable on/off style controls."""

    register_space = "holding"

    system_on = boolean(
        64000,
        writable=True,
        maker_key="Anlage ein/aus",
        description=(
            "0 senden: Klimazonen und Warmwasser ausschalten; 1 senden: "
            "Klimazonen und Warmwasser einschalten. Liest 1 sobald "
            "Warmwasser oder eine Klimazone ungleich 0 ist."
        ),
    )
    reset_fault = boolean(
        64001,
        writable=True,
        maker_key="Reset-Befehl",
        description=(
            "0 senden: keine Ausführung; 1 senden: Reset ausführen. Wert "
            "wird stets als 0 gelesen (momentary trigger)."
        ),
    )
    defrost_command = boolean(
        64002,
        writable=True,
        maker_key="Abtaubefehl Modul 00#",
        description=(
            "0 senden: keine Ausführung; 1 senden: Abtauung ausführen. "
            "Liest 1 solange das Modul im Abtaubetrieb ist."
        ),
    )
    zone_a_on = boolean(
        64017,
        writable=True,
        maker_key="Zone A ein/aus",
    )
    zone_b_on = boolean(
        64018,
        writable=True,
        maker_key="Zone B ein/aus",
    )
    dhw_on = boolean(
        64019,
        writable=True,
        maker_key="Warmwasser ein/aus",
    )
    forced_dhw = boolean(
        64021,
        writable=True,
        maker_key="Zwangsbetrieb Warmwassermodus",
    )
    scheduled_disinfection = boolean(
        64022,
        writable=True,
        maker_key="Zeitgesteuerte Desinfektion (Legionellenschutz)",
    )
    vacation_away = boolean(
        64024,
        writable=True,
        maker_key="Urlaubsmodus abwesend",
    )
    vacation_home = boolean(
        64025,
        writable=True,
        maker_key="Urlaubsmodus zu Hause",
    )
