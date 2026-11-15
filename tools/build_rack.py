"""Author the editable rack, maintenance animation, GLB and Cycles evidence."""

import argparse
from math import atan2, radians, sqrt
from pathlib import Path
import sys

import bpy
from mathutils import Vector

TRAVEL = 0.53
DOOR_LIMIT = radians(105)
LINK_LENGTH = 0.37
SERVER_Z = 1.09
FPS = 20
LAST_FRAME = 121


def material(name, color, roughness, metal=0.0, glow=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metal
    shader.inputs["Emission Color"].default_value = (*color, 1)
    shader.inputs["Emission Strength"].default_value = glow
    return mat


def coat_texture(mat, output):
    image = bpy.data.images.new("Powder coat roughness", width=256, height=256)
    image.colorspace_settings.name = "Non-Color"
    pixels = []
    for y in range(256):
        for x in range(256):
            grain = ((x * 73 ^ y * 151 ^ (x * y * 11)) & 31) / 31
            value = 0.52 + grain * 0.10
            pixels.extend((value, value, value, 1))
    image.pixels.foreach_set(pixels)
    image.filepath_raw = str(output)
    image.file_format = "PNG"
    image.save()
    image.pack()
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = image
    mat.node_tree.links.new(tex.outputs["Color"],
                            mat.node_tree.nodes.get("Principled BSDF").inputs["Roughness"])


def box(name, center, size, mat, parent=None, bevel=0.002):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.parent = parent
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new("Edge radius", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    return obj


def pivot(name, loc=(0, 0, 0), function=None):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    obj.empty_display_type = "ARROWS"
    obj.empty_display_size = 0.09
    if function:
        obj["equipment_function"] = function
    return obj


def label(name, text, location, size, mat, parent=None, rear=False):
    bpy.ops.object.text_add(location=location, rotation=(radians(90), 0, radians(180) if rear else 0))
    obj = bpy.context.object
    obj.data.body = text
    obj.data.size = size
    obj.data.resolution_u = 2
    obj.data.materials.append(mat)
    bpy.ops.object.convert(target="MESH")
    obj.name = name
    obj.parent = parent


def cable(name, coordinates, color, parent=None, radius=0.0035):
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 8
    curve.bevel_depth = radius
    curve.bevel_resolution = 2
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(coordinates) - 1)
    for point, location in zip(spline.bezier_points, coordinates):
        point.co = location
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(color)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    obj.parent = parent
    return obj


def rack_geometry(textures):
    graphite = material("Powder coated graphite", (0.026, 0.044, 0.058), 0.56)
    coat_texture(graphite, textures / "powder-coat-roughness.png")
    steel = material("Zinc plated steel", (0.32, 0.39, 0.46), 0.30, 0.75)
    black = material("Front panel charcoal", (0.013, 0.021, 0.028), 0.44)
    ink = material("Cool white legends", (0.72, 0.86, 0.93), 0.63)
    teal = material("Network blue jacket", (0.025, 0.31, 0.68), 0.37)
    amber = material("Maintenance amber", (0.95, 0.34, 0.027), 0.38)
    green = material("Status green", (0.075, 0.75, 0.27), 0.36, glow=0.9)

    frame = pivot("RACK_FRAME", function="Supports the rack equipment and mounting rails.")
    for x in (-0.285, 0.285):
        for y in (-0.464, 0.464):
            box(f"Post {x:+.3f} {y:+.3f}", (x, y, 1.025), (0.046, 0.05, 2.0), graphite, frame)
            box(f"Floor foot {x:+.3f} {y:+.3f}", (x, y, 0.019),
                (0.065, 0.065, 0.028), steel, frame)
            for marker in range(15):
                height = 0.40 + marker * 0.10
                face_y = y + (-0.026 if y < 0 else 0.026)
                box(f"Post index {x:+.3f} {y:+.3f} {marker:02}",
                    (x, face_y, height), (0.014, 0.0018, 0.0025), steel, frame, 0)
        for height in (0.055, 2.0):
            box(f"Depth crossmember {x:+.3f} {height:.2f}", (x, 0, height),
                (0.046, 0.96, 0.053), graphite, frame)
    for y in (-0.464, 0.464):
        for height in (0.055, 2.0):
            box(f"Width crossmember {y:+.3f} {height:.2f}", (0, y, height),
                (0.60, 0.052, 0.053), graphite, frame)
    box("Left side panel", (-0.301, 0, 1.03), (0.018, 0.88, 1.85), graphite, frame)
    box("Right side panel", (0.301, 0, 1.03), (0.018, 0.88, 1.85), graphite, frame)
    box("Rack top", (0, 0, 2.025), (0.61, 0.98, 0.026), graphite, frame)
    label("Rack identification", "DC-07 / SERVICE BAY", (-0.217, -0.491, 1.987), 0.020, ink, frame)

    doors = []
    for name, loc, sign in (("DOOR_FRONT", (-0.286, -0.575, 0), -1),
                            ("DOOR_REAR", (0.286, 0.505, 0), -1)):
        door = pivot(name, loc, "Swing door provides access to the rack equipment.")
        direction = 1 if name == "DOOR_FRONT" else -1
        for height in (0.40, 1.60):
            box(f"{name} hinge bracket {height:.2f}", (loc[0], loc[1] + 0.033 * direction, height),
                (0.043, 0.078, 0.035), steel, frame)
        for edge, x in (("hinge", 0.013 * direction), ("latch", 0.556 * direction)):
            box(f"{name} {edge} stile", (x, 0, 1.025), (0.032, 0.032, 1.88), graphite, door)
        for height in (0.095, 1.955):
            box(f"{name} header {height:.3f}", (0.285 * direction, 0, height),
                (0.55, 0.031, 0.033), graphite, door)
        for col in range(22):
            box(f"{name} ventilation bar {col:02}", ((0.038 + col * 0.0235) * direction, 0, 1.025),
                (0.009, 0.009, 1.83), graphite, door, 0)
        box(f"{name} pull handle", (0.535 * direction, -0.024 * direction, 1.07),
            (0.025, 0.031, 0.16), steel, door)
        doors.append((door, sign))

    switch = pivot("NETWORK_SWITCH", (0, 0, 1.685),
                   "Aggregates server network uplinks into the rack network.")
    patch = pivot("PATCH_PANEL", (0, 0, 1.79),
                  "Terminates and labels fixed network runs for patching.")
    for parent, name, legend in ((switch, "Switch", "SW-01 / NETWORK"),
                                 (patch, "Patch", "PP-01 / COPPER")):
        box(f"{name} 2U housing", (0, -0.275, 0), (0.46, 0.37, 0.083), black, parent)
        box(f"{name} face", (0, -0.463, 0), (0.51, 0.011, 0.084), graphite, parent)
        label(f"{name} device label", legend, (-0.227, -0.47, 0.024), 0.012, ink, parent)
        for port in range(12):
            x = -0.194 + 0.035 * port
            box(f"{name} port bezel {port + 1:02}", (x, -0.470, -0.005),
                (0.026, 0.01, 0.017), steel, parent)
            box(f"{name} port insert {port + 1:02}", (x, -0.476, -0.005),
                (0.018, 0.006, 0.011), black, parent)
            if port < 6:
                box(f"{name} activity {port + 1:02}", (x, -0.471, 0.010),
                    (0.005, 0.002, 0.003), green, parent, 0)
    for port in range(6):
        x = -0.194 + 0.035 * port
        terminal = x + 0.009
        cable(f"PATCH_{port + 1:02}", ((x, -0.482, 1.785), (x, -0.525, 1.772),
              (terminal, -0.545 - 0.002 * port, 1.730), (x, -0.482, 1.680)), teal)
        label(f"Patch endpoint ID {port + 1:02}", f"{port + 1:02}", (x - 0.008, -0.471, 1.757),
              0.009, ink)

    for level in (0.52, 0.64, 0.76, 0.88, 1.29):
        box(f"Blanking plate {level:.2f}", (0, -0.459, level),
            (0.51, 0.013, 0.075), black, frame)
        for slot in range(12):
            box(f"Blanking detail {level:.2f} {slot:02}",
                (-0.205 + slot * 0.036, -0.466, level),
                (0.025, 0.002, 0.004), graphite, frame, 0)
    for x in (-0.239, 0.239):
        box(f"Fixed rail {x:+.3f}", (x, 0, SERVER_Z - 0.021),
            (0.016, 0.87, 0.022), steel, frame)

    server = pivot("SERVER_TRAY", (0, 0, SERVER_Z),
                   "Pull-out compute unit. Sliding rails support access to serviceable parts.")
    box("Server chassis", (0, -0.025, 0), (0.452, 0.79, 0.079), steel, server)
    box("Server face", (0, -0.426, 0), (0.51, 0.018, 0.086), graphite, server)
    for x in (-0.226, 0.226):
        box(f"Moving rail {x:+.3f}", (x, -0.04, -0.021), (0.009, 0.76, 0.013), steel, server)
        box(f"Server extraction handle {x:+.3f}", (x, -0.455, 0),
            (0.025, 0.04, 0.054), black, server)
    for drive in range(8):
        x = -0.175 + 0.05 * drive
        box(f"Drive carrier {drive + 1:02}", (x, -0.438, -0.008),
            (0.044, 0.012, 0.038), black, server)
        box(f"Drive status {drive + 1:02}", (x + 0.010, -0.445, -0.013),
            (0.008, 0.002, 0.003), green, server, 0)
    label("Server product label", "SRV-01  /  COMPUTE NODE", (-0.183, -0.436, 0.016),
          0.013, ink, server)
    for x in (-0.15, 0.15):
        box(f"Server rear module {x:+.3f}", (x, 0.374, 0),
            (0.09, 0.012, 0.034), black, server)
    label("Rear server label", "SRV-01", (0.046, 0.380, -0.020), 0.015, ink, server, rear=True)

    edge = pivot("SERVER_AUX", (0, 0, 1.415),
                 "Fixed auxiliary compute node used for rack monitoring.")
    box("Auxiliary server chassis", (0, -0.165, 0), (0.45, 0.55, 0.041), black, edge)
    box("Auxiliary server face", (0, -0.448, 0), (0.51, 0.014, 0.041), graphite, edge)
    label("Auxiliary unit label", "SRV-02 / MONITORING", (-0.210, -0.456, -0.003), 0.012, ink, edge)
    for slot in range(12):
        box(f"Auxiliary server vent {slot:02}", (0.012 + 0.016 * slot, -0.456, 0),
            (0.008, 0.002, 0.017), black, edge, 0)
    box("CMA rack-side mounting bracket", (-0.217, 0.45, SERVER_Z + 0.075),
        (0.131, 0.038, 0.022), steel, frame)
    box("CMA server-side mounting riser", (-0.16, 0.37, 0.057),
        (0.028, 0.028, 0.054), steel, server)

    arm_a = pivot("CMA_LINK_A", function="Rack-side link of the cable-management arm.")
    arm_b = pivot("CMA_LINK_B", function="Server-side link of the cable-management arm.")
    for arm in (arm_a, arm_b):
        box(f"{arm.name} channel", (LINK_LENGTH / 2, 0, 0), (LINK_LENGTH, 0.021, 0.016), steel, arm)
        cable(f"{arm.name} cable run",
              ((0, 0, 0.015), (LINK_LENGTH * 0.5, 0.005, 0.018), (LINK_LENGTH, 0, 0.015)),
              amber, arm, radius=0.005)
        for t in (0.08, 0.26):
            box(f"{arm.name} cable saddle {t}", (t, 0, 0.013), (0.019, 0.025, 0.008), graphite, arm)
    return doors, server, arm_a, arm_b


def ease(frame, start, finish):
    value = min(1.0, max(0.0, (frame - start) / (finish - start)))
    return value * value * (3 - 2 * value)


def animate(scene, doors, server, arm_a, arm_b):
    # The arm is driven by the intersection of two equal-radius circles in XY.
    # Each endpoint is fixed to its mounting datum, so the elbow stays connected.
    for frame in range(1, LAST_FRAME + 1):
        opening = ease(frame, 1, 24) - ease(frame, 100, 121)
        travel = TRAVEL * (ease(frame, 27, 58) - ease(frame, 76, 97))
        for door, direction in doors:
            door.rotation_euler.z = direction * DOOR_LIMIT * opening
            door.keyframe_insert("rotation_euler", index=2, frame=frame)
        server.location.y = -travel
        server.keyframe_insert("location", index=1, frame=frame)

        base = Vector((-0.16, 0.45, SERVER_Z + 0.082))
        tip = Vector((-0.16, 0.37 - travel, base.z))
        midpoint = (base + tip) / 2
        elbow = midpoint + Vector((sqrt(LINK_LENGTH ** 2 - ((base - tip).length / 2) ** 2), 0, 0))
        for link, start, end in ((arm_a, base, elbow), (arm_b, elbow, tip)):
            link.location = start
            link.rotation_euler.z = atan2(end.y - start.y, end.x - start.x)
            link.keyframe_insert("location", frame=frame)
            link.keyframe_insert("rotation_euler", index=2, frame=frame)

    for obj in [*(door for door, _ in doors), server, arm_a, arm_b]:
        action = obj.animation_data.action
        action.name = f"Maintenance | {obj.name}"
        slot = obj.animation_data.action_slot
        for fcurve in action.layers[0].strips[0].channelbag(slot).fcurves:
            for key in fcurve.keyframe_points:
                key.interpolation = "LINEAR"
    scene.frame_set(1)


def aim(obj, at):
    obj.rotation_euler = (Vector(at) - obj.location).to_track_quat("-Z", "Y").to_euler()


def camera(name, point, at, scale):
    bpy.ops.object.camera_add(location=point)
    obj = bpy.context.object
    obj.name = name
    obj.data.type = "ORTHO"
    obj.data.ortho_scale = scale
    aim(obj, at)
    return obj


def lamp(name, location, power, size, color):
    bpy.ops.object.light_add(type="AREA", location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.energy = power
    obj.data.shape = "DISK"
    obj.data.size = size
    obj.data.color = color
    aim(obj, (0, 0, 1.03))


def render(scene, at, camera_obj, path):
    scene.frame_set(at)
    scene.camera = camera_obj
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def studio(scene):
    scene.world = bpy.data.worlds.new("Cool studio ambient")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.15, 0.20, 0.26, 1)
    bg.inputs[1].default_value = 0.40
    floor = material("Studio floor", (0.060, 0.085, 0.115), 0.78)
    box("Studio floor", (0, 0, -0.006), (200, 200, 0.03), floor, bevel=0)
    lamp("Front key", (-2.7, -3.6, 4.0), 560, 3.5, (0.82, 0.93, 1))
    lamp("Front fill", (2.4, -2.0, 3.0), 290, 2.1, (1, 0.86, 0.72))
    lamp("Rear softbox", (1.4, 2.8, 3.4), 560, 2.7, (0.61, 0.79, 1))
    lamp("Rear side fill", (-2.0, 2.0, 1.9), 220, 1.7, (1, 0.88, 0.72))
    hero = camera("Rack and extracted tray", (2.9, -4.7, 2.52), (-0.16, -0.21, 1.01), 2.63)
    front = camera("Front equipment detail", (0.30, -4.3, 1.95), (0.015, -0.42, 1.63), 0.77)
    back = camera("Cable arm detail", (0.47, 3.3, 2.48), (-0.025, 0.23, 1.15), 0.91)
    motion_front = camera("Motion front", (2.75, -4.5, 2.78), (-0.12, -0.38, 1.01), 2.9)
    return hero, front, back, motion_front


def main():
    clock = argparse.ArgumentParser(description=__doc__)
    clock.add_argument("--root", type=Path, required=True)
    clock.add_argument("--skip-video", action="store_true")
    args = clock.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    root = args.root.resolve()
    for folder in ("assets", "textures", "renders"):
        (root / folder).mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = "DC-07 Maintenance Demonstrator"
    scene.unit_settings.system = "METRIC"
    scene.render.fps = FPS
    scene.frame_end = LAST_FRAME
    rig = rack_geometry(root / "textures")
    animate(scene, *rig)
    for frame, name in ((1, "Stowed"), (24, "Doors open"), (58, "Tray at service stop"),
                        (76, "Retraction starts"), (121, "Stowed again")):
        scene.timeline_markers.new(name, frame=frame)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=str(root / "assets" / "DC-07.glb"), use_selection=True,
        export_apply=True, export_extras=True, export_animations=True,
        export_animation_mode="SCENE", export_anim_scene_split_object=False,
    )
    hero, front, back, motion_front = studio(scene)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 980
    scene.render.resolution_y = 980
    scene.camera = hero
    scene.frame_set(58)
    scene.render.filepath = "//../renders/service-position.png"
    bpy.ops.object.select_all(action="DESELECT")
    rig[1].select_set(True)
    bpy.context.view_layer.objects.active = rig[1]
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.region_3d.view_perspective = "CAMERA"
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(root / "assets" / "DC-07.blend"))
    render(scene, 58, hero, root / "renders" / "service-position.png")
    render(scene, 58, front, root / "renders" / "network-patching.png")
    render(scene, 58, back, root / "renders" / "cable-management.png")
    if args.skip_video:
        return

    # Cut to the rear during the service dwell to show the arm near full extension.
    for frame, cam in ((1, motion_front), (45, back), (82, motion_front)):
        scene.timeline_markers.new(f"Shot {frame}", frame=frame).camera = cam
    scene.render.resolution_x = 540
    scene.render.resolution_y = 540
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.filepath = str(root / "renders" / "maintenance")
    scene.cycles.samples = 5
    scene.frame_step = 2
    scene.render.fps = FPS // 2
    bpy.ops.render.render(animation=True)
    destination = root / "renders" / "maintenance.mp4"
    generated = [path for path in destination.parent.glob("maintenance*.mp4")
                 if path != destination]
    if len(generated) == 1:
        generated[0].replace(destination)
    elif generated or not destination.is_file():
        raise RuntimeError(f"Expected one rendered video, got {generated}")


if __name__ == "__main__":
    main()
