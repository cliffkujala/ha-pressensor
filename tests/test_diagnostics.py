"""Tests for the Pressensor diagnostics."""

from __future__ import annotations

import pytest
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant

from custom_components.pressensor.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .conftest import MOCK_ADDRESS

pytestmark = pytest.mark.usefixtures("init_integration")


async def test_diagnostics(hass: HomeAssistant, mock_config_entry) -> None:
    """Test diagnostics returns expected data with address redacted."""
    result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert CONF_ADDRESS in result["config_entry"]
    assert result["config_entry"][CONF_ADDRESS] == "**REDACTED**"

    assert "state" in result
    assert result["state"]["pressure_mbar"] == 1050.0
    assert result["state"]["temperature_c"] == 93.5
    assert result["state"]["battery_percent"] == 85
    assert result["state"]["connected"] is True

    assert "connection" in result
    assert result["connection"]["connecting"] is False
    assert isinstance(result["connection"]["was_available"], bool)


async def test_diagnostics_no_battery_check(
    hass: HomeAssistant, mock_config_entry
) -> None:
    """Test diagnostics when no battery check has occurred."""
    coordinator = mock_config_entry.runtime_data
    coordinator._last_battery_check = None

    result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert result["connection"]["last_battery_check"] is None
