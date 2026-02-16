"""Base entity for Pressensor."""

from __future__ import annotations

from homeassistant.helpers.device_registry import (
    CONNECTION_BLUETOOTH,
    DeviceInfo,
    format_mac,
)
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PressensorCoordinator


class PressensorEntity(CoordinatorEntity[PressensorCoordinator]):
    """Base class for Pressensor entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PressensorCoordinator,
        entity_description: EntityDescription,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
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
    def available(self) -> bool:
        """Return True if entity is available."""
        return super().available and self.coordinator.state.connected
