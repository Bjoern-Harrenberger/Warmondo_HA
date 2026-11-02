"""Energy balance: heat and electricity counted over time, and work figures.

The controller reports power, not energy. Two counters on the plant device
add the instantaneous thermal output and electrical input up over time -
the same left Riemann sum Home Assistant's integration helper would form,
done here so nobody has to configure one. They survive a restart through
:class:`~homeassistant.components.sensor.RestoreSensor` and are
``total_increasing``, so the recorder keeps long-term statistics for them
and the energy dashboard can use them directly.

On top of the counters sit the figures a heat-pump owner actually asks for:
heat and electricity over the last 24 hours, 7, 30 and 365 days, and the
seasonal work figure for each window - heat divided by electricity, not the
mean of instantaneous efficiency readings, which would overweight part load.
The windows are read from the recorder's long-term statistics with
``statistic_during_period``, because the recorder keeps plain states only for
ten days by default and 30 or 365 days would otherwise be out of reach.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import DOMAIN, LOGGER
from .entity import MultibetonEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .coordinator import MultibetonDataUpdateCoordinator

#: Thermal output registers summed into the heat counter. At most one of the
#: three operating modes runs at a time; the other two read zero.
_CAPACITIES = ("heating_capacity", "cooling_capacity", "dhw_capacity")
#: Electrical input registers summed into the electricity counter.
_POWER_INPUTS = ("heating_power_input", "cooling_power_input", "dhw_power_input")

#: A gap between two readings longer than this is not bridged: the plant was
#: unreachable or Home Assistant was down, and assuming the last power kept
#: flowing through the gap would invent energy.
_MAX_STEP = timedelta(minutes=5)

#: How often the windows are read from the long-term statistics. They move
#: slowly - a 24-hour figure barely changes in a quarter of an hour - and
#: every refresh is a database query.
_WINDOW_REFRESH = timedelta(minutes=15)

#: Below this much electricity in a window a work figure is noise, not a
#: result: a few hours of standby divide into anything.
_MIN_ELECTRICITY_KWH = 0.5

HEAT_ENERGY_KEY = "heat_energy"
ELECTRIC_ENERGY_KEY = "electric_energy"


@dataclass(frozen=True, kw_only=True)
class EnergyCounterDescription(SensorEntityDescription):
    """Describes one of the two counters and the registers it adds up."""

    registers: tuple[str, ...]


COUNTER_DESCRIPTIONS: tuple[EnergyCounterDescription, ...] = (
    EnergyCounterDescription(
        key=HEAT_ENERGY_KEY,
        translation_key=HEAT_ENERGY_KEY,
        registers=_CAPACITIES,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        icon="mdi:fire",
    ),
    EnergyCounterDescription(
        key=ELECTRIC_ENERGY_KEY,
        translation_key=ELECTRIC_ENERGY_KEY,
        registers=_POWER_INPUTS,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        icon="mdi:lightning-bolt",
    ),
)


class MultibetonEnergyCounter(MultibetonEntity, RestoreSensor):
    """Adds one power reading up over time into kilowatt hours."""

    entity_description: EnergyCounterDescription

    def __init__(
        self,
        coordinator: MultibetonDataUpdateCoordinator,
        entity_description: EnergyCounterDescription,
    ) -> None:
        """Initialize the counter at zero; a restored value replaces it."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{entity_description.key}"
        )
        self._attr_native_value = 0.0
        self._last_time: datetime | None = None
        self._last_power: float | None = None

    async def async_added_to_hass(self) -> None:
        """Pick the count up where it stopped before the restart."""
        await super().async_added_to_hass()
        if (data := await self.async_get_last_sensor_data()) is not None:
            try:
                self._attr_native_value = float(data.native_value or 0)
            except TypeError, ValueError:
                LOGGER.warning(
                    "Could not restore %s from %r, starting at zero",
                    self.entity_id,
                    data.native_value,
                )

    def _power(self) -> float | None:
        """Total power of the three modes in kW, or None if unread."""
        power = self.coordinator.data.power
        values = [getattr(power, name) for name in self.entity_description.registers]
        if all(value is None for value in values):
            return None
        # A mode standing still answers None or 0 - both count as nothing.
        return sum(value for value in values if value is not None)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Add the energy since the previous reading (left Riemann sum)."""
        now = dt_util.utcnow()
        power = self._power() if self.coordinator.last_update_success else None
        if (
            self._last_time is not None
            and self._last_power is not None
            and now - self._last_time <= _MAX_STEP
        ):
            hours = (now - self._last_time).total_seconds() / 3600
            self._attr_native_value = round(
                float(self._attr_native_value or 0) + self._last_power * hours, 4
            )
        self._last_time = now
        self._last_power = power
        super()._handle_coordinator_update()


# -- windows ----------------------------------------------------------------

#: Window key and length, in the order they are shown.
WINDOWS: tuple[tuple[str, timedelta], ...] = (
    ("24h", timedelta(hours=24)),
    ("7d", timedelta(days=7)),
    ("30d", timedelta(days=30)),
    ("365d", timedelta(days=365)),
)


class EnergyBalance:
    """Reads the two counters' changes over each window from the recorder.

    One instance per config entry, shared by every window sensor of that
    entry, so the database is asked once per refresh and not once per
    entity.
    """

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Hold the results; nothing is read before :meth:`async_refresh`."""
        self._hass = hass
        self._entry_id = entry_id
        #: (counter key, window key) -> kWh, or None when unknown.
        self.values: dict[tuple[str, str], float | None] = {}
        self._listeners: list[Any] = []

    @callback
    def async_add_listener(self, update: Any) -> Any:
        """Call ``update`` after every refresh; returns the unsubscribe."""
        self._listeners.append(update)
        return lambda: self._listeners.remove(update)

    def _statistic_id(self, key: str) -> str | None:
        """Return the entity ID the counter's statistics are filed under."""
        registry = er.async_get(self._hass)
        return registry.async_get_entity_id("sensor", DOMAIN, f"{self._entry_id}_{key}")

    async def async_refresh(self, *_: Any) -> None:
        """Read every window of both counters and notify the sensors."""
        if "recorder" not in self._hass.config.components:
            return
        # Imported here: the recorder is optional, and a module-level import
        # would load it for an installation that runs without one.
        from homeassistant.components.recorder import get_instance  # noqa: PLC0415
        from homeassistant.components.recorder.statistics import (  # noqa: PLC0415
            statistic_during_period,
        )

        now = dt_util.utcnow()
        for key in (HEAT_ENERGY_KEY, ELECTRIC_ENERGY_KEY):
            statistic_id = self._statistic_id(key)
            for window, length in WINDOWS:
                value: float | None = None
                if statistic_id is not None:
                    try:
                        result = await get_instance(self._hass).async_add_executor_job(
                            statistic_during_period,
                            self._hass,
                            now - length,
                            now,
                            statistic_id,
                            {"change"},
                            None,
                        )
                    except Exception:  # noqa: BLE001 - a failed read is no figure
                        LOGGER.debug("Could not read %s over %s", statistic_id, window)
                    else:
                        change = result.get("change")
                        value = round(change, 2) if change is not None else None
                self.values[(key, window)] = value
        for update in list(self._listeners):
            update()

    @callback
    def async_start(self) -> Any:
        """Refresh now and then periodically; returns the stop callback."""
        self._hass.async_create_task(self.async_refresh())
        return async_track_time_interval(
            self._hass, self.async_refresh, _WINDOW_REFRESH
        )


@dataclass(frozen=True, kw_only=True)
class EnergyWindowDescription(SensorEntityDescription):
    """Describes one figure over one window.

    ``counter`` names the counter whose change is shown, or is None for the
    work figure, which divides the heat counter's change by the electricity
    counter's.
    """

    window: str
    counter: str | None


def _window_descriptions() -> tuple[EnergyWindowDescription, ...]:
    descriptions: list[EnergyWindowDescription] = []
    for window, _length in WINDOWS:
        descriptions.extend(
            (
                EnergyWindowDescription(
                    key=f"heat_energy_{window}",
                    translation_key=f"heat_energy_{window}",
                    window=window,
                    counter=HEAT_ENERGY_KEY,
                    device_class=SensorDeviceClass.ENERGY,
                    native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                    suggested_display_precision=1,
                    icon="mdi:fire",
                ),
                EnergyWindowDescription(
                    key=f"electric_energy_{window}",
                    translation_key=f"electric_energy_{window}",
                    window=window,
                    counter=ELECTRIC_ENERGY_KEY,
                    device_class=SensorDeviceClass.ENERGY,
                    native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                    suggested_display_precision=1,
                    icon="mdi:lightning-bolt",
                ),
                EnergyWindowDescription(
                    key=f"work_figure_{window}",
                    translation_key=f"work_figure_{window}",
                    window=window,
                    counter=None,
                    state_class=SensorStateClass.MEASUREMENT,
                    suggested_display_precision=2,
                    icon="mdi:chart-line",
                ),
            )
        )
    return tuple(descriptions)


WINDOW_DESCRIPTIONS = _window_descriptions()


class MultibetonEnergyWindowSensor(MultibetonEntity, SensorEntity):
    """Heat, electricity or work figure over one rolling window."""

    entity_description: EnergyWindowDescription

    def __init__(
        self,
        coordinator: MultibetonDataUpdateCoordinator,
        balance: EnergyBalance,
        entity_description: EnergyWindowDescription,
    ) -> None:
        """Initialize the window sensor."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._balance = balance
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{entity_description.key}"
        )

    async def async_added_to_hass(self) -> None:
        """Follow the balance's refreshes rather than the plant's."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._balance.async_add_listener(self.async_write_ha_state)
        )

    @property
    def available(self) -> bool:
        """Return False until the window holds a usable figure."""
        return self.native_value is not None

    @property
    def native_value(self) -> float | None:
        """Return the window's change, or heat over electricity."""
        window = self.entity_description.window
        values = self._balance.values
        if self.entity_description.counter is not None:
            return values.get((self.entity_description.counter, window))
        heat = values.get((HEAT_ENERGY_KEY, window))
        electricity = values.get((ELECTRIC_ENERGY_KEY, window))
        if heat is None or electricity is None or electricity < _MIN_ELECTRICITY_KWH:
            return None
        return round(heat / electricity, 2)
