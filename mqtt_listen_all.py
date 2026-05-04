#!/usr/bin/env python3
"""
Subscribe to YoLink MQTT real-time push for the whole home.

Captures every event message and appends it as one JSON line into:
    device-<typelower>/events/<sanitized-device-name>.jsonl

Why MQTT instead of polling?
  Many fields YoLink sends in push reports don't appear in fetchState
  (e.g. battery%, motion duration, leak duration, finger fingerprint id,
  smart-fob long-press, plug power surge events, etc.).  This is the
  best way to find "lazy" missing fields in the HA integration.

Usage:
    YOLINK_UAID=... YOLINK_SECRET_KEY=... python3 mqtt_listen_all.py [minutes]
default minutes = 60.

Trigger your devices manually during the run (open door, push fob,
toggle plug, etc.) to capture every event type each device emits.
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
from aiomqtt import Client, MqttError, ProtocolVersion
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.yosmart.com/open/yolink/v2/api"
TOKEN_URL = "https://api.yosmart.com/open/yolink/token"
MQTT_HOST_US = "api.yosmart.com"
MQTT_PORT = 8003

ROOT = Path(__file__).parent

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


async def get_access_token(session: aiohttp.ClientSession, uaid: str, secret: str) -> str:
    async with session.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": uaid,
            "client_secret": secret,
        },
    ) as resp:
        resp.raise_for_status()
        return (await resp.json())["access_token"]


async def get_home_id_and_devices(
    session: aiohttp.ClientSession, token: str,
) -> tuple[str, dict[str, dict]]:
    headers = {"Authorization": f"Bearer {token}"}
    async with session.post(
        API_URL, json={"method": "Home.getGeneralInfo"}, headers=headers,
    ) as resp:
        resp.raise_for_status()
        data = await resp.json()
        home_id = data["data"]["id"]

    async with session.post(
        API_URL, json={"method": "Home.getDeviceList"}, headers=headers,
    ) as resp:
        resp.raise_for_status()
        data = await resp.json()
        devs = {
            d["deviceId"]: d for d in data.get("data", {}).get("devices", [])
        }
    return home_id, devs


def event_log_path(device: dict) -> Path:
    dtype = device.get("type", "Unknown")
    folder = TYPE_TO_FOLDER.get(dtype, "device-other")
    out_dir = ROOT / folder / "events"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"{slugify(device.get('name', device['deviceId']))}.jsonl"


async def main() -> None:
    minutes = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    duration_sec = minutes * 60

    uaid = os.environ.get("YOLINK_UAID")
    secret = os.environ.get("YOLINK_SECRET_KEY")
    if not uaid or not secret:
        print("Set YOLINK_UAID and YOLINK_SECRET_KEY (in env or .env).", file=sys.stderr)
        sys.exit(1)

    async with aiohttp.ClientSession() as session:
        print("Authenticating...")
        token = await get_access_token(session, uaid, secret)
        print("Fetching home + devices...")
        home_id, devices = await get_home_id_and_devices(session, token)
        print(f"Home {home_id}, {len(devices)} devices.")
        print(f"Listening for {minutes} minutes (until ~{time.strftime('%H:%M:%S', time.localtime(time.time()+duration_sec))}).\n")
        print("Trigger your devices now (open door, press fob, toggle plug, etc.)\n")

        # event-type counts for live status
        type_counts: dict[str, int] = {}
        per_dev_counts: dict[str, int] = {}
        topic = f"yl-home/{home_id}/+/report"

        deadline = time.time() + duration_sec

        try:
            async with Client(
                hostname=MQTT_HOST_US,
                port=MQTT_PORT,
                username=token,
                password="",
                keepalive=60,
                protocol=ProtocolVersion.V311,
            ) as client:
                await client.subscribe(topic)
                print(f"Subscribed to {topic}\n")

                async def watchdog():
                    await asyncio.sleep(duration_sec)
                    raise asyncio.CancelledError()

                wd = asyncio.create_task(watchdog())

                try:
                    async for msg in client.messages:
                        if time.time() > deadline:
                            break
                        try:
                            payload = json.loads(msg.payload.decode("utf-8"))
                        except Exception:
                            continue
                        # Topic shape: yl-home/{home}/{deviceId}/report
                        parts = str(msg.topic).split("/")
                        if len(parts) != 4 or parts[3] != "report":
                            continue
                        dev_id = parts[2]
                        device = devices.get(dev_id)
                        if device is None:
                            continue

                        entry = {
                            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                            "deviceId": dev_id,
                            "deviceName": device.get("name"),
                            "deviceType": device.get("type"),
                            "deviceModel": device.get("modelName"),
                            "topic": str(msg.topic),
                            "event": payload.get("event"),
                            "payload": payload,
                        }
                        path = event_log_path(device)
                        with path.open("a") as f:
                            f.write(json.dumps(entry) + "\n")

                        ev = payload.get("event", "?")
                        type_counts[ev] = type_counts.get(ev, 0) + 1
                        per_dev_counts[device.get("name", dev_id)] = (
                            per_dev_counts.get(device.get("name", dev_id), 0) + 1
                        )
                        sys.stdout.write(
                            f"\r[{time.strftime('%H:%M:%S')}] "
                            f"{sum(type_counts.values()):4d} msgs | "
                            f"last: {device.get('name','?'):20s} {ev:35s}\033[K"
                        )
                        sys.stdout.flush()
                except asyncio.CancelledError:
                    pass
                finally:
                    wd.cancel()
        except MqttError as e:
            print(f"\nMQTT error: {e}")

        print("\n\n=== Summary by event type ===")
        for ev, n in sorted(type_counts.items(), key=lambda x: -x[1]):
            print(f"  {n:4d}  {ev}")
        print("\n=== Summary by device ===")
        for name, n in sorted(per_dev_counts.items(), key=lambda x: -x[1]):
            print(f"  {n:4d}  {name}")
        print("\nLog files written under device-*/events/")


if __name__ == "__main__":
    asyncio.run(main())
