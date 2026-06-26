"""Constants for DuerOS Smart Home integration."""

DOMAIN = "dueros_smarthome"

# Config keys
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_ACCESS_TOKEN = "access_token"
CONF_TOKEN_EXPIRES = "token_expires"

# DuerOS ConnectedHome Namespaces
NS_DISCOVERY = "DuerOS.ConnectedHome.Discovery"
NS_CONTROL = "DuerOS.ConnectedHome.Control"
NS_QUERY = "DuerOS.ConnectedHome.Query"

# DuerOS Discovery
DISCOVER_REQUEST = "DiscoverAppliancesRequest"
DISCOVER_RESPONSE = "DiscoverAppliancesResponse"

# DuerOS Control directives
TURN_ON = "TurnOnRequest"
TURN_OFF = "TurnOffRequest"
SET_BRIGHTNESS = "SetBrightnessRequest"
ADJUST_BRIGHTNESS = "AdjustBrightnessRequest"
SET_COLOR = "SetColorRequest"
SET_COLOR_TEMPERATURE = "SetColorTemperatureRequest"
SET_TEMPERATURE = "SetTemperatureRequest"
ADJUST_TEMPERATURE = "AdjustTemperatureRequest"
SET_FAN_SPEED = "SetFanSpeedRequest"
SET_MODE = "SetModeRequest"
PERCENTAGE = "PercentageRequest"
PERCENTAGE_ADJUST = "PercentageAdjustRequest"
INCREMENT = "IncrementRequest"
DECREMENT = "DecrementRequest"
SUSPEND = "SuspendRequest"
RESUME = "ResumeRequest"

# DuerOS Query
QUERY_REQUEST = "QueryRequest"

# DuerOS Appliance Types
APPLIANCE_LIGHT = "LIGHT"
APPLIANCE_SWITCH = "SWITCH"
APPLIANCE_OUTLET = "OUTLET"
APPLIANCE_CURTAIN = "CURTAIN"
APPLIANCE_AC = "AIR_CONDITION"
APPLIANCE_THERMOSTAT = "THERMOSTAT"
APPLIANCE_SCENE = "SCENE_TRIGGER"
APPLIANCE_FAN = "FAN"
APPLIANCE_HUMIDIFIER = "HUMIDIFIER"
APPLIANCE_AIRPURIFIER = "AIR_PURIFIER"
APPLIANCE_SENSOR = "SENSOR"

# HA domain to DuerOS appliance type mapping
DOMAIN_TO_APPLIANCE = {
    "light": APPLIANCE_LIGHT,
    "switch": APPLIANCE_SWITCH,
    "input_boolean": APPLIANCE_SWITCH,
    "fan": APPLIANCE_FAN,
    "cover": APPLIANCE_CURTAIN,
    "climate": APPLIANCE_AC,
    "humidifier": APPLIANCE_HUMIDIFIER,
    "scene": APPLIANCE_SCENE,
    "automation": APPLIANCE_SCENE,
    "input_button": APPLIANCE_SCENE,
}

# DuerOS Actions (responses)
ACTION_TURN_ON = "TurnOnConfirmation"
ACTION_TURN_OFF = "TurnOffConfirmation"

# Error types
ERROR_UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"
ERROR_INVALID_ACCESS_TOKEN = "INVALID_ACCESS_TOKEN"
ERROR_NO_SUCH_TARGET = "NO_SUCH_TARGET"
ERROR_BRIDGE_OFFLINE = "BRIDGE_OFFLINE"
ERROR_DEPENDENT_SERVICE_UNAVAILABLE = "DEPENDENT_SERVICE_UNAVAILABLE"
ERROR_TARGET_OFFLINE = "TARGET_OFFLINE"
ERROR_VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
ERROR_NOT_SUPPORTED_IN_CURRENT_MODE = "NOT_SUPPORTED_IN_CURRENT_MODE"

# OAuth paths
OAUTH_AUTHORIZE_PATH = "/auth/dueros/authorize"
OAUTH_TOKEN_PATH = "/auth/dueros/token"
OAUTH_REDIRECT_PATH = "/auth/dueros/callback"

# API paths
API_BASE_PATH = "/api/dueros/smarthome"
