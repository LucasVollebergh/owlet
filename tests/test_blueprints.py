"""Validate the bundled automation blueprints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from homeassistant.components.blueprint.models import Blueprint, BlueprintInputs
from homeassistant.components.blueprint.schemas import BLUEPRINT_SCHEMA
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.trigger import async_validate_trigger_config
from homeassistant.util.yaml import load_yaml_dict

BLUEPRINT_DIR = Path(__file__).parents[1] / "blueprints" / "automation" / "owlet"

INPUTS: dict[str, dict[str, Any]] = {
    "owlet_alert_notification.yaml": {
        "alert_sensors": ["binary_sensor.owlet_low_oxygen_alert"],
        "notify_device": "abc123",
        "critical": True,
    },
    "owlet_stale_data_notification.yaml": {
        "stale_sensor": "binary_sensor.owlet_data_stale",
        "delay": 5,
        "notify_device": "abc123",
    },
}


def test_all_blueprints_covered() -> None:
    """Every blueprint file has test inputs."""
    assert {path.name for path in BLUEPRINT_DIR.glob("*.yaml")} == set(INPUTS)


@pytest.mark.parametrize(("name", "inputs"), INPUTS.items())
async def test_blueprint_is_valid(
    hass: HomeAssistant, name: str, inputs: dict[str, Any]
) -> None:
    """The blueprint passes the schema and produces a valid automation."""
    blueprint = Blueprint(
        load_yaml_dict(BLUEPRINT_DIR / name),
        expected_domain="automation",
        schema=BLUEPRINT_SCHEMA,
    )
    assert blueprint.metadata["source_url"].endswith(name)

    config = BlueprintInputs(
        blueprint, {"use_blueprint": {"path": name, "input": inputs}}
    ).async_substitute()
    await async_validate_trigger_config(hass, cv.TRIGGER_SCHEMA(config["triggers"]))
    cv.SCRIPT_SCHEMA(config["actions"])
