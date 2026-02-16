"""Button platform for Pressensor."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

try:
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
except ImportError:
    from homeassistant.helpers.entity_platform import (
        AddEntitiesCallback as AddConfigEntryEntitiesCallback,
    )

from .coordinator import PressensorConfigEntry, PressensorCoordinator
from .entity import PressensorEntity

PARALLEL_UPDATES = 0


ZERO_PRESSURE_BUTTON = ButtonEntityDescription(
    key="zero_pressure",
    translation_key="zero_pressure",
    name="Zero Pressure",
    icon="mdi:gauge-empty",
)

RECONNECT_BUTTON = ButtonEntityDescription(
    key="reconnect",
    translation_key="reconnect",
    name="Reconnect",
    icon="mdi:bluetooth-connect",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PressensorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Pressensor buttons."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            PressensorZeroPressureButton(coordinator, ZERO_PRESSURE_BUTTON),
            PressensorReconnectButton(coordinator, RECONNECT_BUTTON),
        ]
    )


class PressensorZeroPressureButton(PressensorEntity, ButtonEntity):
    """Button to calibrate the Pressensor pressure reading at zero."""

    async def async_press(self) -> None:
        """Handle the button press — send zero pressure command."""
        if not self.coordinator.client or not self.coordinator.client.connected:
            raise HomeAssistantError(
                "Pressensor is not connected. Wait for the device to wake up or press Reconnect."
            )
        try:
            await self.coordinator.client.zero_pressure()
        except Exception as err:
            raise HomeAssistantError("Failed to send zero pressure command") from err


class PressensorReconnectButton(PressensorEntity, ButtonEntity):
    """Button to manually trigger a BLE reconnection attempt."""

    async def async_press(self) -> None:
        """Handle the button press — request a connection attempt.

        Raises HomeAssistantError if the device is not found or connection fails.
        """
        await self.coordinator.async_request_connect()

    @property
    def available(self) -> bool:
        """Always available so it can be pressed when disconnected."""
        return True
