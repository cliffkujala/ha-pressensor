"""Tests for the Pressensor coordinator."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util.dt import utcnow
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pressensor.client import PressensorState
from custom_components.pressensor.const import DOMAIN
from custom_components.pressensor.coordinator import (
    BATTERY_CHECK_INTERVAL,
    PressensorCoordinator,
)

MOCK_ADDRESS = "AA:BB:CC:DD:EE:FF"
MOCK_NAME = "PRS12345"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable custom integrations for all tests."""


@pytest.fixture
def mock_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a mock config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=MOCK_NAME,
        data={CONF_ADDRESS: MOCK_ADDRESS},
        unique_id="aa:bb:cc:dd:ee:ff",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_ble_device() -> MagicMock:
    """Create a mock BLE device."""
    device = MagicMock()
    device.address = MOCK_ADDRESS
    device.name = MOCK_NAME
    return device


@pytest.fixture
def coordinator(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> PressensorCoordinator:
    """Create a coordinator instance without calling async_setup."""
    return PressensorCoordinator(hass, mock_config_entry)


class TestCoordinatorProperties:
    """Test coordinator properties."""

    def test_state_without_client(self, coordinator: PressensorCoordinator) -> None:
        """Test state returns empty PressensorState when no client."""
        state = coordinator.state
        assert state.pressure_mbar == 0.0
        assert state.connected is False

    def test_state_with_client(self, coordinator: PressensorCoordinator) -> None:
        """Test state returns client state when client exists."""
        mock_client = MagicMock()
        mock_client.state = PressensorState(pressure_mbar=1050.0, connected=True)
        coordinator._client = mock_client

        assert coordinator.state.pressure_mbar == 1050.0
        assert coordinator.state.connected is True

    def test_client_property(self, coordinator: PressensorCoordinator) -> None:
        """Test client property returns None initially."""
        assert coordinator.client is None

    def test_address_property(self, coordinator: PressensorCoordinator) -> None:
        """Test address property returns configured address."""
        assert coordinator.address == MOCK_ADDRESS


class TestCoordinatorCallbacks:
    """Test coordinator callback methods."""

    def test_on_state_update_logs_connected(
        self, coordinator: PressensorCoordinator
    ) -> None:
        """Test _on_state_update logs info on first connection."""
        assert coordinator._was_available is False
        with patch.object(coordinator, "async_set_updated_data") as mock_update:
            coordinator._on_state_update(PressensorState(connected=True))

        assert coordinator._was_available is True
        mock_update.assert_called_once_with(None)

    def test_on_state_update_no_repeat_log(
        self, coordinator: PressensorCoordinator
    ) -> None:
        """Test _on_state_update doesn't log repeatedly when already available."""
        coordinator._was_available = True
        with patch.object(coordinator, "async_set_updated_data"):
            coordinator._on_state_update(PressensorState(connected=True))

        assert coordinator._was_available is True

    def test_on_disconnect_unexpected(self, coordinator: PressensorCoordinator) -> None:
        """Test _on_disconnect logs info when was previously available."""
        coordinator._was_available = True
        with patch.object(coordinator, "async_set_updated_data") as mock_update:
            coordinator._on_disconnect()

        assert coordinator._was_available is False
        mock_update.assert_called_once_with(None)

    def test_on_disconnect_expected(self, coordinator: PressensorCoordinator) -> None:
        """Test _on_disconnect does nothing when expected."""
        coordinator._expected_disconnect = True
        coordinator._was_available = True
        with patch.object(coordinator, "async_set_updated_data") as mock_update:
            coordinator._on_disconnect()

        assert coordinator._was_available is True
        mock_update.assert_not_called()

    def test_on_disconnect_when_not_available(
        self, coordinator: PressensorCoordinator
    ) -> None:
        """Test _on_disconnect when already unavailable doesn't log again."""
        coordinator._was_available = False
        with patch.object(coordinator, "async_set_updated_data") as mock_update:
            coordinator._on_disconnect()

        assert coordinator._was_available is False
        mock_update.assert_called_once_with(None)


class TestCoordinatorAdvertisement:
    """Test Bluetooth advertisement handling."""

    def test_on_advertisement_triggers_connect(
        self,
        coordinator: PressensorCoordinator,
    ) -> None:
        """Test advertisement triggers connection task."""
        service_info = MagicMock()
        service_info.device = MagicMock()
        change = MagicMock()

        with patch.object(
            coordinator.config_entry, "async_create_background_task"
        ) as mock_task:
            coordinator._on_bluetooth_advertisement(service_info, change)

        mock_task.assert_called_once()
        # Close the coroutine to avoid "never awaited" warning
        mock_task.call_args[0][1].close()

    def test_on_advertisement_skips_when_connecting(
        self,
        coordinator: PressensorCoordinator,
    ) -> None:
        """Test advertisement is ignored when already connecting."""
        coordinator._connecting = True
        service_info = MagicMock()
        change = MagicMock()

        with patch.object(
            coordinator.config_entry, "async_create_background_task"
        ) as mock_task:
            coordinator._on_bluetooth_advertisement(service_info, change)

        mock_task.assert_not_called()

    def test_on_advertisement_skips_when_connected(
        self,
        coordinator: PressensorCoordinator,
    ) -> None:
        """Test advertisement is ignored when already connected."""
        mock_client = MagicMock()
        mock_client.connected = True
        coordinator._client = mock_client
        service_info = MagicMock()
        change = MagicMock()

        with patch.object(
            coordinator.config_entry, "async_create_background_task"
        ) as mock_task:
            coordinator._on_bluetooth_advertisement(service_info, change)

        mock_task.assert_not_called()


class TestCoordinatorConnectFromAdvertisement:
    """Test connecting from advertisement."""

    @pytest.mark.asyncio
    async def test_connect_from_advertisement(
        self,
        coordinator: PressensorCoordinator,
        mock_ble_device: MagicMock,
    ) -> None:
        """Test _async_connect_from_advertisement creates client and connects."""
        service_info = MagicMock()
        service_info.device = mock_ble_device

        with patch(
            "custom_components.pressensor.coordinator.PressensorClient"
        ) as mock_cls:
            mock_client = mock_cls.return_value
            mock_client.connect = AsyncMock(return_value=True)
            await coordinator._async_connect_from_advertisement(service_info)

        assert coordinator._connecting is False
        mock_client.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_from_advertisement_skips_if_connecting(
        self,
        coordinator: PressensorCoordinator,
    ) -> None:
        """Test _async_connect_from_advertisement skips if already connecting."""
        coordinator._connecting = True
        service_info = MagicMock()

        with patch(
            "custom_components.pressensor.coordinator.PressensorClient"
        ) as mock_cls:
            await coordinator._async_connect_from_advertisement(service_info)

        mock_cls.assert_not_called()


class TestCoordinatorRequestConnect:
    """Test manual reconnect."""

    @pytest.mark.asyncio
    async def test_request_connect_success(
        self,
        coordinator: PressensorCoordinator,
        mock_ble_device: MagicMock,
    ) -> None:
        """Test async_request_connect succeeds when device is found."""
        with (
            patch(
                "custom_components.pressensor.coordinator.bluetooth.async_ble_device_from_address",
                return_value=mock_ble_device,
            ),
            patch(
                "custom_components.pressensor.coordinator.PressensorClient"
            ) as mock_cls,
        ):
            mock_client = mock_cls.return_value
            mock_client.connect = AsyncMock(return_value=True)
            await coordinator.async_request_connect()

        assert coordinator._connecting is False

    @pytest.mark.asyncio
    async def test_request_connect_device_not_found(
        self,
        coordinator: PressensorCoordinator,
    ) -> None:
        """Test async_request_connect raises when device not found."""
        with patch(
            "custom_components.pressensor.coordinator.bluetooth.async_ble_device_from_address",
            return_value=None,
        ):
            with pytest.raises(HomeAssistantError) as exc_info:
                await coordinator.async_request_connect()
            assert exc_info.value.translation_key == "device_not_found"

    @pytest.mark.asyncio
    async def test_request_connect_already_connected(
        self,
        coordinator: PressensorCoordinator,
    ) -> None:
        """Test async_request_connect returns when already connected."""
        mock_client = MagicMock()
        mock_client.connected = True
        coordinator._client = mock_client

        with patch(
            "custom_components.pressensor.coordinator.bluetooth.async_ble_device_from_address",
        ) as mock_addr:
            await coordinator.async_request_connect()

        mock_addr.assert_not_called()

    @pytest.mark.asyncio
    async def test_request_connect_already_connecting(
        self,
        coordinator: PressensorCoordinator,
    ) -> None:
        """Test async_request_connect returns when already connecting."""
        coordinator._connecting = True

        with patch(
            "custom_components.pressensor.coordinator.bluetooth.async_ble_device_from_address",
        ) as mock_addr:
            await coordinator.async_request_connect()

        mock_addr.assert_not_called()

    @pytest.mark.asyncio
    async def test_request_connect_failure_raises(
        self,
        coordinator: PressensorCoordinator,
        mock_ble_device: MagicMock,
    ) -> None:
        """Test async_request_connect raises HomeAssistantError on failure."""
        with (
            patch(
                "custom_components.pressensor.coordinator.bluetooth.async_ble_device_from_address",
                return_value=mock_ble_device,
            ),
            patch(
                "custom_components.pressensor.coordinator.PressensorClient"
            ) as mock_cls,
        ):
            mock_client = mock_cls.return_value
            mock_client.connect = AsyncMock(side_effect=Exception("BLE error"))
            with pytest.raises(HomeAssistantError) as exc_info:
                await coordinator.async_request_connect()
            assert exc_info.value.translation_key == "connection_failed"

        assert coordinator._connecting is False


class TestCoordinatorUpdateData:
    """Test fallback poll update."""

    @pytest.mark.asyncio
    async def test_update_data_device_found(
        self,
        coordinator: PressensorCoordinator,
        mock_ble_device: MagicMock,
    ) -> None:
        """Test _async_update_data connects when device found."""
        with (
            patch(
                "custom_components.pressensor.coordinator.bluetooth.async_ble_device_from_address",
                return_value=mock_ble_device,
            ),
            patch(
                "custom_components.pressensor.coordinator.PressensorClient"
            ) as mock_cls,
        ):
            mock_client = mock_cls.return_value
            mock_client.connect = AsyncMock(return_value=True)
            await coordinator._async_update_data()

        mock_client.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_data_device_not_found(
        self,
        coordinator: PressensorCoordinator,
    ) -> None:
        """Test _async_update_data does nothing when device not found."""
        with patch(
            "custom_components.pressensor.coordinator.bluetooth.async_ble_device_from_address",
            return_value=None,
        ):
            await coordinator._async_update_data()

        assert coordinator._client is None

    @pytest.mark.asyncio
    async def test_update_data_already_connected(
        self,
        coordinator: PressensorCoordinator,
    ) -> None:
        """Test _async_update_data skips when already connected."""
        mock_client = MagicMock()
        mock_client.connected = True
        coordinator._client = mock_client

        with patch(
            "custom_components.pressensor.coordinator.bluetooth.async_ble_device_from_address",
        ) as mock_addr:
            await coordinator._async_update_data()

        mock_addr.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_data_already_connecting(
        self,
        coordinator: PressensorCoordinator,
    ) -> None:
        """Test _async_update_data skips when already connecting."""
        coordinator._connecting = True

        with patch(
            "custom_components.pressensor.coordinator.bluetooth.async_ble_device_from_address",
        ) as mock_addr:
            await coordinator._async_update_data()

        mock_addr.assert_not_called()


class TestCoordinatorBatteryCheck:
    """Test periodic battery check."""

    @pytest.mark.asyncio
    async def test_battery_check_skip_recent(
        self,
        coordinator: PressensorCoordinator,
    ) -> None:
        """Test battery check skips if checked recently."""
        coordinator._last_battery_check = utcnow()

        await coordinator._async_battery_check(utcnow())

    @pytest.mark.asyncio
    async def test_battery_check_while_connected(
        self,
        coordinator: PressensorCoordinator,
    ) -> None:
        """Test battery check reads battery when already connected."""
        mock_client = MagicMock()
        mock_client.connected = True
        mock_client.read_battery = AsyncMock()
        coordinator._client = mock_client
        coordinator._last_battery_check = None

        with patch.object(coordinator, "async_set_updated_data"):
            await coordinator._async_battery_check(utcnow())

        mock_client.read_battery.assert_called_once()
        assert coordinator._last_battery_check is not None

    @pytest.mark.asyncio
    async def test_battery_check_while_connected_failure(
        self,
        coordinator: PressensorCoordinator,
    ) -> None:
        """Test battery check handles read failure when connected."""
        mock_client = MagicMock()
        mock_client.connected = True
        mock_client.read_battery = AsyncMock(side_effect=Exception("read error"))
        coordinator._client = mock_client
        coordinator._last_battery_check = None

        await coordinator._async_battery_check(utcnow())

    @pytest.mark.asyncio
    async def test_battery_check_not_connected_device_found(
        self,
        coordinator: PressensorCoordinator,
        mock_ble_device: MagicMock,
    ) -> None:
        """Test battery check connects when device available."""
        coordinator._last_battery_check = None

        with (
            patch(
                "custom_components.pressensor.coordinator.bluetooth.async_ble_device_from_address",
                return_value=mock_ble_device,
            ),
            patch(
                "custom_components.pressensor.coordinator.PressensorClient"
            ) as mock_cls,
            patch.object(coordinator, "async_set_updated_data"),
        ):
            mock_client = mock_cls.return_value
            mock_client.connect = AsyncMock(return_value=True)
            await coordinator._async_battery_check(utcnow())

        mock_client.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_battery_check_device_not_found(
        self,
        coordinator: PressensorCoordinator,
    ) -> None:
        """Test battery check warns when device not found."""
        coordinator._last_battery_check = None

        with patch(
            "custom_components.pressensor.coordinator.bluetooth.async_ble_device_from_address",
            return_value=None,
        ):
            await coordinator._async_battery_check(utcnow())

    @pytest.mark.asyncio
    async def test_battery_check_connection_failure(
        self,
        coordinator: PressensorCoordinator,
        mock_ble_device: MagicMock,
    ) -> None:
        """Test battery check handles connection failure."""
        coordinator._last_battery_check = None

        with (
            patch(
                "custom_components.pressensor.coordinator.bluetooth.async_ble_device_from_address",
                return_value=mock_ble_device,
            ),
            patch(
                "custom_components.pressensor.coordinator.PressensorClient"
            ) as mock_cls,
        ):
            mock_client = mock_cls.return_value
            mock_client.connect = AsyncMock(side_effect=Exception("BLE error"))
            await coordinator._async_battery_check(utcnow())


class TestCoordinatorShutdown:
    """Test coordinator shutdown."""

    @pytest.mark.asyncio
    async def test_shutdown_with_client(
        self,
        coordinator: PressensorCoordinator,
    ) -> None:
        """Test shutdown disconnects client and cancels callbacks."""
        cancel_bt = MagicMock()
        cancel_battery = MagicMock()
        mock_client = MagicMock()
        mock_client.disconnect = AsyncMock()

        coordinator._cancel_bluetooth_callback = cancel_bt
        coordinator._cancel_battery_check = cancel_battery
        coordinator._client = mock_client

        await coordinator.async_shutdown()

        assert coordinator._expected_disconnect is True
        cancel_bt.assert_called_once()
        cancel_battery.assert_called_once()
        mock_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_without_client(
        self,
        coordinator: PressensorCoordinator,
    ) -> None:
        """Test shutdown works when no client or callbacks."""
        await coordinator.async_shutdown()

        assert coordinator._expected_disconnect is True


class TestCoordinatorEnsureConnected:
    """Test _async_ensure_connected."""

    @pytest.mark.asyncio
    async def test_ensure_connected_creates_client(
        self,
        coordinator: PressensorCoordinator,
        mock_ble_device: MagicMock,
    ) -> None:
        """Test _async_ensure_connected creates new client on first call."""
        with patch(
            "custom_components.pressensor.coordinator.PressensorClient"
        ) as mock_cls:
            mock_client = mock_cls.return_value
            mock_client.connect = AsyncMock(return_value=True)
            await coordinator._async_ensure_connected(mock_ble_device)

        mock_cls.assert_called_once()
        mock_client.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_connected_reuses_client(
        self,
        coordinator: PressensorCoordinator,
        mock_ble_device: MagicMock,
    ) -> None:
        """Test _async_ensure_connected reuses existing client."""
        existing_client = MagicMock()
        existing_client.connect = AsyncMock(return_value=True)
        existing_client.set_ble_device = MagicMock()
        coordinator._client = existing_client

        await coordinator._async_ensure_connected(mock_ble_device)

        existing_client.set_ble_device.assert_called_once_with(mock_ble_device)
        existing_client.connect.assert_called_once()
