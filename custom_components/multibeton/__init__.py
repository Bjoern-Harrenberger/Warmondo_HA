"""Home Assistant integration for a Warmondo air-to-water heat pump.

Talks to the controller over Modbus.

For more details about this integration, please refer to
https://github.com/Bjoern-Harrenberger/Warmondo_HA
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.loader import async_get_integration, async_get_loaded_integration

from .api import MultibetonApiClient, MultibetonApiClientCommunicationError
from .const import (
    CONF_FRAMER,
    CONF_MODEL,
    CONF_READ_ONLY,
    CONF_UNIT_ID,
    DEFAULT_READ_ONLY,
    DOMAIN,
    LOGGER,
    MODEL_VOLTAGES,
)
from .coordinator import MultibetonDataUpdateCoordinator
from .data import MultibetonData
from .entity import module_device_identifier
from .multibeton_modbus.subsystems import MAX_MODULES
from .notify_faults import FaultNotifier

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.device_registry import DeviceEntry
    from homeassistant.helpers.typing import ConfigType

    from .data import MultibetonConfigEntry

#: Platforms that only ever read the controller.
READING_PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.IMAGE,
]

#: Platforms that write to the controller. Left out entirely on an entry
#: configured read-only - see :data:`~.const.DEFAULT_READ_ONLY`.
WRITING_PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
]

PLATFORMS: list[Platform] = [*READING_PLATFORMS, *WRITING_PLATFORMS]

# The controller is polled directly over a local Modbus TCP link (typically
# an RTU-to-TCP gateway on the same network), so a short interval is cheap
# and keeps readings current - unlike a rate-limited cloud API.
SCAN_INTERVAL = timedelta(seconds=30)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

#: The dashboard strategy offered under Settings -> Dashboards -> Add
#: dashboard. Served by the integration itself, so a customer installs
#: nothing besides it; see frontend/warmondo-dashboard.js.
_DASHBOARD_JS = Path(__file__).parent / "frontend" / "warmondo-dashboard.js"
_DASHBOARD_URL = f"/{DOMAIN}/warmondo-dashboard.js"

# Unique-ID keys of entities that described module 0# from the plant device
# before every module got a device of its own, plus the inverter block
# 1033-1046 that was replaced by the per-module inverter values. Their
# successors carry new unique IDs, so these registry entries are orphans.
_RETIRED_KEYS = (
    "sensors_main_expansion_valve_opening",
    "sensors_aux_expansion_valve_opening",
    "sensors_fin_temp",
    "sensors_discharge_gas_temp",
    "sensors_suction_gas_temp",
    "sensors_after_valve_temp",
    "sensors_evaporation_saturation_temp",
    "sensors_condensation_saturation_temp",
    "sensors_low_pressure",
    "sensors_high_pressure",
    "inverter_status_word",
    "inverter_actual_speed",
    "inverter_target_speed",
    "inverter_module_temp",
    "inverter_pfc_temp",
    "inverter_output_power",
    "inverter_output_current",
    "inverter_input_current",
    "inverter_output_torque",
    "inverter_output_voltage",
    "inverter_dc_bus_voltage",
    "inverter_fault_code",
    "defrost_command",
)


def _platforms_for(entry: MultibetonConfigEntry) -> list[Platform]:
    """Return the platforms this entry sets up.

    An entry marked read-only gets the reading platforms only. Entries
    configured before the option existed have no such key and keep every
    platform, so an update changes nothing for them.
    """
    if entry.data.get(CONF_READ_ONLY, DEFAULT_READ_ONLY):
        return READING_PLATFORMS
    return PLATFORMS


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:  # noqa: ARG001
    """Serve the dashboard strategy once, for every entry alike."""
    await hass.http.async_register_static_paths(
        [StaticPathConfig(_DASHBOARD_URL, str(_DASHBOARD_JS), cache_headers=False)]
    )
    integration = await async_get_integration(hass, DOMAIN)
    # The version in the URL makes browsers fetch the new file after an update.
    add_extra_js_url(hass, f"{_DASHBOARD_URL}?v={integration.version}")
    return True


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(
    hass: HomeAssistant,
    entry: MultibetonConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    client = MultibetonApiClient(
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        unit_id=entry.data[CONF_UNIT_ID],
        framer=entry.data[CONF_FRAMER],
    )
    try:
        await client.async_connect()
    except MultibetonApiClientCommunicationError as exception:
        await client.async_close()
        raise ConfigEntryNotReady(str(exception)) from exception

    coordinator = MultibetonDataUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name=DOMAIN,
        update_interval=SCAN_INTERVAL,
        config_entry=entry,
    )
    entry.runtime_data = MultibetonData(
        client=client,
        integration=async_get_loaded_integration(hass, entry.domain),
        coordinator=coordinator,
    )

    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await coordinator.async_config_entry_first_refresh()

    _check_model_against_plant(hass, entry, client.device.type_parameters.rated_voltage)
    _async_remove_retired_entities(hass, entry, len(client.device.modules))
    _async_remove_writing_entities(hass, entry)

    notifier = FaultNotifier(hass, entry)
    notifier.async_update()
    entry.async_on_unload(coordinator.async_add_listener(notifier.async_update))

    await hass.config_entries.async_forward_entry_setups(entry, _platforms_for(entry))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: MultibetonConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    unloaded = await hass.config_entries.async_unload_platforms(
        entry, _platforms_for(entry)
    )
    if unloaded:
        await entry.runtime_data.client.async_close()
    return unloaded


#: Issue raised when the plant contradicts the configured model.
MODEL_MISMATCH_ISSUE = "model_mismatch"


def _check_model_against_plant(
    hass: HomeAssistant,
    entry: MultibetonConfigEntry,
    rated_voltage: int | None,
) -> None:
    """Compare the plant's supply voltage with the configured model.

    The model cannot be read over Modbus - it is set with DIP switches and
    typed in by hand, so a wrong pick goes unnoticed and takes every limit
    and capacity figure derived from it along. The rated voltage can be
    read, and it separates WM-S/WM-M from WM-L/WM-XL.

    A contradiction becomes a repair issue, because a line in the log is
    easy to miss and this one is worth seeing. A controller that has not
    reached its outdoor unit reports 0: a missing answer, not a
    contradiction, and the issue is withdrawn either way once the two
    agree again.
    """
    issue_id = f"{entry.entry_id}_{MODEL_MISMATCH_ISSUE}"
    model = entry.data.get(CONF_MODEL)
    expected = MODEL_VOLTAGES.get(model) if model else None
    if expected is None or not rated_voltage or rated_voltage == expected:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return

    LOGGER.warning(
        "Plant reports %d V, but %s is a %d V unit - the model set for "
        "this entry is probably not the one installed",
        rated_voltage,
        model,
        expected,
    )
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=MODEL_MISMATCH_ISSUE,
        translation_placeholders={
            "title": entry.title,
            "model": str(model),
            "expected": str(expected),
            "measured": str(rated_voltage),
        },
    )


def _async_remove_retired_entities(
    hass: HomeAssistant,
    entry: MultibetonConfigEntry,
    module_count: int,
) -> None:
    """Drop registry entries no current entity will ever claim again.

    Covers the retired keys above and the enable switches of modules the
    plant does not have - those used to exist for all eight modules.
    """
    retired = {f"{entry.entry_id}_{key}" for key in _RETIRED_KEYS}
    retired.update(
        f"{entry.entry_id}_module_{module}_enabled"
        for module in range(module_count, MAX_MODULES)
    )
    registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.unique_id in retired:
            LOGGER.debug("Removing retired entity %s", entity.entity_id)
            registry.async_remove(entity.entity_id)


def _async_remove_writing_entities(
    hass: HomeAssistant,
    entry: MultibetonConfigEntry,
) -> None:
    """Drop the registry entries of writable entities on a read-only entry.

    Without this they would linger as unavailable leftovers of platforms
    that are no longer set up. Switching the option back off re-creates
    them under their old unique IDs, so they return to the entity IDs they
    had before.
    """
    if not entry.data.get(CONF_READ_ONLY, DEFAULT_READ_ONLY):
        return
    domains = {platform.value for platform in WRITING_PLATFORMS}
    registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.domain in domains:
            LOGGER.debug("Entry is read-only, removing %s", entity.entity_id)
            registry.async_remove(entity.entity_id)


async def async_remove_config_entry_device(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: MultibetonConfigEntry,
    device: DeviceEntry,
) -> bool:
    """Allow removing the device of a module the plant no longer reports."""
    runtime_data = getattr(entry, "runtime_data", None)
    if runtime_data is None:
        # Not loaded, so the current module count is unknown - keep it.
        return False
    modules = len(runtime_data.client.device.modules)
    current = {module_device_identifier(entry.entry_id, m) for m in range(modules)}
    current.add((DOMAIN, entry.entry_id))
    return not device.identifiers & current
