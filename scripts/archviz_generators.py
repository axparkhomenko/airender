"""Reusable, idempotent-ish generators for Airender.

Run inside Blender's Python environment. All dimensions passed to these
functions are metres. The functions create objects/materials in the active
scene and return the created datablock/object.
"""
from __future__ import annotations

import math
import random
from mathutils import Vector
import bpy


def _principled_material(name, color, roughness=0.5, metallic=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = (*color[:3], 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color[:3], 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
    return mat


def create_herringbone_parquet_material(name="Mat_Oak_Herringbone"):
    """Procedural wood-like material; geometry layout is generated separately."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.34
    tex = nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = 7.0
    tex.inputs["Detail"].default_value = 3.0
    tex.inputs["Roughness"].default_value = 0.72
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.18
    ramp.color_ramp.elements[0].color = (0.20, 0.095, 0.038, 1)
    ramp.color_ramp.elements[1].position = 0.82
    ramp.color_ramp.elements[1].color = (0.52, 0.30, 0.13, 1)
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.12
    bump.inputs["Distance"].default_value = 0.006
    links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(tex.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def create_herringbone_floor(name, width, length, z=0.0, plank_length=0.60,
                             plank_width=0.10, thickness=0.012, seed=7):
    """Create actual alternating 90-degree parquet blocks, clipped approximately
    to the room bounds. Uses bevelled cuboids for robust viewport/render geometry.
    """
    rng = random.Random(seed)
    collection = bpy.data.collections.get("Generated_Parquet")
    if collection is None:
        collection = bpy.data.collections.new("Generated_Parquet")
        bpy.context.scene.collection.children.link(collection)
    mats = [
        _principled_material("Mat_Oak_Light", (0.48, 0.29, 0.13), 0.34),
        _principled_material("Mat_Oak_Mid", (0.37, 0.21, 0.09), 0.36),
        _principled_material("Mat_Oak_Dark", (0.28, 0.15, 0.065), 0.38),
    ]
    # The repeating L-pair gives a readable herringbone pattern without relying
    # on the Brick texture node's non-herringbone layout.
    pitch_x = plank_length + plank_width
    pitch_y = plank_length + plank_width
    count = 0
    y = 0.0
    row = 0
    while y < length:
        x = 0.0
        while x < width:
            # Horizontal plank followed by vertical plank at its end.
            for px, py, sx, sy, angle in (
                (x + plank_length / 2, y + plank_width / 2, plank_length, plank_width, 0),
                (x + plank_length + plank_width / 2, y + plank_width + plank_length / 2,
                 plank_width, plank_length, 0),
            ):
                bpy.ops.mesh.primitive_cube_add(size=1, location=(px, py, z + thickness / 2))
                obj = bpy.context.object
                obj.name = f"{name}_{count:04d}"
                obj.dimensions = (sx * 0.985, sy * 0.985, thickness)
                bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
                obj.data.materials.append(rng.choice(mats))
                bevel = obj.modifiers.new("Micro bevel", "BEVEL")
                bevel.width = 0.0015
                bevel.segments = 2
                obj.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
                for c in list(obj.users_collection):
                    c.objects.unlink(obj)
                collection.objects.link(obj)
                count += 1
            x += pitch_x
        y += pitch_y
        row += 1
    return collection


def create_wall_molding(name, width_m, height_m, location=(0, 0, 0),
                        frame_width=0.045, depth=0.018, material=None):
    """Rectangular wall frame made from four bevelled rails, in the X/Z plane.
    Wall faces toward -Y; location is the frame's lower-left-back corner.
    """
    mat = material or _principled_material("Mat_Warm_White_Molding", (0.88, 0.85, 0.80), 0.55)
    x, y, z = location
    rails = [
        ((x + width_m / 2, y, z + frame_width / 2), (width_m, depth, frame_width)),
        ((x + width_m / 2, y, z + height_m - frame_width / 2), (width_m, depth, frame_width)),
        ((x + frame_width / 2, y, z + height_m / 2), (frame_width, depth, height_m)),
        ((x + width_m - frame_width / 2, y, z + height_m / 2), (frame_width, depth, height_m)),
    ]
    made = []
    for i, (pos, dims) in enumerate(rails):
        bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
        obj = bpy.context.object
        obj.name = f"{name}_{i+1}"
        obj.dimensions = dims
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        obj.data.materials.append(mat)
        bevel = obj.modifiers.new("Soft profile", "BEVEL")
        bevel.width = min(0.004, depth * 0.2)
        bevel.segments = 3
        made.append(obj)
    return made


def create_fluted_glass_material(name="Mat_Fluted_Glass"):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.72, 0.82, 0.84, 1)
    bsdf.inputs["Roughness"].default_value = 0.16
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = 1.46
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = 0.72
    tex = nodes.new("ShaderNodeTexWave")
    tex.wave_type = "BANDS"
    tex.bands_direction = "X"
    tex.inputs["Scale"].default_value = 95
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.22
    bump.inputs["Distance"].default_value = 0.012
    links.new(tex.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def create_led_cove_light(name, length_m, location=(0, 0, 0),
                          rotation_euler=(0, 0, 0), power_watts=35,
                          color_temp_k=2700):
    data = bpy.data.lights.new(name + "_Data", "AREA")
    data.shape = "RECTANGLE"
    data.size = 0.025
    data.size_y = length_m
    data.energy = power_watts
    # Approximate warm-white chromaticity; Blender light datablocks use RGB.
    t = max(1000, min(12000, color_temp_k)) / 100.0
    r = 1.0 if t <= 66 else min(1.0, 1.292936 * ((t - 60) ** -0.133205))
    g = min(1.0, max(0.0, 0.3900816 * math.log(max(1, t)) - 0.6318414)) if t <= 66 else min(1.0, max(0.0, 1.129891 * ((t - 60) ** -0.0755148)))
    b = 1.0 if t >= 66 else (0.0 if t <= 19 else min(1.0, max(0.0, 0.543206 * math.log(t - 10) - 1.196254)))
    data.color = (r, g, b)
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = rotation_euler
    return obj


def create_brass_sconce(name, location=(0, 0, 1.7), height_m=0.42, power_watts=24):
    brass = _principled_material("Mat_Brushed_Brass", (0.72, 0.48, 0.18), 0.28, 0.88)
    glow = _principled_material("Mat_Sconce_Diffuser", (1.0, 0.82, 0.58), 0.24)
    bsdf = glow.node_tree.nodes.get("Principled BSDF")
    if bsdf and "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (1.0, 0.55, 0.24, 1)
        bsdf.inputs["Emission Strength"].default_value = 2.0
    x, y, z = location
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.012, depth=height_m,
                                        location=(x, y, z + height_m / 2))
    body = bpy.context.object
    body.name = name + "_Brass"
    body.data.materials.append(brass)
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.018, depth=height_m * 0.82,
                                        location=(x, y - 0.025, z + height_m / 2))
    diffuser = bpy.context.object
    diffuser.name = name + "_Diffuser"
    diffuser.data.materials.append(glow)
    light_data = bpy.data.lights.new(name + "_LightData", "POINT")
    light_data.energy = power_watts
    light_data.color = (1.0, 0.63, 0.32)
    light_data.shadow_soft_size = 0.16
    light = bpy.data.objects.new(name + "_Light", light_data)
    bpy.context.collection.objects.link(light)
    light.location = (x, y - 0.10, z + height_m / 2)
    return body, diffuser, light


def create_chinoiserie_mural_material(name="Mat_Chinoiserie_Mural",
                                      img_path="//textures/chinoiserie_mural.png",
                                      width=1024, height=768, seed=42):
    """Generate an original, stylised botanical mural texture locally.

    This is an illustrative procedural graphic, not a reproduction of a
    specific artist's work or a photorealistic hand-painted asset.
    """
    rng = random.Random(seed)
    image = bpy.data.images.new(name + "_Image", width=width, height=height, alpha=True)
    pixels = [0.0] * (width * height * 4)
    bg = (0.91, 0.88, 0.83, 1.0)
    for i in range(0, len(pixels), 4):
        pixels[i:i+4] = bg
    def dot(cx, cy, radius, color):
        x0, x1 = max(0, int(cx-radius)), min(width-1, int(cx+radius))
        y0, y1 = max(0, int(cy-radius)), min(height-1, int(cy+radius))
        for py in range(y0, y1+1):
            for px in range(x0, x1+1):
                if (px-cx)**2 + (py-cy)**2 <= radius**2:
                    idx = (py*width+px)*4
                    alpha = color[3]
                    for ch in range(3):
                        pixels[idx+ch] = pixels[idx+ch]*(1-alpha) + color[ch]*alpha
    # Elegant branching stems with clustered leaves and blossoms.
    for tree_x in (width*0.12, width*0.48, width*0.84):
        x, y = tree_x, height*0.98
        for step in range(130):
            t = step/129
            x += math.sin(t*8 + tree_x)*1.3 + rng.uniform(-1.0, 1.0)
            y -= height/150
            dot(x, y, max(1.5, 5*(1-t)), (0.28, 0.31, 0.31, 0.9))
            if step % 5 == 0:
                for _ in range(3):
                    lx = x + rng.uniform(-75, 75)
                    ly = y + rng.uniform(-42, 42)
                    col = rng.choice([(0.49,0.59,0.60,0.30),(0.55,0.64,0.65,0.34),(0.38,0.49,0.47,0.28)])
                    dot(lx, ly, rng.uniform(10, 26), col)
                    if rng.random() < 0.22:
                        dot(lx+rng.uniform(-8,8), ly+rng.uniform(-8,8), 4,
                            (0.77,0.43,0.36,0.72))
    image.pixels.foreach_set(pixels)
    image.filepath_raw = img_path
    image.file_format = "PNG"
    try:
        image.save()
    except Exception:
        # Packed image remains available in the .blend even if relative path
        # cannot be written (e.g. unsaved scene or read-only location).
        image.pack()
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.82
    return mat
