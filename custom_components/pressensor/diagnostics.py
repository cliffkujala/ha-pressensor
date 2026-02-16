"""Diagnostics support for Pressensor."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant

from .coordinator import PressensorConfigEntry

TO_REDACT = {CONF_ADDRESS}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: PressensorConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data

    return {
        "config_entry": async_redact_data(dict(entry.data), TO_REDACT),
        "state": asdict(coordinator.state),
        "connection": {
            "connecting": coordinator._connecting,
            "was_available": coordinator._was_available,
            "last_battery_check": (
                coordinator._last_battery_check.isoformat()
                if coordinator._last_battery_check
                else None
            ),
        },
    }
