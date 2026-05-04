# Outlet (`Outlet`) - low-hanging-fruit analysis

Models in this home: **YS6602-UC** (1: plug_misc), **YS6604-UC** (2: Attic Fan Power, Humidifier Plug)

## Currently exposed by HA `yolink` integration

| Platform | Entity                | Source field        | Notes                                |
|----------|-----------------------|---------------------|--------------------------------------|
| switch   | (outlet on/off)       | `data.state`        |                                      |
| sensor   | `power` (current_power)| `data.power / 10`  | only for YS6602/YS6614/YS6803        |
| sensor   | `watt` (energy total) | `data.watt / 100`   | only for YS6602/YS6614/YS6803        |
| sensor   | `loraInfo`            | `data.loraInfo.signal` | diagnostic                        |
| sensor   | `coreTemperature`     | `data.coreTemperature` | only for YS6614 plug              |

## CONFIRMED missing entities

### #1 (highest impact, smallest diff): YS6604 power monitoring

YS6604-UC reports both `state.power` and `state.watt` in fetchState
(values 0/0 in this snapshot because nothing was drawing) but the
integration excludes YS6604 from `POWER_SUPPORT_MODELS` in
`core/homeassistant/components/yolink/sensor.py`.

**Fix:** add `DEV_MODEL_PLUG_YS6604_UC` and `DEV_MODEL_PLUG_YS6604_EC`
to `const.py` and append them to `POWER_SUPPORT_MODELS`.
**Two-line PR.** Affects every YS6604 outdoor plug user globally.

### #2: alertType binary sensors (all Outlet models, both YS6602 and YS6604)

| Raw field                             | Suggested entity                          | Class   |
|---------------------------------------|-------------------------------------------|---------|
| `state.alertType.overload`            | `outlet_overload`         binary_sensor   | PROBLEM |
| `state.alertType.highLoad`            | `outlet_high_load`        binary_sensor   | PROBLEM |
| `state.alertType.lowLoad`             | `outlet_low_load`         binary_sensor   | PROBLEM |
| `state.alertType.highTemperature`     | `outlet_high_temperature` binary_sensor   | PROBLEM |
| `state.alertType.remind`              | `outlet_reminder`         binary_sensor   | PROBLEM |

Five new binary sensors. `overload` and `highTemperature` are real
safety alarms - currently invisible to HA.

### #3: countdown timers + thresholds

| Raw field                  | Suggested entity                          | Notes |
|----------------------------|-------------------------------------------|-------|
| `state.delay.on`  (sec)    | `delay_on`  number/sensor                 | YS6604 only |
| `state.delay.off` (sec)    | `delay_off` number/sensor                 | YS6604 only |
| `state.powerLimitHigh` (W) | `power_limit_high` number/sensor          | YS6602 only - source threshold for `highLoad` alarm |
| `state.powerLimitLow`  (W) | `power_limit_low`  number/sensor          | YS6602 only |
| `state.alertInterval` (sec)| `alert_interval` sensor diagnostic        |  |

### #4: extend coreTemperature to YS6602

YS6602-UC reports `state.coreTemperature` (37 in this snapshot) but the
integration only exposes it for YS6614. **One-line PR**: add
`DEV_MODEL_PLUG_YS6602_UC/EC` to the `coreTemperature` `exists_fn`.

## Suggested PR breakdown

1. **PR #1 (one line):** add YS6604 to `POWER_SUPPORT_MODELS`.
2. **PR #2 (small):** add YS6602 to `coreTemperature` exists_fn.
3. **PR #3 (medium):** 5 alertType binary sensors.
4. **PR #4:** delay/powerLimit numbers (lower priority, needs setter).
