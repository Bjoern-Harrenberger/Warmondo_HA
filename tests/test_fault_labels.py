"""Every modelled fault bit has the manufacturer's wording."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from multibeton_modbus.fault_labels import FAULT_LABELS, fault_label

if TYPE_CHECKING:
    from enum import IntFlag


@pytest.mark.parametrize("flag_type", list(FAULT_LABELS))
def test_every_named_bit_has_a_label(flag_type: type[IntFlag]) -> None:
    """A named bit without a label would show its code name to the owner."""
    for member in flag_type:
        if member.value:
            assert fault_label(member) != member.name, member


def test_labels_are_kept_apart_per_word() -> None:
    """Bit 0 of two different words must not share one label."""
    first_bits = {
        flag_type: labels.get(1)
        for flag_type, labels in FAULT_LABELS.items()
        if labels.get(1) is not None
    }
    assert len(set(first_bits.values())) == len(first_bits)
