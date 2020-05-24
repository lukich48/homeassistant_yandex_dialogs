"""Config flow for YandexDialogs."""
from homeassistant.helpers import config_entry_flow

from .const import DOMAIN

config_entry_flow.register_webhook_flow(
    DOMAIN,
    "YandexDialogs Webhook",
    {
        "yandexdialogs_url": "https://yandex.ru/dev/dialogs/alice/doc/protocol-docpage/",
        "docs_url": "https://github.com/lukich48/",
    },
)
