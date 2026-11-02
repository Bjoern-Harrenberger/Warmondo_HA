"""DataUpdateCoordinator for multibeton."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MultibetonApiClientError
from .const import LOGGER
from .multibeton_modbus.device import clamp_module_count

if TYPE_CHECKING:
    from .data import MultibetonConfigEntry
    from .multibeton_modbus.device import MultibetonHeatPump


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class MultibetonDataUpdateCoordinator(DataUpdateCoordinator["MultibetonHeatPump"]):
    """Class to manage fetching data from the Warmondo heat pump."""

    config_entry: MultibetonConfigEntry

    async def _async_update_data(self) -> MultibetonHeatPump:
        """Update data via the ``multibeton_modbus`` layer."""
        try:
            device = await self.config_entry.runtime_data.client.async_get_data()
        except MultibetonApiClientError as exception:
            raise UpdateFailed(str(exception)) from exception
        count = device.system_status.module_count
        reported = clamp_module_count(count)
        if count is not None and reported != len(device.modules):
            # Modules are fixed when the device object is built, so a plant
            # that gained or lost a module is picked up by setting it up anew.
            LOGGER.info(
                "Module count changed from %s to %s, reloading",
                len(device.modules),
                reported,
            )
            self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)
        return device
