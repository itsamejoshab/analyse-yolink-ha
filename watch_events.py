#!/usr/bin/env python3
"""Tail all device-*/events/*.jsonl files. Prints each new event as it arrives."""
from __future__ import annotations
import glob, json, os, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def scan():
    return {f: os.path.getsize(f) for f in glob.glob(str(ROOT / "device-*/events/*.jsonl"))}

def fmt(line):
    try:
        e = json.loads(line)
        ts = e.get("ts", "?")[11:19]
        name = e.get("deviceName", "?")
        typ = e.get("deviceType", "?")
        ev = e.get("event", "?")
        data = (e.get("payload") or {}).get("data") or {}
        keys = ",".join(sorted(data.keys()))[:60]
        return f"[{ts}] {typ:14s} {name:25s} {ev:35s} keys={keys}"
    except Exception as ex:
        return f"PARSE ERR: {ex} | {line[:120]}"

def main():
    print(f"Watching {ROOT}/device-*/events/*.jsonl  (Ctrl+C to stop)")
    print("-" * 100)
    sizes = scan()
    while True:
        time.sleep(1.0)
        new_sizes = scan()
        for f, sz in new_sizes.items():
            old = sizes.get(f, 0)
            if sz > old:
                with open(f) as fh:
                    fh.seek(old)
                    for line in fh:
                        line = line.strip()
                        if line:
                            print(fmt(line))
                            sys.stdout.flush()
        sizes = new_sizes

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
