"""Tests for the Pressensor sensor platform."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    PERCENTAGE,
    UnitOfPressure,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant

from custom_components.pressensor.client import PressensorState

from .conftest import MOCK_NAME

pytestmark = pytest.mark.usefixtures("init_integration")

DEVICE_SLUG = MOCK_NAME.lower()


async def test_pressure_sensor(hass: HomeAssistant) -> None:
    """Test pressure sensor entity."""
    state = hass.states.get(f"sensor.{DEVICE_SLUG}_pressure")
    assert state is not None
    assert state.state == "1050.0"
    assert state.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.PRESSURE
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfPressure.MBAR


async def test_temperature_sensor(hass: HomeAssistant) -> None:
    """Test temperature sensor entity."""
    state = hass.states.get(f"sensor.{DEVICE_SLUG}_temperature")
    assert state is not None
    assert state.state == "93.5"
    assert state.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.TEMPERATURE
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS


async def test_battery_sensor(hass: HomeAssistant) -> None:
    """Test battery sensor entity."""
    state = hass.states.get(f"sensor.{DEVICE_SLUG}_battery")
    assert state is not None
    assert state.state == "85"
    assert state.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.BATTERY
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == PERCENTAGE


async def test_battery_sensor_coordinator_update(
    hass: HomeAssistant,
    mock_config_entry,
    mock_client: MagicMock,
) -> None:
    """Test battery sensor updates from coordinator and restore availability."""
    entity_id = f"sensor.{DEVICE_SLUG}_battery"

    # Find the entity via the entity component
    entity_component = hass.data["sensor"]
    entity = entity_component.get_entity(entity_id)
    assert entity is not None

    # Test _handle_coordinator_update with a new value
    mock_client.state = PressensorState(
        pressure_mbar=1050.0,
        temperature_c=93.5,
        battery_percent=42,
        connected=True,
    )
    entity._handle_coordinator_update()
    assert entity.native_value == 42

    # Test _handle_coordinator_update with None value (no battery data)
    mock_client.state = PressensorState(
        pressure_mbar=1050.0,
        connected=True,
    )
    entity._handle_coordinator_update()
    # Should retain the previous value
    assert entity.native_value == 42

    # Test available with restored data
    entity._restored_data = MagicMock()
    assert entity.available is True
