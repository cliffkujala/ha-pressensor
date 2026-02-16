"""Config flow for Pressensor integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_ble_device_from_address,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import DOMAIN, PRESSURE_SERVICE_UUID

_LOGGER = logging.getLogger(__name__)


class PressensorConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Pressensor."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered: dict[str, Any] = {}
        self._discovered_devices: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(format_mac(address))
            self._abort_if_unique_id_configured()

            # Verify device is reachable before creating entry
            if (
                async_ble_device_from_address(self.hass, address, connectable=True)
                is None
            ):
                errors["base"] = "cannot_connect"
            else:
                name = self._discovered_devices.get(address, f"Pressensor ({address})")
                return self.async_create_entry(
                    title=name,
                    data={CONF_ADDRESS: address},
                )

        # Find Pressensor devices via bluetooth
        for device in async_discovered_service_info(self.hass):
            if (
                device.name and device.name.startswith("PRS")
            ) or PRESSURE_SERVICE_UUID.lower() in [
                str(u).lower() for u in device.service_uuids
            ]:
                self._discovered_devices[device.address] = (
                    device.name or f"Pressensor ({device.address})"
                )

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        options = [
            SelectOptionDict(
                value=address,
                label=f"{name} ({address})",
            )
            for address, name in self._discovered_devices.items()
        ]

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle a Bluetooth discovery."""
        _LOGGER.debug(
            "Discovered Pressensor: %s (%s)",
            discovery_info.name,
            discovery_info.address,
        )

        await self.async_set_unique_id(format_mac(discovery_info.address))
        self._abort_if_unique_id_configured()

        self._discovered[CONF_ADDRESS] = discovery_info.address
        self._discovered[CONF_NAME] = (
            discovery_info.name or f"Pressensor ({discovery_info.address})"
        )

        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm Bluetooth discovery."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._discovered[CONF_NAME],
                data={CONF_ADDRESS: self._discovered[CONF_ADDRESS]},
            )

        self.context["title_placeholders"] = {
            CONF_NAME: self._discovered[CONF_NAME],
        }

        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={CONF_NAME: self._discovered[CONF_NAME]},
        )
