"""Tests for the Pressensor sensor platform."""

from __future__ import annotations

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
