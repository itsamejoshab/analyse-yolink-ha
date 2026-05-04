# YoLink missing-entity investigation

Goal: find fields YoLink devices emit but the Home Assistant `yolink`
integration ignores. Each one is a small PR (like #168742 for SprinklerV2)
that benefits every user of that device.

## Layout

```
discover_all.py             # one-shot snapshot of all devices
mqtt_listen_all.py [min]    # MQTT real-time push capture (default 60 min)
requirements.txt            # aiohttp, aiomqtt, python-dotenv
devices.json                # sanitized device list (no tokens)
device-thsensor/            # one folder per YoLink device "type"
    snapshots/<name>.json   # one JSON per device, written by discover_all
    events/<name>.jsonl     # MQTT push events, written by mqtt_listen_all
    analysis.md             # current HA exposure + confirmed missing fields
device-doorsensor/
device-leaksensor/
device-outlet/
device-motionsensor/
device-finger/
device-smartremoter/
device-switch/
device-manipulator/         # currently empty (no Manipulator devices)
device-sprinklerv2/         # pre-existing (PR #168742)
device-other/               # Hub etc.
```

## Workflow

```bash
pip install -r requirements.txt          # one time

python3 discover_all.py                  # ~30s, fills snapshots/
python3 mqtt_listen_all.py 60            # 1h MQTT capture, fills events/

# Then per device type, list every key path ever seen:
TYPE=outlet
python3 -c "
import json, glob
from collections import Counter
def walk(d, p=''):
    if isinstance(d, dict):
        for k,v in d.items(): yield from walk(v, f'{p}.{k}' if p else k)
    elif isinstance(d, list):
        for v in d: yield from walk(v, f'{p}[]')
    else: yield p
seen = Counter()
for f in glob.glob(f'device-$TYPE/snapshots/*.json'):
    d = json.load(open(f))
    for s in (d.get('getState'), d.get('fetchState')):
        if s:
            for k in walk(s.get('data', {})): seen[k] += 1
for f in glob.glob(f'device-$TYPE/events/*.jsonl'):
    for line in open(f):
        e = json.loads(line)
        for k in walk(e.get('payload', {}).get('data', {})): seen[k] += 1
for k,n in sorted(seen.items()): print(f'{n:4d}  {k}')
"
```

## Confirmed PR opportunities (after one snapshot run)

Ranked by impact-per-line-of-diff. Full detail in each `analysis.md`.

### TIER A - one/two-line PRs, immediate value

| PR                                                               | File              | Rationale |
|------------------------------------------------------------------|-------------------|-----------|
| **Add YS6604-UC/EC to `POWER_SUPPORT_MODELS`**                   | `sensor.py`       | YS6604 outdoor plug reports `power` and `watt` already; integration ignores it. Affects every YS6604 user worldwide. |
| **Add YS6602-UC/EC to `coreTemperature` exists_fn**              | `sensor.py`       | YS6602 reports coreTemperature (37 in your snapshot). Currently only YS6614 exposes this. |
| **Switch (YS5706) power+watt sensors**                           | `sensor.py`       | YS5706 reports `power` & `watt` like outlets but `Switch` device type isn't in any power model list. |

### TIER B - small PRs, multiple new entities

| PR                                                               | Notes |
|------------------------------------------------------------------|-------|
| **THSensor 5 alarm binary_sensors** (`lowBattery`, `lowTemp`, `highTemp`, `lowHumidity`, `highHumidity`) | All 12 of your THSensors emit these flags. PROBLEM device class. |
| **Outlet 5 alertType binary_sensors** (`overload`, `highLoad`, `lowLoad`, `highTemperature`, `remind`) | Both YS6602 and YS6604 emit these. Real safety alarms currently invisible. |
| **LeakSensor `detector_error` + `freeze_error` binary_sensors**  | Already used internally for availability suppression on detectorError; surface them so users know WHY. `freezeError` is unique alarm not exposed anywhere. |
| **Universal `last_state_change` timestamp sensor** (DoorSensor / LeakSensor / MotionSensor / THSensor) | All emit `state.stateChangedAt` (epoch ms). One helper, four device types, hugely useful for "x has been open/wet/quiet for N min" automations. |

### TIER C - configuration entities (need yolink-api setter support first)

| PR                              | Notes |
|---------------------------------|-------|
| THSensor temperature/humidity limits + correction (4 numbers) | adjustable thresholds |
| Outlet `delay.on`/`delay.off` countdown timers (number)        |  |
| Outlet `powerLimitHigh`/`Low` thresholds (number)              | source of overload alarm |
| MotionSensor `nomotionDelay`, `sensitivity`, `ledAlarm`        |  |
| Switch `pulseMode.enable` + `duration`                         | momentary-press relay mode |
| LeakSensor `beep`, `sensitivity`                               |  |

### Open questions (need MQTT capture)

- Finger: does press event include `fingerprintId` / `userId`? - run `mqtt_listen_all.py` and press both Fingers via app + via fingerprint.
- SmartRemoter: are all `keyMask` values currently mapped in `device_trigger.py`?
- Outlet `state.power` - does it report non-zero values when load is on (snapshot caught all at 0)?

## Process for filing PRs

For each TIER A/B item:

1. Branch off `home-assistant/core` `dev` like the SprinklerV2 PR did.
2. Add the field, plus a translation key in `strings.json`, plus a row in `icons.json` if appropriate.
3. Run `ruff format homeassistant tests`.
4. If you can't write a test against your real device (snapshot-driven test fixtures live under `tests/components/yolink/`), copy the snapshot file from `device-<type>/snapshots/` into the test fixtures (with token already stripped by `discover_all.py`).

## Safety notes

- `discover_all.py` strips device `token` from `devices.json`.
- Per-device snapshot files contain only state data (no token).
- `events/*.jsonl` contains your home id in the topic and raw payloads but no auth secrets.
- `.env` has UAID/secret_key — never commit.
