"""Compatibility layer for the different pyowletapi releases.

pyowletapi 2025.4.4 and later removed OwletEmailError and OwletPasswordError and
only raise OwletCredentialsError. Importing the removed names directly breaks
the config flow ("Invalid handler specified"), so fall back to the generic
credentials error when they are missing.
"""

from pyowletapi.exceptions import (
    OwletAuthenticationError,
    OwletConnectionError,
    OwletCredentialsError,
    OwletDevicesError,
    OwletError,
)

try:
    from pyowletapi.exceptions import OwletEmailError, OwletPasswordError

    HAS_SPECIFIC_CREDENTIAL_ERRORS = True
except ImportError:  # pragma: no cover - depends on installed library version
    OwletEmailError = OwletCredentialsError  # type: ignore[misc,assignment]
    OwletPasswordError = OwletCredentialsError  # type: ignore[misc,assignment]
    HAS_SPECIFIC_CREDENTIAL_ERRORS = False

OWLET_CREDENTIAL_ERRORS = (
    OwletAuthenticationError,
    OwletCredentialsError,
    OwletEmailError,
    OwletPasswordError,
)

__all__ = [
    "HAS_SPECIFIC_CREDENTIAL_ERRORS",
    "OWLET_CREDENTIAL_ERRORS",
    "OwletAuthenticationError",
    "OwletConnectionError",
    "OwletCredentialsError",
    "OwletDevicesError",
    "OwletEmailError",
    "OwletError",
    "OwletPasswordError",
]
