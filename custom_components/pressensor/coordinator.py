"""Coordinator for the Pressensor integration."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta

from bleak.backends.device import BLEDevice

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothCallbackMatcher,
    BluetoothChange,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.dt import utcnow

from .client import PressensorClient, PressensorState
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Fallback poll interval — primary connection trigger is the advertisement callback
SCAN_INTERVAL = timedelta(seconds=300)

# How often to proactively check battery level
BATTERY_CHECK_INTERVAL = timedelta(hours=24)

type PressensorConfigEntry = ConfigEntry[PressensorCoordinator]


class PressensorCoordinator(DataUpdateCoordinator[None]):
    """Manage fetching Pressensor data via advertisement-driven connection."""

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
        self._connecting = False
        self._cancel_bluetooth_callback: Callable[[], None] | None = None
        self._cancel_battery_check: Callable[[], None] | None = None
        self._last_battery_check: datetime | None = None
        self._was_available: bool = False

    async def async_setup(self) -> None:
        """Register BLE advertisement callback and battery check timer."""
        self._cancel_bluetooth_callback = bluetooth.async_register_callback(
            self.hass,
            self._on_bluetooth_advertisement,
            BluetoothCallbackMatcher(address=self._address, connectable=True),
            BluetoothScanningMode.ACTIVE,
        )

        self._cancel_battery_check = async_track_time_interval(
            self.hass,
            self._async_battery_check,
            BATTERY_CHECK_INTERVAL,
        )

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
        if not self._was_available:
            _LOGGER.info("Pressensor %s is connected", self._address)
            self._was_available = True
        self.async_set_updated_data(None)

    @callback
    def _on_disconnect(self) -> None:
        """Handle device disconnection (likely going back to sleep)."""
        if not self._expected_disconnect:
            if self._was_available:
                _LOGGER.info(
                    "Pressensor %s disconnected, waiting for next advertisement",
                    self._address,
                )
                self._was_available = False
            self.async_set_updated_data(None)

    @callback
    def _on_bluetooth_advertisement(
        self,
        service_info: BluetoothServiceInfoBleak,
        change: BluetoothChange,
    ) -> None:
        """Handle BLE advertisement — device has woken up."""
        if self._connecting or (self._client and self._client.connected):
            return

        _LOGGER.debug("Pressensor %s advertisement detected, connecting", self._address)
        self.config_entry.async_create_background_task(
            self.hass,
            self._async_connect_from_advertisement(service_info),
            "pressensor_connect",
        )

    async def _async_connect_from_advertisement(
        self, service_info: BluetoothServiceInfoBleak
    ) -> None:
        """Connect to device after receiving an advertisement."""
        if self._connecting:
            return
        self._connecting = True
        try:
            await self._async_ensure_connected(service_info.device)
        finally:
            self._connecting = False

    async def _async_ensure_connected(self, ble_device: BLEDevice) -> None:
        """Create or update the client and connect."""
        if self._client is None:

            def _state_cb(state: PressensorState) -> None:
                self.hass.loop.call_soon_threadsafe(self._on_state_update, state)

            def _disconnect_cb() -> None:
                self.hass.loop.call_soon_threadsafe(self._on_disconnect)

            self._client = PressensorClient(
                ble_device=ble_device,
                state_callback=_state_cb,
                disconnect_callback=_disconnect_cb,
            )
        else:
            self._client.set_ble_device(ble_device)

        await self._client.connect()
        self._last_battery_check = utcnow()

    async def async_request_connect(self) -> None:
        """Manually request a connection attempt (e.g. from a button press).

        Raises HomeAssistantError if the device cannot be found or connection fails.
        """
        if self._connecting or (self._client and self._client.connected):
            return

        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self._address, connectable=True
        )

        if ble_device is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="device_not_found",
            )

        self._connecting = True
        try:
            await self._async_ensure_connected(ble_device)
        except Exception as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="connection_failed",
            ) from err
        finally:
            self._connecting = False

    async def _async_update_data(self) -> None:
        """Fallback poll — connect if advertisement callback hasn't already."""
        if self._connecting or (self._client and self._client.connected):
            return

        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self._address, connectable=True
        )

        if ble_device is None:
            _LOGGER.debug("Pressensor %s not found by bluetooth stack", self._address)
            return

        await self._async_ensure_connected(ble_device)

    async def _async_battery_check(self, _now: datetime) -> None:
        """Periodic battery check — connect briefly to read battery level."""
        # Skip if we already connected recently (battery was read on connect)
        if self._last_battery_check and (
            utcnow() - self._last_battery_check < BATTERY_CHECK_INTERVAL
        ):
            _LOGGER.debug("Skipping battery check, last check was recent")
            return

        # If already connected, just read the battery
        if self._client and self._client.connected:
            try:
                await self._client.read_battery()
                self._last_battery_check = utcnow()
                self.async_set_updated_data(None)
            except Exception:
                _LOGGER.warning("Failed to read battery while connected")
            return

        # Not connected — try to find and connect briefly
        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self._address, connectable=True
        )

        if ble_device is None:
            _LOGGER.warning(
                "Pressensor %s not reachable for daily battery check — "
                "device may have a dead battery",
                self._address,
            )
            return

        try:
            await self._async_ensure_connected(ble_device)
            self._last_battery_check = utcnow()
            self.async_set_updated_data(None)
        except Exception:
            _LOGGER.warning(
                "Failed to connect to Pressensor %s for battery check",
                self._address,
            )

    async def async_shutdown(self) -> None:
        """Clean up on shutdown."""
        self._expected_disconnect = True
        if self._cancel_bluetooth_callback:
            self._cancel_bluetooth_callback()
        if self._cancel_battery_check:
            self._cancel_battery_check()
        if self._client:
            await self._client.disconnect()
        await super().async_shutdown()
