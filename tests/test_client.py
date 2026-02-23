"""Tests for the Pressensor BLE client."""

from __future__ import annotations

import struct
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bleak import BleakClient
from bleak.backends.service import BleakGATTCharacteristic

from custom_components.pressensor.client import PressensorClient, PressensorState
from custom_components.pressensor.const import (
    BATTERY_CHARACTERISTIC_UUID,
    PRESSURE_CHARACTERISTIC_UUID,
    ZERO_PRESSURE_CHARACTERISTIC_UUID,
)


@pytest.fixture
def mock_ble_device() -> MagicMock:
    """Create a mock BLE device."""
    device = MagicMock()
    device.address = "AA:BB:CC:DD:EE:FF"
    device.name = "PRS12345"
    return device


@pytest.fixture
def mock_bleak_client() -> AsyncMock:
    """Create a mock BleakClient."""
    client = AsyncMock(spec=BleakClient)
    client.is_connected = True
    client.start_notify = AsyncMock()
    client.stop_notify = AsyncMock()
    client.disconnect = AsyncMock()
    client.read_gatt_char = AsyncMock(return_value=bytearray([85]))
    client.write_gatt_char = AsyncMock()
    return client


@pytest.fixture
def state_callback() -> MagicMock:
    """Create a mock state callback."""
    return MagicMock()


@pytest.fixture
def disconnect_callback() -> MagicMock:
    """Create a mock disconnect callback."""
    return MagicMock()


@pytest.fixture
def client(
    mock_ble_device: MagicMock,
    state_callback: MagicMock,
    disconnect_callback: MagicMock,
) -> PressensorClient:
    """Create a PressensorClient instance."""
    return PressensorClient(
        ble_device=mock_ble_device,
        state_callback=state_callback,
        disconnect_callback=disconnect_callback,
    )


class TestPressensorClientProperties:
    """Test PressensorClient properties."""

    def test_initial_state(self, client: PressensorClient) -> None:
        """Test initial state is disconnected with no data."""
        state = client.state
        assert state.pressure_mbar == 0.0
        assert state.temperature_c is None
        assert state.battery_percent is None
        assert state.connected is False

    def test_connected_false_when_no_bleak_client(
        self, client: PressensorClient
    ) -> None:
        """Test connected returns False when no BleakClient exists."""
        assert client.connected is False

    def test_set_ble_device(
        self, client: PressensorClient, mock_ble_device: MagicMock
    ) -> None:
        """Test updating the BLE device reference."""
        new_device = MagicMock()
        new_device.address = "11:22:33:44:55:66"
        client.set_ble_device(new_device)
        assert client._ble_device is new_device


class TestPressensorClientConnect:
    """Test PressensorClient connect/disconnect."""

    @pytest.mark.asyncio
    async def test_connect_success(
        self,
        client: PressensorClient,
        mock_bleak_client: AsyncMock,
        state_callback: MagicMock,
    ) -> None:
        """Test successful connection."""
        with patch(
            "custom_components.pressensor.client.establish_connection",
            return_value=mock_bleak_client,
        ):
            result = await client.connect()

        assert result is True
        assert client.connected is True
        assert client.state.connected is True
        assert client.state.battery_percent == 85
        mock_bleak_client.start_notify.assert_called_once_with(
            PRESSURE_CHARACTERISTIC_UUID,
            client._on_pressure_notification,
        )
        state_callback.assert_called()

    @pytest.mark.asyncio
    async def test_connect_failure(
        self,
        client: PressensorClient,
        state_callback: MagicMock,
    ) -> None:
        """Test failed connection."""
        with patch(
            "custom_components.pressensor.client.establish_connection",
            side_effect=Exception("Connection failed"),
        ):
            result = await client.connect()

        assert result is False
        assert client.state.connected is False
        state_callback.assert_called()

    @pytest.mark.asyncio
    async def test_disconnect(
        self,
        client: PressensorClient,
        mock_bleak_client: AsyncMock,
        state_callback: MagicMock,
    ) -> None:
        """Test disconnection."""
        with patch(
            "custom_components.pressensor.client.establish_connection",
            return_value=mock_bleak_client,
        ):
            await client.connect()

        state_callback.reset_mock()
        await client.disconnect()

        assert client.state.connected is False
        mock_bleak_client.stop_notify.assert_called_once_with(
            PRESSURE_CHARACTERISTIC_UUID
        )
        mock_bleak_client.disconnect.assert_called_once()
        state_callback.assert_called()

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(
        self,
        client: PressensorClient,
    ) -> None:
        """Test disconnect when not connected does not raise."""
        await client.disconnect()
        assert client.state.connected is False

    @pytest.mark.asyncio
    async def test_disconnect_stop_notify_error(
        self,
        client: PressensorClient,
        mock_bleak_client: AsyncMock,
    ) -> None:
        """Test disconnect handles stop_notify errors gracefully."""
        mock_bleak_client.stop_notify.side_effect = Exception("error")
        with patch(
            "custom_components.pressensor.client.establish_connection",
            return_value=mock_bleak_client,
        ):
            await client.connect()

        await client.disconnect()
        assert client.state.connected is False

    @pytest.mark.asyncio
    async def test_disconnect_error(
        self,
        client: PressensorClient,
        mock_bleak_client: AsyncMock,
    ) -> None:
        """Test disconnect handles disconnect errors gracefully."""
        mock_bleak_client.disconnect.side_effect = Exception("error")
        with patch(
            "custom_components.pressensor.client.establish_connection",
            return_value=mock_bleak_client,
        ):
            await client.connect()

        await client.disconnect()
        assert client.state.connected is False


class TestPressensorClientBattery:
    """Test battery reading."""

    @pytest.mark.asyncio
    async def test_read_battery(
        self,
        client: PressensorClient,
        mock_bleak_client: AsyncMock,
        state_callback: MagicMock,
    ) -> None:
        """Test reading battery level."""
        with patch(
            "custom_components.pressensor.client.establish_connection",
            return_value=mock_bleak_client,
        ):
            await client.connect()

        state_callback.reset_mock()
        mock_bleak_client.read_gatt_char.return_value = bytearray([72])
        await client.read_battery()

        assert client.state.battery_percent == 72
        state_callback.assert_called()

    @pytest.mark.asyncio
    async def test_read_battery_not_connected(
        self,
        client: PressensorClient,
    ) -> None:
        """Test reading battery when not connected logs warning."""
        await client.read_battery()
        assert client.state.battery_percent is None


class TestPressensorClientZeroPressure:
    """Test zero pressure command."""

    @pytest.mark.asyncio
    async def test_zero_pressure_success(
        self,
        client: PressensorClient,
        mock_bleak_client: AsyncMock,
    ) -> None:
        """Test sending zero pressure command."""
        with patch(
            "custom_components.pressensor.client.establish_connection",
            return_value=mock_bleak_client,
        ):
            await client.connect()

        await client.zero_pressure()

        mock_bleak_client.write_gatt_char.assert_called_once_with(
            ZERO_PRESSURE_CHARACTERISTIC_UUID,
            bytearray([0x00]),
            response=True,
        )

    @pytest.mark.asyncio
    async def test_zero_pressure_not_connected(
        self,
        client: PressensorClient,
    ) -> None:
        """Test zero pressure when not connected logs warning."""
        await client.zero_pressure()

    @pytest.mark.asyncio
    async def test_zero_pressure_failure(
        self,
        client: PressensorClient,
        mock_bleak_client: AsyncMock,
    ) -> None:
        """Test zero pressure command failure is handled."""
        mock_bleak_client.write_gatt_char.side_effect = Exception("write failed")
        with patch(
            "custom_components.pressensor.client.establish_connection",
            return_value=mock_bleak_client,
        ):
            await client.connect()

        await client.zero_pressure()


class TestPressensorClientNotifications:
    """Test pressure notification handling."""

    def test_pressure_only_notification(
        self,
        client: PressensorClient,
        state_callback: MagicMock,
    ) -> None:
        """Test notification with pressure data only (2 bytes)."""
        data = struct.pack(">h", 1050)
        characteristic = MagicMock(spec=BleakGATTCharacteristic)

        client._on_pressure_notification(characteristic, bytearray(data))

        assert client.state.pressure_mbar == 1050.0
        assert client.state.temperature_c is None
        assert client.state.connected is True
        state_callback.assert_called()

    def test_pressure_and_temperature_notification(
        self,
        client: PressensorClient,
        state_callback: MagicMock,
    ) -> None:
        """Test notification with pressure + temperature data (4 bytes)."""
        data = struct.pack(">hh", 1050, 935)
        characteristic = MagicMock(spec=BleakGATTCharacteristic)

        client._on_pressure_notification(characteristic, bytearray(data))

        assert client.state.pressure_mbar == 1050.0
        assert client.state.temperature_c == 93.5
        state_callback.assert_called()

    def test_negative_pressure(
        self,
        client: PressensorClient,
    ) -> None:
        """Test notification with negative pressure value."""
        data = struct.pack(">h", -50)
        characteristic = MagicMock(spec=BleakGATTCharacteristic)

        client._on_pressure_notification(characteristic, bytearray(data))

        assert client.state.pressure_mbar == -50.0

    def test_rounding_and_deadband_filters_noise(
        self,
        client: PressensorClient,
    ) -> None:
        """Test that rounding to 10 mbar + dead-band suppresses noise."""
        characteristic = MagicMock(spec=BleakGATTCharacteristic)

        # First reading of 1000 mbar exceeds dead-band from initial 0
        data = struct.pack(">h", 1000)
        client._on_pressure_notification(characteristic, bytearray(data))
        assert client.state.pressure_mbar == 1000.0

        # 1004 rounds to 1000 — same as last, filtered by dead-band
        data = struct.pack(">h", 1004)
        client._on_pressure_notification(characteristic, bytearray(data))
        assert client.state.pressure_mbar == 1000.0

        # 1005 rounds to 1000 (banker's rounding) — still filtered
        data = struct.pack(">h", 1005)
        client._on_pressure_notification(characteristic, bytearray(data))
        assert client.state.pressure_mbar == 1000.0

        # 1006 rounds to 1010 — only 10 mbar change, NOT > 10, still filtered
        data = struct.pack(">h", 1006)
        client._on_pressure_notification(characteristic, bytearray(data))
        assert client.state.pressure_mbar == 1000.0

        # 1016 rounds to 1020 — 20 mbar change from 1000, passes dead-band
        data = struct.pack(">h", 1016)
        client._on_pressure_notification(characteristic, bytearray(data))
        assert client.state.pressure_mbar == 1020.0

    def test_rounding_near_zero(
        self,
        client: PressensorClient,
    ) -> None:
        """Test that noise around zero is suppressed by rounding."""
        characteristic = MagicMock(spec=BleakGATTCharacteristic)

        # Initial state: last_reported_pressure = 0.0
        # +4 rounds to 0 — same as last, filtered
        data = struct.pack(">h", 4)
        client._on_pressure_notification(characteristic, bytearray(data))
        assert client.state.pressure_mbar == 0.0

        # -6 rounds to -10 — only 10 mbar change, NOT > 10, filtered
        data = struct.pack(">h", -6)
        client._on_pressure_notification(characteristic, bytearray(data))
        assert client.state.pressure_mbar == 0.0

        # -16 rounds to -20 — 20 mbar change from 0, passes dead-band
        data = struct.pack(">h", -16)
        client._on_pressure_notification(characteristic, bytearray(data))
        assert client.state.pressure_mbar == -20.0

        # +16 rounds to 20 — 40 mbar change from -20, passes
        data = struct.pack(">h", 16)
        client._on_pressure_notification(characteristic, bytearray(data))
        assert client.state.pressure_mbar == 20.0

    def test_short_data_ignored(
        self,
        client: PressensorClient,
    ) -> None:
        """Test notification with too-short data is ignored."""
        characteristic = MagicMock(spec=BleakGATTCharacteristic)

        client._on_pressure_notification(characteristic, bytearray([0x01]))

        assert client.state.pressure_mbar == 0.0


class TestPressensorClientDisconnectCallback:
    """Test disconnect callback handling."""

    def test_on_disconnect_callback(
        self,
        client: PressensorClient,
        state_callback: MagicMock,
        disconnect_callback: MagicMock,
    ) -> None:
        """Test disconnect callback is invoked."""
        mock_bleak = MagicMock(spec=BleakClient)
        client._on_disconnect(mock_bleak)

        assert client.state.connected is False
        state_callback.assert_called()
        disconnect_callback.assert_called_once()

    def test_on_disconnect_no_callback(
        self,
        mock_ble_device: MagicMock,
        state_callback: MagicMock,
    ) -> None:
        """Test disconnect without disconnect callback."""
        client = PressensorClient(
            ble_device=mock_ble_device,
            state_callback=state_callback,
            disconnect_callback=None,
        )
        mock_bleak = MagicMock(spec=BleakClient)
        client._on_disconnect(mock_bleak)

        assert client.state.connected is False
        state_callback.assert_called()


class TestPressensorClientNoCallbacks:
    """Test client without callbacks."""

    def test_notify_state_no_callback(
        self,
        mock_ble_device: MagicMock,
    ) -> None:
        """Test _notify_state does nothing when no callback set."""
        client = PressensorClient(ble_device=mock_ble_device)
        client._notify_state()  # Should not raise
