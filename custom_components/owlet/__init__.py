"""The Owlet Smart Sock integration.

Originally created by Ryan Clark (https://github.com/ryanbdclark/owlet), now
maintained at https://github.com/lucasvollebergh/owlet.
"""

from __future__ import annotations

import asyncio
import logging

from aiohttp import ClientError
from pyowletapi.api import OwletAPI
from pyowletapi.sock import Sock

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_API_TOKEN,
    CONF_REGION,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .compat import (
    OWLET_CREDENTIAL_ERRORS,
    OwletConnectionError,
    OwletDevicesError,
    OwletError,
)
from .const import CONF_OWLET_EXPIRY, CONF_OWLET_REFRESH, SUPPORTED_VERSIONS
from .coordinator import OwletCoordinator

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.SWITCH]

_LOGGER = logging.getLogger(__name__)

type OwletConfigEntry = ConfigEntry[dict[str, OwletCoordinator]]


async def async_setup_entry(hass: HomeAssistant, entry: OwletConfigEntry) -> bool:
    """Set up Owlet Smart Sock from a config entry."""
    owlet_api = OwletAPI(
        region=entry.data[CONF_REGION],
        token=entry.data[CONF_API_TOKEN],
        expiry=entry.data[CONF_OWLET_EXPIRY],
        refresh=entry.data[CONF_OWLET_REFRESH],
        session=async_get_clientsession(hass),
    )

    try:
        await owlet_api.authenticate()
        devices = await owlet_api.get_devices(SUPPORTED_VERSIONS)
    except OWLET_CREDENTIAL_ERRORS as err:
        raise ConfigEntryAuthFailed(
            f"Credentials expired for {entry.data[CONF_USERNAME]}"
        ) from err
    except OwletDevicesError as err:
        raise ConfigEntryNotReady(
            "No supported Owlet socks found on this account"
        ) from err
    except (OwletConnectionError, OwletError, ClientError, TimeoutError) as err:
        raise ConfigEntryNotReady(
            f"Error connecting to Owlet for {entry.data[CONF_USERNAME]}"
        ) from err

    _async_store_tokens(hass, entry, owlet_api)

    coordinators = {
        device["device"]["dsn"]: OwletCoordinator(
            hass, entry, Sock(owlet_api, device["device"])
        )
        for device in devices["response"]
    }

    await asyncio.gather(
        *(
            coordinator.async_config_entry_first_refresh()
            for coordinator in coordinators.values()
        )
    )

    entry.runtime_data = coordinators

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: OwletConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def _async_store_tokens(
    hass: HomeAssistant, entry: OwletConfigEntry, owlet_api: OwletAPI
) -> None:
    """Persist refreshed tokens so a restart does not need a new login."""
    tokens = {key: value for key, value in owlet_api.tokens.items() if value}
    if any(entry.data.get(key) != value for key, value in tokens.items()):
        hass.config_entries.async_update_entry(entry, data={**entry.data, **tokens})
