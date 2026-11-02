"""MULTIBETON-specific wrapper layer over ``modbus_connection.model`` fields.

The ``modbus_connection.model`` field factories (``gauge()``, ``integer()``,
``boolean()``, ``enum()``, ``flags()``, ...) build typed register descriptors
but carry no notion of a manufacturer's own documentation. This module wraps
the handful of factories the MULTIBETON register map actually needs, adding
two pieces of descriptive metadata on top of each field:

* ``maker_key`` - the manufacturer's original German register name (e.g.
  ``"Anlagenstatus"``), letting a caller trace a datapoint back to the
  source register table.
* ``description`` - the manufacturer's German description of the register,
  copied from the source documentation.

Metadata is attached as a :class:`MultibetonMetadata` instance on the
field's ``multibeton_metadata`` attribute, so any caller - including
downstream applications built on top of this library - can introspect a
field's original manufacturer name and description without needing the
raw source spreadsheets. This layer intentionally stays thin: no write
validation, no unit conversion and no unlock sequences are added on top of
what ``modbus_connection.model`` already provides.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, IntFlag
from typing import TYPE_CHECKING, Any

from modbus_connection.model import (
    Component,
)
from modbus_connection.model import (
    boolean as _modbus_boolean,
)
from modbus_connection.model import (
    discrete_input as _modbus_discrete_input,
)
from modbus_connection.model import (
    enum as _modbus_enum,
)
from modbus_connection.model import (
    flags as _modbus_flags,
)
from modbus_connection.model import (
    gauge as _modbus_gauge,
)
from modbus_connection.model import (
    integer as _modbus_integer,
)
from modbus_connection.model import (
    uint32 as _modbus_uint32,
)

if TYPE_CHECKING:
    from modbus_connection.model.fields import NumberField, WriteValidator

__all__ = [
    "MultibetonComponent",
    "MultibetonMetadata",
    "boolean",
    "discrete_input",
    "enum",
    "flags",
    "gauge",
    "integer",
    "uint32",
]


@dataclass(frozen=True)
class MultibetonMetadata:
    """Manufacturer-facing metadata attached to one MULTIBETON datapoint.

    Attributes:
        maker_key: The manufacturer's original German register name, as
            printed in the source Modbus address table.
        description: The manufacturer's German description of the register,
            or an empty string where the source table gives none.
        unit: The physical unit of the decoded value, or ``None`` for a
            unitless, enum, flag or boolean datapoint.

    """

    maker_key: str
    description: str = ""
    unit: str | None = None


def _attach(field: Any, metadata: MultibetonMetadata) -> Any:
    """Attach MULTIBETON metadata to a ``modbus_connection`` field in place."""
    field.multibeton_metadata = metadata
    return field


def gauge(
    address: int,
    scale: float,
    *,
    maker_key: str,
    description: str = "",
    unit: str | None = None,
    **kwargs: Any,
) -> NumberField[float]:
    """Create a scaled numeric register field with MULTIBETON metadata."""
    field = _modbus_gauge(address, scale, unit=unit, **kwargs)
    return _attach(field, MultibetonMetadata(maker_key, description, unit))


def integer(
    address: int,
    *,
    maker_key: str,
    description: str = "",
    unit: str | None = None,
    **kwargs: Any,
) -> NumberField[int]:
    """Create an integer register field with MULTIBETON metadata."""
    field = _modbus_integer(address, unit=unit, **kwargs)
    return _attach(field, MultibetonMetadata(maker_key, description, unit))


def uint32(
    address: int,
    *,
    maker_key: str,
    description: str = "",
    unit: str | None = None,
    **kwargs: Any,
) -> NumberField[int]:
    """Create an unsigned 32-bit register field (two words, big-endian).

    ``modbus_connection.model.fields.uint32`` already combines the high and
    low words documented for a MULTIBETON runtime counter into one value
    when passed the field's single (high-word) address; this wrapper only
    adds MULTIBETON metadata on top.
    """
    field = _modbus_uint32(address, unit=unit, **kwargs)
    return _attach(field, MultibetonMetadata(maker_key, description, unit))


def boolean(
    address: int,
    *,
    maker_key: str,
    description: str = "",
    writable: bool | WriteValidator = False,
    **kwargs: Any,
) -> NumberField[bool]:
    """Create a 0/1 holding-register boolean field with MULTIBETON metadata."""
    field = _modbus_boolean(address, writable=writable, **kwargs)
    return _attach(field, MultibetonMetadata(maker_key, description, None))


def discrete_input(
    address: int,
    *,
    maker_key: str,
    description: str = "",
    **kwargs: Any,
) -> Any:
    """Create a read-only discrete-input field (FC02) with metadata.

    The controller's relay outputs and digital inputs live in the discrete
    space, not in the register space the other fields use: what a relay is
    doing right now is one bit at its own address, independent of the word
    registers. A component may hold both; the backend reads each space with
    its own function code.
    """
    field = _modbus_discrete_input(address, **kwargs)
    return _attach(field, MultibetonMetadata(maker_key, description, None))


def enum[E: IntEnum](
    address: int,
    enum_type: type[E],
    *,
    maker_key: str,
    description: str = "",
    **kwargs: Any,
) -> NumberField[E]:
    """Create a register field mapped to an ``IntEnum``, with metadata."""
    field = _modbus_enum(address, enum_type, **kwargs)
    return _attach(field, MultibetonMetadata(maker_key, description, None))


def flags[F: IntFlag](
    address: int,
    flag_type: type[F],
    *,
    maker_key: str,
    description: str = "",
    **kwargs: Any,
) -> NumberField[F]:
    """Create a register field mapped to an ``IntFlag``, with metadata."""
    field = _modbus_flags(address, flag_type, **kwargs)
    return _attach(field, MultibetonMetadata(maker_key, description, None))


class MultibetonComponent(Component):
    """Base class for MULTIBETON subsystems.

    Adds no behavior over ``modbus_connection.model.Component`` beyond a
    convenience lookup for the :class:`MultibetonMetadata` attached to each
    declared field by this module's field factories.
    """

    def metadata_for(self, field: str) -> MultibetonMetadata | None:
        """Return MULTIBETON metadata for a declared field, or ``None``."""
        descriptor = type(self).declared_fields.get(field)
        if descriptor is None:
            return None
        return getattr(descriptor, "multibeton_metadata", None)

    def require_metadata_for(self, field: str) -> MultibetonMetadata:
        """Return MULTIBETON metadata for a declared field.

        Raises ``AttributeError`` for an unknown or untyped field.
        """
        metadata = self.metadata_for(field)
        if metadata is None:
            msg = f"unknown or untyped MULTIBETON field {field!r}"
            raise AttributeError(msg)
        return metadata
