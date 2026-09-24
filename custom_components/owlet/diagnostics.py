"""Diagnostics support for Owlet."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_API_TOKEN, CONF_USERNAME
from homeassistant.core import HomeAssistant

from . import OwletConfigEntry
from .const import CONF_OWLET_REFRESH

TO_REDACT = {
    CONF_API_TOKEN,
    CONF_OWLET_REFRESH,
    CONF_USERNAME,
    "dsn",
    "mac",
    "lan_ip",
    "device_key",
    "key",
    "serial",
    "BABY_NAME",
    "BIRTHDATE",
    "LATITUDE",
    "LONGITUDE",
    "BLE_MAC_ID",
    "LOCAL_BLE_MAC_ID",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: OwletConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    socks = []
    for index, coordinator in enumerate(entry.runtime_data.values()):
        sock = coordinator.sock
        last_updated = coordinator.last_updated
        socks.append(
            {
                "index": index,
                "version": getattr(sock, "version", None),
                "revision": getattr(sock, "revision", None),
                "model": getattr(sock, "model", None),
                "oem_model": getattr(sock, "oem_model", None),
                "sw_version": getattr(sock, "sw_version", None),
                "connection_status": getattr(sock, "connection_status", None),
                "last_update_success": coordinator.last_update_success,
                "last_updated": last_updated.isoformat() if last_updated else None,
                "is_stale": coordinator.is_stale,
                "properties": sock.properties,
                "raw_properties": async_redact_data(
                    sock.raw_properties or {}, TO_REDACT
                ),
            }
        )

    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "socks": socks,
    }
