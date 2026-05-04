# LeakSensor (`LeakSensor`) - low-hanging-fruit analysis

Models in this home: **YS7903-UC** (2 devices)

## Currently exposed by HA `yolink` integration

| Platform | Entity      | Source field                    | Notes              |
|----------|-------------|---------------------------------|--------------------|
| binary_sensor | `leak_state` | `data.state in ["alert","full"]` | MOISTURE class |
| sensor   | `battery`   | `data.battery`                  | diagnostic         |
| sensor   | `devTemperature` | `data.devTemperature`      | MCU temp           |
| sensor   | `loraInfo`  | `data.loraInfo.signal`          | diagnostic         |

## CONFIRMED missing fields (both devices report)

| Raw field                          | Suggested HA entity                     | Platform | Priority |
|------------------------------------|------------------------------------------|----------|----------|
| `state.alarmState.detectorError` (bool) | `detector_error` binary_sensor PROBLEM | binary_sensor | HIGH |
| `state.alarmState.freezeError` (bool)   | `freeze_error`   binary_sensor PROBLEM | binary_sensor | HIGH |
| `state.alarmState.stayError` (bool)     | `stay_error`     binary_sensor PROBLEM | binary_sensor | MED |
| `state.alarmState.reminder` (bool)      | `reminder_alarm` binary_sensor PROBLEM | binary_sensor | LOW |
| `state.stateChangedAt` (epoch ms)  | `last_state_change` timestamp sensor    | sensor   | HIGH |
| `state.beep` (bool)                | `beep_enabled`   switch (config) / sensor | switch  | MED |
| `state.sensitivity` (string)       | `sensitivity`    select (low/med/high) / sensor | select | MED |
| `state.sensorMode` (string)        | `sensor_mode`    select / sensor enum   | select   | LOW |
| `state.interval` (sec)             | `report_interval` sensor diagnostic     | sensor   | LOW |
| `state.batteryType` (already 22/24 in summary - varies) | `battery_type` attr | sensor | LOW |

**Note**: `is_leak_sensor_state_available()` already reads
`alarmState.detectorError` to suppress the leak entity when the
detector is broken - but the flag itself isn't surfaced as its own
entity for the user to see WHY availability dropped.

## Suggested PRs

1. **PR #1:** `detector_error` and `freeze_error` binary_sensors PROBLEM
   class. Especially valuable - `freeze_error` lets you alarm on burst-
   pipe risk (water hose left out in winter).
2. **PR #2:** `last_state_change` timestamp sensor (same as DoorSensor
   PR - share the helper across types).
3. **PR #3:** `beep`/`sensitivity` as switch+select (needs setter
   support in `yolink-api`; defer).
