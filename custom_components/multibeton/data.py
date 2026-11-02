"""Custom types for multibeton."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import MultibetonApiClient
    from .coordinator import MultibetonDataUpdateCoordinator


type MultibetonConfigEntry = ConfigEntry[MultibetonData]


@dataclass
class MultibetonData:
    """Data for the Warmondo integration."""

    client: MultibetonApiClient
    coordinator: MultibetonDataUpdateCoordinator
    integration: Integration
