"""Test the Owlet setup."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.owlet.const import DOMAIN
from custom_components.owlet.owletapi.exceptions import (
    OwletAuthenticationError,
    OwletConnectionError,
    OwletDevicesError,
)
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .conftest import FRESH_TIME, load_json
from .helpers import setup_integration

pytestmark = pytest.mark.freeze_time(FRESH_TIME)


async def test_setup_and_unload(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_owlet_api: dict[str, AsyncMock],
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test a successful setup and unload."""
    await setup_integration(hass, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.LOADED

    devices = dr.async_entries_for_config_entry(
        device_registry, mock_config_entry.entry_id
    )
    assert len(devices) == 1
    device = devices[0]
    assert device.identifiers == {(DOMAIN, "SERIAL_NUMBER")}
    assert device.name == "Owlet Sock SERIAL_NUMBER"
    assert device.manufacturer == "Owlet Baby Care"
    assert device.model == "SS3-OBL-EU"
    assert device.serial_number == "SERIAL_NUMBER"
    assert device.hw_version == "obl"

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED


@pytest.mark.parametrize(
    ("side_effect", "state"),
    [
        (OwletAuthenticationError(), ConfigEntryState.SETUP_ERROR),
        (OwletConnectionError(), ConfigEntryState.SETUP_RETRY),
        (OwletDevicesError(), ConfigEntryState.SETUP_RETRY),
        (TimeoutError(), ConfigEntryState.SETUP_RETRY),
    ],
)
async def test_setup_errors(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_owlet_api: dict[str, AsyncMock],
    side_effect: Exception,
    state: ConfigEntryState,
) -> None:
    """Test the entry state for errors during setup."""
    mock_owlet_api["get_devices"].side_effect = side_effect
    await setup_integration(hass, mock_config_entry)
    assert mock_config_entry.state is state


async def test_auth_error_starts_reauth(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_owlet_api: dict[str, AsyncMock],
) -> None:
    """Test that invalid credentials start a reauth flow."""
    mock_owlet_api["authenticate"].side_effect = OwletAuthenticationError()
    await setup_integration(hass, mock_config_entry)

    flows = hass.config_entries.flow.async_progress()
    assert len(flows) == 1
    assert flows[0]["context"]["source"] == SOURCE_REAUTH


async def test_refreshed_tokens_are_stored(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_owlet_api: dict[str, AsyncMock],
) -> None:
    """Test that tokens refreshed by the coordinator end up in the entry."""
    properties = load_json("update_properties_asleep.json")
    properties["tokens"] = load_json("get_devices_with_tokens.json")["tokens"]
    mock_owlet_api["get_properties"].side_effect = lambda *_: properties

    await setup_integration(hass, mock_config_entry)

    assert mock_config_entry.data["api_token"] == "new_api_token"
    assert mock_config_entry.data["refresh"] == "new_refresh_token"
    assert mock_config_entry.data["expiry"] == 200
