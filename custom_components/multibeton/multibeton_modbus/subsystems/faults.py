"""System-wide fault/alarm bitfields.

Read from the input-register table (Modbus function code 0x04), source
sheet "04-Stoerungen". The compressor and unit fault words exist once per
module and live on :class:`~multibeton_modbus.subsystems.module.Module`.
Only the fully-documented words are modeled here; sparsely-documented words
(most of ``system_faults_2`` through ``system_faults_5``) are deliberately
left out for a future extension - see the project README.
"""

from __future__ import annotations

from ..data_model import MultibetonComponent, flags
from ..enums import SystemFaults1, SystemFaults6


class Faults(MultibetonComponent):
    """System-wide fault/alarm bitfields."""

    register_space = "input"

    system_faults_1 = flags(
        3342,
        SystemFaults1,
        maker_key="Systemstörungen 1",
    )
    system_faults_6 = flags(
        3347,
        SystemFaults6,
        maker_key="Systemstörungen 6",
    )
