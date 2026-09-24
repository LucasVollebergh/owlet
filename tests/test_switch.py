"""Test the Owlet switch."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.owlet.compat import OwletConnectionError
from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .conftest import FRESH_TIME
from .helpers import entity_id, setup_integration

pytestmark = pytest.mark.freeze_time(FRESH_TIME)


async def test_base_station_switch(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_owlet_api: dict[str, AsyncMock],
) -> None:
    """Test turning the base station on and off."""
    await setup_integration(hass, mock_config_entry)
    base_station = entity_id(hass, "switch", "base_station_on")
    assert hass.states.get(base_station).state == STATE_ON

    polls = mock_owlet_api["get_properties"].call_count
    for service in (SERVICE_TURN_OFF, SERVICE_TURN_ON):
        await hass.services.async_call(
            SWITCH_DOMAIN, service, {ATTR_ENTITY_ID: base_station}, blocking=True
        )
    await hass.async_block_till_done()

    assert mock_owlet_api["post_command"].call_count == 2
    assert mock_owlet_api["post_command"].call_args_list[0].args[1] == (
        "BASE_STATION_ON_CMD"
    )
    assert mock_owlet_api["get_properties"].call_count > polls


async def test_base_station_switch_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_owlet_api: dict[str, AsyncMock],
) -> None:
    """Test a failing command raises a user facing error."""
    await setup_integration(hass, mock_config_entry)
    base_station = entity_id(hass, "switch", "base_station_on")
    mock_owlet_api["post_command"].side_effect = OwletConnectionError()

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: base_station},
            blocking=True,
        )
