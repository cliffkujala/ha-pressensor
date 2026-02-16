"""Sensor platform for Pressensor."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorExtraStoredData,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfPressure,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .client import PressensorState
from .coordinator import PressensorConfigEntry
from .entity import PressensorEntity

PARALLEL_UPDATES = 0


@dataclass(kw_only=True, frozen=True)
class PressensorSensorEntityDescription(SensorEntityDescription):
    """Description for Pressensor sensor entities."""

    value_fn: Callable[[PressensorState], float | int | None]


SENSORS: tuple[PressensorSensorEntityDescription, ...] = (
    PressensorSensorEntityDescription(
        key="pressure",
        translation_key="pressure",
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.MBAR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda state: state.pressure_mbar,
    ),
    PressensorSensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda state: state.temperature_c,
    ),
)

RESTORE_SENSORS: tuple[PressensorSensorEntityDescription, ...] = (
    PressensorSensorEntityDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state: state.battery_percent,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PressensorConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Pressensor sensors."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        PressensorSensor(coordinator, description) for description in SENSORS
    ]
    entities.extend(
        PressensorRestoreSensor(coordinator, description)
        for description in RESTORE_SENSORS
    )
    async_add_entities(entities)


class PressensorSensor(PressensorEntity, SensorEntity):
    """Representation of a Pressensor sensor."""

    entity_description: PressensorSensorEntityDescription

    @property
    def native_value(self) -> float | int | None:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.state)


class PressensorRestoreSensor(PressensorEntity, RestoreSensor):
    """Representation of a Pressensor sensor with restore capability.

    Used for battery level so it persists across disconnects.
    """

    entity_description: PressensorSensorEntityDescription
    _restored_data: SensorExtraStoredData | None = None

    async def async_added_to_hass(self) -> None:
        """Handle entity added to hass — restore previous state."""
        await super().async_added_to_hass()

        self._restored_data = await self.async_get_last_sensor_data()
        if self._restored_data is not None:
            self._attr_native_value = self._restored_data.native_value
            self._attr_native_unit_of_measurement = (
                self._restored_data.native_unit_of_measurement
            )

        value = self.entity_description.value_fn(self.coordinator.state)
        if value is not None:
            self._attr_native_value = value

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        value = self.entity_description.value_fn(self.coordinator.state)
        if value is not None:
            self._attr_native_value = value
        self._async_write_ha_state()

    @property
    def available(self) -> bool:
        """Available if connected or if we have restored data."""
        return super().available or self._restored_data is not None
