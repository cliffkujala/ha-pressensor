"""Tests for the Pressensor sensor platform."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorExtraStoredData
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    PERCENTAGE,
    EntityCategory,
    UnitOfPressure,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.pressensor.client import PressensorState
from custom_components.pressensor.sensor import PressensorRestoreSensor

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


async def test_battery_sensor_entity_category(hass: HomeAssistant) -> None:
    """Test battery sensor has diagnostic entity category."""
    registry = er.async_get(hass)
    entry = registry.async_get(f"sensor.{DEVICE_SLUG}_battery")
    assert entry is not None
    assert entry.entity_category is EntityCategory.DIAGNOSTIC


async def test_pressure_sensor_no_entity_category(hass: HomeAssistant) -> None:
    """Test pressure sensor has no entity category (primary entity)."""
    registry = er.async_get(hass)
    entry = registry.async_get(f"sensor.{DEVICE_SLUG}_pressure")
    assert entry is not None
    assert entry.entity_category is None


async def test_battery_sensor_restores_previous_state(
    hass: HomeAssistant,
    mock_config_entry: MagicMock,
    mock_client: MagicMock,
) -> None:
    """Test battery sensor restores state from previous session."""
    entity_id = f"sensor.{DEVICE_SLUG}_battery"

    # Make client report no battery data so restore value is used
    mock_client.state = PressensorState(
        pressure_mbar=0.0,
        connected=True,
    )

    entity_component = hass.data["sensor"]
    entity = entity_component.get_entity(entity_id)
    assert entity is not None
    assert isinstance(entity, PressensorRestoreSensor)

    # Simulate restored data being available
    restored_data = SensorExtraStoredData(
        native_value=Decimal("72"),
        native_unit_of_measurement=PERCENTAGE,
    )
    with patch.object(
        entity, "async_get_last_sensor_data", return_value=restored_data
    ):
        await entity.async_added_to_hass()

    assert entity._restored_data is not None
    assert entity._attr_native_unit_of_measurement == PERCENTAGE
