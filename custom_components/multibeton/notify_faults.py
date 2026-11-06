"""Tell the owner when the heat pump reports a fault.

A fault sensor nobody looks at helps nobody. On every refresh this compares
the active faults of the plant and of each module with the previous refresh:

* While anything is active, a persistent notification in Home Assistant
  lists it in the manufacturer's own wording, and is withdrawn once the
  plant is clear again - no setup needed, it is simply there.
* Every change fires the event ``multibeton_fault`` with the same text. The
  blueprint shipped in ``blueprints/`` turns that into a push message on a
  phone, which needs a choice only the owner can make: whose phone.
* Every change is written to the logbook. The notification is withdrawn
  once the plant is clear again, and a fault that comes and goes while
  nobody watches would otherwise leave no trace anyone could find - which
  is exactly what happened on 2026-11-05, four faults over an hour and a
  half, gone before they were seen.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components import persistent_notification
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, LOGGER, MANUFACTURER, SUPPORT_EMAIL, SUPPORT_PHONE
from .multibeton_modbus.enums import StatusFlags
from .multibeton_modbus.fault_labels import fault_label

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import MultibetonConfigEntry

#: Event fired whenever the set of active faults changes.
EVENT_FAULT = f"{DOMAIN}_fault"

#: The fully documented system-wide fault words.
SYSTEM_FAULT_FIELDS = ("system_faults_1", "system_faults_6")
#: The fault words every module carries for itself.
MODULE_FAULT_FIELDS = ("compressor_faults_1", "unit_faults_1", "unit_faults_2")


def _labels(component: object, fields: tuple[str, ...]) -> list[str]:
    labels: list[str] = []
    for field in fields:
        value = getattr(component, field, None)
        if value is not None:
            labels.extend(fault_label(flag) for flag in value)
    return labels


def module_name(module: int) -> str:
    """How the trade calls a module: the first is the master."""
    return "Master" if module == 0 else f"Slave {module:02d}#"


def active_faults(device: Any) -> list[str]:
    """Return every active fault as ``"<where>: <text>"``, plant first."""
    system = _labels(device.faults, SYSTEM_FAULT_FIELDS)
    faults = [f"Anlage: {label}" for label in system]
    for index, module in enumerate(device.modules):
        faults.extend(
            f"{module_name(index)}: {label}"
            for label in _labels(module, MODULE_FAULT_FIELDS)
        )
    status = device.system_status.status_flags
    if not faults and status is not None and StatusFlags.FAULT in status:
        # The controller raises its general fault bit for words this
        # integration does not decode. Say so rather than stay silent.
        faults.append("Anlage: Störung ohne nähere Angabe (siehe Anzeige der Regelung)")
    return faults


class FaultNotifier:
    """Keeps the notification and the event in step with the plant."""

    def __init__(self, hass: HomeAssistant, entry: MultibetonConfigEntry) -> None:
        """Start with no known faults; the first refresh sets the baseline."""
        self._hass = hass
        self._entry = entry
        self._previous: list[str] | None = None
        self._notification_id = f"{DOMAIN}_{entry.entry_id}_fault"

    @callback
    def _async_log(self, current: list[str], previous: list[str]) -> None:
        """Write what changed to the logbook, on the plant's fault sensor.

        The logbook is where someone looks afterwards, and it keeps what
        the notification throws away. Guarded, because an installation
        can run without the logbook - it is part of ``default_config``,
        not of the core.
        """
        if "logbook" not in self._hass.config.components:
            return
        from homeassistant.components import logbook  # noqa: PLC0415

        registry = er.async_get(self._hass)
        entity_id = registry.async_get_entity_id(
            "sensor", DOMAIN, f"{self._entry.entry_id}_active_faults"
        )
        appeared = [fault for fault in current if fault not in previous]
        gone = [fault for fault in previous if fault not in current]
        for fault in appeared:
            logbook.async_log_entry(
                self._hass, self._entry.title, f"Störung: {fault}", DOMAIN, entity_id
            )
        for fault in gone:
            logbook.async_log_entry(
                self._hass, self._entry.title, f"behoben: {fault}", DOMAIN, entity_id
            )

    @callback
    def async_update(self) -> None:
        """Compare with the previous refresh and report any change."""
        coordinator = self._entry.runtime_data.coordinator
        if not coordinator.last_update_success or coordinator.data is None:
            return
        current = active_faults(coordinator.data)
        if current == self._previous:
            return
        previous, self._previous = self._previous, current
        title = self._entry.title

        if current:
            persistent_notification.async_create(
                self._hass,
                "\n".join(f"- {fault}" for fault in current)
                + "\n\nBitte die Anzeige der Regelung prüfen. Bleibt die Störung "
                f"bestehen, hilft der {MANUFACTURER}-Service weiter: "
                f"{SUPPORT_PHONE}, {SUPPORT_EMAIL}",
                title=f"{title}: Störung",
                notification_id=self._notification_id,
            )
        else:
            persistent_notification.async_dismiss(self._hass, self._notification_id)

        # The first refresh only establishes what is already there; an event
        # for it would announce an old fault as new after every restart. The
        # notification above covers a fault that was there all along.
        if previous is None:
            return

        self._async_log(current, previous)
        LOGGER.info("Active faults on %s: %s", title, current or "none")
        new = [fault for fault in current if fault not in (previous or [])]
        self._hass.bus.async_fire(
            EVENT_FAULT,
            {
                "entry_id": self._entry.entry_id,
                "title": title,
                "active": current,
                "new": new,
                "cleared": not current,
                "message": (
                    f"{title}: " + "; ".join(new or current)
                    if current
                    else f"{title}: Störung behoben"
                ),
            },
        )
