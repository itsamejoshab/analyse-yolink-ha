# YoLink missing-entity investigation

Goal: find fields YoLink devices emit but the Home Assistant `yolink`
integration ignores. Each one is a small PR (like #168742 for SprinklerV2)
that benefits every user of that device.

See [`README.md`](README.md) for the toolset and workflow.

## Tier system

Each candidate PR is tagged by VERIFICATION STATUS, not optimism:

- **VERIFIED** -- field reaches non-default value in real captured data
- **NEEDS VERIFICATION** -- field present in raw, but never seen non-default
- **INVALID** -- live test proved field is always 0 / never populates

## VERIFIED PRs (safe to write now)

| PR | Device types | Source | Notes |
|----|---|---|---|
| **`last_state_change` timestamp sensor** | DoorSensor, LeakSensor, MotionSensor, THSensor | `state.stateChangedAt` (epoch ms) | Universal across types. Confirmed updating: captured DoorSensor.Alert with `stateChangedAt: 1777908102507` matching the wall-clock event time. ~30 line PR, 4 device types covered. Highest-value single PR. |
| **Add YS6602-UC/EC to `coreTemperature` exists_fn** | Outlet | `state.coreTemperature` (snapshot showed `37` on `plug_misc`) | 3-line diff in `sensor.py`. Existing entity simply needs YS6602 added to its `exists_fn` whitelist (currently YS6614 only). |

## NEEDS VERIFICATION (do not PR until field observed non-default)

| Candidate | Device types | Why needs verify |
|---|---|---|
| 5 THSensor alarm binary_sensors (`lowBattery`, `lowTemp`, `highTemp`, `lowHumidity`, `highHumidity`) | THSensor | All 12 of my sensors emit these flags but all are `false`. Need to force one true (tighten a `tempLimit`) or wait for a real condition. |
| 5 Outlet `alertType.*` binary_sensors (`overload`, `highLoad`, `lowLoad`, `highTemperature`, `remind`) | Outlet | Same situation. `overload` would require unsafe load to test. |
| LeakSensor `detectorError` / `freezeError` | LeakSensor | `detectorError` already used internally for availability. Verify by unplugging probe. |
| Finger `fingerprintId` press attribution | Finger | `Finger.setState` event captured does NOT contain fingerprint ID. Need to capture press-via-fingerprint (not app) and look for other event types. |
| THSensor `DataRecord` historical samples | THSensor | Confirmed event type fires with array of `{time,temperature,humidity}` samples. Need to check whether HA surfaces these or only latest. |
| `alertType` field in DoorSensor push events | DoorSensor | Captured `"alertType":"normal"` in `DoorSensor.Alert`. Other values (e.g. `"tamper"`) need to be observed. |

## INVALID (verified 2026-05-04 -- do NOT PR)

| Candidate | Device | Why invalid |
|---|---|---|
| ~~Add YS6604-UC/EC to `POWER_SUPPORT_MODELS`~~ | YS6604 outdoor plug | Live load test (`poll_live.py "Attic Fan Power" 15`) with fans drawing real load: `power=0, watt=0` across 4 polls. Push events on toggle also lack `power`/`watt` fields. Firmware schema field present, no current-sensing hardware. |
| ~~Switch (YS5706) power+watt sensors~~ | YS5706 wall switch | Same: `power=0, watt=0` even when state=open. No measurement chip. |

## Configuration entities (need yolink-api setter support first)

These would all be useful but require new methods in the upstream
`yolink-api` library. Defer until that lands:

- THSensor temperature/humidity limits + correction (4 numbers)
- Outlet `delay.on`/`delay.off` countdown timers (number)
- Outlet `powerLimitHigh`/`Low` thresholds (number)
- MotionSensor `nomotionDelay`, `sensitivity`, `ledAlarm`
- Switch `pulseMode.enable` + `pulseMode.duration`
- LeakSensor `beep`, `sensitivity`

## Critical methodology lesson

Initial scan based on snapshot field-name presence flagged 3 PRs as
"Tier A" highest-impact. Live load testing revealed **2 of 3 were
invalid** because the device firmware exposes the field schema but
lacks the measurement hardware (always reads 0).

**Field present in raw JSON != hardware actually measures it.**

Workflow rule: for ANY PR adding a sensor that surfaces a numeric
device field, verify the field reaches a non-zero / non-default value
under expected conditions BEFORE writing the PR. Use `poll_live.py`
while exercising the device.

For binary alarm flags, force the alarm to fire (or wait for it
naturally) before assuming the field works. For state-derived sensors
(e.g. `stateChangedAt` timestamps), the snapshot already proves they
update -- those are safe to PR directly.

## Process for filing PRs

For each VERIFIED item:

1. Branch off `home-assistant/core` `dev` (`git checkout -b yolink-<name> upstream/dev`).
2. Add the field, plus a translation key in `strings.json`, plus a row in `icons.json` if appropriate.
3. Run `ruff format homeassistant tests`.
4. Tests: copy a sanitized snapshot from `device-<type>/snapshots/` into `tests/components/yolink/fixtures/` (token already stripped by `discover_all.py`).
5. Push to fork (`git push -u origin yolink-<name>`), open PR via web.
