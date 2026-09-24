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
    VITAL_PROPERTIES_V2,
    VITALS_PROPERTY_V3,
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

    def _property_updated_at(self, raw_key: str) -> datetime | None:
        """Return the data_updated_at timestamp of a raw Ayla property."""
        prop = (self.sock.raw_properties or {}).get(raw_key)
        if not prop:
            return None
        return dt_util.parse_datetime(str(prop.get("data_updated_at")))

    @property
    def last_updated(self) -> datetime | None:
        """Return when the Owlet cloud last received a reading from the sock."""
        timestamps = [
            parsed
            for key in FRESHNESS_PROPERTIES
            if (parsed := self._property_updated_at(key))
        ]
        return max(timestamps) if timestamps else None

    def reading_updated_at(self, key: str) -> datetime | None:
        """Return when the reading behind a normalised property was last updated."""
        if (updated := self._property_updated_at(VITALS_PROPERTY_V3)) is not None:
            return updated
        if key in VITAL_PROPERTIES_V2:
            return self._property_updated_at(VITAL_PROPERTIES_V2[key])
        return self.last_updated

    @property
    def stale_threshold(self) -> timedelta | None:
        """Return the configured staleness threshold, None when disabled."""
        minutes = self.config_entry.options.get(
            CONF_STALE_THRESHOLD, DEFAULT_STALE_THRESHOLD
        )
        return timedelta(minutes=minutes) if minutes else None

    def _readings_expected(self) -> bool:
        """Return False while the sock is not supposed to send readings.

        Readings are not expected while the sock is charging or the base station
        is switched off, so those states never count as stale.
        """
        properties = self.sock.properties
        base_station_on = properties.get("base_station_on")
        return not properties.get("charging") and (
            base_station_on is None or bool(base_station_on)
        )

    def _is_old(self, updated: datetime | None) -> bool:
        """Return True when a timestamp is older than the threshold."""
        threshold = self.stale_threshold
        if threshold is None or updated is None or not self._readings_expected():
            return False
        return dt_util.utcnow() - updated > threshold

    def is_reading_stale(self, key: str) -> bool:
        """Return True when the reading behind a normalised property is stale."""
        return self._is_old(self.reading_updated_at(key))

    @property
    def is_stale(self) -> bool:
        """Return True when any live vital of the sock is stale."""
        if VITALS_PROPERTY_V3 in (self.sock.raw_properties or {}):
            return self._is_old(self._property_updated_at(VITALS_PROPERTY_V3))
        v2_keys = [
            key
            for key, raw_key in VITAL_PROPERTIES_V2.items()
            if raw_key in (self.sock.raw_properties or {})
        ]
        if v2_keys:
            return any(self.is_reading_stale(key) for key in v2_keys)
        return self._is_old(self.last_updated)
