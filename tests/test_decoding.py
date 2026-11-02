"""Decoding: sentinels, scaling, 32-bit counters and the per-module layout."""

from __future__ import annotations

import asyncio

import pytest
from multibeton_modbus import CompressorStatus, MultibetonHeatPump
from multibeton_modbus.device import clamp_module_count

from .conftest import FakeUnit

#: The four sensor sentinels as raw 16-bit words.
SENTINELS = [code & 0xFFFF for code in (-32700, -32701, -32702, -32703)]


def _read(registers: dict[int, int]) -> MultibetonHeatPump:
    async def run() -> MultibetonHeatPump:
        device = await MultibetonHeatPump.async_create(FakeUnit(registers))
        await device.async_update()
        return device

    return asyncio.run(run())


@pytest.mark.parametrize("sentinel", SENTINELS)
def test_sentinel_reads_as_none(sentinel: int) -> None:
    """A sensor problem is never passed on as a measurement."""
    device = _read({1311: sentinel, 3350: sentinel})
    assert device.modules[0].high_pressure is None
    assert device.sensors.ambient_temp is None


def test_scaling_and_sign() -> None:
    """0.1 bar and 0.1 degree steps, negative temperatures signed."""
    device = _read({1311: 152, 3350: (-53) & 0xFFFF})
    assert device.modules[0].high_pressure == pytest.approx(15.2)
    assert device.sensors.ambient_temp == pytest.approx(-5.3)


def test_32_bit_counter_combines_high_and_low_word() -> None:
    """840/841 is one counter, high word first."""
    device = _read({840: 1, 841: 2})
    assert device.system_status.defrost_count == 65538


def test_module_count_comes_from_the_controller() -> None:
    """Register 792 decides how many modules are read."""
    assert len(_read({792: 3}).modules) == 3


@pytest.mark.parametrize(
    ("raw", "expected"), [(None, 1), (0, 1), (1, 1), (8, 8), (9, 8)]
)
def test_module_count_is_clamped(raw: int | None, expected: int) -> None:
    """A missing or impossible count still yields a usable plant."""
    assert clamp_module_count(raw) == expected


def test_each_module_is_256_registers_further() -> None:
    """Module 1# reads the same values 256 addresses after module 0#."""
    device = _read({792: 2, 1311: 152, 1567: 140, 1289: 1 << 13})
    master, slave = device.modules
    assert master.high_pressure == pytest.approx(15.2)
    assert slave.high_pressure == pytest.approx(14.0)
    assert CompressorStatus.DEFROSTING in master.compressor_status
    assert CompressorStatus.DEFROSTING not in slave.compressor_status


def test_module_addresses() -> None:
    """The resolved addresses of module 1# are those of 0# plus 256."""
    device = MultibetonHeatPump(FakeUnit(), module_count=2)
    master, slave = device.modules
    for name, resolved in master.resolved_fields.items():
        assert slave.resolved_fields[name].address == resolved.address + 256
