# DoorSensor (`DoorSensor`) - low-hanging-fruit analysis

Models in this home: **YS7704-UC, YS7706-UC** (6 devices)

## Currently exposed by HA `yolink` integration

| Platform | Entity            | Source field          | Notes                |
|----------|-------------------|-----------------------|----------------------|
| binary_sensor | `door_state` | `data.state == "open"` | DOOR class           |
| sensor   | `battery`         | `data.battery`        | diagnostic           |
| sensor   | `loraInfo`        | `data.loraInfo.signal`| diagnostic, disabled |

## CONFIRMED missing fields (all 6 devices report these in fetchState)

| Raw field                   | Note                                                  |
|-----------------------------|-------------------------------------------------------|
| `state.stateChangedAt` (epoch ms) | Skip -- HA `last_changed` covers this use case |
| `state.openRemindDelay` (sec) | Config value; needs setter support to expose as `number` |
| `state.delay` (sec)         | Config value; same as above                            |
| `state.alertInterval` (sec) | Config value; same as above                            |

## CONFIRMED via captured `DoorSensor.Alert` push event (Garage_Boat, 2026-05-04)

Push payload on door open:
```json
{"state":"open","alertType":"normal","battery":4,"version":"060d",
 "loraInfo":{"signal":-107,...},"stateChangedAt":1777908102507}
```

Notable: `alertType` (e.g. `"normal"`) appears in push events but NOT in
fetchState. Other possible values (`"tamper"`, `"openRemind"`, ...) need
to be observed. If a non-`"normal"` value ever appears, it could be a
useful diagnostic binary_sensor (e.g. tamper PROBLEM class).

## Notes

- **No** `alarm.lowBattery` field on these models (battery low is
  inferred from `battery == 0`).
- **No** `devTemperature` on YS7704/YS7706.

## Conclusion

No high-value PRs from DoorSensor right now. HA's built-in
`last_changed` covers timestamp use cases. Config fields (`delay`,
`openRemindDelay`, `alertInterval`) need yolink-api setter support
before they're useful as `number` entities.

Watch for `alertType != "normal"` in future captures.
