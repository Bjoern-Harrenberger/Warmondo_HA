"""Diagnostics download for a support case.

Settings -> Devices & services -> Warmondo -> three dots -> Download
diagnostics produces one file with everything a service technician asks
for first: integration version, connection settings, module count and every
value the integration currently reads, each with its register address and
the manufacturer's name for it. The gateway address is redacted - the file
is meant to be mailed.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import MultibetonConfigEntry

TO_REDACT = {CONF_HOST}


def _plain(value: Any) -> Any:
    """Turn a decoded register value into something JSON can hold."""
    if isinstance(value, Enum):
        return value.name
    return value


def _component_values(component: Any) -> dict[str, Any]:
    """Every field of one subsystem with its address and current value."""
    values: dict[str, Any] = {}
    for name, resolved in component.resolved_fields.items():
        metadata = component.metadata_for(name)
        values[name] = {
            "address": resolved.address,
            "label": metadata.maker_key if metadata else None,
            "value": _plain(getattr(component, name, None)),
        }
    return values


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: MultibetonConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for one Warmondo plant."""
    runtime = entry.runtime_data
    coordinator = runtime.coordinator
    device = runtime.client.device
    components: dict[str, Any] = {}
    for component in device.components:
        name = type(component).__name__
        offset = getattr(component, "_base_offset", 0)
        if offset:
            name = f"{name} (+{offset})"
        components[name] = _component_values(component)
    return {
        "integration_version": str(runtime.integration.version),
        "entry": {
            "title": entry.title,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
        },
        "last_update_success": coordinator.last_update_success,
        "module_count": len(device.modules),
        "components": components,
    }
