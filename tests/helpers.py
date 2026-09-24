"""Helpers for the Owlet tests."""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.owlet.const import DOMAIN
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er

SERIAL = "SERIAL_NUMBER"


async def setup_integration(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Add the entry to Home Assistant and set it up."""
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def entity_id(hass: HomeAssistant, platform: str, key: str) -> str:
    """Return the entity id for a unique id key.

    Entity ids are looked up through the registry because newer Home Assistant
    releases include the area in the generated entity id.
    """
    result = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{SERIAL}-{key}")
    assert result is not None, f"{platform} {key} not registered"
    return result


def state(hass: HomeAssistant, platform: str, key: str) -> State | None:
    """Return the state of an Owlet entity by unique id key."""
    return hass.states.get(entity_id(hass, platform, key))
