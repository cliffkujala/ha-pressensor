"""Bluetooth client for communicating with Pressensor devices."""

from __future__ import annotations

import asyncio
import logging
import struct
from collections.abc import Callable
from dataclasses import dataclass, field

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak.backends.service import BleakGATTCharacteristic
from bleak_retry_connector import establish_connection

from .const import (
    BATTERY_CHARACTERISTIC_UUID,
    PRESSURE_CHARACTERISTIC_UUID,
    ZERO_PRESSURE_CHARACTERISTIC_UUID,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class PressensorState:
    """Represents the current state of a Pressensor device."""

    pressure_mbar: float = 0.0
    temperature_c: float | None = None
    battery_percent: int | None = None
    connected: bool = False


class PressensorClient:
    """BLE GATT client for the Pressensor pressure transducer."""

    def __init__(
        self,
        ble_device: BLEDevice,
        state_callback: Callable[[PressensorState], None] | None = None,
        disconnect_callback: Callable[[], None] | None = None,
    ) -> None:
        """Initialize the Pressensor client."""
        self._ble_device = ble_device
        self._client: BleakClient | None = None
        self._state = PressensorState()
        self._state_callback = state_callback
        self._disconnect_callback = disconnect_callback
        self._notification_count = 0
        self._last_reported_pressure: float = 0.0

    @property
    def state(self) -> PressensorState:
        """Return the current device state."""
        return self._state

    @property
    def connected(self) -> bool:
        """Return whether the client is connected."""
        return self._client is not None and self._client.is_connected

    def set_ble_device(self, ble_device: BLEDevice) -> None:
        """Update the BLE device reference (e.g. after rediscovery)."""
        self._ble_device = ble_device

    async def connect(self) -> bool:
        """Connect to the Pressensor and subscribe to notifications."""
        try:
            self._client = await establish_connection(
                BleakClient,
                self._ble_device,
                self._ble_device.address,
                disconnected_callback=self._on_disconnect,
            )

            # Subscribe to pressure notifications
            await self._client.start_notify(
                PRESSURE_CHARACTERISTIC_UUID,
                self._on_pressure_notification,
            )

            # Read initial battery level
            await self.read_battery()

            self._state.connected = True
            self._notify_state()

            _LOGGER.debug(
                "Connected to Pressensor %s, battery: %s%%",
                self._ble_device.address,
                self._state.battery_percent,
            )
            return True

        except Exception:
            _LOGGER.exception(
                "Failed to connect to Pressensor %s", self._ble_device.address
            )
            self._state.connected = False
            self._notify_state()
            return False

    async def disconnect(self) -> None:
        """Disconnect from the device."""
        if self._client and self._client.is_connected:
            try:
                await self._client.stop_notify(PRESSURE_CHARACTERISTIC_UUID)
            except Exception:
                _LOGGER.debug("Error stopping notifications during disconnect")
            try:
                await self._client.disconnect()
            except Exception:
                _LOGGER.debug("Error during disconnect")
        self._state.connected = False
        self._notify_state()

    async def read_battery(self) -> None:
        """Read the current battery level from the device."""
        if not self._client or not self._client.is_connected:
            _LOGGER.warning("Cannot read battery: not connected")
            return

        battery_data = await self._client.read_gatt_char(BATTERY_CHARACTERISTIC_UUID)
        if battery_data and len(battery_data) >= 1:
            self._state.battery_percent = battery_data[0]
            self._notify_state()

    async def zero_pressure(self) -> None:
        """Send a zero calibration command to set the current reading as zero."""
        if not self._client or not self._client.is_connected:
            _LOGGER.warning("Cannot zero pressure: not connected")
            return

        try:
            await self._client.write_gatt_char(
                ZERO_PRESSURE_CHARACTERISTIC_UUID,
                bytearray([0x00]),
                response=True,
            )
            _LOGGER.debug("Zero pressure command sent")
        except Exception:
            _LOGGER.exception("Failed to send zero pressure command")

    def _on_pressure_notification(
        self, _characteristic: BleakGATTCharacteristic, data: bytearray
    ) -> None:
        """Handle incoming pressure notification data.

        Protocol:
        - Every notification: signed 2 bytes big-endian, pressure in millibar
        - Every 16th notification: additionally includes signed 2 bytes
          big-endian, temperature in tenths of a degree Celsius
        """
        changed = False

        if len(data) >= 2:
            # Round to nearest 10 mbar (0.01 bar) — sufficient for espresso use
            pressure_mbar = float(round(struct.unpack(">h", data[0:2])[0], -1))
            # Dead-band filter: ignore changes of ≤5 mbar to suppress sensor noise
            if abs(pressure_mbar - self._last_reported_pressure) > 5:
                self._state.pressure_mbar = pressure_mbar
                self._last_reported_pressure = pressure_mbar
                changed = True

        if len(data) >= 4:
            temp_tenths = struct.unpack(">h", data[2:4])[0]
            new_temp = temp_tenths / 10.0
            if new_temp != self._state.temperature_c:
                self._state.temperature_c = new_temp
                changed = True

        self._notification_count += 1
        if not self._state.connected:
            self._state.connected = True
            changed = True

        if changed:
            self._notify_state()

    def _on_disconnect(self, _client: BleakClient) -> None:
        """Handle device disconnection."""
        _LOGGER.debug("Pressensor %s disconnected", self._ble_device.address)
        self._state.connected = False
        self._notify_state()
        if self._disconnect_callback:
            self._disconnect_callback()

    def _notify_state(self) -> None:
        """Notify the callback of a state change."""
        if self._state_callback:
            self._state_callback(self._state)
