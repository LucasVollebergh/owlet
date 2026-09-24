"""Validate the bundled dashboards."""

from __future__ import annotations

from collections.abc import Iterator
import json
from pathlib import Path
import re
from typing import Any
from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.owlet.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify
from homeassistant.util.yaml import load_yaml_dict

from .conftest import FRESH_TIME
from .helpers import setup_integration

pytestmark = pytest.mark.freeze_time(FRESH_TIME)

ROOT = Path(__file__).parents[1]
DASHBOARD_DIR = ROOT / "dashboards"
TRANSLATIONS = ROOT / "custom_components" / "owlet" / "translations"
# Dashboard file and the language its entity ids are generated in.
DASHBOARDS = {"owlet.yaml": "en", "owlet_nl.yaml": "nl"}
ENTITY_ID = re.compile(r"^(sensor|binary_sensor|switch)\.[a-z0-9_]+$")
TEMPLATE_ENTITY_ID = re.compile(r"states\('([^']+)'\)")
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


def _referenced(name: str) -> set[str]:
    """Return every entity id in a dashboard, including those in templates."""
    path = DASHBOARD_DIR / name
    return set(_entity_ids(load_yaml_dict(path))) | set(
        TEMPLATE_ENTITY_ID.findall(path.read_text())
    )


def _to_english(entity_id: str, language: str) -> str:
    """Translate an entity id generated in another language to the English one."""
    if language == "en":
        return entity_id
    names = {
        lang: json.loads((TRANSLATIONS / f"{lang}.json").read_text())["entity"]
        for lang in ("en", language)
    }
    platform, object_id = entity_id.split(".", 1)
    suffix = object_id.removeprefix(f"{PLACEHOLDER}_")
    for key, entity in names[language][platform].items():
        if slugify(entity["name"]) == suffix:
            english = slugify(names["en"][platform][key]["name"])
            return f"{platform}.{PLACEHOLDER}_{english}"
    raise AssertionError(f"{entity_id} matches no {language} entity name")


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


def test_all_dashboards_covered() -> None:
    """Every dashboard file is validated."""
    assert {path.name for path in DASHBOARD_DIR.glob("*.yaml")} == set(DASHBOARDS)


@pytest.mark.parametrize("name", DASHBOARDS)
def test_dashboard_uses_placeholder(name: str) -> None:
    """Every entity id uses the documented placeholder prefix."""
    referenced = _referenced(name)
    assert referenced
    for entity_id in referenced:
        assert entity_id.split(".", 1)[1].startswith(f"{PLACEHOLDER}_"), entity_id


@pytest.mark.parametrize("name", DASHBOARDS)
async def test_dashboard_entities_exist(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_owlet_api: dict[str, AsyncMock],
    entity_registry: er.EntityRegistry,
    name: str,
) -> None:
    """Every entity in the dashboard is created by the integration and enabled."""
    await setup_integration(hass, mock_config_entry)

    registered = _registered(entity_registry)
    for entity_id in _referenced(name):
        english = _to_english(entity_id, DASHBOARDS[name])
        if english in OPTIONAL:
            continue
        entry = registered.get(english)
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
