"""Machine data the controller carries about the unit it drives.

Source is the type-parameter table (``docs/Typenparameter_R290.xlsx``),
not the Modbus address table - these registers are not listed there.
They are marked factory level, so they are read and never written, as
the project's rule for anything above user level requires.

Only one field so far, and it earns its place: the rated voltage is the
one piece of machine data that differs between the Warmondo models and
can be read back from the plant. Everything else the table varies by
model - compressor coding, fan speeds, defrost timings - is factory
level too, but none of it says anything a dashboard or a plausibility
check could use.

What it is good for: the model cannot be read over Modbus, it is set
with DIP switches and typed into the integration by hand. A WM-S or
WM-M runs on 230 V, a WM-L or WM-XL on 400 V. If the plant reports a
voltage that contradicts the model someone picked, the model is wrong -
and every limit, every curve and every capacity figure derived from it
would be wrong with it.

A controller that has not yet heard from its outdoor unit reports 0.
That is not a contradiction, only a missing answer, and is treated as
such.
"""

from __future__ import annotations

from ..data_model import MultibetonComponent, integer


class TypeParameters(MultibetonComponent):
    """Read-only machine data from the type-parameter block."""

    rated_voltage = integer(
        7269,
        unit="V",
        maker_key="Nennspannung der Einheit",
        description=(
            "230 V bei WM-S und WM-M, 400 V bei WM-L und WM-XL. "
            "0, solange die Regelung das Außengerät nicht erreicht."
        ),
    )
