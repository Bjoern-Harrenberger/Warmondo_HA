"""Device subsystems for the MULTIBETON heat-pump controller.

Each subsystem is a ``modbus_connection.model.Component`` subclass reading
one register space (``"input"`` for FC04 status/sensor data, ``"holding"``
for FC03/06/10 read-back-capable commands) of the controller's curated
register map.
"""

from __future__ import annotations

from .commands import Commands
from .faults import Faults
from .heat_meter import HeatMeter
from .heating_curve import HeatingCurve
from .module import MAX_MODULES, MODULE_STRIDE, Module
from .module_io import IO_STRIDE, ModuleIO
from .power import Power
from .sensors import Sensors
from .system_io import SystemIO
from .system_status import SystemStatus
from .type_parameters import TypeParameters
from .user_parameters import UserParameters

__all__ = [
    "IO_STRIDE",
    "MAX_MODULES",
    "MODULE_STRIDE",
    "Commands",
    "Faults",
    "HeatMeter",
    "HeatingCurve",
    "Module",
    "ModuleIO",
    "Power",
    "Sensors",
    "SystemIO",
    "SystemStatus",
    "TypeParameters",
    "UserParameters",
]
