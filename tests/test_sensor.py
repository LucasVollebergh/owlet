"""Test the Owlet sensors."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .conftest import FRESH_TIME
from .helpers import entity_id, setup_integration, state

pytestmark = pytest.mark.freeze_time(FRESH_TIME)


def _state(hass: HomeAssistant, key: str) -> str:
    return state(hass, "sensor", key).state


async def test_sensors_asleep(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_owlet_api: dict[str, AsyncMock],
    entity_registry: er.EntityRegistry,
) -> None:
    """Test sensor values for a sleeping baby."""
    await setup_integration(hass, mock_config_entry)

    assert _state(hass, "battery_percentage") == "50.0"
    assert _state(hass, "battery_minutes") == "400.0"
    assert _state(hass, "heart_rate") == "97.0"
    assert _state(hass, "oxygen_saturation") == "99.0"
    assert _state(hass, "oxygen_10_av") == "97.0"
    assert _state(hass, "signal_strength") == "30.0"
    assert _state(hass, "skin_temperature") == "34"
    assert _state(hass, "sleep_state") == "light_sleep"
    assert _state(hass, "last_updated") == "2023-05-24T14:15:50+00:00"

    # Unique ids must stay stable so the fork is a drop-in replacement.
    entry = entity_registry.async_get(entity_id(hass, "sensor", "heart_rate"))
    assert entry.unique_id == "SERIAL_NUMBER-heart_rate"
    # Movement sensors are disabled by default.
    assert entity_registry.async_get(entity_id(hass, "sensor", "movement")).disabled
    assert state(hass, "sensor", "movement") is None


@pytest.mark.parametrize("properties_fixture", ["update_properties_awake.json"])
async def test_sensors_awake(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_owlet_api: dict[str, AsyncMock],
) -> None:
    """Test sensor values for an awake baby."""
    await setup_integration(hass, mock_config_entry)

    assert _state(hass, "heart_rate") == "110.0"
    assert _state(hass, "sleep_state") == "awake"


@pytest.mark.parametrize("properties_fixture", ["update_properties_charging.json"])
async def test_sensors_charging(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_owlet_api: dict[str, AsyncMock],
) -> None:
    """Test vitals are unavailable while the sock charges."""
    await setup_integration(hass, mock_config_entry)

    assert _state(hass, "battery_percentage") == "100.0"
    assert _state(hass, "signal_strength") == "34.0"
    assert _state(hass, "heart_rate") == STATE_UNAVAILABLE
    assert _state(hass, "oxygen_saturation") == STATE_UNAVAILABLE
    assert _state(hass, "oxygen_10_av") == STATE_UNAVAILABLE


@pytest.mark.freeze_time("2023-11-20T14:06:00+00:00")
@pytest.mark.parametrize("properties_fixture", ["update_properties_v2.json"])
async def test_sensors_v2(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_owlet_api: dict[str, AsyncMock],
) -> None:
    """Test a Smart Sock 2, where every vital has its own timestamp."""
    await setup_integration(hass, mock_config_entry)

    assert _state(hass, "heart_rate") == "145"
    assert _state(hass, "last_updated") == "2023-11-20T14:05:01+00:00"
    # OXYGEN_LEVEL was last updated at 12:22, a fresh heart rate must not
    # keep that old value looking live.
    assert _state(hass, "oxygen_saturation") == STATE_UNAVAILABLE
    assert state(hass, "binary_sensor", "data_stale").state == "on"
