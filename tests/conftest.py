"""Make the ``multibeton_modbus`` layer importable without Home Assistant.

The layer has no Home Assistant dependency, but it lives inside the
integration package, whose ``__init__`` imports Home Assistant. It is loaded
here as a top-level package of its own, so these tests need nothing but
``modbus-connection`` and run in seconds.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

PACKAGE_DIR = (
    Path(__file__).parent.parent
    / "custom_components"
    / "multibeton"
    / "multibeton_modbus"
)


def _load_package() -> None:
    spec = importlib.util.spec_from_file_location(
        "multibeton_modbus",
        PACKAGE_DIR / "__init__.py",
        submodule_search_locations=[str(PACKAGE_DIR)],
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["multibeton_modbus"] = module
    spec.loader.exec_module(module)


_load_package()


class FakeUnit:
    """A Modbus unit answering from a dict; unknown addresses read 0."""

    connected = True

    def __init__(self, registers: dict[int, int] | None = None) -> None:
        """Hold the register image."""
        self.registers = registers or {}

    async def read_input_registers(self, address: int, count: int) -> list[int]:
        """Return input registers from the image."""
        return [self.registers.get(a, 0) for a in range(address, address + count)]

    async def read_holding_registers(self, address: int, count: int) -> list[int]:
        """Return holding registers from the image."""
        return [self.registers.get(a, 0) for a in range(address, address + count)]

    async def read_coils(self, address: int, count: int) -> list[bool]:
        """Return no coil as set."""
        return [False] * count

    async def read_discrete_inputs(self, address: int, count: int) -> list[bool]:
        """Return no discrete input as set."""
        return [False] * count

    def __getattr__(self, name: str) -> Any:
        """Fail loudly on anything a read-only test should never call."""
        msg = f"FakeUnit does not support {name}"
        raise AttributeError(msg)


@pytest.fixture
def fake_unit() -> type[FakeUnit]:
    """Return the fake unit class."""
    return FakeUnit
