"""Test the Owlet coordinator."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.owlet.compat import (
    OwletAuthenticationError,
    OwletConnectionError,
)
from homeassistant.config_entries import SOURCE_REAUTH
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant

from .conftest import FRESH_TIME
from .helpers import setup_integration, state

pytestmark = pytest.mark.freeze_time(FRESH_TIME)

HEART_RATE = ("sensor", "heart_rate")
BATTERY = ("sensor", "battery_percentage")
STALE = ("binary_sensor", "data_stale")


async def test_connection_error_marks_unavailable(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_owlet_api: dict[str, AsyncMock],
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test entities become unavailable when polling fails and recover after."""
    await setup_integration(hass, mock_config_entry)
    assert state(hass, *HEART_RATE).state == "97.0"

    mock_owlet_api["get_properties"].side_effect = OwletConnectionError()
    freezer.tick(timedelta(seconds=10))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert state(hass, *HEART_RATE).state == STATE_UNAVAILABLE


async def test_auth_error_during_poll_starts_reauth(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_owlet_api: dict[str, AsyncMock],
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test an expired login while polling starts a reauth flow."""
    await setup_integration(hass, mock_config_entry)

    mock_owlet_api["get_properties"].side_effect = OwletAuthenticationError()
    freezer.tick(timedelta(seconds=10))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    flows = hass.config_entries.flow.async_progress()
    assert [flow["context"]["source"] for flow in flows] == [SOURCE_REAUTH]


async def test_stale_data(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_owlet_api: dict[str, AsyncMock],
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test vitals turn unavailable once the cloud stops receiving readings."""
    await setup_integration(hass, mock_config_entry)
    assert state(hass, *STALE).state == STATE_OFF
    assert state(hass, *HEART_RATE).state == "97.0"

    freezer.tick(timedelta(minutes=6))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert state(hass, *STALE).state == STATE_ON
    assert state(hass, *HEART_RATE).state == STATE_UNAVAILABLE
    # Battery is still meaningful, it is not a live vital.
    assert state(hass, *BATTERY).state == "50.0"


@pytest.mark.parametrize("properties_fixture", ["update_properties_charging.json"])
async def test_not_stale_while_charging(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_owlet_api: dict[str, AsyncMock],
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test a charging sock is never reported as stale."""
    freezer.tick(timedelta(hours=2))
    await setup_integration(hass, mock_config_entry)
    assert state(hass, *STALE).state == STATE_OFF
