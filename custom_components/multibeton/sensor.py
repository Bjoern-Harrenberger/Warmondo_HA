"""Sensor platform for multibeton."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, IntFlag
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    REVOLUTIONS_PER_MINUTE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumeFlowRate,
)

from .const import CONF_READ_ONLY, DEFAULT_READ_ONLY
from .energy import (
    COUNTER_DESCRIPTIONS,
    WINDOW_DESCRIPTIONS,
    EnergyBalance,
    MultibetonEnergyCounter,
    MultibetonEnergyWindowSensor,
)
from .entity import MultibetonEntity, MultibetonModuleEntity
from .multibeton_modbus.enums import ConfiguredMode, CurrentMode, OperatingState
from .multibeton_modbus.fault_labels import fault_label
from .notify_faults import MODULE_FAULT_FIELDS, SYSTEM_FAULT_FIELDS
from .number import NUMBER_DESCRIPTIONS
from .select import SELECT_DESCRIPTIONS

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import MultibetonDataUpdateCoordinator
    from .data import MultibetonConfigEntry
    from .multibeton_modbus.device import MultibetonHeatPump
    from .multibeton_modbus.subsystems import Module, ModuleIO

# The fault words shared with the fault notification, so the sensors and
# the notification can never disagree about what counts as a fault.
_SYSTEM_FAULT_FIELDS = SYSTEM_FAULT_FIELDS
_MODULE_FAULT_FIELDS = MODULE_FAULT_FIELDS


def _enum_options(enum_type: type[IntEnum]) -> list[str]:
    """Lower-cased option strings for a SensorDeviceClass.ENUM sensor."""
    return [member.name.lower() for member in enum_type]


@dataclass(frozen=True, kw_only=True)
class MultibetonSensorEntityDescription(SensorEntityDescription):
    """Describes a sensor reading one attribute of one device subsystem."""

    component: str
    attribute: str


def _temperature(
    component: str, attribute: str, *, diagnostic: bool = True
) -> MultibetonSensorEntityDescription:
    return MultibetonSensorEntityDescription(
        key=f"{component}_{attribute}",
        translation_key=f"{component}_{attribute}",
        component=component,
        attribute=attribute,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC if diagnostic else None,
    )


def _pressure(component: str, attribute: str) -> MultibetonSensorEntityDescription:
    return MultibetonSensorEntityDescription(
        key=f"{component}_{attribute}",
        translation_key=f"{component}_{attribute}",
        component=component,
        attribute=attribute,
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.BAR,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    )


def _runtime_minutes(
    component: str, attribute: str
) -> MultibetonSensorEntityDescription:
    """Describe a runtime register that reads best in minutes.

    For "how long has it been running / standing still *now*", which is a
    matter of minutes and would read as an awkward fraction in hours.
    """
    return MultibetonSensorEntityDescription(
        key=f"{component}_{attribute}",
        translation_key=f"{component}_{attribute}",
        component=component,
        attribute=attribute,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    )


def _runtime_hours(component: str, attribute: str) -> MultibetonSensorEntityDescription:
    """Describe a cumulative runtime counter, shown in hours.

    The registers count minutes, which is the wrong unit to read an
    operating-hours counter in: a plant that has run for a year reports six
    figures. The native unit stays minutes, as the register has it, and
    Home Assistant is asked to display hours - ``duration`` is a convertible
    unit, so it does the arithmetic and keeps a plant's existing statistics
    intact across this change instead of treating it as a unit break. A
    user who prefers minutes can set that back per entity.
    """
    return MultibetonSensorEntityDescription(
        key=f"{component}_{attribute}",
        translation_key=f"{component}_{attribute}",
        component=component,
        attribute=attribute,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        suggested_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=1,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    )


def _count(component: str, attribute: str) -> MultibetonSensorEntityDescription:
    return MultibetonSensorEntityDescription(
        key=f"{component}_{attribute}",
        translation_key=f"{component}_{attribute}",
        component=component,
        attribute=attribute,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:counter",
    )


def _power(
    component: str, attribute: str, unit: str, *, diagnostic: bool
) -> MultibetonSensorEntityDescription:
    return MultibetonSensorEntityDescription(
        key=f"{component}_{attribute}",
        translation_key=f"{component}_{attribute}",
        component=component,
        attribute=attribute,
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=unit,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC if diagnostic else None,
    )


SENSOR_DESCRIPTIONS: tuple[MultibetonSensorEntityDescription, ...] = (
    # -- system_status -----------------------------------------------------
    MultibetonSensorEntityDescription(
        key="system_status_configured_mode",
        translation_key="system_status_configured_mode",
        component="system_status",
        attribute="configured_mode",
        device_class=SensorDeviceClass.ENUM,
        options=_enum_options(ConfiguredMode),
        icon="mdi:thermostat",
    ),
    MultibetonSensorEntityDescription(
        key="system_status_current_mode",
        translation_key="system_status_current_mode",
        component="system_status",
        attribute="current_mode",
        device_class=SensorDeviceClass.ENUM,
        options=_enum_options(CurrentMode),
        icon="mdi:thermostat",
    ),
    MultibetonSensorEntityDescription(
        key="system_status_operating_state",
        translation_key="system_status_operating_state",
        component="system_status",
        attribute="operating_state",
        device_class=SensorDeviceClass.ENUM,
        options=_enum_options(OperatingState),
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    _temperature("system_status", "power_control_target_temp"),
    _temperature("system_status", "power_control_actual_temp"),
    # -- Kennlinien-Arbeitspunkt ------------------------------------------
    # Die Zahlenwerte der sechzehn festen Kurven sind nicht dokumentiert.
    # Diese beiden Sensoren beantworten die Frage trotzdem in Grad: bei
    # dieser (geglaetteten) Aussentemperatur fordert die gewaehlte Kurve
    # genau diese Vorlauftemperatur.
    _temperature(
        "system_status",
        "curve_ambient_temp",
        diagnostic=False,
    ),
    MultibetonSensorEntityDescription(
        key="system_status_module_count",
        translation_key="system_status_module_count",
        component="system_status",
        attribute="module_count",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:counter",
    ),
    _count("system_status", "defrost_count"),
    _count("system_status", "compressor_starts"),
    _count("system_status", "heating_starts"),
    _count("system_status", "cooling_starts"),
    _count("system_status", "dhw_starts"),
    _count("system_status", "aux_heater_starts"),
    _count("system_status", "tank_heater_starts"),
    _runtime_minutes("system_status", "compressor_runtime_continuous_min"),
    _runtime_minutes("system_status", "compressor_idle_continuous_min"),
    _runtime_hours("system_status", "compressor_runtime_total_min"),
    _runtime_hours("system_status", "compressor_runtime_heating_min"),
    _runtime_hours("system_status", "compressor_runtime_cooling_min"),
    _runtime_hours("system_status", "compressor_runtime_dhw_min"),
    _runtime_hours("system_status", "aux_heater_runtime_min"),
    _runtime_hours("system_status", "tank_heater_runtime_min"),
    # -- system_io ----------------------------------------------------------
    # Die drei Ventilstatuswerte stehen namentlich in der Tabelle, ohne
    # Skalierung und ohne Werteliste. Als Diagnose mitgenommen, damit sich
    # beobachten laesst, wie sie sich beim Umschalten verhalten.
    MultibetonSensorEntityDescription(
        key="system_io_valve_1_status",
        translation_key="system_io_valve_1_status",
        component="system_io",
        attribute="valve_1_status",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:valve",
    ),
    MultibetonSensorEntityDescription(
        key="system_io_valve_2_status",
        translation_key="system_io_valve_2_status",
        component="system_io",
        attribute="valve_2_status",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:valve",
    ),
    MultibetonSensorEntityDescription(
        key="system_io_valve_3_status",
        translation_key="system_io_valve_3_status",
        component="system_io",
        attribute="valve_3_status",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:valve",
    ),
    MultibetonSensorEntityDescription(
        key="system_io_mixing_valve_target_opening",
        translation_key="system_io_mixing_valve_target_opening",
        component="system_io",
        attribute="mixing_valve_target_opening",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:valve",
    ),
    MultibetonSensorEntityDescription(
        key="system_io_mixing_valve_opening",
        translation_key="system_io_mixing_valve_opening",
        component="system_io",
        attribute="mixing_valve_opening",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:valve",
    ),
    # -- type_parameters ----------------------------------------------------
    MultibetonSensorEntityDescription(
        key="type_parameters_rated_voltage",
        translation_key="type_parameters_rated_voltage",
        component="type_parameters",
        attribute="rated_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # -- Smart Grid und Anlagengrenzen --------------------------------------
    # Die beiden SG-Ready-Klemmen selbst sind Binaersensoren; diese zwei
    # Register sagen, was die Regelung daraus macht. Die Wertelisten sind
    # nicht dokumentiert, deshalb rohe Zahlen statt einer Aufzaehlung.
    MultibetonSensorEntityDescription(
        key="system_status_smart_grid_status",
        translation_key="system_status_smart_grid_status",
        component="system_status",
        attribute="smart_grid_status",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:transmission-tower",
    ),
    MultibetonSensorEntityDescription(
        key="system_status_smart_grid_command",
        translation_key="system_status_smart_grid_command",
        component="system_status",
        attribute="smart_grid_command",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:transmission-tower-export",
    ),
    MultibetonSensorEntityDescription(
        key="system_status_pump_speed_max",
        translation_key="system_status_pump_speed_max",
        component="system_status",
        attribute="pump_speed_max",
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:pump",
    ),
    MultibetonSensorEntityDescription(
        key="system_status_pump_speed_min",
        translation_key="system_status_pump_speed_min",
        component="system_status",
        attribute="pump_speed_min",
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:pump",
    ),
    MultibetonSensorEntityDescription(
        key="system_status_pump_flow_max",
        translation_key="system_status_pump_flow_max",
        component="system_status",
        attribute="pump_flow_max",
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        native_unit_of_measurement=UnitOfVolumeFlowRate.LITERS_PER_HOUR,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MultibetonSensorEntityDescription(
        key="system_status_pump_flow_min",
        translation_key="system_status_pump_flow_min",
        component="system_status",
        attribute="pump_flow_min",
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        native_unit_of_measurement=UnitOfVolumeFlowRate.LITERS_PER_HOUR,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    MultibetonSensorEntityDescription(
        key="system_status_mixing_valve_cycle_time_s",
        translation_key="system_status_mixing_valve_cycle_time_s",
        component="system_status",
        attribute="mixing_valve_cycle_time_s",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # -- sensors -------------------------------------------------------------
    _temperature("sensors", "room_temp", diagnostic=False),
    _temperature("sensors", "ambient_temp", diagnostic=False),
    _temperature("sensors", "dhw_tank_temp", diagnostic=False),
    _temperature("sensors", "system_flow_temp", diagnostic=False),
    _temperature("sensors", "solar_temp", diagnostic=False),
    _temperature("sensors", "mean_ambient_temp"),
    _temperature("sensors", "buffer_top_temp", diagnostic=False),
    _temperature(
        "sensors",
        "buffer_bottom_temp",
        diagnostic=False,
    ),
    _temperature("sensors", "climate_flow_temp", diagnostic=False),
    _temperature(
        "sensors",
        "floor_heating_flow_temp",
        diagnostic=False,
    ),
    _temperature(
        "sensors",
        "return_temp_zone_a",
        diagnostic=False,
    ),
    _temperature(
        "sensors",
        "curve_flow_temp_zone_a",
        diagnostic=False,
    ),
    _temperature(
        "sensors",
        "curve_flow_temp_zone_a_corrected",
    ),
    _temperature(
        "sensors",
        "curve_flow_temp_zone_b",
    ),
    _temperature(
        "sensors",
        "curve_flow_temp_zone_b_corrected",
    ),
    # -- power -----------------------------------------------------------------
    # Measured on a two-module cascade, register 5500 reported 2.14 kW while
    # the controller's own heating input (3368) reported 4.29 kW and the two
    # modules' inverter outputs summed to 4.01 kW - so whatever 5500 counts,
    # it is not the whole plant, and it is kept as a diagnostic rather than
    # the headline figure. "active_power_input" below is the dependable one.
    _power("power", "power_consumption", UnitOfPower.WATT, diagnostic=True),
    _power("power", "aux_heater_power", UnitOfPower.WATT, diagnostic=False),
    MultibetonSensorEntityDescription(
        key="power_aux_heater_power_configured",
        translation_key="power_aux_heater_power_configured",
        component="power",
        attribute="aux_heater_power_configured",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # The thermal output per operating mode, and the electrical input that
    # produced it. Only one pair carries a value at a time - the mode the
    # plant is not running in reads zero - so all six stay visible rather
    # than being folded into one, and the efficiency sensors below pick the
    # pair that matters.
    _power("power", "heating_capacity", UnitOfPower.KILO_WATT, diagnostic=False),
    _power("power", "cooling_capacity", UnitOfPower.KILO_WATT, diagnostic=False),
    _power("power", "dhw_capacity", UnitOfPower.KILO_WATT, diagnostic=False),
    _power("power", "heating_power_input", UnitOfPower.KILO_WATT, diagnostic=True),
    _power("power", "cooling_power_input", UnitOfPower.KILO_WATT, diagnostic=True),
    _power("power", "dhw_power_input", UnitOfPower.KILO_WATT, diagnostic=True),
    # -- heating_curve (read-only, no write function documented) --------------
    MultibetonSensorEntityDescription(
        key="heating_curve_heating_max_zone_a",
        translation_key="heating_curve_heating_max_zone_a",
        component="heating_curve",
        attribute="heating_max_zone_a",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chart-bell-curve",
    ),
    MultibetonSensorEntityDescription(
        key="heating_curve_heating_min_zone_a",
        translation_key="heating_curve_heating_min_zone_a",
        component="heating_curve",
        attribute="heating_min_zone_a",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chart-bell-curve",
    ),
    MultibetonSensorEntityDescription(
        key="heating_curve_cooling_max_zone_a",
        translation_key="heating_curve_cooling_max_zone_a",
        component="heating_curve",
        attribute="cooling_max_zone_a",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chart-bell-curve-cumulative",
    ),
    MultibetonSensorEntityDescription(
        key="heating_curve_cooling_min_zone_a",
        translation_key="heating_curve_cooling_min_zone_a",
        component="heating_curve",
        attribute="cooling_min_zone_a",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chart-bell-curve-cumulative",
    ),
    MultibetonSensorEntityDescription(
        key="heating_curve_heating_max_zone_b",
        translation_key="heating_curve_heating_max_zone_b",
        component="heating_curve",
        attribute="heating_max_zone_b",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chart-bell-curve",
    ),
    MultibetonSensorEntityDescription(
        key="heating_curve_heating_min_zone_b",
        translation_key="heating_curve_heating_min_zone_b",
        component="heating_curve",
        attribute="heating_min_zone_b",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chart-bell-curve",
    ),
    MultibetonSensorEntityDescription(
        key="heating_curve_cooling_max_zone_b",
        translation_key="heating_curve_cooling_max_zone_b",
        component="heating_curve",
        attribute="cooling_max_zone_b",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chart-bell-curve-cumulative",
    ),
    MultibetonSensorEntityDescription(
        key="heating_curve_cooling_min_zone_b",
        translation_key="heating_curve_cooling_min_zone_b",
        component="heating_curve",
        attribute="cooling_min_zone_b",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chart-bell-curve-cumulative",
    ),
    MultibetonSensorEntityDescription(
        key="heating_curve_slope_heating_max_zone_a",
        translation_key="heating_curve_slope_heating_max_zone_a",
        component="heating_curve",
        attribute="slope_heating_max_zone_a",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chart-bell-curve",
        entity_registry_enabled_default=False,
    ),
    MultibetonSensorEntityDescription(
        key="heating_curve_slope_heating_min_zone_a",
        translation_key="heating_curve_slope_heating_min_zone_a",
        component="heating_curve",
        attribute="slope_heating_min_zone_a",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chart-bell-curve",
        entity_registry_enabled_default=False,
    ),
    MultibetonSensorEntityDescription(
        key="heating_curve_slope_cooling_max_zone_a",
        translation_key="heating_curve_slope_cooling_max_zone_a",
        component="heating_curve",
        attribute="slope_cooling_max_zone_a",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chart-bell-curve-cumulative",
        entity_registry_enabled_default=False,
    ),
    MultibetonSensorEntityDescription(
        key="heating_curve_slope_cooling_min_zone_a",
        translation_key="heating_curve_slope_cooling_min_zone_a",
        component="heating_curve",
        attribute="slope_cooling_min_zone_a",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chart-bell-curve-cumulative",
        entity_registry_enabled_default=False,
    ),
    MultibetonSensorEntityDescription(
        key="heating_curve_slope_heating_max_zone_b",
        translation_key="heating_curve_slope_heating_max_zone_b",
        component="heating_curve",
        attribute="slope_heating_max_zone_b",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chart-bell-curve",
        entity_registry_enabled_default=False,
    ),
    MultibetonSensorEntityDescription(
        key="heating_curve_slope_heating_min_zone_b",
        translation_key="heating_curve_slope_heating_min_zone_b",
        component="heating_curve",
        attribute="slope_heating_min_zone_b",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chart-bell-curve",
        entity_registry_enabled_default=False,
    ),
    MultibetonSensorEntityDescription(
        key="heating_curve_slope_cooling_max_zone_b",
        translation_key="heating_curve_slope_cooling_max_zone_b",
        component="heating_curve",
        attribute="slope_cooling_max_zone_b",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chart-bell-curve-cumulative",
        entity_registry_enabled_default=False,
    ),
    MultibetonSensorEntityDescription(
        key="heating_curve_slope_cooling_min_zone_b",
        translation_key="heating_curve_slope_cooling_min_zone_b",
        component="heating_curve",
        attribute="slope_cooling_min_zone_b",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chart-bell-curve-cumulative",
        entity_registry_enabled_default=False,
    ),
    # -- heat_meter (RAW/UNSCALED - see multibeton_modbus/subsystems/heat_meter.py) --
    # Disabled by default: these numbers are not yet in an engineering unit
    # (see the raw component's docstring), so showing them by default on a
    # dashboard would invite misreading a raw word as kWh/l/h. Enable them
    # in Settings -> Devices & services -> Warmondo -> entity list once you
    # want to inspect/calibrate them against real hardware.
    MultibetonSensorEntityDescription(
        key="heat_meter_heat_cumulative_raw",
        translation_key="heat_meter_heat_cumulative_raw",
        component="heat_meter",
        attribute="heat_cumulative_raw",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:counter",
        entity_registry_enabled_default=False,
    ),
    MultibetonSensorEntityDescription(
        key="heat_meter_flow_cumulative_raw",
        translation_key="heat_meter_flow_cumulative_raw",
        component="heat_meter",
        attribute="flow_cumulative_raw",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:counter",
        entity_registry_enabled_default=False,
    ),
    MultibetonSensorEntityDescription(
        key="heat_meter_flow_instant_raw",
        translation_key="heat_meter_flow_instant_raw",
        component="heat_meter",
        attribute="flow_instant_raw",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:gauge",
        entity_registry_enabled_default=False,
    ),
    MultibetonSensorEntityDescription(
        key="heat_meter_power_instant_raw",
        translation_key="heat_meter_power_instant_raw",
        component="heat_meter",
        attribute="power_instant_raw",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:gauge",
        entity_registry_enabled_default=False,
    ),
    MultibetonSensorEntityDescription(
        key="heat_meter_flow_temp_raw",
        translation_key="heat_meter_flow_temp_raw",
        component="heat_meter",
        attribute="flow_temp_raw",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:thermometer",
        entity_registry_enabled_default=False,
    ),
    MultibetonSensorEntityDescription(
        key="heat_meter_return_temp_raw",
        translation_key="heat_meter_return_temp_raw",
        component="heat_meter",
        attribute="return_temp_raw",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:thermometer",
        entity_registry_enabled_default=False,
    ),
    MultibetonSensorEntityDescription(
        key="heat_meter_status",
        translation_key="heat_meter_status",
        component="heat_meter",
        attribute="status",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:information-outline",
        entity_registry_enabled_default=False,
    ),
    # -- user_parameters (read-only field only, address 6416) -----------------
    # "Feste Kurvenquelle" carries factory/service ("Werk") permission in the
    # source table, not user permission, unlike every other Benutzerparameter
    # field - modeled read-only in the library (see subsystems/user_parameters.py)
    # and surfaced here as a diagnostic sensor rather than a number/select.
    MultibetonSensorEntityDescription(
        key="user_parameters_fixed_curve_source",
        translation_key="user_parameters_fixed_curve_source",
        component="user_parameters",
        attribute="fixed_curve_source",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:cog-outline",
        entity_registry_enabled_default=False,
    ),
)


# Below this electrical input an efficiency figure says nothing about the
# plant. Standby draw, the circulating pump and the controller itself keep
# drawing while the compressor is off, and dividing a near-zero capacity by
# a near-zero input produces a number that swings wildly. The controller
# reports in 0.01 kW steps, so 0.2 kW is also comfortably clear of the
# quantisation noise at the bottom of the scale.
_MIN_POWER_INPUT_KW = 0.2


@dataclass(frozen=True, kw_only=True)
class MultibetonEfficiencySensorEntityDescription(SensorEntityDescription):
    """Describes a coefficient of performance derived from two registers.

    ``capacity`` and ``power_input`` name the two ``power`` attributes whose
    quotient the sensor reports; ``for_modes`` restricts it to the operating
    modes it is meaningful in, or is empty for the sensor that follows
    whichever mode is running.
    """

    capacity: str
    power_input: str
    for_modes: tuple[CurrentMode, ...] = ()


def _efficiency(
    key: str,
    capacity: str,
    power_input: str,
    *,
    for_modes: tuple[CurrentMode, ...] = (),
    icon: str,
) -> MultibetonEfficiencySensorEntityDescription:
    return MultibetonEfficiencySensorEntityDescription(
        key=key,
        translation_key=key,
        capacity=capacity,
        power_input=power_input,
        for_modes=for_modes,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon=icon,
    )


# The coefficient of performance is dimensionless, so these carry no unit
# and no device class - Home Assistant has none for an efficiency ratio.
# The cooling figure is an EER by the usual naming, but the controller
# derives it exactly as the heating one, so it is modelled alongside.
EFFICIENCY_DESCRIPTIONS: tuple[MultibetonEfficiencySensorEntityDescription, ...] = (
    _efficiency(
        "cop_current",
        "heating_capacity",
        "heating_power_input",
        icon="mdi:gauge",
    ),
    _efficiency(
        "cop_heating",
        "heating_capacity",
        "heating_power_input",
        for_modes=(CurrentMode.HEATING,),
        icon="mdi:radiator",
    ),
    _efficiency(
        "cop_cooling",
        "cooling_capacity",
        "cooling_power_input",
        for_modes=(CurrentMode.COOLING,),
        icon="mdi:snowflake",
    ),
    _efficiency(
        "cop_dhw",
        "dhw_capacity",
        "dhw_power_input",
        for_modes=(CurrentMode.DHW,),
        icon="mdi:water-thermometer",
    ),
)

# Which pair of registers the mode-following sensors read, per mode. Index 0
# is the thermal output, index 1 the electrical input that produced it.
_EFFICIENCY_BY_MODE: dict[CurrentMode, tuple[str, str]] = {
    CurrentMode.HEATING: ("heating_capacity", "heating_power_input"),
    CurrentMode.COOLING: ("cooling_capacity", "cooling_power_input"),
    CurrentMode.DHW: ("dhw_capacity", "dhw_power_input"),
}


@dataclass(frozen=True, kw_only=True)
class MultibetonActiveModeSensorEntityDescription(SensorEntityDescription):
    """Describes a value read from whichever operating mode is running.

    ``half`` indexes :data:`_EFFICIENCY_BY_MODE`: 0 for the thermal output,
    1 for the electrical input.
    """

    half: int


# Each operating mode has its own pair of registers, and the five of six that
# belong to the modes standing still read zero. These two sensors follow the
# running mode instead, so a dashboard has one plain "power out" and one
# plain "power in" to show without a template picking between three.
ACTIVE_MODE_DESCRIPTIONS: tuple[MultibetonActiveModeSensorEntityDescription, ...] = (
    MultibetonActiveModeSensorEntityDescription(
        key="active_capacity",
        translation_key="active_capacity",
        half=0,
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MultibetonActiveModeSensorEntityDescription(
        key="active_power_input",
        translation_key="active_power_input",
        half=1,
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


@dataclass(frozen=True, kw_only=True)
class MultibetonModuleSensorEntityDescription(SensorEntityDescription):
    """Describes a sensor that exists once per module of the cascade."""

    value_fn: Callable[[MultibetonHeatPump, int], Any]


def _module_value(attribute: str) -> Callable[[MultibetonHeatPump, int], Any]:
    return lambda device, module: getattr(device.modules[module], attribute)


def _module(  # noqa: PLR0913 - one keyword per entity property
    attribute: str,
    *,
    device_class: SensorDeviceClass | None = None,
    unit: str | None = None,
    icon: str | None = None,
    diagnostic: bool = True,
    enabled_default: bool = True,
) -> MultibetonModuleSensorEntityDescription:
    return MultibetonModuleSensorEntityDescription(
        key=attribute,
        translation_key=f"module_{attribute}",
        value_fn=_module_value(attribute),
        device_class=device_class,
        native_unit_of_measurement=unit,
        state_class=SensorStateClass.MEASUREMENT,
        icon=icon,
        entity_category=EntityCategory.DIAGNOSTIC if diagnostic else None,
        entity_registry_enabled_default=enabled_default,
    )


def _compressor_cop(device: MultibetonHeatPump, module: int) -> float | None:
    """Thermal output of one module over the power into its compressor.

    The controller reports no electrical input per module - the inverter's
    input current reads 0.0 A and the pump's power register answers "sensor
    not present", both measured on a running plant - so a true per-module
    coefficient of performance cannot be formed. What this divides by is the
    inverter's *output*, the power going into the compressor motor, which
    does carry a value and checks out against the inverter's own output
    voltage and current at sqrt(3) * U * I.

    Fan, circulating pump, controller and the inverter's own losses are
    therefore missing from the denominator, and the figure reads high: 6.6
    to 7.1 per module where the plant was working at 5.7 to 6.0. It is a
    comparison between modules - a fouled coil delivers less heat per
    kilowatt of compressor power - and not an efficiency figure to quote.
    """
    unit = device.modules[module]
    heat = unit.current_power
    compressor = unit.inverter_output_power
    if (
        heat is None
        or compressor is None
        or compressor < _MIN_COMPRESSOR_POWER_KW
        or heat <= 0
    ):
        return None
    return round(heat / compressor, 2)


# A compressor drawing less than this is standing still or just starting;
# the ratio would be noise rather than a figure.
_MIN_COMPRESSOR_POWER_KW = 0.2


def _module_temperature(
    attribute: str, *, diagnostic: bool = True
) -> MultibetonModuleSensorEntityDescription:
    return _module(
        attribute,
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        diagnostic=diagnostic,
    )


def _module_pressure(attribute: str) -> MultibetonModuleSensorEntityDescription:
    return _module(
        attribute,
        device_class=SensorDeviceClass.PRESSURE,
        unit=UnitOfPressure.BAR,
    )


MODULE_SENSOR_DESCRIPTIONS: tuple[MultibetonModuleSensorEntityDescription, ...] = (
    # -- refrigerant circuit -------------------------------------------------
    _module_pressure("high_pressure"),
    _module_pressure("low_pressure"),
    _module_temperature("discharge_gas_temp"),
    _module_temperature("suction_gas_temp"),
    _module_temperature("after_valve_temp"),
    _module_temperature("evaporation_saturation_temp"),
    _module_temperature("condensation_saturation_temp"),
    _module_temperature("fin_temp"),
    _module_temperature("ambient_temp"),
    _module(
        "actual_superheat",
        device_class=SensorDeviceClass.TEMPERATURE_DELTA,
        unit=UnitOfTemperature.KELVIN,
    ),
    _module(
        "target_superheat",
        device_class=SensorDeviceClass.TEMPERATURE_DELTA,
        unit=UnitOfTemperature.KELVIN,
        enabled_default=False,
    ),
    # Expert values below are off by default to keep a customer's device page
    # readable; a service technician switches them on where needed.
    _module(
        "main_expansion_valve_opening",
        unit="steps",
        icon="mdi:valve",
        enabled_default=False,
    ),
    _module(
        "aux_expansion_valve_opening",
        unit="steps",
        icon="mdi:valve",
        enabled_default=False,
    ),
    _module("fan_1_speed", unit=REVOLUTIONS_PER_MINUTE, icon="mdi:fan"),
    # -- water side ----------------------------------------------------------
    _module_temperature("phe_flow_temp", diagnostic=False),
    _module_temperature("total_flow_temp", diagnostic=False),
    _module_temperature("phe_return_temp", diagnostic=False),
    _module(
        "pump_flow",
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        unit=UnitOfVolumeFlowRate.LITERS_PER_HOUR,
        diagnostic=False,
    ),
    _module_pressure("water_pressure"),
    # -- power and inverter --------------------------------------------------
    _module(
        "current_power",
        device_class=SensorDeviceClass.POWER,
        unit=UnitOfPower.KILO_WATT,
        diagnostic=False,
    ),
    _module("inverter_actual_speed", unit="rps", icon="mdi:fan"),
    _module("inverter_target_speed", unit="rps", icon="mdi:fan"),
    _module(
        "inverter_output_power",
        device_class=SensorDeviceClass.POWER,
        unit=UnitOfPower.KILO_WATT,
    ),
    # Dimensionless, so no unit and no device class - see _compressor_cop
    # for what it does and does not include.
    MultibetonModuleSensorEntityDescription(
        key="compressor_cop",
        translation_key="module_compressor_cop",
        value_fn=_compressor_cop,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:gauge",
    ),
    _module(
        "inverter_output_current",
        device_class=SensorDeviceClass.CURRENT,
        unit=UnitOfElectricCurrent.AMPERE,
        enabled_default=False,
    ),
    # Measured on a running plant, this register stays at 0.0 A while the
    # compressor turns at 35.9 rps and the module delivers 8.3 kW - the
    # controller does not fill it in. Kept, because another firmware or
    # board revision may, but off by default rather than showing a constant
    # zero that reads like a measurement.
    _module(
        "inverter_input_current",
        device_class=SensorDeviceClass.CURRENT,
        unit=UnitOfElectricCurrent.AMPERE,
        enabled_default=False,
    ),
    _module(
        "inverter_output_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        unit=UnitOfElectricPotential.VOLT,
        enabled_default=False,
    ),
    _module(
        "inverter_module_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        enabled_default=False,
    ),
    MultibetonModuleSensorEntityDescription(
        key="inverter_fault_code",
        translation_key="module_inverter_fault_code",
        value_fn=_module_value("inverter_fault_code"),
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alert-circle-outline",
    ),
    # -- runtime (register 1025 + module, see SystemStatus) ------------------
    # Neither the assignment to the module nor the unit is documented, so the
    # raw value is shown without a unit until checked on the controller.
    MultibetonModuleSensorEntityDescription(
        key="compressor_runtime",
        translation_key="module_compressor_runtime",
        value_fn=lambda device, module: getattr(
            device.system_status, f"compressor_runtime_{module + 1}"
        ),
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:timer-outline",
        entity_registry_enabled_default=False,
    ),
)


@dataclass(frozen=True, kw_only=True)
class MultibetonCascadeSensorEntityDescription(SensorEntityDescription):
    """Describes a value summarized across every module of the cascade.

    A plant is one to eight modules, and the controller keeps plenty of
    readings only per module - pressures, the compressor, the auxiliary
    heater. A dashboard that shows them has to know how many modules there
    are, and breaks when that number differs. These sensors do the
    summarizing here instead, so one dashboard fits a single unit and a
    cascade of eight alike.
    """

    value_fn: Callable[[tuple[Module, ...], tuple[ModuleIO, ...]], Any]


def _running_compressors(
    modules: tuple[Module, ...],  # noqa: ARG001 symmetry with the other value_fns
    ios: tuple[ModuleIO, ...],
) -> int | None:
    """Return how many modules have their compressor relay pulled in."""
    states = [io.compressor_relay for io in ios]
    if all(state is None for state in states):
        return None
    return sum(1 for state in states if state)


def _highest_high_pressure(
    modules: tuple[Module, ...],
    ios: tuple[ModuleIO, ...],  # noqa: ARG001 symmetry with the other value_fns
) -> float | None:
    """Return the highest high-side pressure of any module.

    The highest rather than the average: one module running against a
    blocked condenser is what matters, and an average over its healthy
    siblings would hide it.
    """
    values = [module.high_pressure for module in modules if module.high_pressure]
    return max(values) if values else None


def _lowest_low_pressure(
    modules: tuple[Module, ...],
    ios: tuple[ModuleIO, ...],  # noqa: ARG001 symmetry with the other value_fns
) -> float | None:
    """Return the lowest low-side pressure of any module, for the same reason."""
    values = [module.low_pressure for module in modules if module.low_pressure]
    return min(values) if values else None


CASCADE_SENSOR_DESCRIPTIONS: tuple[MultibetonCascadeSensorEntityDescription, ...] = (
    MultibetonCascadeSensorEntityDescription(
        key="running_compressors",
        translation_key="running_compressors",
        icon="mdi:engine",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_running_compressors,
    ),
    MultibetonCascadeSensorEntityDescription(
        key="highest_high_pressure",
        translation_key="highest_high_pressure",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.BAR,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_highest_high_pressure,
    ),
    MultibetonCascadeSensorEntityDescription(
        key="lowest_low_pressure",
        translation_key="lowest_low_pressure",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.BAR,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_lowest_low_pressure,
    ),
)


class MultibetonCascadeSensor(MultibetonEntity, SensorEntity):
    """A value summarized over every module, on the plant's own device."""

    entity_description: MultibetonCascadeSensorEntityDescription

    def __init__(
        self,
        coordinator: MultibetonDataUpdateCoordinator,
        entity_description: MultibetonCascadeSensorEntityDescription,
    ) -> None:
        """Initialize the cascade sensor."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{entity_description.key}"
        )

    @property
    def available(self) -> bool:
        """Return False when no module supplied a reading."""
        return super().available and self.native_value is not None

    @property
    def native_value(self) -> Any:
        """Return the summarized value."""
        data = self.coordinator.data
        return self.entity_description.value_fn(data.modules, data.module_ios)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MultibetonConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = entry.runtime_data.coordinator
    entities: list[SensorEntity] = [
        MultibetonSensor(coordinator=coordinator, entity_description=description)
        for description in SENSOR_DESCRIPTIONS
    ]
    entities.extend(
        MultibetonActiveModeSensor(
            coordinator=coordinator, entity_description=description
        )
        for description in ACTIVE_MODE_DESCRIPTIONS
    )
    entities.extend(
        MultibetonEfficiencySensor(
            coordinator=coordinator, entity_description=description
        )
        for description in EFFICIENCY_DESCRIPTIONS
    )
    entities.append(MultibetonActiveFaultsSensor(coordinator=coordinator))
    entities.extend(
        MultibetonEnergyCounter(coordinator, description)
        for description in COUNTER_DESCRIPTIONS
    )
    balance = EnergyBalance(hass, entry.entry_id)
    entities.extend(
        MultibetonEnergyWindowSensor(coordinator, balance, description)
        for description in WINDOW_DESCRIPTIONS
    )
    if entry.data.get(CONF_READ_ONLY, DEFAULT_READ_ONLY):
        entities.extend(
            MultibetonMirrorSensor(coordinator, description)
            for description in MIRROR_SENSOR_DESCRIPTIONS
        )
    entities.extend(
        MultibetonCascadeSensor(coordinator=coordinator, entity_description=description)
        for description in CASCADE_SENSOR_DESCRIPTIONS
    )
    for module in range(len(coordinator.data.modules)):
        entities.extend(
            MultibetonModuleSensor(coordinator, module, description)
            for description in MODULE_SENSOR_DESCRIPTIONS
        )
        entities.append(MultibetonModuleActiveFaultsSensor(coordinator, module))
    async_add_entities(entities)
    # Started only once the counters exist, so the first read finds them.
    entry.async_on_unload(balance.async_start())


class MultibetonSensor(MultibetonEntity, SensorEntity):
    """A single value read from one attribute of one device subsystem."""

    entity_description: MultibetonSensorEntityDescription

    def __init__(
        self,
        coordinator: MultibetonDataUpdateCoordinator,
        entity_description: MultibetonSensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{entity_description.key}"
        )

    @property
    def available(self) -> bool:
        """Return False when the controller reports no usable value.

        An analog register answers a sensor problem with one of the
        documented sentinel codes (not present / fault / open circuit /
        short circuit) rather than a measurement, and the multibeton_modbus layer
        decodes those to ``None`` (see
        ``multibeton_modbus.subsystems.sensors.SENSOR_FAULT_CODES``). Left
        alone, Home Assistant would render that ``None`` as *unknown*, which
        reads like a value that has not arrived yet; *unavailable* is the
        honest state for a datapoint the controller says it cannot provide.
        An enum register decoding to ``None`` - an undocumented value the
        library declines to guess at - is treated the same way.
        """
        return super().available and self.native_value is not None

    @property
    def native_value(self) -> Any:
        """Return the current value, mapping enums to their lowercase name."""
        component = getattr(self.coordinator.data, self.entity_description.component)
        value = getattr(component, self.entity_description.attribute)
        if isinstance(value, IntEnum):
            return value.name.lower()
        return value


class MultibetonEfficiencySensor(MultibetonEntity, SensorEntity):
    """A coefficient of performance, thermal output over electrical input.

    The controller reports no efficiency figure of its own; it reports the
    two halves. Dividing them here keeps the number honest - it is an
    instantaneous ratio of two 0.01 kW readings taken in the same refresh,
    not a seasonal figure, and it is deliberately withheld rather than
    guessed at whenever the plant is not working hard enough for the
    quotient to mean anything (see ``_MIN_POWER_INPUT_KW``).
    """

    entity_description: MultibetonEfficiencySensorEntityDescription
    _attr_native_unit_of_measurement = None

    def __init__(
        self,
        coordinator: MultibetonDataUpdateCoordinator,
        entity_description: MultibetonEfficiencySensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{entity_description.key}"
        )

    def _registers(self) -> tuple[str, str] | None:
        """Return the capacity/input pair to divide, or None for no answer.

        A mode-specific sensor answers only while its own mode runs, so a
        heating COP never reports a figure left over from a hot-water cycle.
        The mode-following sensor takes the pair belonging to whatever the
        controller says it is doing, and stays silent in standby and in the
        undocumented mode 3, which decodes to ``None``.
        """
        description = self.entity_description
        mode = self.coordinator.data.system_status.current_mode
        if description.for_modes:
            if mode not in description.for_modes:
                return None
            return description.capacity, description.power_input
        return _EFFICIENCY_BY_MODE.get(mode)

    @property
    def available(self) -> bool:
        """Return False whenever no meaningful ratio can be formed."""
        return super().available and self.native_value is not None

    @property
    def native_value(self) -> float | None:
        """Return output over input, or None when that would mislead."""
        registers = self._registers()
        if registers is None:
            return None
        power = self.coordinator.data.power
        capacity = getattr(power, registers[0])
        power_input = getattr(power, registers[1])
        # Either register answers a sensor problem with None, and an input
        # below the threshold makes the quotient noise rather than a figure.
        if (
            capacity is None
            or power_input is None
            or power_input < _MIN_POWER_INPUT_KW
            or capacity <= 0
        ):
            return None
        return round(capacity / power_input, 2)


class MultibetonActiveModeSensor(MultibetonEntity, SensorEntity):
    """Output or input of whichever operating mode is currently running."""

    entity_description: MultibetonActiveModeSensorEntityDescription

    def __init__(
        self,
        coordinator: MultibetonDataUpdateCoordinator,
        entity_description: MultibetonActiveModeSensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{entity_description.key}"
        )

    @property
    def available(self) -> bool:
        """Return False in standby, where no mode is running."""
        return super().available and self.native_value is not None

    @property
    def native_value(self) -> float | None:
        """Return the running mode's half of the pair, or None in standby."""
        pair = _EFFICIENCY_BY_MODE.get(self.coordinator.data.system_status.current_mode)
        if pair is None:
            return None
        return getattr(self.coordinator.data.power, pair[self.entity_description.half])


class MultibetonModuleSensor(MultibetonModuleEntity, SensorEntity):
    """A single value of one module, on that module's device."""

    entity_description: MultibetonModuleSensorEntityDescription

    def __init__(
        self,
        coordinator: MultibetonDataUpdateCoordinator,
        module: int,
        entity_description: MultibetonModuleSensorEntityDescription,
    ) -> None:
        """Initialize the sensor for module ``module``."""
        super().__init__(coordinator, module, entity_description.key)
        self.entity_description = entity_description

    @property
    def available(self) -> bool:
        """Return False for a sentinel value - see ``MultibetonSensor``."""
        return super().available and self.native_value is not None

    @property
    def native_value(self) -> Any:
        """Return the module's current value."""
        return self.entity_description.value_fn(
            self.coordinator.data, self.module_index
        )


def _active_flags(component: object, fields: tuple[str, ...]) -> list[IntFlag]:
    """Return the set bits of several fault words, word by word."""
    active: list[IntFlag] = []
    for field in fields:
        value = getattr(component, field)
        if value is not None:
            active.extend(value)
    return active


def _active_flag_names(component: object, fields: tuple[str, ...]) -> list[str]:
    """Names of the set bits of several fault words, as ``word.FLAG``."""
    names: list[str] = []
    for field in fields:
        value = getattr(component, field)
        if value is not None:
            names.extend(f"{field}.{flag.name}" for flag in value)
    return names


def _fault_summary(labels: list[str]) -> str:
    """Condense the active faults into one state string.

    German, like the labels themselves: the manufacturer documents the
    fault wording in German only (see
    :mod:`multibeton_modbus.fault_labels`), so translating just the frame
    around it would read worse than leaving both in one language.
    """
    if not labels:
        return "Keine Störung"
    if len(labels) == 1:
        return labels[0]
    return f"{len(labels)} Störungen"


class MultibetonActiveFaultsSensor(MultibetonEntity, SensorEntity):
    """Summarizes which system-wide fault/alarm flags are currently active.

    Aggregates the fully-documented system fault words into one diagnostic
    sensor rather than exposing one entity per bit. The state and the
    ``active_faults`` attribute carry the manufacturer's own German wording
    of each fault (see :mod:`multibeton_modbus.fault_labels`), which is what
    the controller's display shows; ``active_fault_flags`` keeps the
    ``word.FLAG`` identifiers alongside it, for automations that should not
    depend on wording. The faults of each module are on that module's
    device, see :class:`MultibetonModuleActiveFaultsSensor`.
    """

    _attr_translation_key = "active_faults"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, coordinator: MultibetonDataUpdateCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_active_faults"

    def _active_fault_labels(self) -> list[str]:
        faults = self.coordinator.data.faults
        return [
            fault_label(flag) for flag in _active_flags(faults, _SYSTEM_FAULT_FIELDS)
        ]

    @property
    def native_value(self) -> str:
        """Return the fault's own wording, or how many are active."""
        return _fault_summary(self._active_fault_labels())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the active faults, once as text and once as flag names."""
        faults = self.coordinator.data.faults
        return {
            "active_faults": self._active_fault_labels(),
            "active_fault_flags": _active_flag_names(faults, _SYSTEM_FAULT_FIELDS),
        }


class MultibetonModuleActiveFaultsSensor(MultibetonModuleEntity, SensorEntity):
    """Summarizes the active compressor and unit fault flags of one module.

    Reports them the same way
    :class:`MultibetonActiveFaultsSensor` reports the system-wide ones: the
    manufacturer's German wording in the state and in ``active_faults``,
    the ``word.FLAG`` identifiers in ``active_fault_flags``.
    """

    _attr_translation_key = "module_active_faults"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(
        self, coordinator: MultibetonDataUpdateCoordinator, module: int
    ) -> None:
        """Initialize the sensor for module ``module``."""
        super().__init__(coordinator, module, "active_faults")

    def _active_fault_labels(self) -> list[str]:
        return [
            fault_label(flag)
            for flag in _active_flags(self.module, _MODULE_FAULT_FIELDS)
        ]

    @property
    def native_value(self) -> str:
        """Return the fault's own wording, or how many are active."""
        return _fault_summary(self._active_fault_labels())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the active faults, once as text and once as flag names."""
        return {
            "active_faults": self._active_fault_labels(),
            "active_fault_flags": _active_flag_names(self.module, _MODULE_FAULT_FIELDS),
        }


# -- read-only mirrors ----------------------------------------------------
# An entry configured read-only sets up no number and no select platform,
# and those two carry values a plant still wants to show: the setpoints,
# the selected curve, the power mode. Mirrored here as plain sensors so a
# training rig or a monitoring installation displays everything it did
# before, minus the ability to change it. Built from the very same
# descriptions, so the two can never drift apart.


@dataclass(frozen=True, kw_only=True)
class MultibetonMirrorSensorEntityDescription(SensorEntityDescription):
    """Describes a read-only mirror of one ``user_parameters`` control."""

    field: str
    #: Option string per enum value, for a mirror of a select.
    option_for: dict[int, str] | None = None


def _mirror_of_number(description: Any) -> MultibetonMirrorSensorEntityDescription:
    """Mirror one number description as a measurement sensor."""
    unit = description.native_unit_of_measurement
    if unit == UnitOfTemperature.CELSIUS:
        device_class = SensorDeviceClass.TEMPERATURE
    elif unit == UnitOfTime.MINUTES:
        device_class = SensorDeviceClass.DURATION
    else:
        device_class = None
    return MultibetonMirrorSensorEntityDescription(
        key=f"setting_{description.key}",
        translation_key=description.translation_key,
        field=description.field,
        icon=description.icon,
        native_unit_of_measurement=unit,
        device_class=device_class,
        state_class=SensorStateClass.MEASUREMENT,
        # Home Assistant allows only DIAGNOSTIC on a sensor; a control's
        # CONFIG category would make the entity fail to be added and leave
        # it permanently unavailable. A setting shown read-only is
        # diagnostic information anyway.
        entity_category=(
            EntityCategory.DIAGNOSTIC if description.entity_category else None
        ),
        entity_registry_enabled_default=description.entity_registry_enabled_default,
    )


def _mirror_of_select(description: Any) -> MultibetonMirrorSensorEntityDescription:
    """Mirror one select description as an enum sensor."""
    return MultibetonMirrorSensorEntityDescription(
        key=f"setting_{description.key}",
        translation_key=description.translation_key,
        field=description.field,
        icon=description.icon,
        device_class=SensorDeviceClass.ENUM,
        options=list(description.options),
        option_for={
            member.value: option for option, member in description.options_map.items()
        },
        # Home Assistant allows only DIAGNOSTIC on a sensor; a control's
        # CONFIG category would make the entity fail to be added and leave
        # it permanently unavailable. A setting shown read-only is
        # diagnostic information anyway.
        entity_category=(
            EntityCategory.DIAGNOSTIC if description.entity_category else None
        ),
    )


MIRROR_SENSOR_DESCRIPTIONS: tuple[MultibetonMirrorSensorEntityDescription, ...] = (
    *(_mirror_of_number(d) for d in NUMBER_DESCRIPTIONS),
    *(_mirror_of_select(d) for d in SELECT_DESCRIPTIONS),
)


class MultibetonMirrorSensor(MultibetonEntity, SensorEntity):
    """A setting shown as a sensor because this entry may not change it."""

    entity_description: MultibetonMirrorSensorEntityDescription

    def __init__(
        self,
        coordinator: MultibetonDataUpdateCoordinator,
        entity_description: MultibetonMirrorSensorEntityDescription,
    ) -> None:
        """Initialize the mirror sensor."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{entity_description.key}"
        )

    @property
    def available(self) -> bool:
        """Return False when the parameter was not read."""
        return super().available and self.native_value is not None

    @property
    def native_value(self) -> str | float | None:
        """Return the parameter's current value."""
        value = getattr(
            self.coordinator.data.user_parameters, self.entity_description.field
        )
        if value is None:
            return None
        option_for = self.entity_description.option_for
        if option_for is None:
            return value
        return option_for.get(int(value))
