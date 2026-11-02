"""The top-level MULTIBETON heat-pump device object."""

from __future__ import annotations

from typing import TYPE_CHECKING

from modbus_connection import ModbusError
from modbus_connection.model import Component, ComponentGroup

from .exceptions import MultibetonWriteAccessError
from .subsystems import (
    IO_STRIDE,
    MAX_MODULES,
    MODULE_STRIDE,
    Commands,
    Faults,
    HeatingCurve,
    HeatMeter,
    Module,
    ModuleIO,
    Power,
    Sensors,
    SystemIO,
    SystemStatus,
    TypeParameters,
    UserParameters,
)

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit


class MultibetonHeatPump:
    """A MULTIBETON X1.HL087A.K05.5032 air-to-water heat-pump controller.

    Owns a single ``modbus_connection.ModbusUnit`` and exposes the
    controller's curated Modbus datapoints as typed sub-components. The
    caller is responsible for building and connecting the underlying
    ``ModbusUnit`` (over TCP, a serial/RTU port, or an RTU-to-TCP gateway);
    this class only reads and writes through it.

    A plant is a cascade of one to eight modules. Everything that exists
    once per module - refrigerant circuit, inverter, module faults - is on
    :attr:`modules`, one :class:`Module` per module in address order. How
    many modules there are is fixed when the object is built; use
    :meth:`async_create` to take the number from the controller itself.

    Example::

        from modbus_connection import ModbusTcpParams
        from modbus_connection.pymodbus import PymodbusConnection
        from multibeton_modbus import MultibetonHeatPump

        connection = PymodbusConnection(ModbusTcpParams(host="10.0.0.5"))
        await connection.connect()
        device = await MultibetonHeatPump.async_create(connection.for_unit(1))
        await device.async_update()
        print(device.sensors.ambient_temp)
        await connection.close()
    """

    def __init__(self, unit: ModbusUnit, module_count: int = 1) -> None:
        """Build the sub-components on top of one Modbus unit. No I/O here.

        Raises ``ValueError`` if ``module_count`` is outside 1 to 8.
        """
        if not 1 <= module_count <= MAX_MODULES:
            msg = f"module_count must be 1 to {MAX_MODULES}, got {module_count}"
            raise ValueError(msg)
        self._unit = unit
        self.system_status = SystemStatus(unit)
        self.sensors = Sensors(unit)
        self.system_io = SystemIO(unit)
        self.power = Power(unit)
        self.faults = Faults(unit)
        self.commands = Commands(unit)
        self.heating_curve = HeatingCurve(unit)
        self.heat_meter = HeatMeter(unit)
        self.user_parameters = UserParameters(unit)
        self.type_parameters = TypeParameters(unit)
        self.modules = tuple(
            Module(unit, base_offset=MODULE_STRIDE * module)
            for module in range(module_count)
        )
        # The discrete inputs step 768 per module, not MODULE_STRIDE's 256,
        # so they are their own component - see subsystems.module_io.
        self.module_ios = tuple(
            ModuleIO(unit, base_offset=IO_STRIDE * module)
            for module in range(module_count)
        )
        self._group = ComponentGroup(unit, self.components)

    @classmethod
    async def async_create(cls, unit: ModbusUnit) -> MultibetonHeatPump:
        """Build a device with as many modules as the controller reports.

        Reads the system status once to learn the module count. A count the
        controller does not supply, or one outside 1 to 8, is clamped into
        that range rather than rejected, so a plant always gets at least
        its first module.

        Raises ``modbus_connection.ModbusError`` if the read fails.
        """
        status = SystemStatus(unit)
        await status.async_update()
        return cls(unit, module_count=clamp_module_count(status.module_count))

    @property
    def modbus_unit(self) -> ModbusUnit:
        """The unit this device reads from and writes to."""
        return self._unit

    @property
    def components(self) -> tuple[Component, ...]:
        """Every subsystem this device refreshes in one pooled update."""
        return (
            self.system_status,
            self.sensors,
            self.system_io,
            self.power,
            self.faults,
            self.commands,
            self.heating_curve,
            self.heat_meter,
            self.user_parameters,
            self.type_parameters,
            *self.modules,
            *self.module_ios,
        )

    async def async_update(self) -> None:
        """Refresh every subsystem in pooled Modbus reads.

        Raises ``modbus_connection.ModbusExceptionError`` if the controller
        rejects a read block.
        """
        await self._group.async_update()

    async def async_write_command(self, field: str, *, value: bool) -> None:
        """Write one boolean command register on :attr:`commands`.

        A thin, friendlier wrapper around ``Commands.write`` that reports a
        failed controller write as :class:`MultibetonWriteAccessError`
        rather than letting the backend's raw ``ModbusError`` propagate
        unchanged - useful for a caller that wants one exception type
        regardless of the configured transport backend.

        Raises ``AttributeError`` for an unknown or read-only field and
        :class:`MultibetonWriteAccessError` if the write itself fails.
        """
        try:
            await self.commands.write(field, value)
        except ModbusError as err:
            msg = f"Could not write MULTIBETON command {field!r}"
            raise MultibetonWriteAccessError(msg) from err

    async def async_write_parameter(self, field: str, value: object) -> None:
        """Write one user-adjustable setpoint or mode field on :attr:`user_parameters`.

        Covers the "Benutzerparameter" register block (addresses 6400-6444):
        temperature setpoints (``int``), the disinfection schedule (``int``),
        module-enable flags (``bool``) and the mode/curve-selection enums
        (``int`` or the matching ``IntEnum``, e.g.
        :class:`~multibeton_modbus.enums.ConfiguredMode`).

        Raises ``AttributeError`` for an unknown or read-only field (for
        example ``fixed_curve_source``, which the source documentation marks
        factory/service level) and :class:`MultibetonWriteAccessError` if the
        write itself fails.
        """
        try:
            await self.user_parameters.write(field, value)
        except ModbusError as err:
            msg = f"Could not write MULTIBETON parameter {field!r}"
            raise MultibetonWriteAccessError(msg) from err


def clamp_module_count(count: int | None) -> int:
    """Return a usable module count for a raw "Anzahl Module" reading."""
    if count is None:
        return 1
    return max(1, min(MAX_MODULES, count))
