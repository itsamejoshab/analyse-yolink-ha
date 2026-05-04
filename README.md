# analyse-yolink-ha

Tooling and analysis to find Home Assistant `yolink` integration entities
that should exist but don't - by snapshotting and listening to every
device in a home and diffing the raw payloads against what the
[`homeassistant/components/yolink`][ha-yolink] integration currently
exposes.

Each missing field is a small PR opportunity (precedent:
[home-assistant/core#168742][prev-pr] for SprinklerV2).

[ha-yolink]: https://github.com/home-assistant/core/tree/dev/homeassistant/components/yolink
[prev-pr]: https://github.com/home-assistant/core/pull/168742

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env with your YoLink UAID + secret key
#   from yosmart.com -> Settings -> Account -> Advanced -> User Access Credentials
```

## Run

```bash
# 1. one-shot HTTP snapshot of every device (~30s)
python3 discover_all.py

# 2. MQTT real-time push capture (run for N minutes; trigger devices manually)
python3 mqtt_listen_all.py 60
```

Output goes into `device-<type>/snapshots/<name>.json` and
`device-<type>/events/<name>.jsonl`. Both directories are gitignored
(personal data).

## Analysis

For each YoLink device type, `device-<type>/analysis.md` lists:
- what HA exposes today (with file/line references)
- what the raw API actually returns (CONFIRMED missing fields after running discovery)
- ranked PR suggestions

See [`INVESTIGATION.md`](INVESTIGATION.md) for the master ranked list of
PR opportunities across all device types.

## Layout

```
discover_all.py             one-shot snapshot
mqtt_listen_all.py [min]    MQTT push capture
INVESTIGATION.md            master ranked PR list
.env.example                template for credentials
device-thsensor/
    analysis.md             current HA exposure + missing fields
    snapshots/              gitignored, populated by discover_all.py
    events/                 gitignored, populated by mqtt_listen_all.py
device-doorsensor/
device-leaksensor/
device-outlet/
device-motionsensor/
device-finger/
device-smartremoter/
device-switch/
device-manipulator/
device-sprinklerv2/         pre-existing test scripts from PR #168742 work
device-other/               Hub etc.
```

## Safety

- `.env` is gitignored. **Never commit YoLink UAID or secret key.**
- Per-device snapshot/event files are gitignored - they contain your
  device IDs, gateway IDs, and home id which are private (no auth
  secrets, but identifying).
- Only `analysis.md` files (your conclusions) are committed.
