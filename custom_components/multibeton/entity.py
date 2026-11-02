"""Base entities for the Warmondo heat-pump integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    CONF_MODEL,
    CONTROLLER_MODEL_ID,
    DOMAIN,
    MANUFACTURER,
    MODEL_TYPES,
    PRODUCT_LINE,
)
from .coordinator import MultibetonDataUpdateCoordinator

if TYPE_CHECKING:
    from .multibeton_modbus.subsystems import Module


def module_device_identifier(entry_id: str, module: int) -> tuple[str, str]:
    """Return the device-registry identifier of one module of a plant."""
    return (DOMAIN, f"{entry_id}_module_{module}")


class MultibetonEntity(CoordinatorEntity[MultibetonDataUpdateCoordinator]):
    """An entity of the plant as a whole - one device per config entry.

    Holds what exists once per plant: operating mode, setpoints, system
    temperatures and counters. The device carries the controller
    designation but no model, because WM-S to WM-XL name a single module and
    a plant can consist of several.
    """

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(self, coordinator: MultibetonDataUpdateCoordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        model = entry.data.get(CONF_MODEL)
        self._attr_device_info = DeviceInfo(
            identifiers={(entry.domain, entry.entry_id)},
            manufacturer=MANUFACTURER,
            # The type-plate model belongs here too, not only on the module
            # devices: a cascade is built from identical units, so the one
            # model the setup asks for describes the whole plant. A dashboard
            # can then read it from the device instead of having it typed
            # into a card, which is how it ended up wrong on a second plant.
            model=f"{PRODUCT_LINE} {model}" if model else PRODUCT_LINE,
            model_id=CONTROLLER_MODEL_ID,
            hw_version=MODEL_TYPES.get(model) if model else None,
            name=entry.title,
        )


class MultibetonModuleEntity(MultibetonEntity):
    """An entity of one module of the cascade, on that module's own device.

    Every module is its own device, linked to the plant device, so faults,
    pressures and runtimes are attributed to the module they come from.
    Unique IDs follow ``<entry_id>_module_<n>_<key>`` for every module alike.
    """

    def __init__(
        self,
        coordinator: MultibetonDataUpdateCoordinator,
        module: int,
        key: str,
    ) -> None:
        """Initialize for module ``module`` (0 for 0#)."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        model = entry.data.get(CONF_MODEL)
        self.module_index = module
        self._attr_unique_id = f"{entry.entry_id}_module_{module}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={module_device_identifier(entry.entry_id, module)},
            manufacturer=MANUFACTURER,
            # The model from the type plate names one unit, so it belongs
            # here - never the controller designation, which names a
            # component of the heat pump rather than the heat pump itself.
            model=f"{PRODUCT_LINE} {model}" if model else PRODUCT_LINE,
            hw_version=MODEL_TYPES.get(model) if model else None,
            # The first module is the one the others follow, and the
            # trade calls it that: "Master", the rest "Slave 01#" and up.
            # Two keys rather than one, because the master carries no
            # number - "Master 00#" would be noise.
            translation_key="module_master" if module == 0 else "module_slave",
            translation_placeholders={
                "title": entry.title,
                "module": f"{module:02d}",
            },
            via_device=(entry.domain, entry.entry_id),
        )

    @property
    def module(self) -> Module:
        """The module this entity reports on, from the latest refresh."""
        return self.coordinator.data.modules[self.module_index]
