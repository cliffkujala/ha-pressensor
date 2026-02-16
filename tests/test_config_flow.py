"""Tests for the Pressensor config flow."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import SOURCE_BLUETOOTH, SOURCE_USER
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.pressensor.const import DOMAIN, PRESSURE_SERVICE_UUID

from .conftest import MOCK_ADDRESS, MOCK_NAME

# Fake BluetoothServiceInfoBleak for discovery tests
MOCK_SERVICE_INFO = BluetoothServiceInfoBleak(
    name=MOCK_NAME,
    address=MOCK_ADDRESS,
    rssi=-60,
    manufacturer_data={},
    service_data={},
    service_uuids=[PRESSURE_SERVICE_UUID],
    source="local",
    device=MagicMock(),
    advertisement=MagicMock(),
    connectable=True,
    time=0,
    tx_power=None,
)


async def test_user_flow_no_devices(
    hass: HomeAssistant,
    mock_setup_entry: MagicMock,
) -> None:
    """Test user flow aborts when no devices found."""
    with patch(
        "custom_components.pressensor.config_flow.async_discovered_service_info",
        return_value=[],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


async def test_user_flow_success(
    hass: HomeAssistant,
    mock_setup_entry: MagicMock,
) -> None:
    """Test successful user flow with device selection."""
    with patch(
        "custom_components.pressensor.config_flow.async_discovered_service_info",
        return_value=[MOCK_SERVICE_INFO],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with (
        patch(
            "custom_components.pressensor.config_flow.async_ble_device_from_address",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.pressensor.config_flow.async_discovered_service_info",
            return_value=[MOCK_SERVICE_INFO],
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_ADDRESS: MOCK_ADDRESS},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == MOCK_NAME
    assert result["data"] == {CONF_ADDRESS: MOCK_ADDRESS}


async def test_user_flow_cannot_connect(
    hass: HomeAssistant,
    mock_setup_entry: MagicMock,
) -> None:
    """Test user flow shows error when device not reachable."""
    with patch(
        "custom_components.pressensor.config_flow.async_discovered_service_info",
        return_value=[MOCK_SERVICE_INFO],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )

    assert result["type"] is FlowResultType.FORM

    with (
        patch(
            "custom_components.pressensor.config_flow.async_ble_device_from_address",
            return_value=None,
        ),
        patch(
            "custom_components.pressensor.config_flow.async_discovered_service_info",
            return_value=[MOCK_SERVICE_INFO],
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_ADDRESS: MOCK_ADDRESS},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_bluetooth_discovery(
    hass: HomeAssistant,
    mock_setup_entry: MagicMock,
) -> None:
    """Test Bluetooth discovery flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_BLUETOOTH},
        data=MOCK_SERVICE_INFO,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"


async def test_bluetooth_discovery_confirm(
    hass: HomeAssistant,
    mock_setup_entry: MagicMock,
) -> None:
    """Test Bluetooth discovery confirm step creates entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_BLUETOOTH},
        data=MOCK_SERVICE_INFO,
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == MOCK_NAME
    assert result["data"] == {CONF_ADDRESS: MOCK_ADDRESS}


async def test_already_configured(
    hass: HomeAssistant,
    mock_setup_entry: MagicMock,
    mock_config_entry,
) -> None:
    """Test aborting if device is already configured."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_BLUETOOTH},
        data=MOCK_SERVICE_INFO,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
