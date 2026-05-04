# Manipulator (`Manipulator`) - low-hanging-fruit analysis

**No devices of this type in your home.** Your YS4103 hose timer
("hose_kiwi") reports `type=SprinklerV2`, not Manipulator — so it's
already covered by your in-flight PR #168742.

This folder is kept as a placeholder. If you ever add a YoLink valve
actuator that classifies as `Manipulator` (e.g. older Sprinkler models
or some imports), `discover_all.py` will populate `snapshots/` here.

## What HA currently does for Manipulator

For reference - if you ever do get one:

| Platform | Entity         | Source field    |
|----------|----------------|-----------------|
| switch   | (valve on/off) | `data.state`    |
| sensor   | `battery`, `loraInfo` | diagnostic |

Likely missed entities (parallel to SprinklerV2 PR):
- `state.waterFlowing`         -> binary_sensor
- `state.noWaterWhenRunning`   -> binary_sensor PROBLEM
- `state.delay` countdown
- `state.totalWater` cumulative
