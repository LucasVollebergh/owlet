"""Test the Owlet diagnostics."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from homeassistant.components.diagnostics import REDACTED
from homeassistant.core import HomeAssistant

from .conftest import FRESH_TIME
from .helpers import setup_integration

pytestmark = pytest.mark.freeze_time(FRESH_TIME)


async def test_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
    mock_owlet_api: dict[str, AsyncMock],
) -> None:
    """Test secrets and personal data are redacted."""
    await setup_integration(hass, mock_config_entry)

    result = await get_diagnostics_for_config_entry(
        hass, hass_client, mock_config_entry
    )

    assert result["entry"]["data"]["api_token"] == REDACTED
    assert result["entry"]["data"]["refresh"] == REDACTED
    assert result["entry"]["data"]["username"] == REDACTED
    sock = result["socks"][0]
    assert sock["is_stale"] is False
    assert sock["properties"]["heart_rate"] == 97.0
    assert "SERIAL_NUMBER" not in str(result)
    assert sock["raw_properties"]["REAL_TIME_VITALS"]["device_key"] == REDACTED
