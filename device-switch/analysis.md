# Switch (`Switch`) - low-hanging-fruit analysis

Models in this home: **YS5706-UC** (1 device, "entry_fan_relay")

YS5706 = in-wall single-pole relay switch.

## Currently exposed by HA `yolink` integration

| Platform | Entity         | Source field      | Notes                       |
|----------|----------------|-------------------|-----------------------------|
| switch   | (relay on/off) | `data.state`      | switch.py                   |
| sensor   | `loraInfo`     | `data.loraInfo.signal` | diagnostic              |
| device_trigger | press events | -            | Switch is a trigger source  |

No power, no energy, no pulse-mode entity.

## Fields in raw data

| Raw field                       | Status / suggested entity                  | Priority |
|---------------------------------|---------------------------------------------|----------|
| `state.power` (W)               | **ALWAYS 0, no measurement hardware** -- skip | INVALID |
| `state.watt` (kWh)              | **ALWAYS 0, no measurement hardware** -- skip | INVALID |
| `state.pulseMode.enable` (bool) | `pulse_mode_enabled` switch (config)        | MED |
| `state.pulseMode.duration` (ms) | `pulse_duration` number                     | MED |
| `state.battery` (-1 = N/A)      | suppress entity when -1                     | n/a  |

## Verified 2026-05-04

Live test against `entry_fan_relay` (YS5706-UC):
- Toggled to `open` via getState polls
- `power=0, watt=0` throughout

YS5706-UC firmware has the same `power`/`watt` schema fields as the
power-monitoring outlets, but lacks the current-sensing chip. The Switch
device type cannot reliably expose power/energy entities.

## Suggested PR

`pulseMode.enable` + `pulseMode.duration` could be a follow-up PR to
expose the relay's momentary-press configuration. Requires setter
support in `yolink-api` first (currently no public method to set
pulseMode). Defer until that lands upstream.

No high-priority PRs from this device type after live verification.
