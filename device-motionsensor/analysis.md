# MotionSensor (`MotionSensor`) - low-hanging-fruit analysis

Models in this home: **YS7805-UC** (1 device, "motion_kiwi")

## Currently exposed by HA `yolink` integration

| Platform | Entity         | Source field            | Notes              |
|----------|----------------|-------------------------|--------------------|
| binary_sensor | `motion_state` | `data.state == "alert"` | MOTION class      |
| sensor   | `battery`      | `data.battery`          | diagnostic         |
| sensor   | `devTemperature` | `data.devTemperature` | MCU temp           |
| sensor   | `loraInfo`     | `data.loraInfo.signal`  | diagnostic         |

## CONFIRMED missing fields

| Raw field                       | Suggested HA entity                       | Platform | Priority |
|---------------------------------|--------------------------------------------|----------|----------|
| `state.stateChangedAt` (epoch ms) | Skip -- HA `last_changed` covers this  | -        | -    |
| `state.nomotionDelay` (sec)     | `no_motion_delay`        number/sensor    | number   | MED |
| `state.alertInterval` (sec)     | `alert_interval`         sensor diagnostic | sensor  | LOW |
| `state.ledAlarm` (bool)         | `led_alarm`              switch (config)  | switch   | MED |
| `state.sensitivity` (string)    | `sensitivity`            select / sensor  | select   | MED |
| `state.batteryType` (string)    | `battery_type`           attribute only   | -        | LOW |

**No `lux`** field on YS7805 :(  Some newer PIR variants do have it; if
you ever pick up a YS7806 or PIR-PRO, run `discover_all.py` again.

## Conclusion

No high-value PRs from MotionSensor right now. All remaining candidates
are config fields (`nomotionDelay`, `sensitivity`, `ledAlarm`,
`alertInterval`) that need yolink-api setter support before they're
useful as `number` / `select` / `switch` entities.
