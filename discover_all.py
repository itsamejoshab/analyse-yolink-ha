#!/usr/bin/env python3
"""
One-shot snapshot of every YoLink device in the home.

For each device:
  1. Calls <Type>.getState (live state from device, may fail for sleeping
     Class A/D battery devices).
  2. Calls <Type>.fetchState (cached state from cloud, almost always works).
  3. Saves merged result as JSON into:
        device-<typelower>/snapshots/<sanitized-device-name>.json

Device tokens are stripped before saving so the dumps can be safely
inspected/committed.

Usage:
    YOLINK_UAID=... YOLINK_SECRET_KEY=... python3 discover_all.py
or just `python3 discover_all.py` if creds are in .env.
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

load_dotenv()

API_URL = "https://api.yosmart.com/open/yolink/v2/api"
API_URL_EU = "https://api-eu.yosmart.com/open/yolink/v2/api"
TOKEN_URL = "https://api.yosmart.com/open/yolink/token"

ROOT = Path(__file__).parent

# Device type -> folder name (lowercase, no underscores).
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
    # Catch-all bucket for types not covered yet.
    "_other": "device-other",
}

# Devices that are known not to support certain methods.
HUB_TYPES = {"Hub", "SpeakerHub"}


def slugify(name: str) -> str:
    """Filesystem-safe device name."""
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", name.strip()).strip("_") or "unnamed"


def folder_for_type(device_type: str) -> Path:
    name = TYPE_TO_FOLDER.get(device_type, "device-other")
    out = ROOT / name / "snapshots"
    out.mkdir(parents=True, exist_ok=True)
    return out


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


async def api_call(
    session: aiohttp.ClientSession,
    token: str,
    body: dict,
    *,
    url: str = API_URL,
) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    async with session.post(url, json=body, headers=headers) as resp:
        resp.raise_for_status()
        return await resp.json()


async def snapshot_device(
    session: aiohttp.ClientSession,
    access_token: str,
    device: dict,
) -> tuple[Path, dict]:
    dev_id = device["deviceId"]
    dev_token = device["token"]
    dev_type = device["type"]
    dev_name = device.get("name", dev_id)
    dev_model = device.get("modelName", "?")

    is_hub = dev_type in HUB_TYPES

    base_url = (
        API_URL_EU if (device.get("modelName") or "").endswith("-EC") else API_URL
    )

    result: dict = {
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "device": {
            "deviceId": dev_id,
            "name": dev_name,
            "type": dev_type,
            "modelName": dev_model,
            "parentDeviceId": device.get("parentDeviceId"),
            "serviceZone": device.get("serviceZone"),
        },
        "getState": None,
        "fetchState": None,
        "errors": {},
    }

    if not is_hub:
        for method in ("getState", "fetchState"):
            try:
                resp = await api_call(
                    session,
                    access_token,
                    {
                        "method": f"{dev_type}.{method}",
                        "targetDevice": dev_id,
                        "token": dev_token,
                    },
                    url=base_url,
                )
                result[method] = resp
            except Exception as e:
                result["errors"][method] = str(e)

    out_dir = folder_for_type(dev_type)
    out_path = out_dir / f"{slugify(dev_name)}.json"
    out_path.write_text(json.dumps(result, indent=2, sort_keys=False))
    return out_path, result


async def main() -> None:
    uaid = os.environ.get("YOLINK_UAID")
    secret = os.environ.get("YOLINK_SECRET_KEY")
    if not uaid or not secret:
        print("Set YOLINK_UAID and YOLINK_SECRET_KEY (in env or .env).", file=sys.stderr)
        sys.exit(1)

    async with aiohttp.ClientSession() as session:
        print("Authenticating...")
        token = await get_access_token(session, uaid, secret)

        print("Fetching device list (US)...")
        devlist = await api_call(session, token, {"method": "Home.getDeviceList"})
        devices: list[dict] = devlist.get("data", {}).get("devices", [])

        print("Fetching device list (EU) for token sync...")
        try:
            eu_devlist = await api_call(
                session, token, {"method": "Home.getDeviceList"}, url=API_URL_EU,
            )
            eu_tokens = {
                d["deviceId"]: d["token"]
                for d in eu_devlist.get("data", {}).get("devices", [])
            }
            for d in devices:
                if (d.get("modelName") or "").endswith("-EC"):
                    if (eu := eu_tokens.get(d["deviceId"])) is not None:
                        d["token"] = eu
        except Exception as e:
            print(f"  EU device list failed (probably no EU devices): {e}")

        print(f"Found {len(devices)} devices.\n")

        # Save sanitized device list (tokens stripped) for reference.
        sanitized = [
            {k: v for k, v in d.items() if k != "token"} for d in devices
        ]
        (ROOT / "devices.json").write_text(json.dumps(sanitized, indent=2))
        print(f"  Wrote devices.json ({len(sanitized)} devices)\n")

        # Group by type for friendly summary.
        by_type: dict[str, list[dict]] = {}
        for d in devices:
            by_type.setdefault(d.get("type", "?"), []).append(d)

        for dtype in sorted(by_type):
            print(f"=== {dtype}  ({len(by_type[dtype])} devices) ===")
            for d in by_type[dtype]:
                try:
                    out_path, result = await snapshot_device(session, token, d)
                    err = result.get("errors") or {}
                    err_str = f"  ERR={list(err.keys())}" if err else ""
                    print(f"  {d.get('name','?'):30s} -> {out_path.relative_to(ROOT)}{err_str}")
                except Exception as e:
                    print(f"  {d.get('name','?'):30s} -> FAILED: {e}")
                # Be polite to API rate limits (~6 calls/min/device).
                await asyncio.sleep(0.3)

    print("\nDone.  Inspect:")
    for folder in sorted(set(TYPE_TO_FOLDER.values())):
        snap_dir = ROOT / folder / "snapshots"
        if snap_dir.exists() and any(snap_dir.iterdir()):
            n = sum(1 for _ in snap_dir.glob("*.json"))
            print(f"  {folder}/snapshots/  ({n} files)")


if __name__ == "__main__":
    asyncio.run(main())
