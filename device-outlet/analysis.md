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

### ~~#1: YS6604 power monitoring~~  -- INVALID (verified 2026-05-04)

Live-load test with `poll_live.py "Attic Fan Power" 15`:
- Toggled outlet to `open`, fans drawing real load
- 4 consecutive `Outlet.getState` polls all returned `power=0, watt=0`
- Full payload contained no other power/energy fields
- MQTT push events on toggle (`Outlet.setState`) also contained only
  `state` + `loraInfo` -- no `power`/`watt`

Conclusion: YS6604-UC firmware exposes `power`/`watt` keys but the
**device has no current-sensing hardware**. The integration's existing
`POWER_SUPPORT_MODELS` whitelist correctly excludes YS6604. **Do not PR.**

YS6602-UC (`plug_misc`), in contrast, reported `watt=40` cumulative kWh
in the snapshot - it does measure. Already in `POWER_SUPPORT_MODELS`.

### #2 (still valid): Add YS6602-UC/EC to `coreTemperature` exists_fn

YS6602-UC `plug_misc` snapshot shows `state.coreTemperature: 37`. The
existing entity in `sensor.py` is whitelisted to YS6614 only:

```python
exists_fn=lambda device: (
    device.device_model_name
    in [DEV_MODEL_PLUG_YS6614_EC, DEV_MODEL_PLUG_YS6614_UC]
),
```

**Fix:** add `DEV_MODEL_PLUG_YS6602_UC` and `DEV_MODEL_PLUG_YS6602_EC`
to that list. ~3-line PR. Affects every YS6602 user worldwide.

Same likely true for YS6803 (also a power-monitoring plug). Need a
YS6803 snapshot to confirm before including in same PR.

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
