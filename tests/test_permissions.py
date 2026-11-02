"""Only user-level parameters may be writable.

The controller's type parameter table assigns every parameter a permission
level - user, commissioning, service or factory. This integration gives a
writable entity to user-level parameters only. These tests hold the code to
that rule, so it is proven rather than claimed.
"""

from __future__ import annotations

from typing import Any

from multibeton_modbus import MultibetonHeatPump

from .conftest import FakeUnit

#: Addresses the type parameter table ("Typenparameter R290") marks with the
#: permission level "Benutzer" (user). 35 rows; 6411 and 6416-6424 are not
#: among them.
USER_PARAMETER_ADDRESSES = frozenset(
    [*range(6400, 6411), *range(6412, 6416), *range(6425, 6445)]
)

#: The user commands of the register table's sheet "Benutzerbefehle
#: Lesen-Schreiben" this integration exposes: system, reset, defrost of
#: module 0#, zones, hot water, forced hot water, disinfection, vacation.
USER_COMMAND_ADDRESSES = frozenset(
    [64000, 64001, 64002, 64017, 64018, 64019, 64021, 64022, 64024, 64025]
)


def _writable_fields(device: MultibetonHeatPump) -> list[tuple[str, str, int]]:
    found: list[tuple[str, str, int]] = []
    for component in device.components:
        for name, resolved in component.resolved_fields.items():
            field: Any = resolved.field
            if getattr(field, "writable", False):
                found.append((type(component).__name__, name, resolved.address))
    return found


def test_user_parameter_table_has_35_entries() -> None:
    """The frozen copy matches the 35 user-level rows of the table."""
    assert len(USER_PARAMETER_ADDRESSES) == 35


def test_every_writable_field_is_user_level() -> None:
    """No commissioning, service or factory parameter can be written."""
    device = MultibetonHeatPump(FakeUnit(), module_count=8)
    allowed = USER_PARAMETER_ADDRESSES | USER_COMMAND_ADDRESSES
    offending = [
        (component, name, address)
        for component, name, address in _writable_fields(device)
        if address not in allowed
    ]
    assert not offending, offending


def test_initialisation_coils_are_not_modelled() -> None:
    """Coils 129-133 (factory reset and the like) never become a field."""
    device = MultibetonHeatPump(FakeUnit(), module_count=8)
    addresses = {
        resolved.address
        for component in device.components
        for resolved in component.resolved_fields.values()
        if resolved.space == "coil"
    }
    assert not addresses & set(range(129, 134))


def test_fixed_curve_source_is_read_only() -> None:
    """6416 sits in the user block but carries factory permission."""
    device = MultibetonHeatPump(FakeUnit())
    field: Any = device.user_parameters.resolved_fields["fixed_curve_source"].field
    assert not getattr(field, "writable", False)
