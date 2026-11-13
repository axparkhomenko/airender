"""Create a tiny Blender scene and save it without rendering.

Usage:
  blender --background --python scripts/blender_smoke_test.py -- --output output/airender_blender_smoke_test.blend
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def main():
    args = parse_args()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)

    # A deliberately simple scene: floor, beveled cube, camera and one light.
    bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, 0))
    floor = bpy.context.object
    floor.name = "SmokeTest_Floor"

    bpy.ops.mesh.primitive_cube_add(size=1.5, location=(0, 0, 0.8))
    cube = bpy.context.object
    cube.name = "SmokeTest_Cube"
    bevel = cube.modifiers.new("SoftEdges", "BEVEL")
    bevel.width = 0.08
    bevel.segments = 3

    mat = bpy.data.materials.new("SmokeTest_Material")
    mat.diffuse_color = (0.22, 0.42, 0.68, 1)
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.22, 0.42, 0.68, 1)
    cube.data.materials.append(mat)

    bpy.ops.object.camera_add(location=(4.5, -6.5, 4.2))
    camera = bpy.context.object
    camera.name = "SmokeTest_Camera"
    target = Vector((0, 0, 0.7))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = 50
    bpy.context.scene.camera = camera

    bpy.ops.object.light_add(type="AREA", location=(1.5, -3.5, 5))
    light = bpy.context.object
    light.name = "SmokeTest_KeyLight"
    light.data.energy = 650
    light.data.shape = "DISK"
    light.data.size = 4
    light.rotation_euler = (Vector((0, 0, 0.5)) - light.location).to_track_quat("-Z", "Y").to_euler()

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 480
    scene.render.resolution_percentage = 50
    scene.camera = camera

    bpy.ops.wm.save_as_mainfile(filepath=str(output_path))
    print(f"AIRENDER_SMOKE_TEST_OK={output_path}")
    print(f"AIRENDER_SMOKE_TEST_OBJECTS={len(scene.objects)}")


if __name__ == "__main__":
    main()
