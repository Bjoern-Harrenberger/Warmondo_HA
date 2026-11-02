"""Binary sensor platform for multibeton."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory

from .const import CONF_READ_ONLY, DEFAULT_READ_ONLY
from .entity import MultibetonEntity, MultibetonModuleEntity
from .multibeton_modbus.enums import (
    CompressorStatus,
    OperationFlags,
    StatusFlags,
    SystemInputs,
    SystemRelays,
)
from .switch import SWITCH_DESCRIPTIONS

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import MultibetonDataUpdateCoordinator
    from .data import MultibetonConfigEntry
    from .multibeton_modbus.subsystems import Module, ModuleIO


@dataclass(frozen=True, kw_only=True)
class MultibetonBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a binary sensor read from ``system_status``.

    Either derived from a bit of ``status_flags`` (set ``flag``) or from a
    plain boolean attribute on ``system_status`` (set ``attribute``).
    """

    flag: StatusFlags | None = None
    operation_flag: OperationFlags | None = None
    attribute: str | None = None


BINARY_SENSOR_DESCRIPTIONS: tuple[MultibetonBinarySensorEntityDescription, ...] = (
    MultibetonBinarySensorEntityDescription(
        key="problem",
        translation_key="problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        flag=StatusFlags.FAULT,
    ),
    MultibetonBinarySensorEntityDescription(
        key="defrosting",
        translation_key="defrosting",
        icon="mdi:snowflake-melt",
        flag=StatusFlags.DEFROSTING,
    ),
    MultibetonBinarySensorEntityDescription(
        key="frost_protection",
        translation_key="frost_protection",
        device_class=BinarySensorDeviceClass.COLD,
        flag=StatusFlags.FROST_PROTECTION,
    ),
    MultibetonBinarySensorEntityDescription(
        key="forced_tank_heater",
        translation_key="forced_tank_heater",
        icon="mdi:water-boiler",
        entity_category=EntityCategory.DIAGNOSTIC,
        operation_flag=OperationFlags.FORCED_TANK_HEATER,
    ),
    MultibetonBinarySensorEntityDescription(
        key="forced_aux_heater",
        translation_key="forced_aux_heater",
        icon="mdi:resistor",
        entity_category=EntityCategory.DIAGNOSTIC,
        operation_flag=OperationFlags.FORCED_AUX_HEATER,
    ),
    MultibetonBinarySensorEntityDescription(
        key="forced_external_source",
        translation_key="forced_external_source",
        icon="mdi:fire",
        entity_category=EntityCategory.DIAGNOSTIC,
        operation_flag=OperationFlags.FORCED_EXTERNAL_SOURCE,
    ),
    MultibetonBinarySensorEntityDescription(
        key="floor_heating_present",
        translation_key="floor_heating_present",
        entity_category=EntityCategory.DIAGNOSTIC,
        attribute="floor_heating_present",
    ),
)


@dataclass(frozen=True, kw_only=True)
class MultibetonSystemIoEntityDescription(BinarySensorEntityDescription):
    """Describes one bit of the system board's two IO words.

    Plant-wide, not per module: the hydraulics hang on the master's board
    (see :mod:`multibeton_modbus.subsystems.system_io`), so these exist
    once however many modules the cascade has.
    """

    relay: SystemRelays | None = None
    digital_input: SystemInputs | None = None


SYSTEM_IO_DESCRIPTIONS: tuple[MultibetonSystemIoEntityDescription, ...] = (
    # -- relay outputs: the valves --
    MultibetonSystemIoEntityDescription(
        key="three_way_valve_1",
        translation_key="three_way_valve_1",
        icon="mdi:valve",
        relay=SystemRelays.THREE_WAY_VALVE_1,
    ),
    MultibetonSystemIoEntityDescription(
        key="three_way_valve_2",
        translation_key="three_way_valve_2",
        icon="mdi:valve",
        relay=SystemRelays.THREE_WAY_VALVE_2,
    ),
    MultibetonSystemIoEntityDescription(
        key="three_way_valve_3",
        translation_key="three_way_valve_3",
        icon="mdi:valve",
        relay=SystemRelays.THREE_WAY_VALVE_3,
    ),
    MultibetonSystemIoEntityDescription(
        key="mixing_valve",
        translation_key="mixing_valve",
        icon="mdi:valve",
        relay=SystemRelays.MIXING_VALVE,
    ),
    # -- relay outputs: the pumps --
    MultibetonSystemIoEntityDescription(
        key="external_pump",
        translation_key="external_pump",
        icon="mdi:pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        relay=SystemRelays.EXTERNAL_PUMP,
    ),
    MultibetonSystemIoEntityDescription(
        key="mixing_pump",
        translation_key="mixing_pump",
        icon="mdi:pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        relay=SystemRelays.MIXING_PUMP,
    ),
    MultibetonSystemIoEntityDescription(
        key="return_pump",
        translation_key="return_pump",
        icon="mdi:pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        relay=SystemRelays.RETURN_PUMP,
    ),
    MultibetonSystemIoEntityDescription(
        key="solar_pump",
        translation_key="solar_pump",
        icon="mdi:pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        relay=SystemRelays.SOLAR_PUMP,
    ),
    MultibetonSystemIoEntityDescription(
        key="cell_pump",
        translation_key="cell_pump",
        icon="mdi:pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_category=EntityCategory.DIAGNOSTIC,
        relay=SystemRelays.CELL_PUMP,
    ),
    # -- relay outputs: heat generators beside the heat pump --
    MultibetonSystemIoEntityDescription(
        key="external_heat_source",
        translation_key="external_heat_source",
        icon="mdi:fire",
        device_class=BinarySensorDeviceClass.RUNNING,
        relay=SystemRelays.EXTERNAL_HEAT_SOURCE,
    ),
    MultibetonSystemIoEntityDescription(
        key="tank_heater",
        translation_key="tank_heater",
        icon="mdi:resistor",
        device_class=BinarySensorDeviceClass.RUNNING,
        relay=SystemRelays.TANK_HEATER,
    ),
    # -- relay outputs: the two indication contacts --
    MultibetonSystemIoEntityDescription(
        key="defrost_indication",
        translation_key="defrost_indication",
        icon="mdi:snowflake-melt",
        entity_category=EntityCategory.DIAGNOSTIC,
        relay=SystemRelays.DEFROST_INDICATION,
    ),
    MultibetonSystemIoEntityDescription(
        key="fault_indication",
        translation_key="fault_indication",
        icon="mdi:alert-circle-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        relay=SystemRelays.FAULT_INDICATION,
    ),
    # -- digital inputs: what the installation asks for --
    MultibetonSystemIoEntityDescription(
        key="remote_switch",
        translation_key="remote_switch",
        icon="mdi:toggle-switch-outline",
        digital_input=SystemInputs.REMOTE_SWITCH,
    ),
    MultibetonSystemIoEntityDescription(
        key="heating_switch",
        translation_key="heating_switch",
        icon="mdi:radiator",
        digital_input=SystemInputs.HEATING_SWITCH,
    ),
    MultibetonSystemIoEntityDescription(
        key="cooling_switch",
        translation_key="cooling_switch",
        icon="mdi:snowflake",
        digital_input=SystemInputs.COOLING_SWITCH,
    ),
    MultibetonSystemIoEntityDescription(
        key="dhw_switch",
        translation_key="dhw_switch",
        icon="mdi:water-boiler",
        digital_input=SystemInputs.DHW_SWITCH,
    ),
    MultibetonSystemIoEntityDescription(
        key="thermostat_h",
        translation_key="thermostat_h",
        icon="mdi:thermostat",
        digital_input=SystemInputs.THERMOSTAT_H,
    ),
    MultibetonSystemIoEntityDescription(
        key="thermostat_c",
        translation_key="thermostat_c",
        icon="mdi:thermostat",
        digital_input=SystemInputs.THERMOSTAT_C,
    ),
    MultibetonSystemIoEntityDescription(
        key="solar_signal",
        translation_key="solar_signal",
        icon="mdi:solar-power-variant",
        digital_input=SystemInputs.SOLAR_SIGNAL,
    ),
    MultibetonSystemIoEntityDescription(
        key="tank_heater_feedback",
        translation_key="tank_heater_feedback",
        icon="mdi:electric-switch",
        entity_category=EntityCategory.DIAGNOSTIC,
        digital_input=SystemInputs.TANK_HEATER_FEEDBACK,
    ),
    # -- digital inputs: the two SG-Ready terminals --
    MultibetonSystemIoEntityDescription(
        key="smart_grid_sg",
        translation_key="smart_grid_sg",
        icon="mdi:transmission-tower",
        digital_input=SystemInputs.SMART_GRID_SG,
    ),
    MultibetonSystemIoEntityDescription(
        key="smart_grid_evu",
        translation_key="smart_grid_evu",
        icon="mdi:transmission-tower-import",
        digital_input=SystemInputs.SMART_GRID_EVU,
    ),
)


@dataclass(frozen=True, kw_only=True)
class MultibetonModuleBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a binary sensor that exists once per module."""

    is_on_fn: Callable[[Module], bool | None]


def _module_defrosting(module: Module) -> bool | None:
    if module.compressor_status is None:
        return None
    return CompressorStatus.DEFROSTING in module.compressor_status


def _module_problem(module: Module) -> bool | None:
    words = (module.compressor_faults_1, module.unit_faults_1, module.unit_faults_2)
    if any(word is None for word in words):
        return None
    return any(words)


@dataclass(frozen=True, kw_only=True)
class MultibetonModuleIoEntityDescription(BinarySensorEntityDescription):
    """Describes a binary sensor read straight off one module's IO bits.

    These need their own description because they come from a different
    component than the module's word registers: the discrete inputs are
    their own address space with their own module stride (see
    :mod:`multibeton_modbus.subsystems.module_io`).
    """

    attribute: str


MODULE_IO_DESCRIPTIONS: tuple[MultibetonModuleIoEntityDescription, ...] = (
    # -- what the auxiliary heating is doing --
    MultibetonModuleIoEntityDescription(
        key="aux_heater_1",
        translation_key="module_aux_heater_1",
        attribute="aux_heater_1",
        icon="mdi:resistor",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    MultibetonModuleIoEntityDescription(
        key="aux_heater_2",
        translation_key="module_aux_heater_2",
        attribute="aux_heater_2",
        icon="mdi:resistor",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    MultibetonModuleIoEntityDescription(
        key="aux_heater_feedback",
        translation_key="module_aux_heater_feedback",
        attribute="aux_heater_feedback",
        icon="mdi:electric-switch",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # -- the rest of the module's switching state --
    MultibetonModuleIoEntityDescription(
        key="compressor_relay",
        translation_key="module_compressor_relay",
        attribute="compressor_relay",
        icon="mdi:engine",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    MultibetonModuleIoEntityDescription(
        key="circulation_pump",
        translation_key="module_circulation_pump",
        attribute="circulation_pump",
        icon="mdi:pump",
        device_class=BinarySensorDeviceClass.RUNNING,
    ),
    MultibetonModuleIoEntityDescription(
        key="reversing_valve",
        translation_key="module_reversing_valve",
        attribute="reversing_valve",
        icon="mdi:valve",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MultibetonModuleIoEntityDescription(
        key="evi_valve",
        translation_key="module_evi_valve",
        attribute="evi_valve",
        icon="mdi:valve",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MultibetonModuleIoEntityDescription(
        key="crankcase_heater_1",
        translation_key="module_crankcase_heater_1",
        attribute="crankcase_heater_1",
        icon="mdi:radiator",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MultibetonModuleIoEntityDescription(
        key="crankcase_heater_2",
        translation_key="module_crankcase_heater_2",
        attribute="crankcase_heater_2",
        icon="mdi:radiator",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MultibetonModuleIoEntityDescription(
        key="base_pan_heater",
        translation_key="module_base_pan_heater",
        attribute="base_pan_heater",
        icon="mdi:snowflake-melt",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MultibetonModuleIoEntityDescription(
        key="frost_protection_tape",
        translation_key="module_frost_protection_tape",
        attribute="frost_protection_tape",
        icon="mdi:snowflake-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # -- digital inputs: closed in normal operation, so an opened contact
    # -- is the problem, not the closed one
    MultibetonModuleIoEntityDescription(
        key="flow_switch",
        translation_key="module_flow_switch",
        attribute="flow_switch",
        icon="mdi:waves-arrow-right",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MultibetonModuleIoEntityDescription(
        key="low_pressure_switch",
        translation_key="module_low_pressure_switch",
        attribute="low_pressure_switch",
        icon="mdi:gauge-low",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MultibetonModuleIoEntityDescription(
        key="high_pressure_switch",
        translation_key="module_high_pressure_switch",
        attribute="high_pressure_switch",
        icon="mdi:gauge-full",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


MODULE_BINARY_SENSOR_DESCRIPTIONS: tuple[
    MultibetonModuleBinarySensorEntityDescription, ...
] = (
    MultibetonModuleBinarySensorEntityDescription(
        key="defrosting",
        translation_key="module_defrosting",
        icon="mdi:snowflake-melt",
        is_on_fn=_module_defrosting,
    ),
    MultibetonModuleBinarySensorEntityDescription(
        key="problem",
        translation_key="module_problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        is_on_fn=_module_problem,
    ),
)


class MultibetonAuxHeatingActiveBinarySensor(MultibetonEntity, BinarySensorEntity):
    """Whether any module is running an auxiliary heater right now.

    The relays sit on each module, so a dashboard asking "is the auxiliary
    heating on" would have to know how many modules exist. Summarized here
    instead, this reads the same on a single unit and on a cascade of
    eight.
    """

    _attr_translation_key = "aux_heating_active"
    _attr_icon = "mdi:resistor"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator: MultibetonDataUpdateCoordinator) -> None:
        """Initialize the cascade-wide auxiliary heating sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_aux_heating_active"

    @property
    def available(self) -> bool:
        """Return False when no module supplied its relay state."""
        return super().available and self.is_on is not None

    @property
    def is_on(self) -> bool | None:
        """Return true if any module has either heater stage pulled in."""
        states = [
            state
            for io in self.coordinator.data.module_ios
            for state in (io.aux_heater_1, io.aux_heater_2)
        ]
        if all(state is None for state in states):
            return None
        return any(states)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return how many modules are heating, for a dashboard to show."""
        return {
            "modules_heating": sum(
                1
                for io in self.coordinator.data.module_ios
                if io.aux_heater_1 or io.aux_heater_2
            ),
            "modules_total": len(self.coordinator.data.module_ios),
        }


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: MultibetonConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary_sensor platform."""
    coordinator = entry.runtime_data.coordinator
    entities: list[BinarySensorEntity] = [
        MultibetonBinarySensor(
            coordinator=coordinator,
            entity_description=entity_description,
        )
        for entity_description in BINARY_SENSOR_DESCRIPTIONS
    ]
    entities.append(MultibetonAuxHeatingActiveBinarySensor(coordinator))
    if entry.data.get(CONF_READ_ONLY, DEFAULT_READ_ONLY):
        entities.extend(
            MultibetonMirrorBinarySensor(coordinator, description)
            for description in MIRROR_BINARY_SENSOR_DESCRIPTIONS
        )
        entities.extend(
            MultibetonMirrorModuleEnabledBinarySensor(coordinator, module)
            for module in range(len(coordinator.data.modules))
        )
    entities.extend(
        MultibetonSystemIoBinarySensor(coordinator, entity_description)
        for entity_description in SYSTEM_IO_DESCRIPTIONS
    )
    entities.extend(
        MultibetonModuleBinarySensor(coordinator, module, entity_description)
        for module in range(len(coordinator.data.modules))
        for entity_description in MODULE_BINARY_SENSOR_DESCRIPTIONS
    )
    entities.extend(
        MultibetonModuleIoBinarySensor(coordinator, module, entity_description)
        for module in range(len(coordinator.data.module_ios))
        for entity_description in MODULE_IO_DESCRIPTIONS
    )
    async_add_entities(entities)


class MultibetonBinarySensor(MultibetonEntity, BinarySensorEntity):
    """A binary sensor derived from ``system_status``."""

    entity_description: MultibetonBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: MultibetonDataUpdateCoordinator,
        entity_description: MultibetonBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary_sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{entity_description.key}"
        )

    @property
    def available(self) -> bool:
        """Return False when the underlying status bit is not readable.

        Same reasoning as ``MultibetonSensor.available``: a ``None`` here
        means the controller did not supply the status word, which is
        *unavailable*, not *unknown*.
        """
        return super().available and self.is_on is not None

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary_sensor is on."""
        system_status = self.coordinator.data.system_status
        description = self.entity_description
        if description.flag is not None:
            status_flags = system_status.status_flags
            if status_flags is None:
                return None
            return description.flag in status_flags
        if description.operation_flag is not None:
            operation_flags = system_status.operation_flags
            if operation_flags is None:
                return None
            return description.operation_flag in operation_flags
        return getattr(system_status, description.attribute)


class MultibetonModuleBinarySensor(MultibetonModuleEntity, BinarySensorEntity):
    """A binary sensor of one module, on that module's device."""

    entity_description: MultibetonModuleBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: MultibetonDataUpdateCoordinator,
        module: int,
        entity_description: MultibetonModuleBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor for module ``module``."""
        super().__init__(coordinator, module, entity_description.key)
        self.entity_description = entity_description

    @property
    def available(self) -> bool:
        """Return False when the module's status word is not readable."""
        return super().available and self.is_on is not None

    @property
    def is_on(self) -> bool | None:
        """Return true if the condition is present on this module."""
        return self.entity_description.is_on_fn(self.module)


class MultibetonModuleIoBinarySensor(MultibetonModuleEntity, BinarySensorEntity):
    """One relay output or digital input of a module, on that module's device."""

    entity_description: MultibetonModuleIoEntityDescription

    def __init__(
        self,
        coordinator: MultibetonDataUpdateCoordinator,
        module: int,
        entity_description: MultibetonModuleIoEntityDescription,
    ) -> None:
        """Initialize the IO binary sensor for module ``module``."""
        super().__init__(coordinator, module, entity_description.key)
        self.entity_description = entity_description

    @property
    def module_io(self) -> ModuleIO:
        """Return this module's IO component."""
        return self.coordinator.data.module_ios[self.module_index]

    @property
    def available(self) -> bool:
        """Return False when the bit was not read."""
        return super().available and self.is_on is not None

    @property
    def is_on(self) -> bool | None:
        """Return the state of this bit."""
        return getattr(self.module_io, self.entity_description.attribute)


class MultibetonSystemIoBinarySensor(MultibetonEntity, BinarySensorEntity):
    """One relay output or digital input of the system board.

    Sits on the plant device, not on a module's: these contacts are wired
    to the master and describe the whole installation.
    """

    entity_description: MultibetonSystemIoEntityDescription

    def __init__(
        self,
        coordinator: MultibetonDataUpdateCoordinator,
        entity_description: MultibetonSystemIoEntityDescription,
    ) -> None:
        """Initialize the system IO binary sensor."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_system_{entity_description.key}"
        )

    @property
    def available(self) -> bool:
        """Return False when the IO word was not read."""
        return super().available and self.is_on is not None

    @property
    def is_on(self) -> bool | None:
        """Return the state of this bit."""
        system_io = self.coordinator.data.system_io
        description = self.entity_description
        if description.relay is not None:
            relays = system_io.relay_outputs
            if relays is None:
                return None
            return description.relay in relays
        inputs = system_io.digital_inputs
        if inputs is None:
            return None
        return description.digital_input in inputs


# -- read-only mirrors ----------------------------------------------------
# Same reasoning as the mirror sensors in :mod:`.sensor`: a read-only entry
# sets up no switch platform, but whether a zone is released and whether
# hot water is enabled are things a training rig still wants to display.


@dataclass(frozen=True, kw_only=True)
class MultibetonMirrorBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a read-only mirror of one switch."""

    field: str
    component: str


MIRROR_BINARY_SENSOR_DESCRIPTIONS: tuple[
    MultibetonMirrorBinarySensorEntityDescription, ...
] = tuple(
    MultibetonMirrorBinarySensorEntityDescription(
        key=f"setting_{description.key}",
        translation_key=description.translation_key,
        field=description.field,
        component=description.component,
        icon=description.icon,
        # Same restriction as for the mirror sensors: a binary sensor may
        # not carry CONFIG, only DIAGNOSTIC.
        entity_category=(
            EntityCategory.DIAGNOSTIC if description.entity_category else None
        ),
    )
    for description in SWITCH_DESCRIPTIONS
)


class MultibetonMirrorBinarySensor(MultibetonEntity, BinarySensorEntity):
    """A setting shown as a binary sensor because this entry may not change it."""

    entity_description: MultibetonMirrorBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: MultibetonDataUpdateCoordinator,
        entity_description: MultibetonMirrorBinarySensorEntityDescription,
    ) -> None:
        """Initialize the mirror binary sensor."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{entity_description.key}"
        )

    @property
    def available(self) -> bool:
        """Return False when the command register was not read."""
        return super().available and self.is_on is not None

    @property
    def is_on(self) -> bool | None:
        """Return the command's current state."""
        component = getattr(self.coordinator.data, self.entity_description.component)
        return getattr(component, self.entity_description.field)


class MultibetonMirrorModuleEnabledBinarySensor(
    MultibetonModuleEntity, BinarySensorEntity
):
    """Whether one module is released, on a read-only entry.

    Counterpart of ``MultibetonModuleEnableSwitch`` for a plant nobody may
    change - the release is worth showing even where it cannot be set.
    """

    _attr_translation_key = "module_enabled"
    _attr_icon = "mdi:heat-pump-outline"

    def __init__(
        self,
        coordinator: MultibetonDataUpdateCoordinator,
        module: int,
    ) -> None:
        """Initialize the mirror for module ``module``."""
        super().__init__(coordinator, module, "setting_enabled")
        self._field = f"module_{module}_enabled"

    @property
    def available(self) -> bool:
        """Return False when the parameter was not read."""
        return super().available and self.is_on is not None

    @property
    def is_on(self) -> bool | None:
        """Return true if this module is released."""
        return getattr(self.coordinator.data.user_parameters, self._field)
