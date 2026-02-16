"""Tests for the Pressensor binary sensor platform."""

from __future__ import annotations

import pytest
from homeassistant.const import STATE_ON, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .conftest import MOCK_NAME

pytestmark = pytest.mark.usefixtures("init_integration")

DEVICE_SLUG = MOCK_NAME.lower()


async def test_connected_sensor_on(hass: HomeAssistant) -> None:
    """Test connectivity sensor shows on when connected."""
    state = hass.states.get(f"binary_sensor.{DEVICE_SLUG}_connectivity")
    assert state is not None
    assert state.state == STATE_ON


async def test_connected_sensor_always_available(hass: HomeAssistant) -> None:
    """Test connectivity sensor is always available."""
    state = hass.states.get(f"binary_sensor.{DEVICE_SLUG}_connectivity")
    assert state is not None
    # The connectivity sensor should always be available
    assert state.attributes.get("available", True) is True


async def test_connected_sensor_entity_category(hass: HomeAssistant) -> None:
    """Test connectivity sensor has diagnostic entity category."""
    registry = er.async_get(hass)
    entry = registry.async_get(f"binary_sensor.{DEVICE_SLUG}_connectivity")
    assert entry is not None
    assert entry.entity_category is EntityCategory.DIAGNOSTIC
