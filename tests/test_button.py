"""Tests for the Pressensor button platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.button import SERVICE_PRESS
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .conftest import MOCK_NAME

pytestmark = pytest.mark.usefixtures("init_integration")

DEVICE_SLUG = MOCK_NAME.lower()


async def test_zero_pressure_button(
    hass: HomeAssistant,
    mock_client: MagicMock,
) -> None:
    """Test zero pressure button calls client method."""
    entity_id = f"button.{DEVICE_SLUG}_zero_pressure"
    state = hass.states.get(entity_id)
    assert state is not None

    await hass.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )

    mock_client.zero_pressure.assert_called_once()


async def test_reconnect_button(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Test reconnect button calls coordinator reconnect method."""
    entity_id = f"button.{DEVICE_SLUG}_reconnect"
    state = hass.states.get(entity_id)
    assert state is not None

    coordinator = mock_config_entry.runtime_data
    coordinator.async_request_connect = AsyncMock()

    await hass.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )

    coordinator.async_request_connect.assert_called_once()


async def test_zero_pressure_button_not_connected(
    hass: HomeAssistant,
    mock_client: MagicMock,
    mock_config_entry,
) -> None:
    """Test zero pressure button raises error when not connected."""
    entity_id = f"button.{DEVICE_SLUG}_zero_pressure"

    # Make the client report as disconnected
    mock_client.connected = False

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
    assert exc_info.value.translation_key == "not_connected"


async def test_zero_pressure_button_failure(
    hass: HomeAssistant,
    mock_client: MagicMock,
) -> None:
    """Test zero pressure button raises error when command fails."""
    entity_id = f"button.{DEVICE_SLUG}_zero_pressure"

    mock_client.zero_pressure = AsyncMock(side_effect=Exception("BLE write error"))

    with pytest.raises(HomeAssistantError) as exc_info:
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
    assert exc_info.value.translation_key == "zero_pressure_failed"


async def test_reconnect_button_device_not_found(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Test reconnect button raises error when device not found."""
    entity_id = f"button.{DEVICE_SLUG}_reconnect"

    coordinator = mock_config_entry.runtime_data
    coordinator.async_request_connect = AsyncMock(
        side_effect=HomeAssistantError("not found")
    )

    with pytest.raises(HomeAssistantError, match="not found"):
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
