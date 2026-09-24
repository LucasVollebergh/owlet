"""Owlet integration coordinator class."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import TYPE_CHECKING, Any

from aiohttp import ClientError
from pyowletapi.sock import Sock

from homeassistant.const import CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .compat import OWLET_CREDENTIAL_ERRORS, OwletConnectionError, OwletError
from .const import (
    CONF_STALE_THRESHOLD,
    DEFAULT_STALE_THRESHOLD,
    DOMAIN,
    FRESHNESS_PROPERTIES,
    POLLING_INTERVAL,
)

if TYPE_CHECKING:
    from . import OwletConfigEntry

_LOGGER = logging.getLogger(__name__)


class OwletCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll the Owlet cloud for the properties of a single sock."""

    config_entry: OwletConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: OwletConfigEntry, sock: Sock
    ) -> None:
        """Initialise the coordinator."""
        interval = entry.options.get(CONF_SCAN_INTERVAL) or POLLING_INTERVAL
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{sock.serial}",
            update_interval=timedelta(seconds=interval),
        )
        self.sock = sock

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the latest properties from the Owlet cloud."""
        try:
            response = await self.sock.update_properties()
        except OWLET_CREDENTIAL_ERRORS as err:
            raise ConfigEntryAuthFailed(
                f"Authentication failed for {self.config_entry.data[CONF_USERNAME]}"
            ) from err
        except (OwletConnectionError, OwletError, ClientError, TimeoutError) as err:
            raise UpdateFailed(f"Error communicating with Owlet: {err}") from err

        if tokens := response.get("tokens"):
            self.hass.config_entries.async_update_entry(
                self.config_entry, data={**self.config_entry.data, **tokens}
            )

        return self.sock.properties

    @property
    def last_updated(self) -> datetime | None:
        """Return when the Owlet cloud last received a reading from the sock."""
        raw = self.sock.raw_properties or {}
        timestamps = [
            parsed
            for key in FRESHNESS_PROPERTIES
            if key in raw
            and (parsed := dt_util.parse_datetime(str(raw[key].get("data_updated_at"))))
        ]
        return max(timestamps) if timestamps else None

    @property
    def stale_threshold(self) -> timedelta | None:
        """Return the configured staleness threshold, None when disabled."""
        minutes = self.config_entry.options.get(
            CONF_STALE_THRESHOLD, DEFAULT_STALE_THRESHOLD
        )
        return timedelta(minutes=minutes) if minutes else None

    @property
    def is_stale(self) -> bool:
        """Return True when the sock should be sending data but the cloud has none.

        Readings are not expected while the sock is charging or the base station
        is switched off, so those states never count as stale.
        """
        threshold = self.stale_threshold
        last_updated = self.last_updated
        if threshold is None or last_updated is None:
            return False
        properties = self.sock.properties
        base_station_on = properties.get("base_station_on")
        if properties.get("charging") or (
            base_station_on is not None and not base_station_on
        ):
            return False
        return dt_util.utcnow() - last_updated > threshold
