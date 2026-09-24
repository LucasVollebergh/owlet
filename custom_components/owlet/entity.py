"""Base class for Owlet entities."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import OwletCoordinator


class OwletBaseEntity(CoordinatorEntity[OwletCoordinator]):
    """Base class for Owlet Sock entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: OwletCoordinator) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)
        self.sock = coordinator.sock
        mac = getattr(self.sock, "mac", None)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.sock.serial)},
            name=f"Owlet Sock {self.sock.serial}",
            connections={(CONNECTION_NETWORK_MAC, mac)} if mac else set(),
            suggested_area="Nursery",
            configuration_url="https://my.owletcare.com/",
            manufacturer=MANUFACTURER,
            model=getattr(self.sock, "oem_model", None)
            or getattr(self.sock, "model", None),
            serial_number=self.sock.serial,
            sw_version=getattr(self.sock, "sw_version", None),
            hw_version=self.sock.properties.get("hardware_version"),
        )
