# Finger (`Finger`) - low-hanging-fruit analysis

Models in this home: **YS4908-UC** (2 devices, "Finger 1", "Finger 2")

## Currently exposed by HA `yolink` integration

| Platform | Entity        | Source field            | Notes                         |
|----------|---------------|-------------------------|-------------------------------|
| cover    | (door cover)  | derived                 | Treated like garage door      |
| sensor   | `battery`     | `data.battery`          | diagnostic                    |
| sensor   | `loraInfo`    | `data.loraInfo.signal`  | diagnostic                    |

## CONFIRMED fields in raw data

`fetchState` returns mostly empty. The Finger only emits a meaningful
payload when **pressed**, so static snapshots are uninformative.

To find missing fields here, **run `mqtt_listen_all.py 30`** then
press each Finger from the YoLink app AND with a registered fingerprint.
Then check `events/Finger_1.jsonl` for the `setState` / `StatusChange`
event payload — the fingerprint id and event source are likely there
but only on press events.

## Hypothesized missing fields (verify via MQTT)

- [ ] `fingerprintId` / `userId` in press event payload
- [ ] `pressType` (fingerprint vs app vs button)
- [ ] `lastPressedTime` timestamp

If confirmed, **fingerprint-id-as-event** would be very high value.
Fires `yolink_event` with the fingerprint id so HA can route on which
person triggered it.

## Suggested PR

Defer until MQTT capture confirms event payload schema.
