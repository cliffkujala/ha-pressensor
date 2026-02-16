"""Binary sensor platform for Pressensor."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import PressensorConfigEntry
from .entity import PressensorEntity

PARALLEL_UPDATES = 0

BINARY_SENSORS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="connected",
        translation_key="connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PressensorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Pressensor binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        PressensorBinarySensor(coordinator, description)
        for description in BINARY_SENSORS
    )


class PressensorBinarySensor(PressensorEntity, BinarySensorEntity):
    """Representation of Pressensor connection status."""

    @property
    def is_on(self) -> bool:
        """Return true if connected."""
        return self.coordinator.state.connected

    @property
    def available(self) -> bool:
        """Connectivity sensor is always available."""
        return True
