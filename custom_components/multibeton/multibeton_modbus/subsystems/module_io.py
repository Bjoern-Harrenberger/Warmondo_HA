"""Per-module relay outputs and digital inputs of a cascade.

Read from the discrete-input space (Modbus function code 0x02), source
sheet "IO Bit (FC02)" of the manufacturer's register documentation. These
are the controller's actual switching state: whether a relay is pulled in
right now, and what its digital inputs report back. Everything else this
library reads is a word register saying what the plant intends; these bits
say what it is doing.

**The module stride here is not** :data:`~.module.MODULE_STRIDE`. The word
registers of consecutive modules sit 256 apart, the discrete inputs 768 -
module 0#'s auxiliary heater is bit 801, module 1#'s is 1569. A field's
address is shifted once per component instance, so these bits cannot share
a component with the word registers and live in their own, built with
``base_offset=IO_STRIDE * module``.

A note on reading them: a relay output reports the controller's own
command, a digital input what the hardware answers. "Zusatzheizstab 1" at
801 means the contact is closed; "Rückmeldung Zusatzheizstab" at 848 is a
separate input and was observed reading 1 while the heater was off, so it
is not a running indication and is modeled as what the table calls it.
"""

from __future__ import annotations

from ..data_model import MultibetonComponent, discrete_input

#: Address distance between two consecutive modules' discrete inputs.
IO_STRIDE = 768


class ModuleIO(MultibetonComponent):
    """One module's relay outputs and digital inputs."""

    # -- relay outputs, compressor circuit --
    compressor_relay = discrete_input(
        768,
        maker_key="Inverter-Verdichter",
        description="Relaisausgang Verdichter 1.",
    )
    reversing_valve = discrete_input(
        769,
        maker_key="4-Wege-Ventil",
        description="Angezogen im Kühlbetrieb und während der Abtauung.",
    )
    evi_valve = discrete_input(
        770,
        maker_key="Flüssigkeitseinspritzventil (EVI)",
    )
    crankcase_heater_1 = discrete_input(
        773,
        maker_key="Kurbelwannenheizung 1",
    )
    crankcase_heater_2 = discrete_input(
        775,
        maker_key="Kurbelwannenheizung 2",
    )

    # -- relay outputs, unit --
    circulation_pump = discrete_input(
        800,
        maker_key="Inverter-Umwälzpumpe",
    )
    aux_heater_1 = discrete_input(
        801,
        maker_key="Zusatzheizstab 1",
    )
    aux_heater_2 = discrete_input(
        802,
        maker_key="Zusatzheizstab 2",
    )
    base_pan_heater = discrete_input(
        803,
        maker_key="Bodenwannenheizung",
    )
    frost_protection_tape = discrete_input(
        804,
        maker_key="Frostschutz-Heizband",
    )
    base_pan_heater_2 = discrete_input(
        805,
        maker_key="Bodenwannenheizung 2",
    )

    # -- digital inputs --
    low_pressure_switch = discrete_input(
        816,
        maker_key="Niederdruckschalter",
        description="Geschlossen im Normalbetrieb; öffnet bei Niederdruck.",
    )
    high_pressure_switch = discrete_input(
        817,
        maker_key="Hochdruckschalter",
        description="Geschlossen im Normalbetrieb; öffnet bei Hochdruck.",
    )
    aux_heater_feedback = discrete_input(
        848,
        maker_key="Rückmeldung Zusatzheizstab",
    )
    flow_switch = discrete_input(
        849,
        maker_key="Strömungswächter",
        description="Geschlossen, solange Durchfluss vorhanden ist.",
    )
