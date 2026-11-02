"""Thin API client wrapping this integration's ``multibeton_modbus`` layer.

Owns the Modbus TCP connection to the RTU-to-TCP gateway (or native Modbus
TCP device) and the :class:`MultibetonHeatPump` device object built
on top of it. See ``multibeton_modbus/`` (see ``MODBUS_LIBRARY.md``) for
the register-level detail and ``modbus_connection`` (a real pip requirement,
see ``manifest.json``) for the transport this client drives.

This integration owns its connection outright - unlike, say, an integration
that borrows a unit from a shared ``modbus_connection`` config entry - so a
config entry here maps to exactly one TCP connection to one gateway/device.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from modbus_connection import ModbusError, ModbusTcpParams
from modbus_connection.tmodbus import TmodbusConnection

from .const import LOGGER
from .multibeton_modbus.device import MultibetonHeatPump
from .multibeton_modbus.exceptions import MultibetonWriteAccessError

if TYPE_CHECKING:
    from modbus_connection import ModbusConnection


class MultibetonApiClientError(Exception):
    """Exception to indicate a general API error."""


class MultibetonApiClientCommunicationError(MultibetonApiClientError):
    """Exception to indicate a communication (connect/read) error."""


class MultibetonApiClientWriteError(MultibetonApiClientError):
    """Exception to indicate a command-write error."""


class MultibetonApiClient:
    """Owns one Modbus TCP connection to a Warmondo heat pump."""

    def __init__(
        self,
        host: str,
        port: int,
        unit_id: int,
        framer: str = "rtu",
    ) -> None:
        """Build the connection. Performs no I/O yet.

        The device object follows in :meth:`async_connect`, because how many
        modules it has is read from the controller.
        """
        self._connection: ModbusConnection = TmodbusConnection(
            ModbusTcpParams(host=host, port=port, framer=framer),
        )
        self._unit_id = unit_id
        self._device: MultibetonHeatPump | None = None

    @property
    def device(self) -> MultibetonHeatPump:
        """The device object, available once :meth:`async_connect` succeeded."""
        if self._device is None:
            msg = "async_connect() must succeed before the device is used"
            raise RuntimeError(msg)
        return self._device

    async def async_connect(self) -> None:
        """Open the Modbus TCP connection and read the plant's module count.

        Raises :class:`MultibetonApiClientCommunicationError` if the
        connection cannot be established or the controller does not answer.
        """
        try:
            await self._connection.connect()
            self._device = await MultibetonHeatPump.async_create(
                self._connection.for_unit(self._unit_id)
            )
        except ModbusError as exception:
            msg = f"Could not connect to the Warmondo heat pump - {exception}"
            raise MultibetonApiClientCommunicationError(msg) from exception

    async def async_get_data(self) -> MultibetonHeatPump:
        """Refresh every subsystem and return the updated device.

        A failed read is retried once on a fresh link. The gateway between
        this integration and the controller can leave a socket open and stop
        answering on it - after a restart on this side, or because it only
        serves one client at a time. The backend then considers itself
        connected and every further poll fails, for good, until someone
        reloads the integration by hand. ``disconnect()`` exists for exactly
        this: it drops the dead link without closing the connection, and the
        next request builds a new one.

        A second failure is reported as before: a plant that is switched off
        or unplugged should show as unavailable rather than hide behind
        endless retries.

        Raises :class:`MultibetonApiClientCommunicationError` if the retry
        fails too.
        """
        try:
            await self.device.async_update()
        except ModbusError as first_error:
            LOGGER.debug(
                "Read failed (%s), dropping the link and trying once more",
                first_error,
            )
            try:
                await self._connection.disconnect()
                await self.device.async_update()
            except ModbusError as retry_error:
                msg = f"Error reading the Warmondo heat pump - {retry_error}"
                raise MultibetonApiClientCommunicationError(msg) from retry_error
            LOGGER.info("Modbus link had gone dead; reconnected and read again")
        return self.device

    async def async_write_command(self, field: str, *, value: bool) -> None:
        """Write one boolean command register.

        Raises :class:`MultibetonApiClientWriteError` if the write fails.
        """
        try:
            await self.device.async_write_command(field, value=value)
        except MultibetonWriteAccessError as exception:
            msg = f"Could not write Warmondo command {field!r} - {exception}"
            raise MultibetonApiClientWriteError(msg) from exception

    async def async_write_parameter(self, field: str, value: object) -> None:
        """Write one user-adjustable setpoint or mode field ("Benutzerparameter").

        Raises :class:`MultibetonApiClientWriteError` if the write fails.
        """
        try:
            await self.device.async_write_parameter(field, value)
        except MultibetonWriteAccessError as exception:
            msg = f"Could not write Warmondo parameter {field!r} - {exception}"
            raise MultibetonApiClientWriteError(msg) from exception

    async def async_close(self) -> None:
        """Close the Modbus TCP connection permanently."""
        await self._connection.close()
