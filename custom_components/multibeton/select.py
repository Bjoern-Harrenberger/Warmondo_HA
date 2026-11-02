"""Select platform for multibeton.

Covers the mode and curve-selection ("Benutzerparameter", addresses
6400-6444) enum fields on
``multibeton_modbus.subsystems.user_parameters.UserParameters`` - the numeric
setpoints on the same component are number entities instead, see
``number.py``.

The four curve selectors name the curve but cannot show what it demands in
degrees: the manufacturer's documentation does not define the sixteen fixed
curves numerically. The controller answers that itself - see the
"Curve ambient temperature" and "Curve flow temperature" sensors, which
report the working point the selected curve is currently producing.

Whether this address range is reachable through a given RTU-to-TCP gateway
has not been confirmed against real hardware; verify against the real
controller before relying on these entities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError

from .api import MultibetonApiClientWriteError
from .entity import MultibetonEntity
from .multibeton_modbus.enums import ConfiguredMode, CurveSelection, PowerMode

if TYPE_CHECKING:
    from enum import IntEnum

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import MultibetonDataUpdateCoordinator
    from .data import MultibetonConfigEntry

# Human-readable option labels, in enum declaration order, for each select's
# ``IntEnum``. ``current_option``/``async_select_option`` translate between
# these labels and the enum member the register actually stores.
_CONTROL_MODE_OPTIONS: dict[str, ConfiguredMode] = {
    "cool": ConfiguredMode.COOL,
    "heat": ConfiguredMode.HEAT,
    "auto": ConfiguredMode.AUTO,
}
# Curve selection, addresses 6425-6428. Values 1-8 are the controller's fixed
# low-temperature curves, 9-16 its fixed high-temperature curves, 17-20 the
# four configurable ones (curve 9 is the user-defined two-point curve exposed
# as the "Curve 9 ..." number entities).
_CURVE_OPTIONS: dict[str, CurveSelection] = {
    "disabled": CurveSelection.DISABLED,
    **{f"low_temp_{i}": CurveSelection(i) for i in range(1, 9)},
    **{f"high_temp_{i}": CurveSelection(i + 8) for i in range(1, 9)},
    "curve_9": CurveSelection.CURVE_9,
    "curve_10": CurveSelection.CURVE_10,
    "curve_11": CurveSelection.CURVE_11,
    "curve_12": CurveSelection.CURVE_12,
}

_POWER_MODE_OPTIONS: dict[str, PowerMode] = {
    "standard": PowerMode.STANDARD,
    "boost": PowerMode.BOOST,
    "eco": PowerMode.ECO,
    "auto": PowerMode.AUTO,
}


@dataclass(frozen=True, kw_only=True)
class MultibetonSelectEntityDescription(SelectEntityDescription):
    """Describes a select backed by one writable ``user_parameters`` enum field."""

    field: str
    options_map: dict[str, IntEnum]


SELECT_DESCRIPTIONS: tuple[MultibetonSelectEntityDescription, ...] = (
    MultibetonSelectEntityDescription(
        key="control_mode",
        translation_key="control_mode",
        field="control_mode",
        icon="mdi:sync",
        options=list(_CONTROL_MODE_OPTIONS),
        options_map=_CONTROL_MODE_OPTIONS,
    ),
    MultibetonSelectEntityDescription(
        key="curve_select_heating_zone_a",
        field="curve_select_heating_zone_a",
        translation_key="curve_select_heating_zone_a",
        icon="mdi:chart-bell-curve",
        entity_category=EntityCategory.CONFIG,
        options=list(_CURVE_OPTIONS),
        options_map=_CURVE_OPTIONS,
    ),
    MultibetonSelectEntityDescription(
        key="curve_select_cooling_zone_a",
        field="curve_select_cooling_zone_a",
        translation_key="curve_select_cooling_zone_a",
        icon="mdi:chart-bell-curve-cumulative",
        entity_category=EntityCategory.CONFIG,
        options=list(_CURVE_OPTIONS),
        options_map=_CURVE_OPTIONS,
    ),
    # Zone B is shown by default: a second zone, typically an underfloor
    # circuit with its own curves, is common rather than the exception. A
    # plant without a second zone simply reports "disabled" here, which is a
    # better answer than no entity at all.
    MultibetonSelectEntityDescription(
        key="curve_select_heating_zone_b",
        field="curve_select_heating_zone_b",
        translation_key="curve_select_heating_zone_b",
        icon="mdi:chart-bell-curve",
        entity_category=EntityCategory.CONFIG,
        options=list(_CURVE_OPTIONS),
        options_map=_CURVE_OPTIONS,
    ),
    MultibetonSelectEntityDescription(
        key="curve_select_cooling_zone_b",
        field="curve_select_cooling_zone_b",
        translation_key="curve_select_cooling_zone_b",
        icon="mdi:chart-bell-curve-cumulative",
        entity_category=EntityCategory.CONFIG,
        options=list(_CURVE_OPTIONS),
        options_map=_CURVE_OPTIONS,
    ),
    MultibetonSelectEntityDescription(
        key="power_mode",
        translation_key="power_mode",
        field="power_mode",
        icon="mdi:speedometer",
        options=list(_POWER_MODE_OPTIONS),
        options_map=_POWER_MODE_OPTIONS,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: MultibetonConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select platform."""
    async_add_entities(
        MultibetonSelect(
            coordinator=entry.runtime_data.coordinator,
            entity_description=entity_description,
        )
        for entity_description in SELECT_DESCRIPTIONS
    )


class MultibetonSelect(MultibetonEntity, SelectEntity):
    """A writable ``user_parameters`` mode-selection register."""

    entity_description: MultibetonSelectEntityDescription

    def __init__(
        self,
        coordinator: MultibetonDataUpdateCoordinator,
        entity_description: MultibetonSelectEntityDescription,
    ) -> None:
        """Initialize the select class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{entity_description.key}"
        )
        self._value_to_option = {
            value: option for option, value in entity_description.options_map.items()
        }

    @property
    def current_option(self) -> str | None:
        """Return the currently selected option."""
        value = getattr(
            self.coordinator.data.user_parameters, self.entity_description.field
        )
        if value is None:
            return None
        return self._value_to_option.get(value)

    async def async_select_option(self, option: str) -> None:
        """Write the newly selected option to the controller."""
        value = self.entity_description.options_map[option]
        try:
            client = self.coordinator.config_entry.runtime_data.client
            await client.async_write_parameter(
                self.entity_description.field, value=value
            )
        except MultibetonApiClientWriteError as exception:
            raise HomeAssistantError(str(exception)) from exception
        await self.coordinator.async_request_refresh()
