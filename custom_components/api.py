"""DuerOS ConnectedHome protocol handler.

Implements the DuerOS Smart Home skill protocol:
- Discovery: List available devices
- Control: Send commands to devices
- Query: Get device state
"""

import logging
from typing import Any

from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.core import HomeAssistant, ServiceCall, State
from homeassistant.helpers import entity_registry as er
import homeassistant.helpers.config_validation as cv

from .const import (
    ACTION_TURN_OFF,
    ACTION_TURN_ON,
    APPLIANCE_AC,
    APPLIANCE_CURTAIN,
    APPLIANCE_FAN,
    APPLIANCE_HUMIDIFIER,
    APPLIANCE_LIGHT,
    APPLIANCE_SCENE,
    APPLIANCE_SENSOR,
    APPLIANCE_SWITCH,
    ERROR_INVALID_ACCESS_TOKEN,
    ERROR_NO_SUCH_TARGET,
    ERROR_UNSUPPORTED_OPERATION,
    NS_CONTROL,
    NS_DISCOVERY,
    NS_QUERY,
)
from .mapping import (
    DUREOS_MODE_REVERSE,
    _make_appliance_id,
    discover_appliances,
    query_state,
)

_LOGGER = logging.getLogger(__name__)

# Reverse lookup: appliance_id → entity_id
_appliance_to_entity: dict[str, str] = {}


def _refresh_appliance_map(hass: HomeAssistant) -> None:
    """Rebuild appliance_id → entity_id mapping."""
    global _appliance_to_entity
    _appliance_to_entity = {}
    for state in hass.states.async_all():
        _appliance_to_entity[_make_appliance_id(state.entity_id)] = state.entity_id


def _entity_id_from_appliance(appliance_id: str) -> str | None:
    """Look up entity_id from DuerOS appliance ID."""
    return _appliance_to_entity.get(appliance_id)


def _error_response(namespace: str, name: str, error_type: str) -> dict[str, Any]:
    """Build a DuerOS error response."""
    return {
        "header": {
            "namespace": namespace,
            "name": f"{name}Response",
            "messageId": "",
            "payloadVersion": "1",
        },
        "payload": {"type": error_type},
    }


def handle_request(hass: HomeAssistant, request_data: dict[str, Any]) -> dict[str, Any]:
    """Route DuerOS ConnectedHome request to appropriate handler."""
    header = request_data.get("header", {})
    namespace = header.get("namespace", "")
    name = header.get("name", "")
    payload = request_data.get("payload", {})

    _LOGGER.debug("DuerOS request: namespace=%s, name=%s", namespace, name)

    if namespace == NS_DISCOVERY:
        return _handle_discovery(hass, name, payload)
    elif namespace == NS_CONTROL:
        return _handle_control(hass, name, payload)
    elif namespace == NS_QUERY:
        return _handle_query(hass, name, payload)
    else:
        return _error_response(namespace, name, ERROR_UNSUPPORTED_OPERATION)


def _handle_discovery(
    hass: HomeAssistant, name: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """Handle DiscoverAppliancesRequest."""
    _refresh_appliance_map(hass)
    appliances = discover_appliances(hass)

    return {
        "header": {
            "namespace": NS_DISCOVERY,
            "name": "DiscoverAppliancesResponse",
            "messageId": "",
            "payloadVersion": "1",
        },
        "payload": {"discoveredAppliances": appliances},
    }


def _handle_control(
    hass: HomeAssistant, name: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """Handle control directives."""
    appliance_id = payload.get("appliance", {}).get("applianceId", "")
    entity_id = _entity_id_from_appliance(appliance_id)

    if not entity_id:
        return _error_response(NS_CONTROL, name, ERROR_NO_SUCH_TARGET)

    domain = entity_id.split(".")[0]
    state = hass.states.get(entity_id)
    if not state:
        return _error_response(NS_CONTROL, name, ERROR_NO_SUCH_TARGET)

    _LOGGER.info("DuerOS control: %s on %s (%s)", name, entity_id, domain)

    # Dispatch to specific handler
    try:
        if name in ("TurnOnRequest",):
            return _turn_on(hass, entity_id, domain, state, payload)
        elif name in ("TurnOffRequest",):
            return _turn_off(hass, entity_id, domain, state, payload)
        elif name in ("SetBrightnessRequest",):
            return _set_brightness(hass, entity_id, payload)
        elif name in ("AdjustBrightnessRequest",):
            return _adjust_brightness(hass, entity_id, state, payload)
        elif name in ("SetColorRequest",):
            return _set_color(hass, entity_id, payload)
        elif name in ("SetColorTemperatureRequest",):
            return _set_color_temperature(hass, entity_id, payload)
        elif name in ("SetTemperatureRequest",):
            return _set_temperature(hass, entity_id, domain, payload)
        elif name in ("AdjustTemperatureRequest",):
            return _adjust_temperature(hass, entity_id, state, payload)
        elif name in ("SetModeRequest",):
            return _set_mode(hass, entity_id, domain, payload)
        elif name in ("PercentageRequest",):
            return _set_percentage(hass, entity_id, domain, payload)
        elif name in ("IncrementRequest",):
            return _adjust_percentage(hass, entity_id, state, 10, domain)
        elif name in ("DecrementRequest",):
            return _adjust_percentage(hass, entity_id, state, -10, domain)
        elif name in ("SuspendRequest",):
            return _suspend(hass, entity_id, domain)
        elif name in ("ResumeRequest",):
            return _resume(hass, entity_id, domain)
        else:
            return _error_response(NS_CONTROL, name, ERROR_UNSUPPORTED_OPERATION)
    except Exception as exc:
        _LOGGER.error("Error handling control %s: %s", name, exc)
        return _error_response(NS_CONTROL, name, ERROR_UNSUPPORTED_OPERATION)


def _turn_on(
    hass: HomeAssistant, entity_id: str, domain: str, state: Any, payload: dict
) -> dict[str, Any]:
    """Handle TurnOnRequest."""
    data = {ATTR_ENTITY_ID: entity_id}

    if domain == "scene":
        hass.services.async_call("scene", "turn_on", data, blocking=False)
    elif domain == "automation":
        hass.services.async_call("automation", "trigger", data, blocking=False)
    elif domain == "cover":
        hass.services.async_call("cover", "open_cover", data, blocking=False)
    elif domain == "climate":
        hass.services.async_call("climate", "turn_on", data, blocking=False)
    else:
        hass.services.async_call(domain, SERVICE_TURN_ON, data, blocking=False)

    return {
        "header": {
            "namespace": NS_CONTROL,
            "name": ACTION_TURN_ON,
            "messageId": "",
            "payloadVersion": "1",
        },
        "payload": {"success": True},
    }


def _turn_off(
    hass: HomeAssistant, entity_id: str, domain: str, state: Any, payload: dict
) -> dict[str, Any]:
    """Handle TurnOffRequest."""
    data = {ATTR_ENTITY_ID: entity_id}

    if domain == "cover":
        hass.services.async_call("cover", "close_cover", data, blocking=False)
    elif domain == "climate":
        hass.services.async_call("climate", "turn_off", data, blocking=False)
    else:
        hass.services.async_call(domain, SERVICE_TURN_OFF, data, blocking=False)

    return {
        "header": {
            "namespace": NS_CONTROL,
            "name": ACTION_TURN_OFF,
            "messageId": "",
            "payloadVersion": "1",
        },
        "payload": {"success": True},
    }


def _set_brightness(hass: HomeAssistant, entity_id: str, payload: dict) -> dict:
    """Handle SetBrightnessRequest."""
    brightness = payload.get("appliance", {}).get("brightness", {})
    value = brightness.get("value", 100)

    # DuerOS sends 0-100, HA expects 0-255
    ha_brightness = round(value / 100 * 255)
    hass.services.async_call(
        "light",
        "turn_on",
        {ATTR_ENTITY_ID: entity_id, "brightness": ha_brightness},
        blocking=False,
    )

    return {
        "header": {
            "namespace": NS_CONTROL,
            "name": "SetBrightnessConfirmation",
            "messageId": "",
            "payloadVersion": "1",
        },
        "payload": {"brightness": value},
    }


def _adjust_brightness(
    hass: HomeAssistant, entity_id: str, state: State, payload: dict
) -> dict:
    """Handle AdjustBrightnessRequest."""
    delta = payload.get("appliance", {}).get("brightness", {}).get("value", 10)
    current = state.attributes.get("brightness", 128)
    new_brightness = max(0, min(255, current + round(delta / 100 * 255)))

    hass.services.async_call(
        "light",
        "turn_on",
        {ATTR_ENTITY_ID: entity_id, "brightness": new_brightness},
        blocking=False,
    )

    return {
        "header": {
            "namespace": NS_CONTROL,
            "name": "AdjustBrightnessConfirmation",
            "messageId": "",
            "payloadVersion": "1",
        },
        "payload": {"brightness": round(new_brightness / 255 * 100)},
    }


def _set_color(hass: HomeAssistant, entity_id: str, payload: dict) -> dict:
    """Handle SetColorRequest."""
    color = payload.get("appliance", {}).get("color", {})
    r = color.get("r", 255)
    g = color.get("g", 255)
    b = color.get("b", 255)

    # Convert RGB to HS
    from homeassistant.util.color import color_RGB_to_hs
    hs = color_RGB_to_hs(r, g, b)

    hass.services.async_call(
        "light",
        "turn_on",
        {ATTR_ENTITY_ID: entity_id, "hs_color": list(hs)},
        blocking=False,
    )

    return {
        "header": {
            "namespace": NS_CONTROL,
            "name": "SetColorConfirmation",
            "messageId": "",
            "payloadVersion": "1",
        },
        "payload": {"color": color},
    }


def _set_color_temperature(
    hass: HomeAssistant, entity_id: str, payload: dict
) -> dict:
    """Handle SetColorTemperatureRequest."""
    ct = payload.get("appliance", {}).get("colorTemperature", {})
    value = ct.get("value", 4000)

    hass.services.async_call(
        "light",
        "turn_on",
        {ATTR_ENTITY_ID: entity_id, "color_temp_kelvin": value},
        blocking=False,
    )

    return {
        "header": {
            "namespace": NS_CONTROL,
            "name": "SetColorTemperatureConfirmation",
            "messageId": "",
            "payloadVersion": "1",
        },
        "payload": {"colorTemperature": value},
    }


def _set_temperature(
    hass: HomeAssistant, entity_id: str, domain: str, payload: dict
) -> dict:
    """Handle SetTemperatureRequest."""
    temp = payload.get("appliance", {}).get("temperature", {})
    value = temp.get("value", 24)

    if domain == "climate":
        hass.services.async_call(
            "climate",
            "set_temperature",
            {ATTR_ENTITY_ID: entity_id, ATTR_TEMPERATURE: value},
            blocking=False,
        )

    return {
        "header": {
            "namespace": NS_CONTROL,
            "name": "SetTemperatureConfirmation",
            "messageId": "",
            "payloadVersion": "1",
        },
        "payload": {"temperature": value},
    }


def _adjust_temperature(
    hass: HomeAssistant, entity_id: str, state: Any, payload: dict
) -> dict:
    """Handle AdjustTemperatureRequest."""
    delta = payload.get("appliance", {}).get("temperature", {}).get("value", 1)
    current = state.attributes.get("temperature", 24)
    new_temp = current + delta

    hass.services.async_call(
        "climate",
        "set_temperature",
        {ATTR_ENTITY_ID: entity_id, ATTR_TEMPERATURE: new_temp},
        blocking=False,
    )

    return {
        "header": {
            "namespace": NS_CONTROL,
            "name": "AdjustTemperatureConfirmation",
            "messageId": "",
            "payloadVersion": "1",
        },
        "payload": {"temperature": new_temp},
    }


def _set_mode(
    hass: HomeAssistant, entity_id: str, domain: str, payload: dict
) -> dict:
    """Handle SetModeRequest."""
    mode = payload.get("appliance", {}).get("mode", "AUTO")

    if domain == "climate":
        ha_mode = DUREOS_MODE_REVERSE.get(mode)
        if ha_mode:
            hass.services.async_call(
                "climate",
                "set_hvac_mode",
                {ATTR_ENTITY_ID: entity_id, "hvac_mode": ha_mode},
                blocking=False,
            )
    elif domain == "fan":
        hass.services.async_call(
            "fan",
            "set_preset_mode",
            {ATTR_ENTITY_ID: entity_id, "preset_mode": mode.lower()},
            blocking=False,
        )

    return {
        "header": {
            "namespace": NS_CONTROL,
            "name": "SetModeConfirmation",
            "messageId": "",
            "payloadVersion": "1",
        },
        "payload": {"mode": mode},
    }


def _set_percentage(
    hass: HomeAssistant, entity_id: str, domain: str, payload: dict
) -> dict:
    """Handle PercentageRequest (cover position / fan speed)."""
    percentage = payload.get("appliance", {}).get("percentage", {}).get("value", 50)

    if domain == "cover":
        # cover position
        if percentage == 0:
            hass.services.async_call(
                "cover", "close_cover", {ATTR_ENTITY_ID: entity_id}, blocking=False
            )
        elif percentage == 100:
            hass.services.async_call(
                "cover", "open_cover", {ATTR_ENTITY_ID: entity_id}, blocking=False
            )
        else:
            hass.services.async_call(
                "cover",
                "set_cover_position",
                {ATTR_ENTITY_ID: entity_id, "position": percentage},
                blocking=False,
            )
    elif domain == "fan":
        hass.services.async_call(
            "fan",
            "set_percentage",
            {ATTR_ENTITY_ID: entity_id, "percentage": percentage},
            blocking=False,
        )
    elif domain == "humidifier":
        hass.services.async_call(
            "humidifier",
            "set_humidity",
            {ATTR_ENTITY_ID: entity_id, "humidity": percentage},
            blocking=False,
        )

    return {
        "header": {
            "namespace": NS_CONTROL,
            "name": "SetPercentageConfirmation",
            "messageId": "",
            "payloadVersion": "1",
        },
        "payload": {"percentage": percentage},
    }


def _adjust_percentage(
    hass: HomeAssistant,
    entity_id: str,
    state: Any,
    delta: int,
    domain: str,
) -> dict:
    """Handle Increment/Decrement percentage."""
    current = state.attributes.get("percentage", state.attributes.get("current_position", 50))
    new_value = max(0, min(100, current + delta))

    if domain == "cover":
        hass.services.async_call(
            "cover",
            "set_cover_position",
            {ATTR_ENTITY_ID: entity_id, "position": new_value},
            blocking=False,
        )
    elif domain == "fan":
        hass.services.async_call(
            "fan",
            "set_percentage",
            {ATTR_ENTITY_ID: entity_id, "percentage": new_value},
            blocking=False,
        )

    return {
        "header": {
            "namespace": NS_CONTROL,
            "name": "PercentageConfirmation",
            "messageId": "",
            "payloadVersion": "1",
        },
        "payload": {"percentage": new_value},
    }


def _suspend(hass: HomeAssistant, entity_id: str, domain: str) -> dict:
    """Handle SuspendRequest (pause)."""
    if domain == "cover":
        hass.services.async_call(
            "cover", "stop_cover", {ATTR_ENTITY_ID: entity_id}, blocking=False
        )
    else:
        hass.services.async_call(
            domain, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: entity_id}, blocking=False
        )

    return {
        "header": {
            "namespace": NS_CONTROL,
            "name": "SuspendConfirmation",
            "messageId": "",
            "payloadVersion": "1",
        },
        "payload": {"success": True},
    }


def _resume(hass: HomeAssistant, entity_id: str, domain: str) -> dict:
    """Handle ResumeRequest."""
    hass.services.async_call(
        domain, SERVICE_TURN_ON, {ATTR_ENTITY_ID: entity_id}, blocking=False
    )

    return {
        "header": {
            "namespace": NS_CONTROL,
            "name": "ResumeConfirmation",
            "messageId": "",
            "payloadVersion": "1",
        },
        "payload": {"success": True},
    }


def _handle_query(
    hass: HomeAssistant, name: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """Handle QueryRequest."""
    appliance_id = payload.get("appliance", {}).get("applianceId", "")
    entity_id = _entity_id_from_appliance(appliance_id)

    if not entity_id:
        return _error_response(NS_QUERY, name, ERROR_NO_SUCH_TARGET)

    properties = query_state(hass, entity_id)
    if properties is None:
        return _error_response(NS_QUERY, name, ERROR_NO_SUCH_TARGET)

    return {
        "header": {
            "namespace": NS_QUERY,
            "name": "QueryResponse",
            "messageId": "",
            "payloadVersion": "1",
        },
        "payload": {"properties": properties},
    }



