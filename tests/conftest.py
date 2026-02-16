"""Common fixtures for Pressensor tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pressensor.client import PressensorState
from custom_components.pressensor.const import DOMAIN

MOCK_ADDRESS = "AA:BB:CC:DD:EE:FF"
MOCK_NAME = "PRS12345"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> None:
    """Enable custom integrations for all tests."""


@pytest.fixture(autouse=True)
def patch_bluetooth_deps() -> Generator[None]:
    """Prevent bluetooth_adapters from being loaded as a dependency."""
    with patch(
        "homeassistant.setup.async_process_deps_reqs",
        return_value=None,
    ):
        yield


@pytest.fixture
def mock_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a mock config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=MOCK_NAME,
        data={CONF_ADDRESS: MOCK_ADDRESS},
        unique_id="aa:bb:cc:dd:ee:ff",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Patch async_setup_entry for config flow tests."""
    with patch(
        "custom_components.pressensor.async_setup_entry",
        return_value=True,
    ) as mock:
        yield mock


@pytest.fixture
def mock_client() -> Generator[MagicMock]:
    """Patch PressensorClient with a mock."""
    with patch(
        "custom_components.pressensor.coordinator.PressensorClient",
        autospec=True,
    ) as client_cls:
        client = client_cls.return_value
        client.connected = True
        client.state = PressensorState(
            pressure_mbar=1050.0,
            temperature_c=93.5,
            battery_percent=85,
            connected=True,
        )
        client.connect = AsyncMock(return_value=True)
        client.disconnect = AsyncMock()
        client.zero_pressure = AsyncMock()
        client.read_battery = AsyncMock()
        client.set_ble_device = MagicMock()
        yield client


@pytest.fixture
def mock_ble_device() -> MagicMock:
    """Return a mock BLE device."""
    device = MagicMock()
    device.address = MOCK_ADDRESS
    device.name = MOCK_NAME
    return device


@pytest.fixture
def mock_pressensor_bluetooth(mock_ble_device: MagicMock) -> Generator[MagicMock]:
    """Patch Pressensor-specific bluetooth functions."""
    with (
        patch(
            "custom_components.pressensor.coordinator.bluetooth.async_ble_device_from_address",
            return_value=mock_ble_device,
        ) as mock_from_addr,
        patch(
            "custom_components.pressensor.coordinator.bluetooth.async_register_callback",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.pressensor.coordinator.async_track_time_interval",
            return_value=MagicMock(),
        ),
    ):
        yield mock_from_addr


@pytest.fixture
async def init_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
    mock_pressensor_bluetooth: MagicMock,
) -> MockConfigEntry:
    """Set up the Pressensor integration for testing."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    return mock_config_entry
