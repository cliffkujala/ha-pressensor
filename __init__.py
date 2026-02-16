"""The Pressensor integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import PressensorConfigEntry, PressensorCoordinator

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: PressensorConfigEntry) -> bool:
    """Set up Pressensor from a config entry."""
    coordinator = PressensorCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: PressensorConfigEntry
) -> bool:
    """Unload a Pressensor config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator: PressensorCoordinator = entry.runtime_data
        await coordinator.async_shutdown()

    return unload_ok
