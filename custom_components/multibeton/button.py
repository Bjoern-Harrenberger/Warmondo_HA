"""Button platform for multibeton.

Covers the momentary (trigger-and-reset) command registers on
``multibeton_modbus.subsystems.commands.Commands`` - writing ``True`` starts
the action and the controller reports it back as ``0``/``False`` on the next
read once done, so these are represented as buttons rather than switches
(compare ``switch.py`` for the persistent on/off commands).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.exceptions import HomeAssistantError

from .api import MultibetonApiClientWriteError
from .entity import MultibetonEntity, MultibetonModuleEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import MultibetonDataUpdateCoordinator
    from .data import MultibetonConfigEntry


@dataclass(frozen=True, kw_only=True)
class MultibetonButtonEntityDescription(ButtonEntityDescription):
    """Describes a button backed by one writable, momentary ``commands`` field."""

    field: str


BUTTON_DESCRIPTIONS: tuple[MultibetonButtonEntityDescription, ...] = (
    MultibetonButtonEntityDescription(
        key="reset_fault",
        translation_key="reset_fault",
        field="reset_fault",
        icon="mdi:restart-alert",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: MultibetonConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        [
            *(
                MultibetonButton(
                    coordinator=coordinator,
                    entity_description=entity_description,
                )
                for entity_description in BUTTON_DESCRIPTIONS
            ),
            MultibetonModuleDefrostButton(coordinator),
        ]
    )


class MultibetonButton(MultibetonEntity, ButtonEntity):
    """A momentary command register, triggered by writing ``True``."""

    entity_description: MultibetonButtonEntityDescription

    def __init__(
        self,
        coordinator: MultibetonDataUpdateCoordinator,
        entity_description: MultibetonButtonEntityDescription,
    ) -> None:
        """Initialize the button class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{entity_description.key}"
        )

    async def async_press(self) -> None:
        """Trigger the momentary command."""
        try:
            client = self.coordinator.config_entry.runtime_data.client
            await client.async_write_command(self.entity_description.field, value=True)
        except MultibetonApiClientWriteError as exception:
            raise HomeAssistantError(str(exception)) from exception
        await self.coordinator.async_request_refresh()


class MultibetonModuleDefrostButton(MultibetonModuleEntity, ButtonEntity):
    """Starts a defrost on module 0#, on that module's device.

    Only module 0#'s defrost command (64002) is modeled; the commands of
    modules 1# to 7# (64003-64009) are documented but not exposed.
    """

    _attr_translation_key = "module_defrost_command"
    _attr_icon = "mdi:snowflake-melt"

    def __init__(self, coordinator: MultibetonDataUpdateCoordinator) -> None:
        """Initialize the button for module 0#."""
        super().__init__(coordinator, 0, "defrost_command")

    async def async_press(self) -> None:
        """Trigger the defrost."""
        try:
            client = self.coordinator.config_entry.runtime_data.client
            await client.async_write_command("defrost_command", value=True)
        except MultibetonApiClientWriteError as exception:
            raise HomeAssistantError(str(exception)) from exception
        await self.coordinator.async_request_refresh()
