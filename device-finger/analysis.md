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

## CONFIRMED via captured `Finger.setState` push event (Finger_2, 2026-05-04)

Press payload (after press completes):
```json
{"state":"stop","battery":4,"version":"0830",
 "time":"2026-04-04T07:21:49.000Z","loraInfo":{"signal":-73,...}}
```

**No fingerprint ID in this `setState` event.** Possibilities:
- Fingerprint metadata may live in a `StatusChange` or `Report` event we haven't captured yet (would need to press via fingerprint specifically and watch for events with different `event` types)
- The YoLink cloud API may not expose fingerprint ID at all (only the YoLink app might know which user pressed)
- Different firmware versions may differ

Need more capture: press via fingerprint (not app), capture both
`StatusChange` and any other event types, before drawing conclusions.

## Suggested PR

Defer until additional MQTT capture answers the fingerprint-id question.
