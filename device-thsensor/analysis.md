# THSensor (`THSensor`) - low-hanging-fruit analysis

Models in this home: **YS8003-UC, YS8004-UC, YS8005-UC, YS8006-UC** (12 devices)

## Currently exposed by HA `yolink` integration

Source: `core/homeassistant/components/yolink/sensor.py`

| HA entity key       | Source field             | Notes                                   |
|---------------------|--------------------------|-----------------------------------------|
| `battery`           | `data.battery` (1-4 -> %)| diagnostic                              |
| `humidity`          | `data.humidity`          | suppressed for YS8004/YS8008/YS8014/YS8017 |
| `temperature`       | `data.temperature`       |                                         |
| `loraInfo`          | `data.loraInfo.signal`   | dBm, diagnostic, disabled by default    |

That's it.

## CONFIRMED missing fields (from `snapshots/*.json` - all 12 devices report these)

| Raw field                          | Suggested HA entity                              | Platform | Priority |
|------------------------------------|---------------------------------------------------|----------|----------|
| `state.alarm.lowBattery` (bool)    | `lowbattery_problem` binary_sensor PROBLEM        | binary_sensor | HIGH |
| `state.alarm.lowTemp` (bool)       | `low_temperature_alarm`  binary_sensor PROBLEM    | binary_sensor | HIGH |
| `state.alarm.highTemp` (bool)      | `high_temperature_alarm` binary_sensor PROBLEM    | binary_sensor | HIGH |
| `state.alarm.lowHumidity` (bool)   | `low_humidity_alarm`     binary_sensor PROBLEM    | binary_sensor | HIGH |
| `state.alarm.highHumidity` (bool)  | `high_humidity_alarm`    binary_sensor PROBLEM    | binary_sensor | HIGH |
| `state.alarm.period` (bool)        | `period_alarm`           binary_sensor PROBLEM    | binary_sensor | MED |
| `state.tempLimit.min` (number)     | `temperature_low_limit`  number/sensor (config)   | number   | HIGH |
| `state.tempLimit.max` (number)     | `temperature_high_limit` number/sensor            | number   | HIGH |
| `state.humidityLimit.min` (number) | `humidity_low_limit`     number/sensor            | number   | HIGH |
| `state.humidityLimit.max` (number) | `humidity_high_limit`    number/sensor            | number   | HIGH |
| `state.tempCorrection` (number)    | `temperature_correction` number (calibration offset) | number | MED |
| `state.humidityCorrection` (number)| `humidity_correction`    number                   | number   | MED |
| `state.interval` (sec)             | `report_interval`        sensor diagnostic        | sensor   | LOW |
| `state.recordInterval` (sec)       | `record_interval`        sensor diagnostic        | sensor   | LOW |
| `state.mode` (string)              | `mode`                   sensor enum              | sensor   | LOW |
| `state.batteryType` (string, e.g. "AAA") | `battery_type`     sensor diagnostic, attr only | sensor | LOW |

**Note** that `loraInfo` (signal) is also nested under `state.loraInfo` in
fetchState responses; integration reads top-level only. May want to also
read from `state.loraInfo` if missing top-level.

## CONFIRMED via captured `THSensor.DataRecord` push events (Guest, Kids_Temp, 2026-05-04)

The DataRecord event type is distinct from periodic `Report`. Payload:
```json
{"records":[{"temperature":19.7,"humidity":56,"time":"2026-05-04T15:12:59Z"}]}
```

Each record is a time-series sample with its own timestamp. The
integration appears to handle this via `_is_message_acceptable` in
`yolink-api/yolink/mqtt_client.py` (`THSensor.DataRecord` is whitelisted)
but it's worth verifying whether HA actually surfaces these historical
samples or only the latest. If only latest, this is a candidate for
exposing as historical data points (longer-term sensor history).

The captured records confirm `temperature` is in Celsius and `humidity`
is integer or float percent -- matches existing HA exposure.

## Suggested PR breakdown

1. **PR #1 (highest impact, smallest diff):** Add 5 alarm binary_sensors
   (`lowBattery`, `lowTemp`, `highTemp`, `lowHumidity`, `highHumidity`).
   Pattern is identical to `pipe_leak_detected` in `binary_sensor.py`.
2. **PR #2:** Add the 4 limit numbers as read-only diagnostic sensors first
   (write support comes later). Promotes them to `number` once a setter
   message is added to `yolink-api`.
3. **PR #3 (low priority):** add interval/mode/batteryType diagnostic sensors.

## How to verify on a specific device

Look in `snapshots/<name>.json` -> `fetchState.data.state` to see exact
values for that unit. All 12 of your sensors emit identical schema, so
gating by `device_type == THSensor` (no model check) is safe.
