"""Exceptions raised by multibeton-modbus."""

from __future__ import annotations


class MultibetonModbusError(Exception):
    """Base class for errors raised by this library."""


class MultibetonWriteAccessError(MultibetonModbusError, RuntimeError):
    """Raised when writing a MULTIBETON command register fails.

    Wraps the backend's raw ``modbus_connection.ModbusError`` so a caller can
    catch one MULTIBETON-specific exception regardless of transport backend.
    """
