"""Config flow for Owlet Smart Sock integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from aiohttp import ClientError
from pyowletapi.api import OwletAPI
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from . import OwletConfigEntry
from .compat import (
    HAS_SPECIFIC_CREDENTIAL_ERRORS,
    OWLET_CREDENTIAL_ERRORS,
    OwletConnectionError,
    OwletDevicesError,
    OwletEmailError,
    OwletPasswordError,
)
from .const import (
    CONF_STALE_THRESHOLD,
    DEFAULT_STALE_THRESHOLD,
    DOMAIN,
    MIN_POLLING_INTERVAL,
    POLLING_INTERVAL,
    REGIONS,
)

_LOGGER = logging.getLogger(__name__)

REGION_SELECTOR = selector.SelectSelector(
    selector.SelectSelectorConfig(
        options=REGIONS,
        translation_key="region",
        mode=selector.SelectSelectorMode.DROPDOWN,
    )
)
PASSWORD_SELECTOR = selector.TextSelector(
    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_REGION): REGION_SELECTOR,
        vol.Required(CONF_USERNAME): selector.TextSelector(
            selector.TextSelectorConfig(
                type=selector.TextSelectorType.EMAIL, autocomplete="username"
            )
        ),
        vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR,
    }
)


async def _async_login(
    hass: HomeAssistant, region: str, username: str, password: str
) -> tuple[dict[str, Any], dict[str, str]]:
    """Log in to the Owlet cloud and return the tokens and any form errors."""
    owlet_api = OwletAPI(
        region=region,
        user=username,
        password=password,
        session=async_get_clientsession(hass),
    )
    errors: dict[str, str] = {}
    try:
        await owlet_api.authenticate()
        await owlet_api.validate_authentication()
    except OwletDevicesError:
        errors["base"] = "no_devices"
    except OWLET_CREDENTIAL_ERRORS as err:
        errors.update(_credential_error(err))
    except (OwletConnectionError, ClientError, TimeoutError):
        errors["base"] = "cannot_connect"
    except Exception:
        _LOGGER.exception("Unexpected exception while logging in to Owlet")
        errors["base"] = "unknown"
    return owlet_api.tokens, errors


def _credential_error(err: Exception) -> dict[str, str]:
    """Map a login failure to the matching form field.

    Newer pyowletapi releases no longer tell an unknown email apart from a wrong
    password, in that case only a generic error can be shown.
    """
    if HAS_SPECIFIC_CREDENTIAL_ERRORS:
        if isinstance(err, OwletEmailError):
            return {CONF_USERNAME: "invalid_email"}
        if isinstance(err, OwletPasswordError):
            return {CONF_PASSWORD: "invalid_password"}
    return {"base": "invalid_credentials"}


class OwletConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Owlet Smart Sock."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            await self.async_set_unique_id(username.lower())
            self._abort_if_unique_id_configured()

            tokens, errors = await _async_login(
                self.hass,
                user_input[CONF_REGION],
                username,
                user_input[CONF_PASSWORD],
            )
            if not errors:
                return self.async_create_entry(
                    title=username,
                    data={
                        CONF_REGION: user_input[CONF_REGION],
                        CONF_USERNAME: username,
                        **tokens,
                    },
                    options={
                        CONF_SCAN_INTERVAL: POLLING_INTERVAL,
                        CONF_STALE_THRESHOLD: DEFAULT_STALE_THRESHOLD,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA, user_input
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle a reauthentication request."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask the user for a new password."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            tokens, errors = await _async_login(
                self.hass,
                entry.data[CONF_REGION],
                entry.data[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )
            if not errors:
                return self.async_update_reload_and_abort(entry, data_updates=tokens)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR}),
            description_placeholders={CONF_USERNAME: entry.data[CONF_USERNAME]},
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the region or log in again without removing the entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            tokens, errors = await _async_login(
                self.hass,
                user_input[CONF_REGION],
                entry.data[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )
            if not errors:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={CONF_REGION: user_input[CONF_REGION], **tokens},
                )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_REGION, default=entry.data[CONF_REGION]
                ): REGION_SELECTOR,
                vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR,
            }
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            description_placeholders={CONF_USERNAME: entry.data[CONF_USERNAME]},
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: OwletConfigEntry) -> OwletOptionsFlow:
        """Get the options flow for this handler."""
        return OwletOptionsFlow()


class OwletOptionsFlow(OptionsFlowWithReload):
    """Handle the Owlet options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the polling and staleness options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=options.get(CONF_SCAN_INTERVAL, POLLING_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=MIN_POLLING_INTERVAL)),
                vol.Required(
                    CONF_STALE_THRESHOLD,
                    default=options.get(CONF_STALE_THRESHOLD, DEFAULT_STALE_THRESHOLD),
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=120)),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
