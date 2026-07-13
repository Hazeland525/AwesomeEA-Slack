#!/usr/bin/env python3
"""
Download persona avatars to scripts/avatars/.

Files are named <key>.jpg (e.g. jane.jpg, tim.jpg) so you can upload them
directly to each member's Slack profile:
  Profile → Edit profile → hover the avatar → Upload photo
"""

import sys
import urllib.request
from pathlib import Path

AVATARS = {
    "jane":      ("Jane Miller",      "https://randomuser.me/api/portraits/women/44.jpg"),
    "tim":       ("Tim Smith",        "https://randomuser.me/api/portraits/men/32.jpg"),
    "sue":       ("Sue Chen",         "https://randomuser.me/api/portraits/women/63.jpg"),
    "steven":    ("Steven Johnson",   "https://randomuser.me/api/portraits/men/52.jpg"),
    "philip":    ("Philip Lim",       "https://randomuser.me/api/portraits/men/75.jpg"),
    "elizabeth": ("Elizabeth Barry",  "https://randomuser.me/api/portraits/women/17.jpg"),
    "rosario":   ("Rosario Bennett",  "https://randomuser.me/api/portraits/women/90.jpg"),
}

out_dir = Path(__file__).parent / "avatars"
out_dir.mkdir(exist_ok=True)

ok = failed = 0
for key, (name, url) in AVATARS.items():
    dest = out_dir / f"{key}.jpg"
    try:
        urllib.request.urlretrieve(url, dest)
        size_kb = dest.stat().st_size // 1024
        print(f"  ✓ {name:20s} → avatars/{key}.jpg  ({size_kb} KB)")
        ok += 1
    except Exception as e:
        print(f"  ✗ {name}: {e}", file=sys.stderr)
        failed += 1

print(f"\nSaved {ok} avatars to {out_dir}")
if failed:
    sys.exit(1)
