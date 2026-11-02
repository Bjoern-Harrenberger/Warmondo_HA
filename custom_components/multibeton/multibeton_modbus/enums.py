"""Enumerations for the MULTIBETON heat-pump controller's Modbus datapoints.

Members are named after the documented meaning of each value or bit; a value
or bit position the manufacturer's register tables leave undocumented is
simply not given a name (a flag class keeps such bits, an ``IntEnum`` decodes
an undocumented value to ``None`` with a one-time warning).
"""

from __future__ import annotations

from enum import IntEnum, IntFlag


class ConfiguredMode(IntEnum):
    """User-configured operating mode (Anlagenstatus -> Eingestellter Modus)."""

    COOL = 1
    HEAT = 2
    AUTO = 3


class CurrentMode(IntEnum):
    """Actual operating mode the controller is currently running.

    Value 3 ("reserviert") is not documented and is intentionally omitted;
    the controller reading it decodes to ``None``.
    """

    NONE = 0
    COOLING = 1
    HEATING = 2
    DHW = 4


class PowerMode(IntEnum):
    """User-selected power/performance mode (Benutzerparameter -> Leistungsmodus)."""

    STANDARD = 0
    BOOST = 1
    ECO = 2
    AUTO = 3


class OperationFlags(IntFlag):
    """What the plant is currently running (Betriebs-Flags 0, register 912).

    Each bit says that the named function is active now - not that it is
    configured. The three forced-operation bits are the readable
    counterpart of the write-only forcing commands at 1042-1047.
    """

    NONE = 0
    ZONE_A = 1 << 0
    ZONE_B = 1 << 1
    DHW = 1 << 2
    RETURN_PUMP_SCHEDULE = 1 << 3
    FORCED_DHW = 1 << 4
    SCHEDULED_DISINFECTION = 1 << 5
    DISINFECTION_RETURN_PUMP = 1 << 6
    VACATION_AWAY = 1 << 7
    VACATION_HOME = 1 << 8
    FORCED_TANK_HEATER = 1 << 9
    FORCED_AUX_HEATER = 1 << 10
    FORCED_EXTERNAL_SOURCE = 1 << 11
    FLOOR_PREHEAT = 1 << 12
    FLOOR_SCREED_DRYING = 1 << 13
    CAPACITY_TEST = 1 << 14
    REFRIGERANT_RECOVERY = 1 << 15


class CurveSelection(IntEnum):
    """Heating/cooling curve selected for a climate zone (Kurvenauswahl).

    Addresses 6425-6428. The numeric definition of the sixteen fixed curves
    (which flow temperature each demands at a given ambient temperature) is
    not given in the manufacturer's documentation available to this project -
    only their names. What the *selected* curve currently demands is readable
    from the controller instead: see ``SystemStatus.curve_ambient_temp`` and
    ``Sensors.curve_flow_temp_zone_a``/``_zone_b``.

    Curves 9 and 10 are two-point curves defined by an ambient/outlet pair
    (curve 9 user-adjustable at 6429-6436, curve 10 factory-set); curves 11
    and 12 are slope/offset curves whose resulting bounds are readable at
    addresses 875-882 (see
    :class:`~multibeton_modbus.subsystems.heating_curve.HeatingCurve`).
    """

    DISABLED = 0
    LOW_TEMP_1 = 1
    LOW_TEMP_2 = 2
    LOW_TEMP_3 = 3
    LOW_TEMP_4 = 4
    LOW_TEMP_5 = 5
    LOW_TEMP_6 = 6
    LOW_TEMP_7 = 7
    LOW_TEMP_8 = 8
    HIGH_TEMP_1 = 9
    HIGH_TEMP_2 = 10
    HIGH_TEMP_3 = 11
    HIGH_TEMP_4 = 12
    HIGH_TEMP_5 = 13
    HIGH_TEMP_6 = 14
    HIGH_TEMP_7 = 15
    HIGH_TEMP_8 = 16
    CURVE_9 = 17
    CURVE_10 = 18
    CURVE_11 = 19
    CURVE_12 = 20


class OperatingState(IntEnum):
    """Coarse system operating state (Betriebszustand)."""

    STANDBY = 0
    STARTING = 1
    RUNNING = 2
    SHUTTING_DOWN = 3
    SEVERE_ALARM = 4


class StatusFlags(IntFlag):
    """Bit flags of the overall system status word (Anlagenstatus)."""

    NONE = 0
    STANDBY = 1 << 0
    STARTING = 1 << 1
    RUNNING = 1 << 2
    SHUTTING_DOWN = 1 << 3
    SEVERE_ALARM = 1 << 4
    PREHEATING = 1 << 8
    FAULT = 1 << 9
    FROST_PROTECTION = 1 << 10
    DEFROSTING = 1 << 11


class CompressorStatus(IntFlag):
    """Bit flags of one module's compressor status word (Verdichterstatus).

    The register table documents a single bit of this word; the others are
    kept as unnamed bits rather than guessed at.
    """

    NONE = 0
    DEFROSTING = 1 << 13


class CompressorFaults1(IntFlag):
    """Compressor-circuit fault bits of one module (Verdichterstörungen 1)."""

    NONE = 0
    LOW_PRESSURE = 1 << 0
    HIGH_PRESSURE = 1 << 1
    FIN_TEMP_FAULT = 1 << 4
    DISCHARGE_TEMP_FAULT = 1 << 5
    DISCHARGE_TEMP_TOO_HIGH = 1 << 6
    PRESSURE_SENSOR_J5_FAULT = 1 << 7
    PRESSURE_SENSOR_J6_FAULT = 1 << 8
    LOW_PRESSURE_TOO_LOW = 1 << 9
    HIGH_PRESSURE_TOO_HIGH = 1 << 10
    SUCTION_TEMP_FAULT = 1 << 11
    AFTER_VALVE_TEMP_FAULT = 1 << 12
    SUCTION_TEMP_TOO_LOW = 1 << 13
    EMERGENCY_DEFROST_TOO_FREQUENT = 1 << 14
    SUCTION_DISCHARGE_DIFF_IMPLAUSIBLE = 1 << 15


class UnitFaults1(IntFlag):
    """Heat-pump unit fault bits, group 1 (Einheitenstörungen 1)."""

    NONE = 0
    AMBIENT_TEMP_FAULT = 1 << 0
    COMMUNICATION_FAULT = 1 << 1
    EEPROM_DATA_ERROR = 1 << 2
    AUX_HEATER_OVERLOAD = 1 << 3
    PHE_FLOW_TEMP_TOO_LOW = 1 << 5
    PHE_FLOW_TEMP_TOO_HIGH = 1 << 6
    PHE_FLOW_TEMP_FAULT = 1 << 7
    FLOW_TOO_LOW = 1 << 8
    PHASE_LOSS_PROTECTION = 1 << 9
    PHE_RETURN_TEMP_FAULT = 1 << 10
    SYSTEM_FLOW_TEMP_FAULT = 1 << 11
    PHASE_SEQUENCE_PROTECTION = 1 << 12
    PHE_FLOW_RETURN_DIFF_TOO_LARGE = 1 << 13
    PHE_FLOW_RETURN_DIFF_IMPLAUSIBLE = 1 << 14
    INVERTER_PUMP_WARNING = 1 << 15


class UnitFaults2(IntFlag):
    """Heat-pump unit fault bits, group 2 (Einheitenstörungen 2)."""

    NONE = 0
    COMMUNICATION_ERROR = 1 << 0
    INDOOR_OUTDOOR_COMM_FAULT = 1 << 1
    PROTOCOL_VERSION_TOO_LOW = 1 << 2
    INVERTER_PUMP_FAULT = 1 << 3
    TYPE_SETTING_ERROR = 1 << 4
    R290_SENSOR_FAULT = 1 << 5
    R290_LEAK = 1 << 6
    FLOW_SENSOR_FAULT = 1 << 7
    WATER_PRESSURE_SENSOR_FAULT = 1 << 8
    INDOOR_OUTDOOR_COMM_ERROR = 1 << 9
    LED_BAR_COMM_FAULT = 1 << 10
    HEAT_METER_COMM_FAULT = 1 << 11
    ENERGY_METER_COMM_FAULT = 1 << 12


class SystemFaults1(IntFlag):
    """System-wide fault bits, group 1 (Systemstörungen 1)."""

    NONE = 0
    PHASE_SEQUENCE_PROTECTION = 1 << 1
    EEPROM_DATA_ERROR = 1 << 2
    CELL_TEMP_1_FAULT = 1 << 3
    CELL_TEMP_2_FAULT = 1 << 4
    SYSTEM_MAINTENANCE_DATA_ERROR = 1 << 6
    PHASE_LOSS_PROTECTION = 1 << 7
    TANK_HEATER_OVERLOAD = 1 << 10
    DHW_TANK_TEMP_FAULT = 1 << 12
    SYSTEM_FLOW_TEMP_FAULT = 1 << 14
    FLOOR_HEATING_FLOW_TEMP_FAULT = 1 << 15


class SystemFaults6(IntFlag):
    """System-wide fault bits, group 6 (Systemstörungen 6)."""

    NONE = 0
    BUFFER_TOP_TEMP_FAULT = 1 << 0
    BUFFER_BOTTOM_TEMP_FAULT = 1 << 1
    SOLAR_TEMP_FAULT = 1 << 2
    WIRED_REMOTE_COMM_FAULT = 1 << 3
    CLIMATE_FLOW_TEMP_FAULT = 1 << 4
    ROOM_TEMP_FAULT = 1 << 5
    SYSTEM_LOCKED_FREQUENT_STARTS = 1 << 7
    ZONE_A_RETURN_TEMP_FAULT = 1 << 9


class SystemRelays(IntFlag):
    """Relay outputs of the system board (Relaisausgänge System).

    These are the plant's shared hydraulics, not a module's own relays.
    In a cascade every valve, pump and external heat source is wired to
    the master; the slaves have no system board of their own.
    """

    NONE = 0
    DEFROST_INDICATION = 1 << 0
    FAULT_INDICATION = 1 << 1
    EXTERNAL_HEAT_SOURCE = 1 << 2
    THREE_WAY_VALVE_1 = 1 << 3
    # B4 is valve 3 and B5 is valve 2 - the table lists them in that order.
    THREE_WAY_VALVE_3 = 1 << 4
    THREE_WAY_VALVE_2 = 1 << 5
    TANK_HEATER = 1 << 6
    MIXING_VALVE = 1 << 7
    RETURN_PUMP = 1 << 8
    SOLAR_PUMP = 1 << 9
    MIXING_PUMP = 1 << 10
    EXTERNAL_PUMP = 1 << 11
    CELL_PUMP = 1 << 12


class SystemInputs(IntFlag):
    """Digital inputs of the system board (Digitaleingänge System).

    Everything an installation can feed the plant from outside: the remote
    switch, the three mode switches, both thermostat signals, the solar
    signal, the tank heater's feedback contact and the two SG-Ready
    terminals. Like :class:`SystemRelays` these are wired to the master.
    """

    NONE = 0
    REMOTE_SWITCH = 1 << 1
    COOLING_SWITCH = 1 << 3
    HEATING_SWITCH = 1 << 4
    DHW_SWITCH = 1 << 5
    TANK_HEATER_FEEDBACK = 1 << 8
    THERMOSTAT_C = 1 << 9
    THERMOSTAT_H = 1 << 10
    SOLAR_SIGNAL = 1 << 11
    SMART_GRID_SG = 1 << 12
    SMART_GRID_EVU = 1 << 13
