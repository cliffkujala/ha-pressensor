"""Tests for the Pressensor switch platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
)
from homeassistant.core import HomeAssistant

from .conftest import MOCK_NAME

pytestmark = pytest.mark.usefixtures("init_integration")

DEVICE_SLUG = MOCK_NAME.lower()


async def test_connection_switch_exists(
    hass: HomeAssistant,
) -> None:
    """Test connection switch entity is created."""
    entity_id = f"switch.{DEVICE_SLUG}_connection_enabled"
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_ON


async def test_connection_switch_turn_off(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Test turning off the connection switch."""
    entity_id = f"switch.{DEVICE_SLUG}_connection_enabled"

    coordinator = mock_config_entry.runtime_data
    coordinator.async_set_connection_enabled = AsyncMock()

    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )

    coordinator.async_set_connection_enabled.assert_called_once_with(False)


async def test_connection_switch_turn_on(
    hass: HomeAssistant,
    mock_config_entry,
) -> None:
    """Test turning on the connection switch."""
    entity_id = f"switch.{DEVICE_SLUG}_connection_enabled"

    coordinator = mock_config_entry.runtime_data
    coordinator.async_set_connection_enabled = AsyncMock()

    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )

    coordinator.async_set_connection_enabled.assert_called_once_with(True)
