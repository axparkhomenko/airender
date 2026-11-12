"""Validate an Airender room brief before scene generation (Python stdlib only)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate(spec):
    errors, warnings = [], []
    dims = spec.get("room_dimensions_mm", {})
    keys = ("width_x", "length_y", "ceiling_height_z", "wardrobe_start_y")
    for key in keys:
        if not isinstance(dims.get(key), (int, float)) or dims[key] <= 0:
            errors.append(f"room_dimensions_mm.{key} must be a positive number")
    if errors:
        return errors, warnings

    width, length, height = dims["width_x"], dims["length_y"], dims["ceiling_height_z"]
    wardrobe_y = dims["wardrobe_start_y"]
    if wardrobe_y >= length:
        errors.append("wardrobe_start_y must be less than room length")
    if wardrobe_y < 0:
        errors.append("wardrobe_start_y cannot be negative")

    for opening in spec.get("openings", []):
        wall = opening.get("wall")
        span = width if wall in ("north", "south") else length
        opening_width = opening.get("width", 0)
        opening_height = opening.get("height", 0)
        sill = opening.get("sill_height", 0)
        center = opening.get("center_along_wall", span / 2)
        if opening_width <= 0 or opening_height <= 0:
            errors.append(f"{opening.get('name', 'opening')}: width and height must be positive")
        if center - opening_width / 2 < 0 or center + opening_width / 2 > span:
            errors.append(f"{opening.get('name', 'opening')}: opening exceeds host wall span")
        if sill < 0 or sill + opening_height > height:
            errors.append(f"{opening.get('name', 'opening')}: vertical opening bounds exceed room")

    for key, item in spec.get("furniture", {}).items():
        if not isinstance(item, dict) or "position_mm" not in item:
            continue
        pos = item["position_mm"]
        if len(pos) != 3:
            errors.append(f"furniture.{key}.position_mm must have three coordinates")
            continue
        item_w = item.get("width", 0)
        item_l = item.get("length", item.get("depth", 0))
        if pos[0] < 0 or pos[1] < 0 or pos[0] + item_w > width or pos[1] + item_l > length:
            warnings.append(f"furniture.{key} bounding box may extend outside the room")

    if wardrobe_y == 4000 and length == 5400:
        warnings.append(
            "Brief places the wardrobe zone at Y=4000..5400 while also naming the far north wall "
            "as the headboard wall; confirm the intended bed/headboard orientation and partition layout."
        )
    return errors, warnings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("spec", nargs="?", default=str(Path(__file__).resolve().parents[1] / "config" / "bedroom_neoclassical.json"))
    args = parser.parse_args()
    with open(args.spec, "r", encoding="utf-8") as handle:
        spec = json.load(handle)
    errors, warnings = validate(spec)
    for warning in warnings:
        print("WARNING:", warning)
    for error in errors:
        print("ERROR:", error)
    if errors:
        raise SystemExit(1)
    print("Brief validation passed (warnings require human review).")


if __name__ == "__main__":
    main()
