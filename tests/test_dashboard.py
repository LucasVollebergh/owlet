"""Validate the bundled dashboard."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import re
from typing import Any
from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.owlet.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util.yaml import load_yaml_dict

from .conftest import FRESH_TIME
from .helpers import setup_integration

pytestmark = pytest.mark.freeze_time(FRESH_TIME)

DASHBOARD = Path(__file__).parents[1] / "dashboards" / "owlet.yaml"
ENTITY_ID = re.compile(r"^(sensor|binary_sensor|switch)\.[a-z0-9_]+$")
# Placeholder prefix users replace; matches the entity ids of the test sock.
PLACEHOLDER = "owlet_sock_serial_number"
# Only created when the sock reports them, so they are hidden cards otherwise.
OPTIONAL = {
    f"binary_sensor.{PLACEHOLDER}_critical_oxygen_alert",
    f"binary_sensor.{PLACEHOLDER}_critical_battery_alert",
}


def _entity_ids(node: Any) -> Iterator[str]:
    """Yield every entity id referenced anywhere in the dashboard."""
    if isinstance(node, dict):
        for value in node.values():
            yield from _entity_ids(value)
    elif isinstance(node, list):
        for value in node:
            yield from _entity_ids(value)
    elif isinstance(node, str) and ENTITY_ID.match(node):
        yield node


def _registered(entity_registry: er.EntityRegistry) -> dict[str, er.RegistryEntry]:
    """Return the Owlet entities keyed by their entity id without the area.

    Newer Home Assistant releases put the suggested area in front of the
    generated entity id, users replace that whole prefix in the dashboard.
    """
    result = {}
    for entry in entity_registry.entities.values():
        if entry.platform != DOMAIN:
            continue
        domain, object_id = entry.entity_id.split(".", 1)
        result[f"{domain}.{object_id[object_id.index(PLACEHOLDER) :]}"] = entry
    return result


def test_dashboard_uses_placeholder() -> None:
    """Every entity id uses the documented placeholder prefix."""
    dashboard = load_yaml_dict(DASHBOARD)
    entity_ids = set(_entity_ids(dashboard))
    assert entity_ids
    for entity_id in entity_ids:
        assert entity_id.split(".", 1)[1].startswith(f"{PLACEHOLDER}_"), entity_id
    # Entity ids inside templates use the placeholder too.
    for template in re.findall(r"states\('([^']+)'\)", DASHBOARD.read_text()):
        assert template.split(".", 1)[1].startswith(f"{PLACEHOLDER}_"), template


async def test_dashboard_entities_exist(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_owlet_api: dict[str, AsyncMock],
    entity_registry: er.EntityRegistry,
) -> None:
    """Every entity in the dashboard is created by the integration and enabled."""
    await setup_integration(hass, mock_config_entry)

    text = DASHBOARD.read_text()
    referenced = set(_entity_ids(load_yaml_dict(DASHBOARD)))
    referenced |= set(re.findall(r"states\('([^']+)'\)", text))
    registered = _registered(entity_registry)
    for entity_id in referenced - OPTIONAL:
        entry = registered.get(entity_id)
        assert entry is not None, f"{entity_id} does not exist"
        assert not entry.disabled, f"{entity_id} is disabled by default"


@pytest.mark.parametrize("properties_fixture", ["update_properties_v2.json"])
async def test_dashboard_optional_entities_exist(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_owlet_api: dict[str, AsyncMock],
    entity_registry: er.EntityRegistry,
) -> None:
    """The optional entities exist on a sock that reports them."""
    await setup_integration(hass, mock_config_entry)

    registered = _registered(entity_registry)
    for entity_id in OPTIONAL:
        assert entity_id in registered, entity_id
