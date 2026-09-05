#!/usr/bin/env python3
"""AIS live vessel capture for Singapore Strait (AISStream.io WebSocket).

Connects to wss://stream.aisstream.io/v0/stream, subscribes to the Singapore
Strait bounding box, and captures PositionReport + ShipStaticData messages.
Captures for a configurable duration, then outputs vessel snapshots.

Usage: .venv/bin/python experiments/ais_capture.py [duration_seconds] [output_json]
"""
import asyncio, json, os, sys, time
from datetime import datetime, timezone
from collections import defaultdict

import websockets

# Singapore Strait bounding box: [lat_max, lon_min], [lat_min, lon_max]
# AISStream format: BoundingBoxes: [[[lat1, lon1], [lat2, lon2]]]
BBOX = [[[1.6, 103.4], [1.0, 104.5]]]
WS_URL = "wss://stream.aisstream.io/v0/stream"

def get_key():
    env = dict(l.strip().split("=", 1) for l in open(".env") if "=" in l and not l.startswith("#"))
    return env.get("AISSTREAM_API_KEY", "")

async def capture(duration_s=60, output="experiments/results/ais_snapshot.json"):
    api_key = get_key()
    if not api_key:
        print("ERROR: AISSTREAM_API_KEY not in .env"); return

    vessels = defaultdict(lambda: {"positions": [], "static": None})
    msg_count = 0
    pos_count = 0
    static_count = 0
    t0 = time.time()

    print(f"Connecting to AISStream for {duration_s}s...", flush=True)

    try:
        async with websockets.connect(WS_URL, compression="deflate") as ws:
            # Send subscription within 3 seconds (API requirement)
            sub = json.dumps({
                "APIKey": api_key,
                "BoundingBoxes": BBOX,
                "FilterMessageTypes": ["PositionReport", "ShipStaticData"]
            })
            await ws.send(sub)
            print("  subscription sent", flush=True)

            # Read messages
            async for raw in ws:
                if time.time() - t0 > duration_s:
                    break
                try:
                    msg = json.loads(raw)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue

                msg_type = msg.get("MessageType")
                meta = msg.get("MetaData", {})
                mmsi = meta.get("MMSI")
                msg_count += 1

                if msg_type == "PositionReport":
                    pr = msg.get("Message", {}).get("PositionReport", {})
                    if not pr.get("Valid", False): continue
                    pos_count += 1
                    if mmsi:
                        vessels[mmsi]["positions"].append({
                            "t": datetime.now(timezone.utc).isoformat(),
                            "lat": pr.get("Latitude"),
                            "lon": pr.get("Longitude"),
                            "sog": pr.get("Sog"),
                            "cog": pr.get("Cog"),
                            "hdg": pr.get("TrueHeading"),
                            "nav_status": pr.get("NavigationalStatus"),
                        })
                        vessels[mmsi]["name"] = meta.get("ShipName", "")

                elif msg_type == "ShipStaticData":
                    sd = msg.get("Message", {}).get("ShipStaticData", {})
                    static_count += 1
                    if mmsi:
                        dim = sd.get("Dimension", {}) or {}
                        length = (dim.get("A", 0) or 0) + (dim.get("B", 0) or 0)
                        width = (dim.get("C", 0) or 0) + (dim.get("D", 0) or 0)
                        vessels[mmsi]["static"] = {
                            "name": meta.get("ShipName", sd.get("Name", "")),
                            "type": sd.get("Type"),
                            "length": length if length > 0 else None,
                            "width": width if width > 0 else None,
                            "destination": sd.get("Destination"),
                            "imo": sd.get("ImoNumber"),
                            "callsign": sd.get("CallSign"),
                            "draught": sd.get("MaximumStaticDraught"),
                        }

                if msg_count % 500 == 0:
                    elapsed = time.time() - t0
                    print(f"  {elapsed:.0f}s: {msg_count} msgs | {len(vessels)} vessels | {pos_count} pos | {static_count} static", flush=True)

    except Exception as e:
        print(f"  connection ended: {e}")

    elapsed = time.time() - t0
    print(f"\nCapture complete: {elapsed:.0f}s")
    print(f"  messages: {msg_count}")
    print(f"  position reports: {pos_count}")
    print(f"  static data: {static_count}")
    print(f"  unique vessels (MMSI): {len(vessels)}")

    # Build vessel snapshot (latest position + static data)
    snapshot = []
    for mmsi, v in vessels.items():
        latest = v["positions"][-1] if v["positions"] else None
        n_pos = len(v["positions"])
        entry = {
            "mmsi": mmsi,
            "name": v.get("name", ""),
            "n_positions": n_pos,
        }
        if latest:
            entry.update({"lat": latest["lat"], "lon": latest["lon"],
                         "sog": latest["sog"], "cog": latest["cog"],
                         "nav_status": latest["nav_status"]})
        if v["static"]:
            entry.update(v["static"])
        # Classify anchored (sog < 0.5 knots)
        if latest and latest.get("sog") is not None:
            entry["anchored"] = latest["sog"] < 0.5
        snapshot.append(entry)

    # Sort by name
    snapshot.sort(key=lambda x: x.get("name", ""))

    # Save
    out = {"captured_at": datetime.now(timezone.utc).isoformat(),
           "duration_s": round(elapsed),
           "total_messages": msg_count,
           "unique_vessels": len(vessels),
           "vessels": snapshot}
    with open(output, "w") as f:
        json.dump(out, f, indent=1)
    print(f"\nSaved {output} ({len(snapshot)} vessels)")

    # Summary
    anchored = sum(1 for v in snapshot if v.get("anchored"))
    with_type = sum(1 for v in snapshot if v.get("type") is not None)
    print(f"\nSummary:")
    print(f"  anchored (sog<0.5): {anchored}")
    print(f"  with static data: {with_type}")

    # Zone breakdown
    ZONES = {"port_core": (103.68,1.20,104.02,1.34),
             "eastern_opl": (104.00,1.24,104.35,1.40),
             "western_opl": (103.58,1.10,103.78,1.32)}
    zone_counts = defaultdict(int)
    for v in snapshot:
        lat, lon = v.get("lat"), v.get("lon")
        if lat is None or lon is None: continue
        zone = "strait_other"
        for zname, (w_, s_, e_, n_) in ZONES.items():
            if w_ <= lon <= e_ and s_ <= lat <= n_:
                zone = zname; break
        zone_counts[zone] += 1
    print(f"  zones: {dict(zone_counts)}")

    # Top-10 vessel types
    type_counts = defaultdict(int)
    for v in snapshot:
        t = v.get("type")
        if t is not None:
            type_counts[t] += 1
    if type_counts:
        print(f"  vessel types (AIS code): {dict(sorted(type_counts.items(), key=lambda x:-x[1])[:10])}")

    # Show first 10 named vessels
    named = [v for v in snapshot if v.get("name")]
    print(f"\n  sample vessels:")
    for v in named[:10]:
        print(f"    {v['name'][:20]:20s} | MMSI {v['mmsi']} | lat={v.get('lat','?')} lon={v.get('lon','?')} | sog={v.get('sog','?')} | type={v.get('type','?')}")

if __name__ == "__main__":
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    output = sys.argv[2] if len(sys.argv) > 2 else "experiments/results/ais_snapshot.json"
    asyncio.run(capture(duration, output))
