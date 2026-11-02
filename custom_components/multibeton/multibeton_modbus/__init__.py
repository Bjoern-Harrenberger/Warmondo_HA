"""Read and control a MULTIBETON air-to-water heat-pump controller.

Model X1.HL087A.K05.5032, protocol V100C30, over Modbus.

Construct ``MultibetonHeatPump(unit)`` with a ``modbus_connection.ModbusUnit``,
call ``await device.async_update()``, then read its sub-components as normal
Python objects::

    device.sensors.ambient_temp
    device.system_status.current_mode
    device.modules[0].high_pressure

Write a read-back-capable command with::

    await device.async_write_command("system_on", True)

Write a user-adjustable setpoint or mode ("Benutzerparameter", addresses
6400-6444) with::

    await device.async_write_parameter("heating_setpoint_zone_a", 55)

This is a general-purpose, transport-independent Python library: it only
needs a ``modbus_connection.ModbusUnit`` and has no dependency on any
particular application framework. It curates a subset of the controller's
Modbus register map, including every module of a compressor cascade - see
the project README for the full list of covered and deliberately deferred
datapoints.
"""

from __future__ import annotations

from .data_model import MultibetonComponent, MultibetonMetadata
from .device import MultibetonHeatPump
from .enums import (
    CompressorFaults1,
    CompressorStatus,
    ConfiguredMode,
    CurrentMode,
    CurveSelection,
    OperatingState,
    PowerMode,
    StatusFlags,
    SystemFaults1,
    SystemFaults6,
    UnitFaults1,
    UnitFaults2,
)
from .exceptions import MultibetonModbusError, MultibetonWriteAccessError
from .subsystems import (
    Commands,
    Faults,
    HeatingCurve,
    HeatMeter,
    Module,
    Power,
    Sensors,
    SystemStatus,
    UserParameters,
)

__all__ = [
    "Commands",
    "CompressorFaults1",
    "CompressorStatus",
    "ConfiguredMode",
    "CurrentMode",
    "CurveSelection",
    "Faults",
    "HeatMeter",
    "HeatingCurve",
    "Module",
    "MultibetonComponent",
    "MultibetonHeatPump",
    "MultibetonMetadata",
    "MultibetonModbusError",
    "MultibetonWriteAccessError",
    "OperatingState",
    "Power",
    "PowerMode",
    "Sensors",
    "StatusFlags",
    "SystemFaults1",
    "SystemFaults6",
    "SystemStatus",
    "UnitFaults1",
    "UnitFaults2",
    "UserParameters",
]
