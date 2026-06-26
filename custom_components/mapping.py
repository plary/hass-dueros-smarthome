"""Map Home Assistant entities to DuerOS ConnectedHome device descriptions."""

import logging
from typing import Any

from homeassistant.components.climate import HVACMode
from homeassistant.components.cover import CoverEntityFeature
from homeassistant.components.fan import FanEntityFeature
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    COLOR_MODE_BRIGHTNESS,
    COLOR_MODE_COLOR_TEMP,
    COLOR_MODE_HS,
    COLOR_MODE_RGB,
    COLOR_MODE_XY,
    LightEntityFeature,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_FRIENDLY_NAME,
    ATTR_SUPPORTED_FEATURES,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.util import color as color_util

from .const import (
    APPLIANCE_AC,
    APPLIANCE_CURTAIN,
    APPLIANCE_FAN,
    APPLIANCE_HUMIDIFIER,
    APPLIANCE_LIGHT,
    APPLIANCE_OUTLET,
    APPLIANCE_SCENE,
    APPLIANCE_SENSOR,
    APPLIANCE_SWITCH,
    DOMAIN_TO_APPLIANCE,
)

_LOGGER = logging.getLogger(__name__)

# DuerOS device actions that each appliance type supports
ACTION_MAP: dict[str, list[str]] = {
    APPLIANCE_LIGHT: [
        "turnOn",
        "turnOff",
        "setBrightness",
        "adjustBrightness",
        "setColor",
        "setColorTemperature",
    ],
    APPLIANCE_SWITCH: ["turnOn", "turnOff"],
    APPLIANCE_OUTLET: ["turnOn", "turnOff"],
    APPLIANCE_CURTAIN: ["turnOn", "turnOff", "setPercentage", "incrementPercentage", "decrementPercentage"],
    APPLIANCE_AC: ["turnOn", "turnOff", "setTemperature", "adjustTemperature", "setMode", "setFanSpeed"],
    APPLIANCE_FAN: ["turnOn", "turnOff", "setPercentage", "incrementPercentage", "decrementPercentage"],
    APPLIANCE_HUMIDIFIER: ["turnOn", "turnOff", "setPercentage", "incrementPercentage", "decrementPercentage"],
    APPLIANCE_SCENE: ["turnOn"],
    APPLIANCE_SENSOR: [],
    APPLIANCE_THERMOSTAT: ["turnOn", "turnOff", "setTemperature", "adjustTemperature"],
}

# Properties each appliance type can report
PROPERTY_MAP: dict[str, list[str]] = {
    APPLIANCE_LIGHT: ["powerState", "brightness", "color", "colorTemperature"],
    APPLIANCE_SWITCH: ["powerState"],
    APPLIANCE_OUTLET: ["powerState"],
    APPLIANCE_CURTAIN: ["powerState", "percentage"],
    APPLIANCE_AC: ["powerState", "temperature", "targetTemperature", "fanSpeed", "mode"],
    APPLIANCE_FAN: ["powerState", "percentage"],
    APPLIANCE_HUMIDIFIER: ["powerState", "percentage"],
    APPLIANCE_SCENE: [],
    APPLIANCE_SENSOR: ["temperature", "humidity"],
    APPLIANCE_THERMOSTAT: ["powerState", "temperature", "targetTemperature"],
}

# Climate HVACMode -> DuerOS mode mapping
HVAC_MODE_MAP = {
    HVACMode.AUTO: "AUTO",
    HVACMode.COOL: "COOL",
    HVACMode.HEAT: "HEAT",
    HVACMode.DRY: "DRY",
    HVACMode.FAN_ONLY: "FAN",
}

DUREOS_MODE_REVERSE = {v: k for k, v in HVAC_MODE_MAP.items()}


def _make_appliance_id(entity_id: str) -> str:
    """Create a DuerOS appliance ID from HA entity ID."""
    return entity_id.replace(".", "_")


def _get_appliance_type(state: State) -> str | None:
    """Determine DuerOS appliance type from HA entity state."""
    domain = state.entity_id.split(".")[0]
    return DOMAIN_TO_APPLIANCE.get(domain)


def _supports_feature(state: State, feature: int) -> bool:
    """Check if entity supports a feature."""
    features = state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)
    return bool(features & feature)


def _brightness_pct(state: State) -> int | None:
    """Get brightness as percentage (0-100)."""
    brightness = state.attributes.get(ATTR_BRIGHTNESS)
    if brightness is not None:
        return round(brightness / 255 * 100)
    return None


def _color_temperature(state: State) -> int | None:
    """Get color temperature in Kelvin."""
    return state.attributes.get(ATTR_COLOR_TEMP_KELVIN)


def _hs_color_to_rgb(state: State) -> tuple[int, int, int] | None:
    """Convert HA HS color to RGB tuple."""
    hs = state.attributes.get("hs_color")
    if hs:
        rgb = color_util.color_hs_to_RGB(hs[0], hs[1])
        return rgb
    return None


def discover_appliances(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Discover all controllable entities and map to DuerOS appliances."""
    appliances = []

    for state in hass.states.async_all():
        appliance_type = _get_appliance_type(state)
        if not appliance_type:
            continue
        if state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            continue

        appliance = _build_appliance(state, appliance_type)
        if appliance:
            appliances.append(appliance)

    return appliances


def _build_appliance(state: State, appliance_type: str) -> dict[str, Any] | None:
    """Build a DuerOS appliance description from HA state."""
    entity_id = state.entity_id
    friendly_name = state.attributes.get(ATTR_FRIENDLY_NAME, entity_id)
    domain = entity_id.split(".")[0]
    device_class = state.attributes.get("device_class", "")

    appliance: dict[str, Any] = {
        "applianceId": _make_appliance_id(entity_id),
        "manufacturerName": "Home Assistant",
        "modelName": domain,
        "version": "1.0",
        "friendlyName": friendly_name,
        "friendlyDescription": f"Home Assistant {domain}: {friendly_name}",
        "isReachable": state.state != STATE_UNAVAILABLE,
        "actions": ACTION_MAP.get(appliance_type, []),
        "additionalApplianceDetails": {
            "entity_id": entity_id,
            "domain": domain,
        },
    }

    # Add appliance types
    appliance["applianceTypes"] = [appliance_type]

    # Add attributes based on type
    attributes: dict[str, Any] = {}
    if appliance_type in (APPLIANCE_LIGHT, APPLIANCE_SWITCH, APPLIANCE_OUTLET):
        attributes["turnOn"] = {}
    if appliance_type in (APPLIANCE_LIGHT, APPLIANCE_SWITCH, APPLIANCE_OUTLET):
        attributes["turnOff"] = {}

    # Light-specific attributes
    if appliance_type == APPLIANCE_LIGHT:
        color_modes = state.attributes.get("supported_color_modes", [])
        if COLOR_MODE_BRIGHTNESS in color_modes or any(
            m in color_modes
            for m in [COLOR_MODE_HS, COLOR_MODE_RGB, COLOR_MODE_XY, COLOR_MODE_COLOR_TEMP]
        ):
            attributes["setBrightness"] = {"brightness": {"value": 0, "scale": "percentage"}}
            attributes["adjustBrightness"] = {"brightness": {"value": 0, "scale": "percentage"}}
        if any(m in color_modes for m in [COLOR_MODE_HS, COLOR_MODE_RGB, COLOR_MODE_XY]):
            attributes["setColor"] = {"color": {"colorModel": "rgb"}}
        if COLOR_MODE_COLOR_TEMP in color_modes:
            attrs = state.attributes
            min_kelvin = attrs.get("min_color_temp_kelvin", 2000)
            max_kelvin = attrs.get("max_color_temp_kelvin", 6500)
            attributes["setColorTemperature"] = {
                "colorTemperature": {
                    "value": 0,
                    "scale": "kelvin",
                    "range": {"minimumValue": min_kelvin, "maximumValue": max_kelvin},
                }
            }

    # Cover-specific
    if appliance_type == APPLIANCE_CURTAIN:
        attributes["setPercentage"] = {}
        attributes["incrementPercentage"] = {}
        attributes["decrementPercentage"] = {}

    # Climate-specific
    if appliance_type == APPLIANCE_AC:
        attributes["turnOn"] = {}
        attributes["turnOff"] = {}
        attributes["setTemperature"] = {}
        attributes["adjustTemperature"] = {}
        attributes["setMode"] = {}
        attributes["setFanSpeed"] = {}

    appliance["attributes"] = attributes

    return appliance


def query_state(hass: HomeAssistant, entity_id: str) -> dict[str, Any] | None:
    """Query current state of an entity and return DuerOS properties."""
    state = hass.states.get(entity_id)
    if not state:
        return None

    domain = entity_id.split(".")[0]
    appliance_type = _get_appliance_type(state)
    if not appliance_type:
        return None

    properties: dict[str, Any] = {}

    # Power state
    if state.state in (STATE_ON, STATE_OFF):
        properties["powerState"] = "ON" if state.state == STATE_ON else "OFF"

    # Brightness
    brightness = _brightness_pct(state)
    if brightness is not None:
        properties["brightness"] = brightness

    # Color
    rgb = _hs_color_to_rgb(state)
    if rgb:
        properties["color"] = {"colorModel": "rgb", "r": rgb[0], "g": rgb[1], "b": rgb[2]}

    # Color temperature
    ct = _color_temperature(state)
    if ct is not None:
        properties["colorTemperature"] = ct

    # Temperature (climate)
    if domain == "climate":
        current_temp = state.attributes.get("current_temperature")
        if current_temp is not None:
            properties["temperature"] = current_temp
        target_temp = state.attributes.get("temperature")
        if target_temp is not None:
            properties["targetTemperature"] = target_temp
        hvac_mode = state.state
        dueros_mode = HVAC_MODE_MAP.get(hvac_mode, "AUTO")
        properties["mode"] = dueros_mode
        fan_speed = state.attributes.get("fan_mode")
        if fan_speed:
            properties["fanSpeed"] = fan_speed

    # Cover percentage
    if domain == "cover":
        position = state.attributes.get("current_position")
        if position is not None:
            properties["percentage"] = position

    # Fan percentage
    if domain == "fan":
        percentage = state.attributes.get("percentage")
        if percentage is not None:
            properties["percentage"] = percentage

    # Sensor temperature/humidity
    if domain == "sensor":
        device_class = state.attributes.get("device_class", "")
        if device_class == "temperature":
            try:
                properties["temperature"] = float(state.state)
            except (ValueError, TypeError):
                pass
        elif device_class == "humidity":
            try:
                properties["humidity"] = float(state.state)
            except (ValueError, TypeError):
                pass

    return properties
