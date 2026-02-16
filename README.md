# Pressensor Home Assistant Integration

A native Home Assistant integration for the [Pressensor](https://pressensor.com/) Bluetooth pressure transducer, commonly used for real-time espresso extraction pressure monitoring on E61 group head machines.

## Features

- **Auto-discovery** via Bluetooth — HA will detect your Pressensor automatically
- **Works through Bluetooth Proxies** — any ESPHome Bluetooth proxy in range will relay the connection
- **Real-time pressure** in millibar (convertible to bar via HA unit settings)
- **Temperature** readings (sent every 16th pressure notification)
- **Battery level** with state restore across disconnects
- **Connection status** binary sensor
- **Zero Pressure** button — calibrate the pressure reading to zero from HA

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

## Setup

During setup you will be asked to select your Pressensor from a list of discovered Bluetooth devices. Make sure the device is powered on and within Bluetooth range of your Home Assistant host or an ESPHome Bluetooth Proxy before starting.

No credentials, API keys, or additional configuration parameters are required.

If your Pressensor is not discovered automatically, pull a shot of espresso or use the blind filter in order to apply pressure to the sensor, which should wake it up, then go to **Settings → Devices & Services → Add Integration** and search for "Pressensor".

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
| Zero Pressure | Button | Calibrate the pressure reading to zero |
| Reconnect | Button | Manually trigger a BLE connection attempt |

## Supported Devices

- [Pressensor PRS Pressure Transducer](https://pressensor.com/products/pressure-sensor-for-coffee-machines-with-e61-group-heads-m6-thread) — M6 thread, designed for E61 group head espresso machines
- Devices advertising a BLE name starting with `PRS` or the Pressensor service UUID

No other pressure transducers are currently supported.

## Data Updates

The Pressensor sleeps to conserve battery and wakes when it detects a pressure change (threshold ~0.1 bar). The integration uses an **advertisement-driven** connection model:

1. The device wakes and sends a BLE advertisement
2. Home Assistant detects the advertisement and connects automatically
3. Pressure data arrives via BLE GATT notifications in real time
4. Temperature is included with every 16th pressure notification
5. Battery level is read on each connection and checked daily
6. When the device goes back to sleep, HA waits for the next advertisement

A 5-minute fallback poll ensures connectivity if an advertisement is missed.

## Automation Examples

### Auto-tare scale and start timer on extraction

Detects a 200 mbar (0.2 bar) pressure rise — indicating the pump has engaged — then tares a Bluetooth scale and starts its timer automatically.

```yaml
automation:
  - alias: "Auto-tare and start timer on extraction"
    trigger:
      - platform: state
        entity_id: sensor.prs12345_pressure
    condition:
      - condition: template
        value_template: >
          {{ (trigger.to_state.state | float(0))
             - (trigger.from_state.state | float(0)) >= 200 }}
    action:
      - service: button.press
        target:
          entity_id: button.acaia_lunar_tare
      - service: button.press
        target:
          entity_id: button.acaia_lunar_start_stop
```

### Low battery notification

```yaml
automation:
  - alias: "Pressensor low battery"
    trigger:
      - platform: numeric_state
        entity_id: sensor.prs12345_battery
        below: 15
    action:
      - service: notify.mobile_app
        data:
          title: "Pressensor"
          message: "Battery is low ({{ states('sensor.prs12345_battery') }}%). Replace the CR2032."
```

Replace `prs12345` with your device's actual entity ID prefix.

## Known Limitations

- **Exclusive Bluetooth connection** — While this integration is connected to your Pressensor, you won't be able to use the official app, as BLE devices only support one connection at a time. The Pressensor's sleep/wake cycle creates natural windows where the app can connect, but not while HA holds an active connection
- **Bluetooth range** — The device must be within BLE range of your HA host or an ESPHome Bluetooth Proxy (~10 m line of sight, less through walls)
- **No data when idle** — The Pressensor sleeps between pressure changes to save battery. Readings stop when the device is idle
- **Temperature update frequency** — Temperature is only sent every 16th pressure notification, so it updates less frequently than pressure
- **Battery life** — The CR2032 coin cell battery life depends on how often the device wakes. Frequent use reduces battery life
- **Single device per entry** — Each Pressensor requires its own integration config entry

## Troubleshooting

### Device not discovered

- Ensure the Pressensor has a fresh CR2032 battery installed
- Confirm your HA host has a working Bluetooth adapter, or that an ESPHome Bluetooth Proxy is within range
- Bring the device closer to the Bluetooth adapter or proxy
- Press the button on the Pressensor to wake it up, then check **Settings -> Devices & Services** for a new discovery

### Connection drops frequently

- Place an ESPHome Bluetooth Proxy closer to the Pressensor
- Reduce interference from other Bluetooth or Wi-Fi devices
- The device intentionally disconnects when idle to save battery — this is normal behavior

### Readings appear stale or unavailable

- The device may be asleep. Apply pressure to the group head or press the Reconnect button in HA
- Check the Connected binary sensor — if it shows Off, the device is not currently streaming data

### Battery reads 0% or unavailable

- Replace the CR2032 battery
- After replacing, wake the device and press the Reconnect button

## Removal

1. Go to **Settings → Devices & Services**
2. Find the **Pressensor** integration
3. Click the three-dot menu and select **Delete**
4. Restart Home Assistant

If installed via HACS, you can also uninstall the integration from HACS after removing it from Devices & Services.

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
