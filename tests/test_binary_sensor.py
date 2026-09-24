"""Test the Owlet binary sensors."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant

from .conftest import FRESH_TIME
from .helpers import ENTITY_PREFIX, setup_integration

pytestmark = pytest.mark.freeze_time(FRESH_TIME)

ALERTS = (
    "high_heart_rate_alert",
    "low_heart_rate_alert",
    "high_oxygen_alert",
    "low_oxygen_alert",
    "low_battery_alert",
    "lost_power_alert",
    "sock_disconnected_alert",
)


def _state(hass: HomeAssistant, key: str) -> str:
    return hass.states.get(f"binary_sensor.{ENTITY_PREFIX}_{key}").state


async def test_binary_sensors_asleep(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_owlet_api: dict[str, AsyncMock],
) -> None:
    """Test binary sensor values for a sleeping baby."""
    await setup_integration(hass, mock_config_entry)

    assert _state(hass, "charging") == STATE_OFF
    assert _state(hass, "sock_off") == STATE_OFF
    assert _state(hass, "awake") == STATE_OFF
    assert _state(hass, "data_stale") == STATE_OFF
    for alert in ALERTS:
        assert _state(hass, alert) == STATE_OFF, alert


@pytest.mark.parametrize("properties_fixture", ["update_properties_awake.json"])
async def test_binary_sensors_awake(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_owlet_api: dict[str, AsyncMock],
) -> None:
    """Test binary sensor values when the vitals alerts are active."""
    await setup_integration(hass, mock_config_entry)

    assert _state(hass, "awake") == STATE_ON
    for alert in ALERTS[:-1]:
        assert _state(hass, alert) == STATE_ON, alert
    assert _state(hass, "sock_disconnected_alert") == STATE_OFF


@pytest.mark.parametrize("properties_fixture", ["update_properties_charging.json"])
async def test_binary_sensors_charging(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_owlet_api: dict[str, AsyncMock],
) -> None:
    """Test the awake sensor is unavailable while charging."""
    await setup_integration(hass, mock_config_entry)

    assert _state(hass, "charging") == STATE_ON
    assert _state(hass, "awake") == STATE_UNAVAILABLE
