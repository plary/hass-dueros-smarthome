"""DuerOS Smart Home integration for Home Assistant.

Exposes Home Assistant devices to Baidu DuerOS (小度) for voice control.
Implements the DuerOS ConnectedHome protocol over HTTPS.

Setup:
1. Install this component to custom_components/dueros_smarthome/
2. Add integration via HA UI (config_flow)
3. Configure OAuth client_id and client_secret
4. Create DuerOS smart home skill on DuerOS open platform
5. Point skill endpoint to your HA instance
"""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.components.http import HomeAssistantHTTP

from .const import CONF_CLIENT_ID, CONF_CLIENT_SECRET, DOMAIN
from .http_api import (
    DuerOSConnectedHomeView,
    DuerOSOAuthAuthorizeView,
    DuerOSOAuthTokenView,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = []


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up DuerOS Smart Home from configuration.yaml (legacy)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up DuerOS Smart Home from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Register HTTP views
    hass.http.register_view(DuerOSOAuthAuthorizeView)
    hass.http.register_view(DuerOSOAuthTokenView)
    hass.http.register_view(DuerOSConnectedHomeView)

    _LOGGER.info(
        "DuerOS Smart Home integration loaded. "
        "API endpoint: https://YOUR_DOMAIN%s",
        "/api/dueros/smarthome",
    )
    _LOGGER.info(
        "OAuth authorize: https://YOUR_DOMAIN%s",
        "/auth/dueros/authorize",
    )
    _LOGGER.info(
        "OAuth token: https://YOUR_DOMAIN%s",
        "/auth/dueros/token",
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
