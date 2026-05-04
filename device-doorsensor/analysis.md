# DoorSensor (`DoorSensor`) - low-hanging-fruit analysis

Models in this home: **YS7704-UC, YS7706-UC** (6 devices)

## Currently exposed by HA `yolink` integration

| Platform | Entity            | Source field          | Notes                |
|----------|-------------------|-----------------------|----------------------|
| binary_sensor | `door_state` | `data.state == "open"` | DOOR class           |
| sensor   | `battery`         | `data.battery`        | diagnostic           |
| sensor   | `loraInfo`        | `data.loraInfo.signal`| diagnostic, disabled |

## CONFIRMED missing fields (all 6 devices report these)

| Raw field                   | Suggested HA entity                       | Platform | Priority |
|-----------------------------|--------------------------------------------|----------|----------|
| `state.stateChangedAt` (epoch ms) | `last_state_change` timestamp sensor | sensor (TIMESTAMP) | HIGH |
| `state.openRemindDelay` (sec) | `open_reminder_delay`  number/sensor      | number   | MED |
| `state.delay` (sec)         | `auto_close_delay`       number/sensor    | number   | MED |
| `state.alertInterval` (sec) | `alert_interval`         sensor diagnostic | sensor  | LOW |

**No** `alarm.lowBattery` field on these models (battery low is inferred
from `battery == 0`).
**No** `devTemperature` on YS7704/YS7706.

## Suggested PR

Single small PR adding `last_state_change` timestamp sensor (TIMESTAMP
device class). Hugely useful for "alert if door open more than X minutes"
automations. Same shape as proposed for THSensor `stateChangedAt`.

The other three (delay/openRemindDelay/alertInterval) only useful once
the integration also supports configuring them; can be a follow-up.
