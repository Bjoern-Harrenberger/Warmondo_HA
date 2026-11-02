"""Image platform: the curve a zone follows, drawn from the plant's own values.

A zone's curve selection is a word like "Niedrige Temperatur 6", and a list
of setpoints next to it says nothing about what that curve demands. This
platform draws it: one picture per zone and mode, always showing the curve
the plant is actually set to.

The drawing comes out of the integration itself, over Home Assistant's
``image`` platform, which serves it under the usual authenticated image
URL. That matters for what ships to a customer: no card from HACS, no
extra dependency, nothing to install alongside - the plant is added and the
picture is there.

SVG rather than a raster format because a curve is a handful of lines and
labels: it stays sharp at any size, needs no imaging library, and is built
from text, so it costs nothing to generate.

Three kinds of curve exist, and the picture is honest about which it has:
the sixteen fixed ones are tabulated in :mod:`multibeton_modbus.curve_tables`
and drawn point by point; curve 9 is readable from the user parameters and
drawn as the straight line through its two points; curves 10 to 12 have no
registers released for them at all, so they get a plate saying the curve can
only be set at the controller rather than an invented line.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.image import ImageEntity, ImageEntityDescription
from homeassistant.util import dt as dt_util

from .entity import MultibetonEntity
from .multibeton_modbus.curve_tables import curve_points
from .multibeton_modbus.enums import CurveSelection

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import MultibetonDataUpdateCoordinator
    from .data import MultibetonConfigEntry

# Plot frame in SVG user units. A wide format, because the picture is meant
# to span a dashboard's full width: a near-square drawing stretched that wide
# grows as tall as the screen and its labels grow with it.
_W, _H = 720, 270
_LEFT, _RIGHT, _TOP, _BOTTOM = 78, 700, 22, 200

#: Text sizes in user units. The style block enlarges them when the picture
#: is rendered narrow - on a phone a 720-unit drawing shrinks to half its
#: size, and so would its labels.
_STYLE = (
    "<style>text{font-family:Roboto,Arial,sans-serif}"
    ".l{font-size:13px}.t{font-size:15px}"
    "@media (max-width:520px){.l{font-size:20px}.t{font-size:22px}"
    ".c{stroke-width:5px}.p{stroke-width:4px;r:7px}}</style>"
)

#: Ambient range of each mode's axis, warm to cold - the controller's own
#: curve screens use a different one for heating than for cooling.
_AXIS_HEATING = (20.0, -20.0)
_AXIS_COOLING = (30.0, -10.0)

#: Below this spread the curve is nearly flat and would be drawn glued to
#: one axis edge; the flow axis is widened around it instead.
_MIN_AXIS_SPAN = 10.0
#: The typographic minus, U+2212: a hyphen reads as a dash at 10 px.
#: Spelled by code point so the glyph cannot be mistaken for one in the
#: source, which is what the linter objects to.
_MINUS = chr(0x2212)

_COLOR_HEATING = "#ef5350"
_COLOR_COOLING = "#42a5f5"
_COLOR_BACKGROUND = "#1b1e25"
_COLOR_HOLE = "#111318"
_COLOR_GRID = "#2a2e37"
_COLOR_LABEL = "#9aa0a6"
_COLOR_TEXT = "#e8eaed"


def _number(value: float) -> str:
    """Return ``value`` with a typographic minus, for an axis label."""
    return f"{_MINUS if value < 0 else ''}{abs(value):.0f}"


def _flow_axis(values: list[float]) -> tuple[float, float]:
    """Return a flow-temperature axis containing ``values``, in whole steps."""
    low, high = min(values), max(values)
    if high - low < _MIN_AXIS_SPAN:
        middle = (high + low) / 2
        low, high = middle - _MIN_AXIS_SPAN / 2, middle + _MIN_AXIS_SPAN / 2
    margin = (high - low) * 0.15
    return (round((low - margin) / 5) * 5, round((high + margin) / 5) * 5)


class MultibetonCurveImage(MultibetonEntity, ImageEntity):
    """The curve one zone follows in one mode, drawn as it is set."""

    _attr_content_type = "image/svg+xml"

    def __init__(
        self,
        coordinator: MultibetonDataUpdateCoordinator,
        hass: HomeAssistant,
        zone: str,
        *,
        heating: bool,
    ) -> None:
        """Initialize the curve image of zone ``zone`` ("a" or "b")."""
        MultibetonEntity.__init__(self, coordinator)
        ImageEntity.__init__(self, hass)
        self._zone = zone
        self._heating = heating
        mode = "heating" if heating else "cooling"
        key = f"{mode}_curve_zone_{zone}"
        self.entity_description = ImageEntityDescription(
            key=key,
            translation_key=key,
        )
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{key}"
        self._drawn = self._state()
        self._attr_image_last_updated = dt_util.utcnow()

    # -- what the plant currently says --------------------------------------

    def _selection(self) -> CurveSelection | None:
        """Return the curve this zone is set to."""
        mode = "heating" if self._heating else "cooling"
        value = getattr(
            self.coordinator.data.user_parameters,
            f"curve_select_{mode}_zone_{self._zone}",
            None,
        )
        return value if isinstance(value, CurveSelection) else None

    def _custom_points(self) -> tuple[tuple[float, float], ...] | None:
        """Return curve 9's two points, or ``None`` if they are unreadable."""
        params = self.coordinator.data.user_parameters
        mode = "heating" if self._heating else "cooling"
        values = [
            getattr(params, f"curve9_{mode}_{name}", None)
            for name in ("ambient_1", "outlet_1", "ambient_2", "outlet_2")
        ]
        if any(value is None for value in values):
            return None
        a1, o1, a2, o2 = (float(value) for value in values)  # type: ignore[arg-type]
        if a1 == a2:  # a vertical "curve" is not a curve
            return None
        return ((a1, o1), (a2, o2))

    def _state(self) -> tuple[object, ...]:
        """Return everything the drawing depends on, for change detection."""
        return (self._selection(), self._custom_points())

    # -- drawing -------------------------------------------------------------

    def _x(self, ambient: float) -> float:
        warm, cold = _AXIS_HEATING if self._heating else _AXIS_COOLING
        return _LEFT + (warm - ambient) / (warm - cold) * (_RIGHT - _LEFT)

    def _y(self, flow: float, low: float, high: float) -> float:
        return _BOTTOM - (flow - low) / (high - low) * (_BOTTOM - _TOP)

    def _svg(self) -> str:
        """Return the current curve as an SVG document."""
        selection = self._selection()
        if selection is None:
            return self._plate("Kurve nicht lesbar")
        if selection is CurveSelection.DISABLED:
            return self._plate("Keine Kurve - fester Sollwert")

        fixed = curve_points(selection, heating=self._heating)
        if fixed is not None:
            return self._plot(list(fixed), extend=False)
        if selection is CurveSelection.CURVE_9:
            custom = self._custom_points()
            if custom is None:
                return self._plate("Kurve 9 nicht lesbar")
            return self._plot(list(custom), extend=True)
        return self._plate("Nur an der Regelung einstellbar")

    def _plot(self, points: list[tuple[float, float]], *, extend: bool) -> str:
        """Return the SVG of ``points``, extended to the axis if asked."""
        warm, cold = _AXIS_HEATING if self._heating else _AXIS_COOLING
        color = _COLOR_HEATING if self._heating else _COLOR_COOLING

        drawn = list(points)
        if extend:  # two points define a line that runs past them
            (a1, o1), (a2, o2) = points[0], points[1]
            slope = (o2 - o1) / (a2 - a1)
            drawn = [(a, o1 + (a - a1) * slope) for a in (warm, cold)]

        low, high = _flow_axis([flow for _, flow in [*points, *drawn]])
        step = max(5, round((high - low) / 4 / 5) * 5)

        grid, labels = [], []
        ambient = warm
        while ambient >= cold:
            x = self._x(ambient)
            grid.append(f'<line x1="{x:.0f}" y1="{_TOP}" x2="{x:.0f}" y2="{_BOTTOM}"/>')
            labels.append(
                f'<text x="{x:.0f}" y="{_BOTTOM + 30}" fill="{_COLOR_LABEL}"'
                f' class="l" text-anchor="middle">{_number(ambient)}</text>'
            )
            ambient -= 10
        flow = low
        while flow <= high:
            y = self._y(flow, low, high)
            grid.append(f'<line x1="{_LEFT}" y1="{y:.0f}" x2="{_RIGHT}" y2="{y:.0f}"/>')
            labels.append(
                f'<text x="{_LEFT - 10}" y="{y + 5:.0f}" fill="{_COLOR_LABEL}"'
                f' class="l" text-anchor="end">{_number(flow)}</text>'
            )
            flow += step

        line = " ".join(
            f"{self._x(a):.0f},{self._y(o, low, high):.1f}" for a, o in drawn
        )
        dots = "".join(
            f'<circle class="p" cx="{self._x(a):.0f}"'
            f' cy="{self._y(o, low, high):.1f}" r="4"'
            f' fill="{_COLOR_HOLE}" stroke="{color}" stroke-width="2.5"/>'
            for a, o in points
        )
        ends = f"{points[0][1]:.0f} bis {points[-1][1]:.0f} Grad Vorlauf"
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_W} {_H}"'
            f' width="{_W}" height="{_H}" role="img"'
            f' aria-label="Kennlinie, {ends}, von {_number(warm)}'
            f' bis {_number(cold)} Grad Aussentemperatur">'
            f"{_STYLE}"
            f'<rect width="{_W}" height="{_H}" fill="{_COLOR_BACKGROUND}"/>'
            f'<g stroke="{_COLOR_GRID}" stroke-width="1">{"".join(grid)}</g>'
            f"{''.join(labels)}"
            f'<polyline class="c" points="{line}" fill="none" stroke="{color}"'
            f' stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'
            f"{dots}"
            f'<text x="{_W / 2:.0f}" y="{_H - 8}" fill="{_COLOR_LABEL}"'
            f' class="l" text-anchor="middle">'
            f"Außentemperatur °C — Vorlauf °C</text>"
            f"</svg>"
        )

    def _plate(self, message: str) -> str:
        """Return a plate carrying ``message`` instead of a curve."""
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_W} {_H}"'
            f' width="{_W}" height="{_H}" role="img" aria-label="{message}">'
            f"{_STYLE}"
            f'<rect width="{_W}" height="{_H}" fill="{_COLOR_BACKGROUND}"/>'
            f'<text x="{_W / 2:.0f}" y="{_H / 2:.0f}" fill="{_COLOR_TEXT}"'
            f' class="t" text-anchor="middle">{message}</text></svg>'
        )

    # -- Home Assistant ------------------------------------------------------

    def _handle_coordinator_update(self) -> None:
        """Redraw only when the curve itself has changed.

        A new timestamp makes every open dashboard fetch the picture again,
        so setting one on each poll would refetch it every thirty seconds
        for a drawing that changes perhaps twice a year.
        """
        state = self._state()
        if state != self._drawn:
            self._drawn = state
            self._attr_image_last_updated = dt_util.utcnow()
        super()._handle_coordinator_update()

    async def async_image(self) -> bytes | None:
        """Return the current drawing."""
        return self._svg().encode("utf-8")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MultibetonConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the image platform."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        MultibetonCurveImage(coordinator, hass, zone, heating=heating)
        for zone in ("a", "b")
        for heating in (True, False)
    )
