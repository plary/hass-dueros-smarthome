"""HTTP API endpoints for DuerOS Smart Home integration.

Provides:
- OAuth2 authorization endpoint
- OAuth2 token endpoint
- ConnectedHome API endpoint (discovery, control, query)
"""

import json
import logging
from typing import Any

from aiohttp import web
from aiohttp.web import Request, Response

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import (
    API_BASE_PATH,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    OAUTH_AUTHORIZE_PATH,
    OAUTH_TOKEN_PATH,
)
from .oauth2 import (
    exchange_code_for_token,
    generate_auth_code,
    get_client_credentials,
    refresh_access_token,
    validate_token,
)

_LOGGER = logging.getLogger(__name__)


class DuerOSOAuthAuthorizeView(HomeAssistantView):
    """OAuth2 Authorization endpoint.

    DuerOS redirects user here to get authorization code.
    After login, user is redirected back with ?code=xxx
    """

    url = OAUTH_AUTHORIZE_PATH
    name = "api:dueros:oauth:authorize"
    requires_auth = False

    async def get(self, request: Request) -> Response:
        """Handle authorization request."""
        hass = request.app["hass"]
        params = request.query

        client_id = params.get("client_id", "")
        redirect_uri = params.get("redirect_uri", "")
        state = params.get("state", "")

        # Validate client_id
        configured_id, _ = get_client_credentials(hass)
        if client_id != configured_id:
            return web.Response(
                text="Invalid client_id",
                status=400,
            )

        # Check if user is already authenticated via HA session
        # If not, redirect to HA login page
        # For simplicity, we use HA's auth middleware
        # The user needs to be logged into HA already

        # Generate auth code
        # We use a simple approach: if the user is authenticated in HA,
        # generate the code directly
        try:
            # Try to get the HA user from the request
            # HomeAssistantView provides this via request
            user = request.get("hass_user")
            if user:
                code = generate_auth_code(client_id, user.id)
            else:
                # Fallback: generate with a placeholder user ID
                code = generate_auth_code(client_id, "default")

            # Build redirect URL
            separator = "&" if "?" in redirect_uri else "?"
            redirect_url = f"{redirect_uri}{separator}code={code}"
            if state:
                redirect_url += f"&state={state}"

            return web.Response(
                status=302,
                headers={"Location": redirect_url},
            )
        except Exception as exc:
            _LOGGER.error("OAuth authorize error: %s", exc)
            return web.Response(text="Authorization failed", status=500)


class DuerOSOAuthTokenView(HomeAssistantView):
    """OAuth2 Token endpoint.

    DuerOS exchanges authorization code for access token.
    Also supports refresh_token grant.
    """

    url = OAUTH_TOKEN_PATH
    name = "api:dueros:oauth:token"
    requires_auth = False

    async def post(self, request: Request) -> Response:
        """Handle token exchange."""
        hass = request.app["hass"]
        try:
            body = await request.post()
        except Exception:
            body = {}

        grant_type = body.get("grant_type", "")
        client_id = body.get("client_id", "")
        client_secret = body.get("client_secret", "")

        # Validate client credentials
        configured_id, configured_secret = get_client_credentials(hass)
        if client_id != configured_id or client_secret != configured_secret:
            return web.json_response(
                {"error": "invalid_client"},
                status=401,
            )

        if grant_type == "authorization_code":
            code = body.get("code", "")
            token_data = exchange_code_for_token(code, client_id, client_secret)
            if not token_data:
                return web.json_response(
                    {"error": "invalid_grant"},
                    status=400,
                )
            return web.json_response({
                "access_token": token_data["access_token"],
                "token_type": "Bearer",
                "expires_in": token_data["expires_in"],
                "refresh_token": token_data.get("refresh_token", ""),
            })

        elif grant_type == "refresh_token":
            refresh = body.get("refresh_token", "")
            token_data = refresh_access_token(refresh, client_id, client_secret)
            if not token_data:
                return web.json_response(
                    {"error": "invalid_grant"},
                    status=400,
                )
            return web.json_response({
                "access_token": token_data["access_token"],
                "token_type": "Bearer",
                "expires_in": token_data["expires_in"],
                "refresh_token": token_data.get("refresh_token", ""),
            })

        else:
            return web.json_response(
                {"error": "unsupported_grant_type"},
                status=400,
            )


class DuerOSConnectedHomeView(HomeAssistantView):
    """DuerOS ConnectedHome API endpoint.

    Receives all DuerOS smart home directives:
    - Discovery
    - Control
    - Query
    """

    url = API_BASE_PATH
    name = "api:dueros:smarthome"
    requires_auth = False

    async def post(self, request: Request) -> Response:
        """Handle DuerOS ConnectedHome directive."""
        hass = request.app["hass"]

        # Extract access token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            _LOGGER.warning("Missing or invalid Authorization header")
            return web.json_response(
                {"error": "unauthorized"},
                status=401,
            )

        access_token = auth_header[7:]
        token_data = validate_token(access_token)
        if not token_data:
            _LOGGER.warning("Invalid or expired access token")
            return web.json_response(
                {"error": "invalid_token"},
                status=401,
            )

        # Parse request body
        try:
            body = await request.json()
        except Exception as exc:
            _LOGGER.warning("Invalid JSON body: %s", exc)
            return web.json_response(
                {"error": "invalid_request"},
                status=400,
            )

        _LOGGER.debug("DuerOS directive: %s", json.dumps(body, ensure_ascii=False)[:500])

        # Delegate to protocol handler
        from .api import handle_request

        response = handle_request(hass, body)

        _LOGGER.debug("DuerOS response: %s", json.dumps(response, ensure_ascii=False)[:500])

        return web.json_response(response)
