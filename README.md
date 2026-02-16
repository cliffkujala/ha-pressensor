# Pressensor Home Assistant Integration

A native Home Assistant integration for the [Pressensor](https://pressensor.com/) Bluetooth pressure transducer, commonly used for real-time espresso extraction pressure monitoring on E61 group head machines.

## Features

- **Auto-discovery** via Bluetooth — HA will detect your Pressensor automatically
- **Works through Bluetooth Proxies** — any ESPHome Bluetooth proxy in range will relay the connection
- **Real-time pressure** in millibar (convertible to bar via HA unit settings)
- **Temperature** readings (sent every 16th pressure notification)
- **Battery level** with state restore across disconnects
- **Connection status** binary sensor
- **Zero/Tare pressure** button — reset the pressure baseline from HA

## Installation

### Manual Installation

1. Copy the `custom_components/pressensor` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant
3. The Pressensor should be auto-discovered if Bluetooth is set up — check **Settings → Devices & Services** for a new discovery notification
4. If not auto-discovered, go to **Settings → Devices & Services → Add Integration** and search for "Pressensor"

### HACS (Custom Repository)

1. In HACS, add this as a custom repository (Integration type)
2. Install the "Pressensor" integration
3. Restart Home Assistant

## Requirements

- Home Assistant with the **Bluetooth** integration enabled
- A Bluetooth adapter on your HA host, **or** one or more ESPHome Bluetooth Proxies in range of the Pressensor
- A [Pressensor](https://pressensor.com/products/pressure-sensor-for-coffee-machines-with-e61-group-heads-m6-thread) device with battery installed

## Entities

| Entity | Type | Description |
|--------|------|-------------|
| Pressure | Sensor | Real-time group head pressure (mbar) |
| Temperature | Sensor | Group temperature (°C, updated every ~16th reading) |
| Battery | Sensor | Battery percentage (0–100%) |
| Connected | Binary Sensor | BLE connection status |
| Zero pressure | Button | Tare/zero the pressure reading |

## BLE Protocol Reference

Based on the [official Pressensor BLE protocol documentation](https://pressensor.com/pages/prs-protocol).

- Advertising name: starts with `PRS`
- Pressure Service UUID: `873ae82a-4c5a-4342-b539-9d900bf7ebd0`
- Uses standard Battery Service (`0x180F`)
- Pressure notifications: signed 16-bit big-endian millibar values
- Temperature piggybacks on every 16th pressure notification

## Credits

- [Pressensor](https://pressensor.com/) — the hardware and protocol
- [Magnus Nordlander / variegated-coffee](https://github.com/variegated-coffee) — the original ESPHome component that served as protocol reference
- [Acaia HA integration](https://github.com/home-assistant/core/tree/dev/homeassistant/components/acaia) — architectural reference for BLE integration patterns
