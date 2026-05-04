#!/usr/bin/env python3
"""
Poll SprinklerV2.getState every 10s for 10 minutes (stays within 6 calls/min).
Prints only fields that change between successful polls.

Run this, then open the valve from the YoLink app.
"""

import asyncio
import json
import os
import sys
from datetime import datetime

import aiohttp
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.yosmart.com/open/yolink/v2/api"
TOKEN_URL = "https://api.yosmart.com/open/yolink/token"

DEV_ID = "d88b4c030000e601"
DEV_TYPE = "SprinklerV2"
DEV_TOKEN = None  # filled from device list at startup

POLL_INTERVAL = 20
POLL_DURATION = 10 * 60


async def get_token_and_dev(session, uaid, secret):
    async with session.post(TOKEN_URL, data={
        "grant_type": "client_credentials",
        "client_id": uaid,
        "client_secret": secret,
    }) as resp:
        resp.raise_for_status()
        access_token = (await resp.json())["access_token"]

    headers = {"Authorization": f"Bearer {access_token}"}
    async with session.post(API_URL, json={"method": "Home.getDeviceList"}, headers=headers) as resp:
        resp.raise_for_status()
        data = await resp.json()
        for d in data.get("data", {}).get("devices", []):
            if d.get("deviceId") == DEV_ID:
                return access_token, d["token"]

    print(f"Device {DEV_ID} not found")
    sys.exit(1)


def flatten(d, prefix=""):
    items = {}
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            items.update(flatten(v, key))
        else:
            items[key] = v
    return items


LOG_FILE = "sprinkler_poll_log.jsonl"


def ts():
    return datetime.now().strftime("%H:%M:%S")


def log_to_file(entry):
    """Append one JSON line per response to the log file."""
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


async def main():
    uaid = os.environ.get("YOLINK_UAID")
    secret = os.environ.get("YOLINK_SECRET_KEY")
    if not uaid or not secret:
        print("Set YOLINK_UAID and YOLINK_SECRET_KEY in .env")
        sys.exit(1)

    async with aiohttp.ClientSession() as session:
        access_token, dev_token = await get_token_and_dev(session, uaid, secret)
        headers = {"Authorization": f"Bearer {access_token}"}

        with open(LOG_FILE, "w") as f:
            f.write("")

        print(f"Device: {DEV_ID} ({DEV_TYPE})")
        print(f"Polling every {POLL_INTERVAL}s for {POLL_DURATION // 60} min (rate-safe).")
        print(f"Logging every response to {LOG_FILE}")
        print(f"Open the valve from the YoLink app whenever ready.\n")

        prev_flat = None
        all_snapshots = []
        polls = 0
        elapsed = 0

        while elapsed < POLL_DURATION:
            try:
                async with session.post(API_URL, json={
                    "method": f"{DEV_TYPE}.fetchState",
                    "targetDevice": DEV_ID,
                    "token": dev_token,
                }, headers=headers) as resp:
                    raw = await resp.json()

                code = raw.get("code", "?")
                data = raw.get("data", {})
                polls += 1
                log_to_file({"ts": datetime.now().isoformat(), "elapsed": elapsed, "poll": polls, "raw": raw})

                if code != "000000":
                    print(f"[{ts()}] poll #{polls} +{elapsed}s -- {code}: {raw.get('desc', '?')}")
                    all_snapshots.append({"elapsed": elapsed, "code": code, "data": data})
                    await asyncio.sleep(POLL_INTERVAL)
                    elapsed += POLL_INTERVAL
                    continue

                cur_flat = flatten(data)

                if prev_flat is None:
                    print(f"[{ts()}] INITIAL STATE (poll #{polls}, +{elapsed}s):")
                    print(json.dumps(data, indent=2))
                    print()
                else:
                    changes = {
                        k: {"old": prev_flat.get(k), "new": v}
                        for k, v in cur_flat.items()
                        if prev_flat.get(k) != v
                    }
                    gone = {k for k in prev_flat if k not in cur_flat}
                    if changes or gone:
                        print(f"[{ts()}] CHANGES (poll #{polls}, +{elapsed}s):")
                        for k, ch in sorted(changes.items()):
                            print(f"  {k}: {ch['old']} -> {ch['new']}")
                        for k in sorted(gone):
                            print(f"  {k}: {prev_flat[k]} -> (removed)")
                        print()
                    else:
                        sys.stdout.write(f"[{ts()}] poll #{polls} +{elapsed}s -- no change\r")
                        sys.stdout.flush()

                prev_flat = cur_flat
                all_snapshots.append({"elapsed": elapsed, "code": code, "data": data})

            except Exception as e:
                print(f"\n[{ts()}] ERROR: {e}")

            await asyncio.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL

        print(f"\n\n{'='*70}")
        print("FINAL STATE:")
        last_good = next((s for s in reversed(all_snapshots) if s.get("code") == "000000"), None)
        if last_good:
            print(json.dumps(last_good["data"], indent=2))
        print(f"\nTotal polls: {polls}")

        with open("sprinkler_poll_log.json", "w") as f:
            json.dump(all_snapshots, f, indent=2)
        print("Full log saved to sprinkler_poll_log.json")


if __name__ == "__main__":
    asyncio.run(main())
