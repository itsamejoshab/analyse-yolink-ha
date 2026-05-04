#!/usr/bin/env python3
"""
Test script to explore YoLink SprinklerV2 API payloads.

Calls getState on your SprinklerV2 device and dumps the FULL raw JSON
response so we can see what water usage / flow / meter fields exist
beyond what the HA integration currently exposes.

Usage:
    1. Get your UAID and Secret Key from https://www.yosmart.com
       -> Settings -> Account -> Advanced Settings -> User Access Credentials
    2. Run:
       YOLINK_UAID=your_uaid YOLINK_SECRET_KEY=your_secret python3 test_sprinkler_api.py
"""

import asyncio
import json
import os
import sys

import aiohttp
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.yosmart.com/open/yolink/v2/api"
TOKEN_URL = "https://api.yosmart.com/open/yolink/token"

SPRINKLER_TYPES = {"Sprinkler", "SprinklerV2"}


async def get_access_token(session: aiohttp.ClientSession, uaid: str, secret: str) -> str:
    """Get access token via client_credentials grant."""
    async with session.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": uaid,
            "client_secret": secret,
        },
    ) as resp:
        resp.raise_for_status()
        data = await resp.json()
        return data["access_token"]


async def api_call(session: aiohttp.ClientSession, token: str, body: dict) -> dict:
    """POST to YoLink API, return raw JSON dict."""
    headers = {"Authorization": f"Bearer {token}"}
    async with session.post(API_URL, json=body, headers=headers) as resp:
        resp.raise_for_status()
        return await resp.json()


async def main() -> None:
    uaid = os.environ.get("YOLINK_UAID")
    secret = os.environ.get("YOLINK_SECRET_KEY")

    if not uaid or not secret:
        print("Set YOLINK_UAID and YOLINK_SECRET_KEY env vars.")
        print("Get them from: yosmart.com -> Settings -> Account -> Advanced Settings -> User Access Credentials")
        sys.exit(1)

    async with aiohttp.ClientSession() as session:
        print("Authenticating...")
        token = await get_access_token(session, uaid, secret)
        print("OK\n")

        # List devices
        print("Fetching device list...")
        device_list = await api_call(session, token, {"method": "Home.getDeviceList"})
        devices = device_list.get("data", {}).get("devices", [])

        sprinklers = [d for d in devices if d.get("type") in SPRINKLER_TYPES]

        if not sprinklers:
            print("No sprinkler devices found. All devices:")
            for d in devices:
                print(f"  {d.get('name')} | type={d.get('type')} | model={d.get('modelName')} | id={d.get('deviceId')}")
            sys.exit(0)

        print(f"Found {len(sprinklers)} sprinkler(s):\n")

        for spr in sprinklers:
            dev_id = spr["deviceId"]
            dev_token = spr["token"]
            dev_type = spr["type"]
            dev_name = spr.get("name", "?")
            dev_model = spr.get("modelName", "?")

            print(f"{'='*70}")
            print(f"Device: {dev_name}  |  type: {dev_type}  |  model: {dev_model}")
            print(f"ID: {dev_id}")
            print(f"{'='*70}\n")

            # --- getState (raw, no message resolution) ---
            print(f">>> {dev_type}.getState")
            state_resp = await api_call(session, token, {
                "method": f"{dev_type}.getState",
                "targetDevice": dev_id,
                "token": dev_token,
            })
            print(json.dumps(state_resp, indent=2))
            print()

            # --- fetchState (cached state from cloud) ---
            print(f">>> {dev_type}.fetchState")
            try:
                fetch_resp = await api_call(session, token, {
                    "method": f"{dev_type}.fetchState",
                    "targetDevice": dev_id,
                    "token": dev_token,
                })
                print(json.dumps(fetch_resp, indent=2))
            except Exception as e:
                print(f"  fetchState failed: {e}")
            print()

            # --- getSchedules ---
            print(f">>> {dev_type}.getSchedules")
            try:
                sched_resp = await api_call(session, token, {
                    "method": f"{dev_type}.getSchedules",
                    "targetDevice": dev_id,
                    "token": dev_token,
                    "params": {"offset": 0},
                })
                print(json.dumps(sched_resp, indent=2))
            except Exception as e:
                print(f"  getSchedules failed: {e}")
            print()

            # --- Try undocumented methods that might exist ---
            for method in ["getWaterUsage", "getHistory", "getMeterReading"]:
                print(f">>> {dev_type}.{method} (speculative)")
                try:
                    resp = await api_call(session, token, {
                        "method": f"{dev_type}.{method}",
                        "targetDevice": dev_id,
                        "token": dev_token,
                    })
                    print(json.dumps(resp, indent=2))
                except Exception as e:
                    print(f"  {method} -> {e}")
                print()


if __name__ == "__main__":
    asyncio.run(main())
