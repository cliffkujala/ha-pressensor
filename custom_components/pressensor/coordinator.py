"""Coordinator for the Pressensor integration."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

from bleak.backends.device import BLEDevice

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .client import PressensorClient, PressensorState

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)
RECONNECT_INTERVAL = timedelta(seconds=15)

type PressensorConfigEntry = ConfigEntry[PressensorCoordinator]


class PressensorCoordinator(DataUpdateCoordinator[None]):
    """Manage fetching Pressensor data and reconnection."""

    config_entry: PressensorConfigEntry

    def __init__(self, hass: HomeAssistant, entry: PressensorConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Pressensor",
            update_interval=SCAN_INTERVAL,
            config_entry=entry,
        )

        self._address: str = entry.data[CONF_ADDRESS]
        self._client: PressensorClient | None = None
        self._expected_disconnect = False

    @property
    def client(self) -> PressensorClient | None:
        """Return the BLE client."""
        return self._client

    @property
    def state(self) -> PressensorState:
        """Return the current Pressensor state."""
        if self._client:
            return self._client.state
        return PressensorState()

    @property
    def address(self) -> str:
        """Return the BLE address."""
        return self._address

    @callback
    def _on_state_update(self, state: PressensorState) -> None:
        """Handle state updates from the BLE client (runs in event loop)."""
        self.async_set_updated_data(None)

    @callback
    def _on_disconnect(self) -> None:
        """Handle unexpected disconnects."""
        if not self._expected_disconnect:
            _LOGGER.debug("Pressensor disconnected, will reconnect on next update")
            self.async_set_updated_data(None)

    async def _async_update_data(self) -> None:
        """Called periodically — reconnect if not connected."""
        if self._client and self._client.connected:
            return

        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self._address, connectable=True
        )

        if ble_device is None:
            _LOGGER.debug(
                "Pressensor %s not found by bluetooth stack", self._address
            )
            return

        if self._client is None:
            self._client = PressensorClient(
                ble_device=ble_device,
                state_callback=lambda state: self.hass.loop.call_soon_threadsafe(
                    self._on_state_update, state
                ),
                disconnect_callback=lambda: self.hass.loop.call_soon_threadsafe(
                    self._on_disconnect
                ),
            )
        else:
            self._client.set_ble_device(ble_device)

        await self._client.connect()

    async def async_shutdown(self) -> None:
        """Clean up on shutdown."""
        self._expected_disconnect = True
        if self._client:
            await self._client.disconnect()
        await super().async_shutdown()
