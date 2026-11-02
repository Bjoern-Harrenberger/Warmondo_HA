"""Overall system state, operating mode, and lifetime run/start counters.

Read from the input-register table (Modbus function code 0x04), source
sheet "Anlageninformationen" of the manufacturer's register documentation.
"""

from __future__ import annotations

from ..data_model import (
    MultibetonComponent,
    boolean,
    enum,
    flags,
    gauge,
    integer,
    uint32,
)
from ..enums import (
    ConfiguredMode,
    CurrentMode,
    OperatingState,
    OperationFlags,
    StatusFlags,
)
from .sensors import SENSOR_FAULT_CODES


class SystemStatus(MultibetonComponent):
    """Overall system state, operating mode, and lifetime run/start counters."""

    register_space = "input"

    status_flags = flags(
        768,
        StatusFlags,
        maker_key="Anlagenstatus",
        description=(
            "B0: Anlage im Standby | B1: Anlage startet | B2: Anlage in Betrieb | "
            "B3: Anlage fährt herunter | B4: Anlage im schweren Alarmzustand | "
            "B8: Anlage im Vorwärmbetrieb | B9: Anlage hat eine Störung | "
            "B10: Anlage im Frostschutz | B11: Anlage im Abtaubetrieb"
        ),
    )
    configured_mode = enum(
        770,
        ConfiguredMode,
        maker_key="Eingestellter Modus",
        description="1: Kühlbetrieb; 2: Heizbetrieb; 3: Automatikbetrieb",
    )
    current_mode = enum(
        771,
        CurrentMode,
        maker_key="Aktueller Betriebsmodus",
        description="0: keiner; 1: Kühlen; 2: Heizen; 3: reserviert; 4: Warmwasser",
    )
    power_control_target_temp = gauge(
        772,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Zieltemperatur Leistungsregelung",
        description="Einheit 0,1 °C",
    )
    power_control_actual_temp = gauge(
        773,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Regeltemperatur Leistungsregelung",
        description="Einheit 0,1 °C",
    )
    curve_ambient_temp = gauge(
        839,
        0.1,
        unit="°C",
        nan=SENSOR_FAULT_CODES,
        maker_key="Berechnete Umgebungstemperatur für die Kennlinie",
        description=(
            "Die Umgebungstemperatur, mit der die Regelung die Heiz-/Kühl"
            "kennlinie auswertet - geglättet, nicht der Rohwert von "
            "Sensors.ambient_temp. Zusammen mit der Kennlinien-Vorlauf"
            "temperatur (Register 1342/1344) beschreibt sie den aktuellen "
            "Arbeitspunkt der gewählten Kurve in Zahlen."
        ),
    )
    # -- the Smart-Grid pair, 823/824 --
    # The two SG-Ready terminals land in SystemIO.digital_inputs; these two
    # registers are what the controller makes of them. Observed 0/0 on a
    # plant with both terminals open. The value lists are not in the
    # register table, so both are kept as raw integers.
    smart_grid_status = integer(
        823,
        maker_key="Smart-Grid-Status",
        description="Werteliste nicht dokumentiert; 0 bei offenen Klemmen.",
    )
    smart_grid_command = integer(
        824,
        maker_key="Smart-Grid-Befehl",
        description="Werteliste nicht dokumentiert; 0 bei offenen Klemmen.",
    )
    mixing_valve_cycle_time_s = integer(
        829,
        unit="s",
        maker_key="Kumulierte Zykluszeit Mischventil",
        description="Einheit Sekunden",
    )

    # -- what the inverter pump may do, 811-814 --
    # Commissioning limits, not measurements: the window the controller
    # keeps its pump inside. Useful to judge whether a flow reading sits
    # at the top or the bottom of what the pump can deliver.
    pump_speed_max = integer(
        811,
        unit="rpm",
        maker_key="Maximaldrehzahl Inverter-Umwälzpumpe",
    )
    pump_speed_min = integer(
        812,
        unit="rpm",
        maker_key="Minimaldrehzahl Inverter-Umwälzpumpe",
    )
    pump_flow_max = integer(
        813,
        unit="l/h",
        maker_key="Maximaldurchfluss Inverter-Umwälzpumpe",
    )
    pump_flow_min = integer(
        814,
        unit="l/h",
        maker_key="Minimaldurchfluss Inverter-Umwälzpumpe",
    )
    module_count = integer(
        792,
        maker_key="Anzahl Module",
    )
    operating_state = enum(
        793,
        OperatingState,
        maker_key="Betriebszustand",
        description=(
            "0: Anlage im Standby; 1: Anlage startet; 2: Anlage in Betrieb; "
            "3: Anlage fährt herunter; 4: Anlage im schweren Alarmzustand"
        ),
    )
    floor_heating_present = boolean(
        866,
        maker_key="Flag Übergabesystem Fußbodenheizung",
        description=(
            "1, wenn das Übergabesystem in Zone A oder Zone B eine "
            "Fußbodenheizung ist, sonst 0"
        ),
    )
    # The counters 840-870 are listed once, without a module suffix. Whether
    # they sum up every module of a cascade or describe module 0# alone is
    # not documented and still has to be checked on a multi-module plant.
    defrost_count = uint32(
        840,
        maker_key="Anzahl Abtauvorgänge",
        description="High Word 840 / Low Word 841",
    )
    compressor_starts = uint32(
        842,
        maker_key="Anzahl Verdichterstarts",
        description="High Word 842 / Low Word 843",
    )
    heating_starts = uint32(
        844,
        maker_key="Anzahl Starts Heizbetrieb",
        description="High Word 844 / Low Word 845",
    )
    cooling_starts = uint32(
        846,
        maker_key="Anzahl Starts Kühlbetrieb",
        description="High Word 846 / Low Word 847",
    )
    dhw_starts = uint32(
        848,
        maker_key="Anzahl Starts Warmwasserbereitung",
        description="High Word 848 / Low Word 849",
    )
    compressor_runtime_continuous_min = uint32(
        850,
        unit="min",
        maker_key="Ununterbrochene Verdichterlaufzeit",
        description=(
            "High Word 850 / Low Word 851, Einheit Minuten. Zählt nur, "
            "solange der Verdichter läuft; steht er, bleibt der Wert auf "
            "der Dauer des letzten Laufs stehen. An der Anlage gemessen: "
            "bei stehenden Verdichtern blieb der Wert über fünf Minuten "
            "auf 38, während die Stillstandszeit weiterzählte. Ob die Zahl "
            "den laufenden oder den letzten Zeitraum meint, ergibt sich "
            "deshalb nur aus dem Verdichterzustand, nicht aus dem Register."
        ),
    )
    compressor_idle_continuous_min = uint32(
        852,
        unit="min",
        maker_key="Ununterbrochene Verdichterstillstandszeit",
        description=(
            "High Word 852 / Low Word 853, Einheit Minuten. Gegenstück zu "
            "compressor_runtime_continuous_min und mit derselben Einschränkung: "
            "zählt nur bei stehendem Verdichter, sonst hält es den letzten "
            "Stillstand fest. Beide Register sind daher praktisch immer "
            "ungleich null."
        ),
    )
    compressor_runtime_total_min = uint32(
        854,
        unit="min",
        maker_key="Kumulierte Verdichterlaufzeit",
        description="High Word 854 / Low Word 855, Einheit Minuten",
    )
    compressor_runtime_heating_min = uint32(
        856,
        unit="min",
        maker_key="Kumulierte Verdichterlaufzeit Heizbetrieb",
        description="High Word 856 / Low Word 857",
    )
    compressor_runtime_cooling_min = uint32(
        858,
        unit="min",
        maker_key="Kumulierte Verdichterlaufzeit Kühlbetrieb",
        description="High Word 858 / Low Word 859",
    )
    compressor_runtime_dhw_min = uint32(
        860,
        unit="min",
        maker_key="Kumulierte Verdichterlaufzeit Warmwasserbereitung",
        description="High Word 860 / Low Word 861",
    )
    aux_heater_runtime_min = uint32(
        862,
        unit="min",
        maker_key="Laufzeit Zusatzheizstab",
        description="High Word 862 / Low Word 863",
    )
    tank_heater_runtime_min = uint32(
        864,
        unit="min",
        maker_key="Laufzeit Speicher-Heizstab",
        description="High Word 864 / Low Word 865",
    )
    aux_heater_starts = uint32(
        867,
        maker_key="Anzahl Starts Zusatzheizstab",
        description="High Word 867 / Low Word 868",
    )
    tank_heater_starts = uint32(
        869,
        maker_key="Anzahl Starts Speicher-Heizstab",
        description="High Word 869 / Low Word 870",
    )
    operation_flags = flags(
        912,
        OperationFlags,
        maker_key="Betriebs-Flags 0",
        description=(
            "Was gerade laeuft, Bit fuer Bit: Zonen, Warmwasser, "
            "Desinfektion, Urlaubsmodus und die drei Zwangsbetriebe "
            "fuer Speicher-Heizstab, Zusatzheizstab und externe "
            "Waermequelle."
        ),
    )
    # Eight runtimes for at most eight modules: most likely one per module,
    # but neither that assignment nor the unit is documented. Exposed raw
    # until checked against the controller.
    compressor_runtime_1 = integer(
        1025,
        signed=False,
        maker_key="Verdichterlaufzeit 1",
        description=(
            "Vermutlich Laufzeit des Verdichters von Modul 0#; Einheit "
            "nicht dokumentiert."
        ),
    )
    compressor_runtime_2 = integer(
        1026,
        signed=False,
        maker_key="Verdichterlaufzeit 2",
        description=(
            "Vermutlich Laufzeit des Verdichters von Modul 1#; Einheit "
            "nicht dokumentiert."
        ),
    )
    compressor_runtime_3 = integer(
        1027,
        signed=False,
        maker_key="Verdichterlaufzeit 3",
        description=(
            "Vermutlich Laufzeit des Verdichters von Modul 2#; Einheit "
            "nicht dokumentiert."
        ),
    )
    compressor_runtime_4 = integer(
        1028,
        signed=False,
        maker_key="Verdichterlaufzeit 4",
        description=(
            "Vermutlich Laufzeit des Verdichters von Modul 3#; Einheit "
            "nicht dokumentiert."
        ),
    )
    compressor_runtime_5 = integer(
        1029,
        signed=False,
        maker_key="Verdichterlaufzeit 5",
        description=(
            "Vermutlich Laufzeit des Verdichters von Modul 4#; Einheit "
            "nicht dokumentiert."
        ),
    )
    compressor_runtime_6 = integer(
        1030,
        signed=False,
        maker_key="Verdichterlaufzeit 6",
        description=(
            "Vermutlich Laufzeit des Verdichters von Modul 5#; Einheit "
            "nicht dokumentiert."
        ),
    )
    compressor_runtime_7 = integer(
        1031,
        signed=False,
        maker_key="Verdichterlaufzeit 7",
        description=(
            "Vermutlich Laufzeit des Verdichters von Modul 6#; Einheit "
            "nicht dokumentiert."
        ),
    )
    compressor_runtime_8 = integer(
        1032,
        signed=False,
        maker_key="Verdichterlaufzeit 8",
        description=(
            "Vermutlich Laufzeit des Verdichters von Modul 7#; Einheit "
            "nicht dokumentiert."
        ),
    )
