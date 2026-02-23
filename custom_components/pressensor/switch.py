"""Switch platform for Pressensor."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import (
    CONNECTION_BLUETOOTH,
    DeviceInfo,
    format_mac,
)

try:
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
except ImportError:
    from homeassistant.helpers.entity_platform import (
        AddEntitiesCallback as AddConfigEntryEntitiesCallback,
    )

from .const import DOMAIN
from .coordinator import PressensorConfigEntry, PressensorCoordinator

PARALLEL_UPDATES = 0

CONNECTION_SWITCH = SwitchEntityDescription(
    key="connection_enabled",
    translation_key="connection_enabled",
    entity_category=EntityCategory.CONFIG,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PressensorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Pressensor switches."""
    coordinator = entry.runtime_data
    async_add_entities([PressensorConnectionSwitch(coordinator, CONNECTION_SWITCH)])


class PressensorConnectionSwitch(SwitchEntity):
    """Switch to enable or disable the BLE connection.

    When turned off, HA disconnects from the Pressensor and stops listening
    for advertisements, freeing the BLE link for other apps.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PressensorCoordinator,
        entity_description: SwitchEntityDescription,
    ) -> None:
        """Initialize the switch."""
        self.coordinator = coordinator
        self.entity_description = entity_description

        formatted_mac = format_mac(coordinator.address)
        self._attr_unique_id = f"{formatted_mac}_{entity_description.key}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, formatted_mac)},
            name=coordinator.config_entry.title,
            manufacturer="Pressensor",
            model="PRS Pressure Transducer",
            connections={(CONNECTION_BLUETOOTH, coordinator.address)},
        )

    @property
    def is_on(self) -> bool:
        """Return true if the BLE connection is enabled."""
        return self.coordinator.connection_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the BLE connection."""
        await self.coordinator.async_set_connection_enabled(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the BLE connection."""
        await self.coordinator.async_set_connection_enabled(False)
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Always available — can be toggled regardless of connection state."""
        return True
