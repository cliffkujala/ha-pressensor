"""Button platform for Pressensor."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import PressensorConfigEntry
from .entity import PressensorEntity

PARALLEL_UPDATES = 0

BUTTONS: tuple[ButtonEntityDescription, ...] = (
    ButtonEntityDescription(
        key="zero_pressure",
        translation_key="zero_pressure",
        icon="mdi:gauge-empty",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PressensorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Pressensor buttons."""
    coordinator = entry.runtime_data
    async_add_entities(
        PressensorButton(coordinator, description) for description in BUTTONS
    )


class PressensorButton(PressensorEntity, ButtonEntity):
    """Button to zero/tare the Pressensor pressure reading."""

    async def async_press(self) -> None:
        """Handle the button press — send zero pressure command."""
        if self.coordinator.client:
            await self.coordinator.client.zero_pressure()
