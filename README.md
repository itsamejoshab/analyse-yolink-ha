# analyse-yolink-ha

Tooling and analysis to find Home Assistant `yolink` integration entities
that should exist but don't - by snapshotting and listening to every
device in a home, then diffing the raw payloads against what
[`homeassistant/components/yolink`][ha-yolink] currently exposes.

Each truly missing field is a small PR opportunity. Precedent:
[home-assistant/core#168742][prev-pr] for SprinklerV2.

[ha-yolink]: https://github.com/home-assistant/core/tree/dev/homeassistant/components/yolink
[prev-pr]: https://github.com/home-assistant/core/pull/168742

## Setup (first time)

```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env with your YoLink UAID + secret key
#   yosmart.com -> Settings -> Account -> Advanced -> User Access Credentials
```

## Tools

All scripts live at the repo root. Output lands in
`device-<typelower>/{snapshots,events}/` (both gitignored).

| Script | Purpose | Use when |
|--------|---------|----------|
| `discover_all.py` | One-shot snapshot: calls `getState` + `fetchState` for every device, dumps to per-device JSON | Starting an investigation; refreshing baseline state |
| `mqtt_listen_all.py [min]` | Subscribes to YoLink MQTT real-time push for whole home, appends each event to per-device JSONL | Capturing state changes, alerts, push reports as you trigger devices |
| `poll_live.py "<deviceName>" [sec]` | Polls one device's `getState` every N seconds, prints power/state/etc. | Verifying a specific field actually populates under load |
| `watch_events.py` | `tail -f`-style monitor across all `device-*/events/*.jsonl` files | Run alongside `mqtt_listen_all.py` in a second terminal to see events live |

## Workflow: starting fresh

```bash
# 1. snapshot baseline (~30s, saves to device-*/snapshots/)
python3 discover_all.py

# 2. start MQTT capture in background (or its own terminal)
python3 mqtt_listen_all.py 240

# 3. (separate terminal) live event watcher
python3 watch_events.py

# 4. trigger devices manually:
#    open doors, press fobs, walk past PIRs, toggle plugs, etc.
#    each event appears in watch_events.py and appends to a JSONL file

# 5. when done
pkill -f mqtt_listen_all
```

## Workflow: picking back up later

Resumable - existing snapshots and events stay where they are.

```bash
cd analyse-yolink-ha

# Refresh snapshots (overwrites device-*/snapshots/)
python3 discover_all.py

# Resume MQTT capture (appends to existing event JSONLs)
python3 mqtt_listen_all.py 240

# Watch live in another terminal
python3 watch_events.py

# Verify a single device under load (e.g. confirm a power field populates)
python3 poll_live.py "Attic Fan Power" 15

# Tally what's been captured per device
python3 -c "
import glob
from collections import Counter
total = 0
for f in sorted(glob.glob('device-*/events/*.jsonl')):
    n = sum(1 for _ in open(f))
    total += n
    if n: print(f'  {n:4d}  {f}')
print(f'TOTAL: {total} events')
"

# Stop background capture when done
pkill -f mqtt_listen_all
```

## Per-device-type analysis

Each `device-<type>/analysis.md` lists:
- what HA exposes today (file/line refs into `core/homeassistant/components/yolink/`)
- raw fields actually returned by your devices (snapshot + MQTT-derived)
- ranked PR suggestions, with verification status

See [`INVESTIGATION.md`](INVESTIGATION.md) for the master cross-type ranked list.

## Critical methodology lesson (learned 2026-05-04)

Initial Tier A list flagged 3 PRs based on snapshot field-name presence.
Live load testing revealed **2 of 3 were invalid**:

- YS6604-UC outdoor plug "reports" `power`/`watt` keys but always returns 0 -- no current-sensing hardware
- YS5706-UC switch same situation -- firmware schema fields, no measurement chip

**Field present in raw JSON != hardware actually measures it.**

Rule for any future PR: before adding a sensor that surfaces a numeric
device field, verify the field reaches a non-zero / non-default value
under expected conditions. Use `poll_live.py` while exercising the
device. For binary alarm flags, force the alarm to fire (or wait for it
naturally) before assuming the field works.

For state-derived sensors (e.g. `stateChangedAt` timestamps), the
snapshot already proves they update -- those are safe to PR directly.

## Layout

```
discover_all.py             snapshot all
mqtt_listen_all.py          MQTT capture all
poll_live.py                getState poll one device
watch_events.py             tail event files
INVESTIGATION.md            master ranked PR list with verification status
.env.example                template for credentials
device-thsensor/
    analysis.md             current HA exposure + missing fields + PR notes
    snapshots/              gitignored, populated by discover_all
    events/                 gitignored, populated by mqtt_listen_all + poll_live
device-doorsensor/
device-leaksensor/
device-outlet/
device-motionsensor/
device-finger/
device-smartremoter/
device-switch/
device-manipulator/         empty in my home (no Manipulator devices)
device-sprinklerv2/         pre-existing test scripts from PR #168742 work
device-other/               Hub etc.
```

## Safety

- `.env` gitignored. **Never commit YoLink UAID or secret key.**
- `device-*/snapshots/` and `device-*/events/` gitignored - they
  contain device IDs, gateway IDs, and your home id (no auth secrets,
  but identifying).
- Only `analysis.md` files (your conclusions) and the scripts are
  committed.
