"""The sixteen fixed heating and cooling curves, in numbers.

The controller names its curves but never states what any of them demands:
the manufacturer's documentation lists "Niedrige Temperatur 3" and leaves
it at that. The tables here were read off the controller's own display
(menus *Heizkurve für Zone A* and *Zone A Cooling Curve*) and are written
down in ``docs/heizkurven.md``; this module is generated from that file, so
the two cannot drift apart.

Each curve is a series of (ambient, flow) points in °C. **Heating and
cooling do not share an axis**: the controller plots heating from +20 down
to -20 °C ambient and cooling from +30 down to -10 °C, which is why the two
tables carry their own ambient values rather than a shared list.

One caveat carried over from the source: two of the photographed screens
were both captioned "Hohe Temperatur 4" at different values. The series
with 43/44/46/47/48 is filed here as ``HIGH_TEMP_5``, by its place in an
evenly spaced row.
"""

from __future__ import annotations

from .enums import CurveSelection

__all__ = ["COOLING_CURVES", "HEATING_CURVES", "curve_points"]

#: Flow temperature each fixed heating curve demands, +20 °C to -20 °C ambient.
HEATING_CURVES: dict[CurveSelection, tuple[tuple[float, float], ...]] = {
    CurveSelection.LOW_TEMP_1: ((20, 32), (10, 33), (0, 35), (-10, 37), (-20, 38)),
    CurveSelection.LOW_TEMP_2: ((20, 31), (10, 32), (0, 34), (-10, 36), (-20, 37)),
    CurveSelection.LOW_TEMP_3: ((20, 29), (10, 31), (0, 33), (-10, 34), (-20, 36)),
    CurveSelection.LOW_TEMP_4: ((20, 28), (10, 30), (0, 32), (-10, 33), (-20, 35)),
    CurveSelection.LOW_TEMP_5: ((20, 27), (10, 29), (0, 31), (-10, 32), (-20, 34)),
    CurveSelection.LOW_TEMP_6: ((20, 26), (10, 28), (0, 29), (-10, 31), (-20, 32)),
    CurveSelection.LOW_TEMP_7: ((20, 25), (10, 27), (0, 28), (-10, 30), (-20, 31)),
    CurveSelection.LOW_TEMP_8: ((20, 24), (10, 25), (0, 26), (-10, 28), (-20, 29)),
    CurveSelection.HIGH_TEMP_1: ((20, 50), (10, 51), (0, 53), (-10, 54), (-20, 55)),
    CurveSelection.HIGH_TEMP_2: ((20, 48), (10, 49), (0, 51), (-10, 52), (-20, 53)),
    CurveSelection.HIGH_TEMP_3: ((20, 47), (10, 48), (0, 50), (-10, 51), (-20, 52)),
    CurveSelection.HIGH_TEMP_4: ((20, 45), (10, 46), (0, 48), (-10, 49), (-20, 50)),
    CurveSelection.HIGH_TEMP_5: ((20, 43), (10, 44), (0, 46), (-10, 47), (-20, 48)),
    CurveSelection.HIGH_TEMP_6: ((20, 40), (10, 41), (0, 43), (-10, 44), (-20, 45)),
    CurveSelection.HIGH_TEMP_7: ((20, 38), (10, 39), (0, 41), (-10, 42), (-20, 43)),
    CurveSelection.HIGH_TEMP_8: ((20, 35), (10, 36), (0, 38), (-10, 39), (-20, 40)),
}

#: The same for cooling - note the different ambient range, +30 °C to -10 °C.
COOLING_CURVES: dict[CurveSelection, tuple[tuple[float, float], ...]] = {
    CurveSelection.LOW_TEMP_1: ((30, 5), (20, 11), (10, 16), (0, 16), (-10, 16)),
    CurveSelection.LOW_TEMP_2: ((30, 6), (20, 12), (10, 17), (0, 17), (-10, 17)),
    CurveSelection.LOW_TEMP_3: ((30, 7), (20, 13), (10, 18), (0, 18), (-10, 18)),
    CurveSelection.LOW_TEMP_4: ((30, 8), (20, 14), (10, 19), (0, 19), (-10, 19)),
    CurveSelection.LOW_TEMP_5: ((30, 9), (20, 15), (10, 20), (0, 20), (-10, 20)),
    CurveSelection.LOW_TEMP_6: ((30, 10), (20, 16), (10, 21), (0, 21), (-10, 21)),
    CurveSelection.LOW_TEMP_7: ((30, 11), (20, 17), (10, 22), (0, 22), (-10, 22)),
    CurveSelection.LOW_TEMP_8: ((30, 12), (20, 18), (10, 23), (0, 23), (-10, 23)),
    CurveSelection.HIGH_TEMP_1: ((30, 16), (20, 18), (10, 20), (0, 20), (-10, 20)),
    CurveSelection.HIGH_TEMP_2: ((30, 17), (20, 19), (10, 21), (0, 21), (-10, 21)),
    CurveSelection.HIGH_TEMP_3: ((30, 17), (20, 20), (10, 22), (0, 22), (-10, 22)),
    CurveSelection.HIGH_TEMP_4: ((30, 18), (20, 21), (10, 23), (0, 23), (-10, 23)),
    CurveSelection.HIGH_TEMP_5: ((30, 18), (20, 21), (10, 24), (0, 24), (-10, 24)),
    CurveSelection.HIGH_TEMP_6: ((30, 19), (20, 22), (10, 24), (0, 24), (-10, 24)),
    CurveSelection.HIGH_TEMP_7: ((30, 19), (20, 22), (10, 25), (0, 25), (-10, 25)),
    CurveSelection.HIGH_TEMP_8: ((30, 20), (20, 23), (10, 25), (0, 25), (-10, 25)),
}


def curve_points(
    selection: CurveSelection, *, heating: bool
) -> tuple[tuple[float, float], ...] | None:
    """Return a fixed curve's points, or ``None`` if it is not one."""
    table = HEATING_CURVES if heating else COOLING_CURVES
    return table.get(selection)
