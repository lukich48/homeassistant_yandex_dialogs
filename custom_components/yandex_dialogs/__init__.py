"""Support for Yandex Dialogs webhook."""
import logging

from aiohttp import web
import voluptuous as vol

from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_entry_flow, intent, template

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SOURCE = "Home Assistant Yandex Dialogs"
WELCOME_INTENT = "Welcome"
DEFAULT_INTENT = "Default"  # todo in params

CONFIG_SCHEMA = vol.Schema({DOMAIN: {}}, extra=vol.ALLOW_EXTRA)


class YandexDialogsError(HomeAssistantError):
    """Raised when a YandexDialogs error happens."""


async def async_setup(hass, config):
    """Set up the YandexDialogs component."""
    return True


async def handle_webhook(hass, webhook_id, request):
    """Handle incoming webhook with YandexDialogs requests."""
    message = await request.json()

    _LOGGER.debug("Received YandexDialogs request: %s", message)

    try:
        response = await async_handle_message(hass, message)
        return b"" if response is None else web.json_response(response)

    except YandexDialogsError as err:
        _LOGGER.warning(str(err))
        return web.json_response(yandex_dialogs_error_response(message, str(err)))

    except intent.UnknownIntent as err:
        _LOGGER.warning(str(err))
        return web.json_response(
            yandex_dialogs_error_response(
                message, "This intent is not yet configured within Home Assistant."
            )
        )

    except intent.InvalidSlotInfo as err:
        _LOGGER.warning(str(err))
        return web.json_response(
            yandex_dialogs_error_response(
                message, "Invalid slot information received for this intent."
            )
        )

    except intent.IntentError as err:
        _LOGGER.warning(str(err))
        return web.json_response(
            yandex_dialogs_error_response(message, "Error handling intent.")
        )


async def async_setup_entry(hass, entry):
    """Configure based on config entry."""
    hass.components.webhook.async_register(
        DOMAIN, "YandexDialogs", entry.data[CONF_WEBHOOK_ID], handle_webhook
    )
    return True


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    hass.components.webhook.async_unregister(entry.data[CONF_WEBHOOK_ID])
    return True


# pylint: disable=invalid-name
async_remove_entry = config_entry_flow.webhook_async_remove_entry


def yandex_dialogs_error_response(message, error):
    """Return a response saying the error message."""

    response = ResponseBuilder(message)
    response.set_speach(error)
    return response.as_dict()


async def async_handle_message(hass, message):
    """Handle a YandexDialogs message."""

    response = ResponseBuilder(message)

    action, slots = get_intent(message)

    if response.is_new and action == DEFAULT_INTENT:
        action = WELCOME_INTENT

    intent_response = await intent.async_handle(hass, DOMAIN, action, slots)

    response.set_speach(intent_response.speech["plain"]["speech"])

    return response.as_dict()


def get_intent(message):
    intents = message["request"]["nlu"]["intents"]
    if intents:
        for key, value in intents.items():
            return key, get_slots(value["slots"])
    else:
        return DEFAULT_INTENT, {}


def get_slots(slots):
    if slots:
        return {key: {"value": value["value"]} for key, value in slots.items()}
    else:
        return {}


class ResponseBuilder:
    """Help generating the response for Yandex Dialogs."""

    def __init__(self, message):
        self.message = message
        self.response = {
            "version": message["version"],
            "session": message["session"],
            "response": {"end_session": False},
        }

    def set_speach(self, text):
        """Add speech to the response."""

        if isinstance(text, template.Template):
            text = text.async_render()

        self.response["response"]["text"] = text

    @property
    def is_new(self):
        """Is new session"""
        return bool(self.message["session"]["new"])

    def as_dict(self):
        """Return response in a Yandex Dialogs valid dictionary."""
        return self.response
