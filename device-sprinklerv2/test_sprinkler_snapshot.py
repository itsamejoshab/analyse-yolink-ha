#!/usr/bin/env python3
"""Quick one-shot snapshot of sprinkler state."""
import asyncio, json, os, aiohttp
from dotenv import load_dotenv
load_dotenv()

API = "https://api.yosmart.com/open/yolink/v2/api"

async def main():
    async with aiohttp.ClientSession() as s:
        async with s.post("https://api.yosmart.com/open/yolink/token", data={
            "grant_type": "client_credentials",
            "client_id": os.environ["YOLINK_UAID"],
            "client_secret": os.environ["YOLINK_SECRET_KEY"],
        }) as r:
            token = (await r.json())["access_token"]

        h = {"Authorization": f"Bearer {token}"}

        async with s.post(API, json={"method": "Home.getDeviceList"}, headers=h) as r:
            resp = await r.json()
            devs = resp.get("data", {}).get("devices", [])
            if not devs:
                print("Device list response:", json.dumps(resp, indent=2))
                return
        spr = next(d for d in devs if d["type"] in ("Sprinkler", "SprinklerV2"))

        for method in ["getState", "fetchState"]:
            print(f"=== {spr['type']}.{method} ===")
            async with s.post(API, json={
                "method": f"{spr['type']}.{method}",
                "targetDevice": spr["deviceId"],
                "token": spr["token"],
            }, headers=h) as r:
                print(json.dumps(await r.json(), indent=2))
            print()

asyncio.run(main())
