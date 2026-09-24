"""Support for Owlet binary sensors."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import OwletConfigEntry
from .coordinator import OwletCoordinator
from .entity import OwletBaseEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class OwletBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Represent the owlet binary sensor entity description."""

    available_during_charging: bool


SENSORS: tuple[OwletBinarySensorEntityDescription, ...] = (
    OwletBinarySensorEntityDescription(
        key="charging",
        translation_key="charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        available_during_charging=True,
    ),
    OwletBinarySensorEntityDescription(
        key="high_heart_rate_alert",
        translation_key="high_hr_alrt",
        device_class=BinarySensorDeviceClass.SOUND,
        available_during_charging=True,
    ),
    OwletBinarySensorEntityDescription(
        key="low_heart_rate_alert",
        translation_key="low_hr_alrt",
        device_class=BinarySensorDeviceClass.SOUND,
        available_during_charging=True,
    ),
    OwletBinarySensorEntityDescription(
        key="high_oxygen_alert",
        translation_key="high_ox_alrt",
        device_class=BinarySensorDeviceClass.SOUND,
        available_during_charging=True,
    ),
    OwletBinarySensorEntityDescription(
        key="low_oxygen_alert",
        translation_key="low_ox_alrt",
        device_class=BinarySensorDeviceClass.SOUND,
        available_during_charging=True,
    ),
    OwletBinarySensorEntityDescription(
        key="critical_oxygen_alert",
        translation_key="crit_ox_alrt",
        device_class=BinarySensorDeviceClass.SOUND,
        available_during_charging=True,
    ),
    OwletBinarySensorEntityDescription(
        key="low_battery_alert",
        translation_key="low_batt_alrt",
        device_class=BinarySensorDeviceClass.SOUND,
        available_during_charging=True,
    ),
    OwletBinarySensorEntityDescription(
        key="critical_battery_alert",
        translation_key="crit_batt_alrt",
        device_class=BinarySensorDeviceClass.SOUND,
        available_during_charging=True,
    ),
    OwletBinarySensorEntityDescription(
        key="lost_power_alert",
        translation_key="lost_pwr_alrt",
        device_class=BinarySensorDeviceClass.SOUND,
        available_during_charging=True,
    ),
    OwletBinarySensorEntityDescription(
        key="sock_disconnected",
        translation_key="sock_discon_alrt",
        device_class=BinarySensorDeviceClass.SOUND,
        available_during_charging=True,
    ),
    OwletBinarySensorEntityDescription(
        key="sock_off",
        translation_key="sock_off",
        device_class=BinarySensorDeviceClass.POWER,
        available_during_charging=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: OwletConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the owlet binary sensors from config entry."""
    sensors: list[BinarySensorEntity] = []

    for coordinator in config_entry.runtime_data.values():
        properties = coordinator.sock.properties
        sensors.extend(
            OwletBinarySensor(coordinator, description)
            for description in SENSORS
            if description.key in properties
        )
        if OwletAwakeSensor.entity_description.key in properties:
            sensors.append(OwletAwakeSensor(coordinator))
        sensors.append(OwletStaleSensor(coordinator))

    async_add_entities(sensors)


class OwletBinarySensor(OwletBaseEntity, BinarySensorEntity):
    """Representation of an Owlet binary sensor."""

    def __init__(
        self,
        coordinator: OwletCoordinator,
        description: OwletBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{self.sock.serial}-{description.key}"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available:
            return False
        if self.entity_description.available_during_charging:
            return True
        return (
            not self.sock.properties.get("charging") and not self.coordinator.is_stale
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        value = self.sock.properties.get(self.entity_description.key)
        return None if value is None else bool(value)


class OwletAwakeSensor(OwletBinarySensor):
    """Representation of the Owlet awake sensor."""

    entity_description = OwletBinarySensorEntityDescription(
        key="sleep_state",
        translation_key="awake",
        available_during_charging=False,
    )

    def __init__(
        self,
        coordinator: OwletCoordinator,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, self.entity_description)

    @property
    def is_on(self) -> bool:
        """Return true if the baby is not in light or deep sleep."""
        return self.sock.properties.get(self.entity_description.key) not in (8, 15)


class OwletStaleSensor(OwletBaseEntity, BinarySensorEntity):
    """On when the Owlet cloud stopped receiving readings from the sock."""

    entity_description = BinarySensorEntityDescription(
        key="data_stale",
        translation_key="data_stale",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
    )

    def __init__(self, coordinator: OwletCoordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{self.sock.serial}-data_stale"

    @property
    def is_on(self) -> bool:
        """Return true when the latest reading is older than the threshold."""
        return self.coordinator.is_stale
