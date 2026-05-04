# SmartRemoter (`SmartRemoter`) - low-hanging-fruit analysis

Models in this home: **YS3604-UC** (1 device, "Fob Garage")

## Currently exposed by HA `yolink` integration

| Surface | What HA does                                    |
|---------|-------------------------------------------------|
| device_trigger | Press events fire `yolink_event` triggers (see `device_trigger.py`) |
| sensor  | `battery`, `loraInfo` only                      |

## CONFIRMED fields in fetchState

| Raw field                      | Suggested HA entity                  | Priority |
|--------------------------------|---------------------------------------|----------|
| `state.devTemperature`         | already exposed                       | -        |
| `state.event.keyMask`          | already used by device_trigger        | -        |
| `state.event.type`             | already used by device_trigger        | -        |
| `state.beep` (bool)            | `beep_enabled` switch (config) / sensor | LOW    |

The fob is well covered. Only minor missed item is `state.beep`
(audible feedback on press, configurable).

## Suggested PR

Skip unless MQTT capture reveals per-press metadata not currently
mapped to triggers.
