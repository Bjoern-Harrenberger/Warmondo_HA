"""Switch platform for multibeton.

Covers two kinds of persistent on/off style registers:

* the read-back-capable command registers on
  ``multibeton_modbus.subsystems.commands.Commands`` (the momentary
  trigger-and-reset commands ``reset_fault`` and ``defrost_command`` are
  button entities instead, see ``button.py``); and
* the boolean "Benutzerparameter" fields on
  ``multibeton_modbus.subsystems.user_parameters.UserParameters``
  (``disinfection_enabled`` and the per-module ``module_N_enabled`` flags,
  addresses 6412 and 6437-6444). A module's enable switch sits on that
  module's device and exists only for the modules the plant reports.

Both are written the same way from Home Assistant's point of view, but go
through different ``multibeton_modbus`` write methods
(``async_write_command`` vs. ``async_write_parameter``), hence the
``component`` field on each description.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError

from .api import MultibetonApiClientWriteError
from .entity import MultibetonEntity, MultibetonModuleEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import MultibetonDataUpdateCoordinator
    from .data import MultibetonConfigEntry


@dataclass(frozen=True, kw_only=True)
class MultibetonSwitchEntityDescription(SwitchEntityDescription):
    """Describes a switch backed by one writable boolean register field."""

    field: str
    component: str = "commands"


SWITCH_DESCRIPTIONS: tuple[MultibetonSwitchEntityDescription, ...] = (
    MultibetonSwitchEntityDescription(
        key="system_on",
        translation_key="system_on",
        field="system_on",
        icon="mdi:power",
    ),
    MultibetonSwitchEntityDescription(
        key="zone_a_on",
        translation_key="zone_a_on",
        field="zone_a_on",
    ),
    MultibetonSwitchEntityDescription(
        key="zone_b_on",
        translation_key="zone_b_on",
        field="zone_b_on",
    ),
    MultibetonSwitchEntityDescription(
        key="dhw_on",
        translation_key="dhw_on",
        field="dhw_on",
        icon="mdi:water-boiler",
    ),
    MultibetonSwitchEntityDescription(
        key="forced_dhw",
        translation_key="forced_dhw",
        field="forced_dhw",
        icon="mdi:water-boiler-alert",
        entity_category=EntityCategory.CONFIG,
    ),
    MultibetonSwitchEntityDescription(
        key="scheduled_disinfection",
        translation_key="scheduled_disinfection",
        field="scheduled_disinfection",
        icon="mdi:biohazard",
        entity_category=EntityCategory.CONFIG,
    ),
    MultibetonSwitchEntityDescription(
        key="vacation_away",
        translation_key="vacation_away",
        field="vacation_away",
        icon="mdi:bag-suitcase",
        entity_category=EntityCategory.CONFIG,
    ),
    MultibetonSwitchEntityDescription(
        key="vacation_home",
        translation_key="vacation_home",
        field="vacation_home",
        icon="mdi:home-account",
        entity_category=EntityCategory.CONFIG,
    ),
    # -- user_parameters ("Benutzerparameter", address 6412) --
    MultibetonSwitchEntityDescription(
        key="disinfection_enabled",
        translation_key="disinfection_enabled",
        field="disinfection_enabled",
        component="user_parameters",
        icon="mdi:biohazard",
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: MultibetonConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    coordinator = entry.runtime_data.coordinator
    entities: list[SwitchEntity] = [
        MultibetonSwitch(
            coordinator=coordinator,
            entity_description=entity_description,
        )
        for entity_description in SWITCH_DESCRIPTIONS
    ]
    entities.extend(
        MultibetonModuleEnableSwitch(coordinator, module)
        for module in range(len(coordinator.data.modules))
    )
    async_add_entities(entities)


class MultibetonSwitch(MultibetonEntity, SwitchEntity):
    """A persistent on/off register (a command or a user parameter)."""

    entity_description: MultibetonSwitchEntityDescription

    def __init__(
        self,
        coordinator: MultibetonDataUpdateCoordinator,
        entity_description: MultibetonSwitchEntityDescription,
    ) -> None:
        """Initialize the switch class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{entity_description.key}"
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        component = getattr(self.coordinator.data, self.entity_description.component)
        return getattr(component, self.entity_description.field)

    async def async_turn_on(self, **_: Any) -> None:
        """Turn on the switch."""
        await self._async_write(value=True)

    async def async_turn_off(self, **_: Any) -> None:
        """Turn off the switch."""
        await self._async_write(value=False)

    async def _async_write(self, *, value: bool) -> None:
        client = self.coordinator.config_entry.runtime_data.client
        write = (
            client.async_write_parameter
            if self.entity_description.component == "user_parameters"
            else client.async_write_command
        )
        try:
            await write(self.entity_description.field, value=value)
        except MultibetonApiClientWriteError as exception:
            raise HomeAssistantError(str(exception)) from exception
        await self.coordinator.async_request_refresh()


class MultibetonModuleEnableSwitch(MultibetonModuleEntity, SwitchEntity):
    """Enables or disables one module of the cascade (6437 + module).

    A user-level parameter in the type parameter table. The unique ID
    ``<entry_id>_module_<n>_enabled`` is the one this switch had before the
    modules got devices of their own, so existing entity IDs carry over.
    """

    _attr_translation_key = "module_enabled"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:developer-board"

    def __init__(
        self, coordinator: MultibetonDataUpdateCoordinator, module: int
    ) -> None:
        """Initialize the switch for module ``module``."""
        super().__init__(coordinator, module, "enabled")
        self._field = f"module_{module}_enabled"

    @property
    def is_on(self) -> bool | None:
        """Return true if the module is enabled."""
        return getattr(self.coordinator.data.user_parameters, self._field)

    async def async_turn_on(self, **_: Any) -> None:
        """Enable the module."""
        await self._async_write(value=True)

    async def async_turn_off(self, **_: Any) -> None:
        """Disable the module."""
        await self._async_write(value=False)

    async def _async_write(self, *, value: bool) -> None:
        client = self.coordinator.config_entry.runtime_data.client
        try:
            await client.async_write_parameter(self._field, value=value)
        except MultibetonApiClientWriteError as exception:
            raise HomeAssistantError(str(exception)) from exception
        await self.coordinator.async_request_refresh()
