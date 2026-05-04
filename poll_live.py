#!/usr/bin/env python3
"""
Poll one YoLink device's getState every N seconds. Prints power/state/etc.
in a clean table and appends raw payload to a JSONL log so we can review
exact field values over time.

getState forces a live device read (fresher than fetchState's cached cloud
copy). Use this when you need to verify a field actually populates under
load (we learned the hard way that some firmware fields are always 0
because the device lacks measurement hardware).

Usage:
    python3 poll_live.py "Attic Fan Power"            # 15s default
    python3 poll_live.py "Attic Fan Power" 30         # every 30s
    python3 poll_live.py "<deviceId>" 15              # by id

Log lands in device-<typelower>/events/<name>_poll.jsonl
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

import aiohttp
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

API = "https://api.yosmart.com/open/yolink/v2/api"
TOKEN_URL = "https://api.yosmart.com/open/yolink/token"

TARGET = sys.argv[1] if len(sys.argv) > 1 else "Attic Fan Power"
INTERVAL = int(sys.argv[2]) if len(sys.argv) > 2 else 15

TYPE_TO_FOLDER: dict[str, str] = {
    "THSensor": "device-thsensor",
    "DoorSensor": "device-doorsensor",
    "LeakSensor": "device-leaksensor",
    "MultiCapsLeakSensor": "device-leaksensor",
    "Outlet": "device-outlet",
    "MultiOutlet": "device-outlet",
    "MotionSensor": "device-motionsensor",
    "Finger": "device-finger",
    "SmartRemoter": "device-smartremoter",
    "Switch": "device-switch",
    "Manipulator": "device-manipulator",
    "Sprinkler": "device-sprinklerv2",
    "SprinklerV2": "device-sprinklerv2",
}


def slugify(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", name.strip()).strip("_") or "unnamed"


async def get_token(s):
    async with s.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": os.environ["YOLINK_UAID"],
            "client_secret": os.environ["YOLINK_SECRET_KEY"],
        },
    ) as r:
        return (await r.json())["access_token"]


async def get_device(s, token, target):
    async with s.post(
        API, json={"method": "Home.getDeviceList"},
        headers={"Authorization": f"Bearer {token}"},
    ) as r:
        for d in (await r.json())["data"]["devices"]:
            if d.get("name") == target or d.get("deviceId") == target:
                return d
    return None


async def fetch(s, token, dev, method="getState"):
    async with s.post(
        API,
        json={
            "method": f"{dev['type']}.{method}",
            "targetDevice": dev["deviceId"],
            "token": dev["token"],
        },
        headers={"Authorization": f"Bearer {token}"},
    ) as r:
        return await r.json()


async def main():
    async with aiohttp.ClientSession() as s:
        token = await get_token(s)
        dev = await get_device(s, token, TARGET)
        if not dev:
            print(f"Device {TARGET!r} not found", file=sys.stderr)
            sys.exit(1)

        log_dir = ROOT / TYPE_TO_FOLDER.get(dev["type"], "device-other") / "events"
        log_dir.mkdir(parents=True, exist_ok=True)
        log = log_dir / f"{slugify(dev['name'])}_poll.jsonl"

        print(f"Polling {dev['name']} ({dev['deviceId']}, {dev['type']}, {dev['modelName']}) every {INTERVAL}s")
        print(f"Log -> {log.relative_to(ROOT)}")
        print(f"{'time':10s}  {'state':10s}  {'power':>8s}  {'watt':>8s}  reportAt")
        print("-" * 90)
        sys.stdout.flush()

        prev = None
        while True:
            try:
                resp = await fetch(s, token, dev)
                data = resp.get("data") or {}
                state = data.get("state") or {}
                if isinstance(state, dict):
                    s_val = state.get("state")
                    power = state.get("power")
                    watt = state.get("watt")
                else:
                    s_val, power, watt = state, data.get("power"), data.get("watt")
                report_at = data.get("reportAt", "?")
                cur = (s_val, power, watt)
                changed = "" if cur == prev else "  <-- CHANGED"
                print(
                    f"{time.strftime('%H:%M:%S'):10s}  {str(s_val):10s}  "
                    f"{str(power):>8s}  {str(watt):>8s}  {report_at}{changed}"
                )
                sys.stdout.flush()
                prev = cur
                with log.open("a") as f:
                    f.write(json.dumps({
                        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                        "raw": resp,
                    }) + "\n")
            except Exception as e:
                print(f"{time.strftime('%H:%M:%S')}  ERR: {e}")
                sys.stdout.flush()
            await asyncio.sleep(INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
