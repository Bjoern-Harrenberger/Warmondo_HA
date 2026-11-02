"""Per-module refrigerant-circuit, inverter and fault data of a cascade.

A Warmondo installation is a cascade of one to eight heat-pump modules
(0# to 7#). The controller lays every module's datapoints out identically,
each module ``MODULE_STRIDE`` addresses after the previous one: the
compressor status word of module 0# sits on 1289, that of module 1# on 1545.
The fields below are therefore declared at module 0#'s addresses, and one
:class:`Module` instance per module is built with
``base_offset=MODULE_STRIDE * module``.

Read from the input-register table (Modbus function code 0x04), source
sheets "Analogwerte", "IO Wort (FC04)" and "Stoerungen Wort (FC04)" of the
manufacturer's register documentation, where each of these rows is listed
once per module.
"""

from __future__ import annotations

from ..data_model import MultibetonComponent, flags, gauge, integer
from ..enums import CompressorFaults1, CompressorStatus, UnitFaults1, UnitFaults2
from .sensors import SENSOR_FAULT_CODES

# Address distance between two consecutive modules' datapoints.
MODULE_STRIDE = 256

# A cascade has at most eight modules, 0# to 7#.
MAX_MODULES = 8


class Module(MultibetonComponent):
    """One module of the cascade, addressed through its ``base_offset``."""

    register_space = "input"

    compressor_status = flags(
        1289,
        CompressorStatus,
        maker_key="Verdichterstatus",
        description="B13: Abtaubetrieb läuft",
    )
    compressor_faults_1 = flags(
        1294,
        CompressorFaults1,
        maker_key="Verdichterstörungen 1",
    )
    unit_faults_1 = flags(
        1298,
        UnitFaults1,
        maker_key="Einheitenstörungen 1",
    )
    unit_faults_2 = flags(
        1299,
        UnitFaults2,
        maker_key="Einheitenstörungen 2",
    )
    main_expansion_valve_opening = integer(
        1301,
        unit="steps",
        nan=SENSOR_FAULT_CODES,
        maker_key="Öffnung Haupt-Expansionsventil",
    )
    aux_expansion_valve_opening = integer(
        1302,
        unit="steps",
        nan=SENSOR_FAULT_CODES,
        maker_key="Öffnung Zusatz-Expansionsventil",
    )
    fin_temp = gauge(
        1303,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Lamellentemperatur",
    )
    discharge_gas_temp = gauge(
        1304,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Heißgastemperatur",
    )
    suction_gas_temp = gauge(
        1305,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Sauggastemperatur",
    )
    after_valve_temp = gauge(
        1306,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Temperatur nach Ventil",
    )
    evaporation_saturation_temp = gauge(
        1308,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Verdampfungssättigungstemperatur",
    )
    condensation_saturation_temp = gauge(
        1309,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Kondensationssättigungstemperatur",
    )
    low_pressure = gauge(
        1310,
        0.1,
        unit="bar",
        nan=SENSOR_FAULT_CODES,
        maker_key="Niederdruck",
    )
    high_pressure = gauge(
        1311,
        0.1,
        unit="bar",
        nan=SENSOR_FAULT_CODES,
        maker_key="Hochdruck",
    )
    target_superheat = gauge(
        1312,
        0.1,
        unit="K",
        nan=SENSOR_FAULT_CODES,
        maker_key="Sollüberhitzung Hauptventil",
        description="Einheit laut Tabelle 0,1 °C; als Differenz in Kelvin geführt.",
    )
    actual_superheat = gauge(
        1313,
        0.1,
        unit="K",
        nan=SENSOR_FAULT_CODES,
        maker_key="Aktuelle Überhitzung Hauptventil",
        description="Einheit laut Tabelle 0,1 °C; als Differenz in Kelvin geführt.",
    )
    inverter_target_speed = gauge(
        1319,
        0.1,
        unit="rps",
        nan=SENSOR_FAULT_CODES,
        maker_key="Solldrehzahl Inverter",
    )
    inverter_actual_speed = gauge(
        1320,
        0.1,
        unit="rps",
        nan=SENSOR_FAULT_CODES,
        maker_key="Aktuelle Drehzahl Inverter",
    )
    inverter_output_voltage = gauge(
        1321,
        0.1,
        unit="V",
        nan=SENSOR_FAULT_CODES,
        maker_key="Ausgangsspannung Inverter",
    )
    inverter_output_current = gauge(
        1322,
        0.1,
        unit="A",
        nan=SENSOR_FAULT_CODES,
        maker_key="Ausgangsstrom Inverter",
    )
    inverter_module_temp = gauge(
        1323,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Modultemperatur Inverter",
    )
    inverter_input_current = gauge(
        1325,
        0.1,
        unit="A",
        nan=SENSOR_FAULT_CODES,
        maker_key="Eingangsstrom Frequenzumrichter",
    )
    inverter_output_power = gauge(
        1326,
        0.01,
        unit="kW",
        nan=SENSOR_FAULT_CODES,
        maker_key="Ausgangsleistung Inverter",
        description=(
            "Die Tabelle nennt hier nur den Faktor 0,01 ohne Einheit; kW "
            "entspricht der gleichnamigen Ausgangsleistung auf Register 1036 "
            "(Einheit 0,01 kW)."
        ),
    )
    fan_1_speed = integer(
        1328,
        unit="rpm",
        nan=SENSOR_FAULT_CODES,
        maker_key="Aktuelle Drehzahl Ventilator 1",
    )
    water_pressure = gauge(
        1341,
        0.1,
        unit="bar",
        nan=SENSOR_FAULT_CODES,
        maker_key="Wasserdruck der Anlage",
    )
    phe_return_temp = gauge(
        1348,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Rücklauftemperatur Plattenwärmetauscher",
    )
    phe_flow_temp = gauge(
        1349,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Vorlauftemperatur Plattenwärmetauscher",
    )
    total_flow_temp = gauge(
        1350,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Gesamt-Vorlauftemperatur",
        description=(
            "Vorlauftemperatur hinter diesem Modul, nach der Zusammenführung "
            "- phe_flow_temp misst davor, am Plattenwärmetauscher."
        ),
    )
    ambient_temp = gauge(
        1351,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Umgebungstemperatur",
        description="Außenfühler dieses Moduls, nicht der Systemwert auf 3350.",
    )
    pump_flow = integer(
        1353,
        unit="L/h",
        nan=SENSOR_FAULT_CODES,
        maker_key="Aktueller Durchfluss Inverter-Umwälzpumpe",
    )
    current_power = gauge(
        1358,
        0.01,
        unit="kW",
        nan=SENSOR_FAULT_CODES,
        maker_key="Aktuelle Leistung der Anlage",
        description=(
            "Thermische Leistung dieses Moduls, nicht die elektrische "
            "Aufnahme - der Herstellername 'Aktuelle Leistung der Anlage' "
            "legt beides nahe. Auf einer Kaskade mit zwei Modulen summierten "
            "sich 10,83 kW und 9,38 kW exakt auf die 20,21 kW der "
            "Anlagen-Heizleistung (Register 3371)."
        ),
    )
    inverter_fault_code = integer(
        1369,
        nan=SENSOR_FAULT_CODES,
        maker_key="Inverter-Verdichter: Störungscode",
        description="0 = keine Störung, sonst aktueller Störungscode",
    )
