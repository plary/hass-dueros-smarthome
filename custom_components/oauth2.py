"""OAuth2 provider for DuerOS Smart Home skill.

DuerOS uses OAuth2 Authorization Code flow:
1. User visits authorize URL → gets redirected to login page
2. After login, redirected back with authorization code
3. DuerOS exchanges code for access_token via token endpoint
"""

import hashlib
import logging
import secrets
import time
from typing import Any

from homeassistant.core import HomeAssistant

from .const import CONF_ACCESS_TOKEN, CONF_CLIENT_ID, CONF_CLIENT_SECRET, DOMAIN

_LOGGER = logging.getLogger(__name__)

# In-memory store for auth codes and tokens
# In production, consider persisting these
_auth_codes: dict[str, dict[str, Any]] = {}
_tokens: dict[str, dict[str, Any]] = {}


def generate_auth_code(client_id: str, hass_user_id: str) -> str:
    """Generate an authorization code."""
    code = secrets.token_urlsafe(32)
    _auth_codes[code] = {
        "client_id": client_id,
        "user_id": hass_user_id,
        "created_at": time.time(),
        "expires_at": time.time() + 600,  # 10 min to exchange
    }
    return code


def exchange_code_for_token(
    code: str, client_id: str, client_secret: str
) -> dict[str, Any] | None:
    """Exchange authorization code for access token."""
    code_data = _auth_codes.get(code)
    if not code_data:
        _LOGGER.warning("Auth code not found: %s", code[:8])
        return None
    if code_data["expires_at"] < time.time():
        _auth_codes.pop(code, None)
        _LOGGER.warning("Auth code expired")
        return None
    if code_data["client_id"] != client_id:
        _LOGGER.warning("Client ID mismatch for auth code")
        return None

    # Remove used code
    _auth_codes.pop(code)

    # Generate tokens
    access_token = secrets.token_urlsafe(48)
    refresh_token = secrets.token_urlsafe(48)
    expires_in = 86400 * 30  # 30 days

    token_data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "expires_at": time.time() + expires_in,
        "user_id": code_data["user_id"],
        "client_id": client_id,
    }
    _tokens[access_token] = token_data

    return token_data


def refresh_access_token(
    refresh_token: str, client_id: str, client_secret: str
) -> dict[str, Any] | None:
    """Refresh an access token."""
    for token_data in list(_tokens.values()):
        if (
            token_data.get("refresh_token") == refresh_token
            and token_data["client_id"] == client_id
        ):
            # Remove old token
            old_access = token_data["access_token"]
            _tokens.pop(old_access, None)

            # Generate new tokens
            new_access = secrets.token_urlsafe(48)
            new_refresh = secrets.token_urlsafe(48)
            expires_in = 86400 * 30

            new_data = {
                "access_token": new_access,
                "refresh_token": new_refresh,
                "token_type": "Bearer",
                "expires_in": expires_in,
                "expires_at": time.time() + expires_in,
                "user_id": token_data["user_id"],
                "client_id": client_id,
            }
            _tokens[new_access] = new_data
            return new_data

    _LOGGER.warning("Refresh token not found")
    return None


def validate_token(access_token: str) -> dict[str, Any] | None:
    """Validate an access token and return token data."""
    token_data = _tokens.get(access_token)
    if not token_data:
        return None
    if token_data["expires_at"] < time.time():
        _tokens.pop(access_token, None)
        return None
    return token_data


def revoke_token(access_token: str) -> bool:
    """Revoke an access token."""
    return _tokens.pop(access_token, None) is not None


def get_client_credentials(hass: HomeAssistant) -> tuple[str, str]:
    """Get configured client_id and client_secret."""
    entry_data = _get_config_data(hass)
    return entry_data.get(CONF_CLIENT_ID, ""), entry_data.get(CONF_CLIENT_SECRET, "")


def _get_config_data(hass: HomeAssistant) -> dict[str, Any]:
    """Get the first config entry data."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if entries:
        return entries[0].data
    return {}
