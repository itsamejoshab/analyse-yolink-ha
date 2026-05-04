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

## CONFIRMED missing fields (YS5706 reports all of these)

| Raw field                       | Suggested HA entity                       | Priority |
|---------------------------------|--------------------------------------------|----------|
| `state.power` (W)               | `current_power` sensor POWER, MEASUREMENT  | HIGH |
| `state.watt` (kWh, /100 like Outlet) | `power_consumption` sensor ENERGY, TOTAL | HIGH |
| `state.pulseMode.enable` (bool) | `pulse_mode_enabled` switch (config) / sensor | MED |
| `state.pulseMode.duration` (ms) | `pulse_duration` number/sensor             | MED |
| `state.battery` (-1 means N/A)  | suppress entity when -1                    | n/a  |

## Suggested PR

**One PR (highest impact for least diff):** add `power` and `watt` sensors
for `device_type == ATTR_DEVICE_SWITCH and model in [YS5706-UC, YS5706-EC]`.

Pattern is identical to existing `power`/`watt` exists_fn for
`POWER_SUPPORT_MODELS` outlets. Either:
- add a new `SWITCH_POWER_SUPPORT_MODELS` constant, or
- add YS5706 to `POWER_SUPPORT_MODELS` and broaden `exists_fn` to match
  device_type in {Outlet, Switch}. Latter is cleaner.

A second follow-up PR can add `pulseMode` as switch+number for relay
"momentary press" mode (handy for garage door wiring use cases).
