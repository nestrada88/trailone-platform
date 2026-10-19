#!/usr/bin/env python3
"""Generate/check the UI CSS palette from canonical immutable TrailOne palette JSON.

Usage: python scripts/sync_palette.py [--check]
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "frontend" / "brand" / "trailone.palette.json"
EXPECTED_SOURCE_HASH = "092f71bb78c05738e8189c181a0c97454269caedddd3d16794d7622fc94107e9"
OUTPUT = ROOT / "frontend" / "src" / "palette.css"


def main() -> int:
    actual = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if actual != EXPECTED_SOURCE_HASH:
        print(f"ERROR: canonical palette checksum mismatch: {actual}", file=sys.stderr)
        return 1
    spec = json.loads(SOURCE.read_text("utf-8"))
    if spec.get("version") != "1.0.0" or spec.get("status") != "APPROVED":
        print("ERROR: unexpected palette status/version", file=sys.stderr)
        return 1
    colors = spec["colors"]
    expected = ["forest", "mountain", "mountain_dark", "sage", "ochre", "sandstone", "ivory", "canvas"]
    if list(colors) != expected:
        print("ERROR: unexpected canonical token inventory", file=sys.stderr)
        return 1
    for token in expected:
        if colors[token]["hex"].upper() != colors[token]["hex"]:
            print(f"ERROR: invalid HEX case at {token}", file=sys.stderr)
            return 1
    result = ["/* GENERATED FILE — DO NOT EDIT. Source: brand/trailone.palette.json v1.0.0. */", ":root {"]
    result += [f"  --trailone-{key.replace('_', '-')}: {colors[key]['hex']};" for key in expected]
    result += ["}", ""]
    output_text = "\n".join(result)
    if "--check" in sys.argv:
        if not OUTPUT.exists() or OUTPUT.read_text() != output_text:
            print("ERROR: frontend/src/palette.css is not synchronized", file=sys.stderr)
            return 1
        print("PASS: approved palette and generated CSS match")
        return 0
    OUTPUT.write_text(output_text)
    print(f"Generated {OUTPUT.relative_to(ROOT)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
