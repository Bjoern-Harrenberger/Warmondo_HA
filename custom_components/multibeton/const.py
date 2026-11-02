"""Constants for the Warmondo heat-pump integration."""

from __future__ import annotations

from logging import Logger, getLogger
from typing import Final

LOGGER: Logger = getLogger(__package__)

DOMAIN = "multibeton"

# Product and manufacturer are two different things and are kept apart
# deliberately: MULTIBETON GmbH builds the heat pumps, "Warmondo" is the
# product line they are sold as. The company name is written in capitals,
# always - that is how MULTIBETON writes it.
MANUFACTURER: Final = "MULTIBETON"
PRODUCT_LINE: Final = "Warmondo"

# Where an owner gets help with the heat pump and with this integration.
# Shown in the setup dialog, in fault notifications and in the README.
SUPPORT_ADDRESS: Final = "MULTIBETON GmbH, Heuserweg 23, 53842 Troisdorf"
SUPPORT_PHONE: Final = "+49 2241 252000"
SUPPORT_EMAIL: Final = "waermepumpe@multibeton.de"
DOCUMENTATION_URL: Final = "https://github.com/Bjoern-Harrenberger/Warmondo_HA"

ATTRIBUTION = f"Data provided by the {PRODUCT_LINE} heat pump via Modbus"

# The unit's own model designation, as printed on its type plate. The
# controller does NOT report it: the model is set with DIP switches on the
# main board (SW1/SW4/SW5) and no Modbus register reads it back, so it can
# only come from the person setting the integration up.
# The type designation from the nameplate per Warmondo model. Nobody
# commissioning a plant carries "WM-M" in their head - they have a
# delivery note and a nameplate, and those say F90HCR5INVMV2. The setup
# form therefore offers both, and the designation is kept on the device
# so a service case can read it without opening the cabinet.
#
# The trailing T on the two large ones means three-phase: the parameter
# table lists F130 twice, as F130R5V24 at 230 V and F130R5TV24 at 400 V,
# and the designations here carry the T. The 230 V F130 has no Warmondo
# model name, so it is not offered.
MODEL_TYPES: Final[dict[str, str]] = {
    "WM-S": "F60HCR5INVMV2",
    "WM-M": "F90HCR5INVMV2",
    "WM-L": "F130HCR5TINVMV2",
    "WM-XL": "F160HCR5TINVMV2",
}

MODELS: Final[tuple[str, ...]] = tuple(MODEL_TYPES)

# Supply voltage per model. The only machine datum that differs between
# the models and can be read back from the plant (register 7269), which
# makes it the one check on a model nobody can read over Modbus.
MODEL_VOLTAGES: Final[dict[str, int]] = {
    "WM-S": 230,
    "WM-M": 230,
    "WM-L": 400,
    "WM-XL": 400,
}

# The regulation this integration speaks to, which is a component of the
# heat pump and not the heat pump itself. It is reported as the device's
# model_id so the information stays available for service purposes without
# masquerading as the product name.
CONTROLLER_MODEL_ID: Final = "X1.HL087A.K05.5032"

CONF_UNIT_ID = "unit_id"
CONF_FRAMER = "framer"
CONF_MODEL = "model"
CONF_READ_ONLY = "read_only"

DEFAULT_PORT = 502
DEFAULT_UNIT_ID = 1
# The controller speaks Modbus RTU, but the gateway MULTIBETON installs in
# front of it terminates Modbus TCP itself, so native TCP framing ("socket")
# is what works. "rtu" stays selectable for gateways that pass the RTU
# frames through unchanged.
DEFAULT_FRAMER = "socket"

# A plant everyone may look at and nobody may change: a training rig, a
# demonstration unit, or an installation that is only monitored. With this
# set, the switch, number, select and button platforms are not set up at
# all, so there is nothing to operate - not from a dashboard, not from the
# developer tools, not from an automation or a voice assistant. Off by
# default, because a heat pump a customer owns is theirs to adjust.
DEFAULT_READ_ONLY = False

# Fallback title for a config entry when the user leaves the Name field
# empty. Kept free of the host/IP on purpose - the title becomes the device
# name and seeds every entity ID, so a gateway address here would end up in
# entity IDs across the installation.
DEFAULT_TITLE = PRODUCT_LINE
