"""Config flow for the Warmondo heat-pump integration.

Two entry points share one form and one validation routine: the initial
setup, and the reconfigure flow reached from the entry's menu. The latter
exists because two of these values change over a heat pump's life without
anything being wrong - the model is picked by hand (the controller cannot
report it) and a gateway can move to a different address. Without it, the
only way to correct either would be to delete the entry and add it again,
which hands out new entity IDs and breaks every automation and dashboard
built on the old ones.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.data_entry_flow import section
from homeassistant.helpers import selector

from .api import MultibetonApiClient, MultibetonApiClientCommunicationError
from .const import (
    CONF_FRAMER,
    CONF_MODEL,
    CONF_READ_ONLY,
    CONF_UNIT_ID,
    DEFAULT_FRAMER,
    DEFAULT_PORT,
    DEFAULT_READ_ONLY,
    DEFAULT_TITLE,
    DEFAULT_UNIT_ID,
    DOCUMENTATION_URL,
    DOMAIN,
    LOGGER,
    MODEL_TYPES,
    MODELS,
    PRODUCT_LINE,
    SUPPORT_EMAIL,
    SUPPORT_PHONE,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

#: Name of the collapsed form section holding the connection details most
#: installations never need to touch.
SECTION_ADVANCED = "advanced"

#: Settings kept in the collapsed section. Stored flat in the entry, like
#: everything else, so the section is a matter of presentation only.
ADVANCED_KEYS = (CONF_PORT, CONF_UNIT_ID, CONF_FRAMER, CONF_READ_ONLY)

#: Shown in the dialog's text, so help is one click away while setting up.
DESCRIPTION_PLACEHOLDERS = {
    "docs_url": DOCUMENTATION_URL,
    "support_phone": SUPPORT_PHONE,
    "support_email": SUPPORT_EMAIL,
}

ADVANCED_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
            selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=65535,
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
            vol.Coerce(int),
        ),
        vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): vol.All(
            selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=247,
                    mode=selector.NumberSelectorMode.BOX,
                ),
            ),
            vol.Coerce(int),
        ),
        vol.Required(CONF_FRAMER, default=DEFAULT_FRAMER): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=["rtu", "socket"],
                mode=selector.SelectSelectorMode.DROPDOWN,
            ),
        ),
        vol.Required(
            CONF_READ_ONLY, default=DEFAULT_READ_ONLY
        ): selector.BooleanSelector(),
    },
)

STEP_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT),
        ),
        vol.Optional(CONF_MODEL): selector.SelectSelector(
            selector.SelectSelectorConfig(
                # Both names in the list: the Warmondo model is what the
                # dashboard shows, the type designation is what is printed
                # on the plant.
                options=[
                    selector.SelectOptionDict(
                        value=model, label=f"{model} — {MODEL_TYPES[model]}"
                    )
                    for model in MODELS
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            ),
        ),
        vol.Required(CONF_HOST): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT),
        ),
        vol.Required(SECTION_ADVANCED): section(ADVANCED_SCHEMA, {"collapsed": True}),
    },
)


def _flatten(user_input: Mapping[str, Any]) -> dict[str, Any]:
    """Lift the collapsed section's fields to the top level for storage."""
    data = {k: v for k, v in user_input.items() if k != SECTION_ADVANCED}
    data.update(user_input.get(SECTION_ADVANCED, {}))
    return data


def _nest(data: Mapping[str, Any]) -> dict[str, Any]:
    """Arrange stored settings the way the form expects them."""
    nested = {k: v for k, v in data.items() if k not in ADVANCED_KEYS}
    nested[SECTION_ADVANCED] = {k: data[k] for k in ADVANCED_KEYS if k in data}
    return nested


def _unique_id(data: Mapping[str, Any]) -> str:
    """Identify one controller behind one gateway."""
    return f"{data[CONF_HOST]}:{data[CONF_PORT]}:{data[CONF_UNIT_ID]}"


def _default_title(data: Mapping[str, Any]) -> str:
    """Title for an entry whose Name field was left empty.

    Host-free on purpose: the title becomes the device name and seeds every
    entity ID, so anything host-derived would write the gateway's address
    across the installation.
    """
    model = data.get(CONF_MODEL)
    return f"{PRODUCT_LINE} {model}" if model else DEFAULT_TITLE


class MultibetonFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Warmondo."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data = _flatten(user_input)
            errors = await self._async_validate(data)
            if not errors:
                await self.async_set_unique_id(_unique_id(data))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=data.get(CONF_NAME) or _default_title(data),
                    data=data,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_SCHEMA, user_input or {}
            ),
            errors=errors,
            description_placeholders=DESCRIPTION_PLACEHOLDERS,
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Change the settings of an existing entry, keeping its entity IDs."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input = _flatten(user_input)
            errors = await self._async_validate(user_input)
            if not errors:
                unique_id = _unique_id(user_input)
                # The unique ID is derived from the connection, and changing
                # the connection is a large part of why this step exists - so
                # it is rewritten rather than asserted. Guard only against
                # pointing this entry at a controller another entry already
                # owns; matching the entry's own previous ID is the normal
                # case and must not abort.
                if any(
                    other.unique_id == unique_id and other.entry_id != entry.entry_id
                    for other in self._async_current_entries()
                ):
                    return self.async_abort(reason="already_configured")

                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=user_input,
                    title=self._title_for_reconfigure(entry, user_input),
                    unique_id=unique_id,
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_SCHEMA, _nest({**entry.data, **(user_input or {})})
            ),
            errors=errors,
            description_placeholders=DESCRIPTION_PLACEHOLDERS,
        )

    @staticmethod
    def _title_for_reconfigure(
        entry: config_entries.ConfigEntry,
        user_input: Mapping[str, Any],
    ) -> str:
        """Decide the entry title without overwriting a name the user chose.

        A name typed into the form always wins. Otherwise the title is only
        recomputed when it still matches what this integration generated from
        the previous settings - a title the user set themselves, whether
        through the Name field or by renaming the entry in the UI, is left
        alone even when the model changes.
        """
        if name := user_input.get(CONF_NAME):
            return str(name)
        if entry.title == _default_title(entry.data):
            return _default_title(user_input)
        return entry.title

    async def _async_validate(self, user_input: Mapping[str, Any]) -> dict[str, str]:
        """Return form errors for these settings, empty if they work."""
        try:
            await self._test_connection(
                host=user_input[CONF_HOST],
                port=user_input[CONF_PORT],
                unit_id=user_input[CONF_UNIT_ID],
                framer=user_input[CONF_FRAMER],
            )
        except MultibetonApiClientCommunicationError as exception:
            LOGGER.warning(exception)
            return {"base": "cannot_connect"}
        except Exception:  # noqa: BLE001 - surface anything unexpected as "unknown"
            LOGGER.exception("Unexpected error validating Warmondo connection")
            return {"base": "unknown"}
        return {}

    async def _test_connection(
        self,
        host: str,
        port: int,
        unit_id: int,
        framer: str,
    ) -> None:
        """Validate the connection by connecting and reading the device once."""
        client = MultibetonApiClient(
            host=host,
            port=port,
            unit_id=unit_id,
            framer=framer,
        )
        try:
            await client.async_connect()
            await client.async_get_data()
        finally:
            await client.async_close()
