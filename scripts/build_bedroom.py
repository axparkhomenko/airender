"""Build the sample bedroom scene in Blender 4.x.

Usage:
  blender --background --python scripts/build_bedroom.py -- --spec config/bedroom_neoclassical.json --output output
  blender --background --python scripts/build_bedroom.py -- --spec config/bedroom_neoclassical.json --output output --final
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from archviz_generators import (
    create_herringbone_parquet_material, create_herringbone_floor,
    create_wall_molding, create_fluted_glass_material,
    create_led_cove_light, create_brass_sconce,
    create_chinoiserie_mural_material,
)


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", default=str(ROOT / "config" / "bedroom_neoclassical.json"))
    parser.add_argument("--output", default=str(ROOT / "output"))
    parser.add_argument("--final", action="store_true")
    return parser.parse_args(argv)


def hex_rgb(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i+2], 16)/255 for i in (0, 2, 4))


def material(name, color, roughness=0.6, metallic=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def cube(name, loc, dims, mat=None, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new("Edge softness", "BEVEL")
        mod.width = bevel
        mod.segments = 3
        obj.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")
    return obj


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_camera(data, item, output_dir, final):
    cam_data = bpy.data.cameras.new(item["name"])
    cam_data.lens = item["lens_mm"]
    cam = bpy.data.objects.new(item["name"], cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = tuple(v / 1000 for v in item["position_mm"])
    target = tuple(v / 1000 for v in item["target_mm"])
    look_at(cam, target)
    # Preserve verticals using Blender's camera shift where possible. The
    # target is levelled in the brief; no arbitrary camera roll is introduced.
    bpy.context.scene.camera = cam
    scene = bpy.context.scene
    scene.render.resolution_x = item["resolution_x"]
    scene.render.resolution_y = item["resolution_y"]
    scene.render.resolution_percentage = 100 if final else 50
    scene.render.filepath = str(output_dir / (item["name"] + ".png"))
    bpy.ops.render.render(write_still=True)
    return cam


def build_room(spec, output_dir, final):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        # Keep datablocks if still referenced by other scenes.
        pass

    dims = spec["room_dimensions_mm"]
    w, length, h = (dims[k] / 1000 for k in ("width_x", "length_y", "ceiling_height_z"))
    wardrobe_y = dims["wardrobe_start_y"] / 1000
    design = spec["design"]
    wall_mat = material("Mat_Warm_Greige_Plaster", hex_rgb(design["wall_color_hex"]), 0.84)
    ceiling_mat = material("Mat_Ceiling_Warm_White", (0.91, 0.89, 0.85), 0.8)
    blue_mat = material("Mat_Dusty_Blue", (0.34, 0.45, 0.53), 0.62)
    oak_mat = create_herringbone_parquet_material()
    brass_mat = material("Mat_Brushed_Brass", (0.72, 0.48, 0.18), 0.28, 0.88)
    glass_mat = create_fluted_glass_material()
    mural_mat = create_chinoiserie_mural_material(
        seed=design["mural"]["seed"],
        width=design["mural"]["width_px"],
        height=design["mural"]["height_px"],
    )

    # Floor, ceiling and wall shell. Openings are represented by separate
    # jamb/header elements for clarity in this initial visual prototype.
    cube("Floor_Substrate", (w/2, length/2, -0.045), (w, length, 0.08), material("Mat_Floor_Substrate", (0.22,0.18,0.13), 0.8))
    create_herringbone_floor("Parquet_Plank", w, length, z=0.0, plank_length=0.60, plank_width=0.10, thickness=0.012)
    ceiling = cube("Ceiling_Main", (w/2, length/2, h+0.06), (w, length, 0.12), ceiling_mat)
    wall_t = 0.12
    cube("Wall_West_Mirror", (-wall_t/2, length/2, h/2), (wall_t, length, h), wall_mat)
    cube("Wall_South", (w/2, -wall_t/2, h/2), (w, wall_t, h), wall_mat)
    cube("Wall_North_Headboard", (w/2, length+wall_t/2, h/2), (w, wall_t, h), wall_mat)
    # East wall with window opening: lower, upper, and side piers.
    win = spec["openings"][0]
    win_w, win_h, sill = win["width"]/1000, win["height"]/1000, win["sill_height"]/1000
    win_center = win["center_along_wall"]/1000
    win_y0, win_y1 = win_center-win_w/2, win_center+win_w/2
    cube("Wall_East_Lower", (w+wall_t/2, length/2, sill/2), (wall_t, length, sill), wall_mat)
    cube("Wall_East_Upper", (w+wall_t/2, length/2, sill+win_h+(h-sill-win_h)/2), (wall_t, length, h-sill-win_h), wall_mat)
    cube("Wall_East_Pier_A", (w+wall_t/2, win_y0/2, sill+win_h/2), (wall_t, win_y0, win_h), wall_mat)
    cube("Wall_East_Pier_B", (w+wall_t/2, (win_y1+length)/2, sill+win_h/2), (wall_t, length-win_y1, win_h), wall_mat)

    # Wardrobe ceiling accent and partition portal/glass panels.
    cube("Wardrobe_Ceiling_Accent", (w/2, (wardrobe_y+length)/2, h-0.035),
         (w, length-wardrobe_y, 0.07), blue_mat)
    part = spec["details"]["fluted_partition"]
    part_y = part["y_mm"]/1000
    part_w = part["width_mm"]/1000
    panel_h = part["height_mm"]/1000
    panel_count = max(1, int(part["panel_count"]))
    panel_w = part_w/panel_count
    for i in range(panel_count):
        x = (w-part_w)/2 + (i+0.5)*panel_w
        panel = cube(f"Partition_Glass_{i+1:02d}", (x, part_y, panel_h/2),
                     (panel_w-0.012, 0.025, panel_h), glass_mat, 0.004)
    for x in ((w-part_w)/2, (w+part_w)/2):
        cube("Partition_Bronze_Jamb", (x, part_y, panel_h/2), (0.035, 0.05, panel_h), brass_mat)

    # Feature mural plane on north wall, oriented toward room (-Y).
    mural = cube("Mural_Headboard", (w/2, length-0.055, 1.95), (2.4, 0.012, 2.15), mural_mat)
    mural.data.materials.clear()
    mural.data.materials.append(mural_mat)

    # Bed and upholstered headboard. Brief coordinates locate the bed's SW
    # floor corner; bed long axis runs along Y.
    bed = spec["furniture"]["bed"]
    bx, by, _ = (v/1000 for v in bed["position_mm"])
    bw, bl, bh = bed["width"]/1000, bed["length"]/1000, bed["headboard_height"]/1000
    cube("Bed_Frame", (bx+bw/2, by+bl/2, 0.22), (bw, bl, 0.34), material("Mat_Bed_Base", (0.23,0.25,0.28), 0.75), 0.04)
    cube("Bed_Mattress", (bx+bw/2, by+bl/2, 0.43), (bw*0.98, bl*0.98, 0.18), material("Mat_Linen", (0.91,0.89,0.84), 0.9), 0.05)
    cube("Bed_Headboard", (bx+bw/2, by+bl+0.05, bh/2), (bw, 0.12, bh), blue_mat, 0.06)

    ns = spec["furniture"]["nightstands"]
    nw, nd, nh = ns["width"]/1000, ns["depth"]/1000, ns["height"]/1000
    for side, x in (("L", bx-nw/2-0.10), ("R", bx+bw+nw/2+0.10)):
        cube(f"Nightstand_{side}", (x, by+bl-nd/2, nh/2), (nw, nd, nh),
             material("Mat_Nightstand", (0.58,0.57,0.52), 0.4), 0.025)

    vanity = spec["furniture"]["vanity"]
    vx, vy, _ = (v/1000 for v in vanity["position_mm"])
    vw, vd, vh = vanity["width"]/1000, vanity["depth"]/1000, vanity["height"]/1000
    walnut = material("Mat_Walnut", (0.22,0.105,0.045), 0.32)
    cube("Vanity_Desk_Top", (vx+vw/2, vy+vd/2, vh), (vw, vd, 0.055), walnut, 0.015)
    for dx in (0.06, vw-0.06):
        for dy in (0.06, vd-0.06):
            cube("Vanity_Desk_Leg", (vx+dx, vy+dy, vh/2), (0.035,0.035,vh), brass_mat)

    # Full-height mirror on west wall as a reflective panel.
    mirror_mat = material("Mat_Mirror", (0.72,0.78,0.80), 0.08, 0.85)
    cube("Mirror_Main", (0.075, 2.55, 1.35), (0.012, 1.10, 2.4), mirror_mat, 0.012)

    # Boiserie frames along north wall.
    boi = spec["details"]["boiserie"]
    if boi["enabled"]:
        frame_w, depth = boi["frame_width_m"], boi["depth_m"]
        for i in range(3):
            panel_width = 1.05 if i != 1 else 2.05
            x0 = 0.22 + i*1.28
            create_wall_molding(f"Boiserie_North_{i+1}", panel_width, boi["upper_panel_height_m"],
                                (x0, length-0.13, 0.95), frame_w, depth)
        for i in range(4):
            create_wall_molding(f"Boiserie_West_{i+1}", 0.72, boi["lower_panel_height_m"],
                                (-0.13, 0.35+i*1.0, 0.25), frame_w, depth)

    # Brass sconces flanking headboard; sconces are visual details plus lights.
    sconce_z = spec["details"]["sconce_mount_height_mm"]/1000
    for i, x in enumerate((0.72, w-0.72)):
        create_brass_sconce(f"Sconce_Bed_{i+1}", (x, length-0.20, sconce_z-0.21), 0.42, 30)

    # Hidden warm cove lighting along feature wall and wardrobe portal.
    create_led_cove_light("LED_Headboard_Cove", 2.5, (w/2, length-0.20, 2.85),
                          (math.pi/2, 0, 0), 45, spec["details"]["led_color_temperature_k"])
    create_led_cove_light("LED_Wardrobe_Portal", 2.3, (w/2, part_y, 2.35),
                          (0, 0, math.pi/2), 32, spec["details"]["led_color_temperature_k"])

    # Daylight area source at the window; soft ambient world.
    world = bpy.data.worlds.new("World_Daylight") if not bpy.data.worlds else bpy.data.worlds[0]
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.52,0.62,0.72,1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35
    area_data = bpy.data.lights.new("Window_Softbox_Data", "AREA")
    area_data.energy = 900
    area_data.shape = "RECTANGLE"
    area_data.size = 2.2
    area_data.size_y = 2.0
    area = bpy.data.objects.new("Window_Softbox", area_data)
    bpy.context.collection.objects.link(area)
    area.location = (w+0.35, win_center, 2.1)
    area.rotation_euler = (0, math.radians(-90), 0)

    # Render engine and quality.
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = spec["render"]["final"]["samples"] if final else spec["render"]["preview"]["samples"]
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = "OPENIMAGEDENOISE"
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    scene.render.resolution_percentage = 100 if final else spec["render"]["preview"]["percentage"]
    # Prefer GPU, but retain a safe CPU fallback if Blender cannot initialize it.
    try:
        scene.cycles.device = "GPU"
    except Exception:
        scene.cycles.device = "CPU"

    output_dir.mkdir(parents=True, exist_ok=True)
    blend_path = output_dir / (spec["project_name"] + ".blend")
    camera_specs = spec["render"]["cameras"]
    for camera_spec in camera_specs:
        target_dir = output_dir / ("final" if final else "preview")
        target_dir.mkdir(parents=True, exist_ok=True)
        add_camera(spec, camera_spec, target_dir, final)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print(f"Airender scene saved: {blend_path}")
    print(f"Rendered {'final' if final else 'preview'} images to: {output_dir}")


if __name__ == "__main__":
    args = parse_args()
    with open(args.spec, "r", encoding="utf-8") as handle:
        brief = json.load(handle)
    build_room(brief, Path(args.output).resolve(), args.final)
