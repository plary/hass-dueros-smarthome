"""Config flow for DuerOS Smart Home integration."""

import logging
import secrets
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_CLIENT_ID, CONF_CLIENT_SECRET, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CLIENT_ID): str,
        vol.Required(CONF_CLIENT_SECRET): str,
    }
)


class DuerOSFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DuerOS Smart Home."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            client_id = user_input.get(CONF_CLIENT_ID, "").strip()
            client_secret = user_input.get(CONF_CLIENT_SECRET, "").strip()

            if not client_id or not client_secret:
                errors["base"] = "invalid_auth"
            else:
                # Check if already configured
                await self.async_set_unique_id(client_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title="DuerOS Smart Home (小度智能家居)",
                    data={
                        CONF_CLIENT_ID: client_id,
                        CONF_CLIENT_SECRET: client_secret,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
