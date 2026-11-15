"""Validate the rack scene and its animated GLB and write a JSON quality report."""

import argparse
import json
from math import degrees
from pathlib import Path
import struct
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_rack import DOOR_LIMIT, FPS, LAST_FRAME, LINK_LENGTH, SERVER_Z, TRAVEL

RIG_NAMES = ("DOOR_FRONT", "DOOR_REAR", "SERVER_TRAY", "CMA_LINK_A", "CMA_LINK_B")
REQUIRED_NAMES = ("RACK_FRAME", "NETWORK_SWITCH", "PATCH_PANEL", "SERVER_AUX", *RIG_NAMES,
                  *(f"PATCH_{i:02}" for i in range(1, 7)))
TOLERANCE = 0.0001


def get_objects():
    return {obj.name: obj for obj in bpy.context.scene.objects if obj.type in {"EMPTY", "MESH"}
            and obj.name != "Studio floor"}


def frame_checks(scene, objects, start, stride, failures):
    front, rear, server, arm_a, arm_b = (objects[name] for name in RIG_NAMES)
    maximum_opening = [0.0, 0.0]
    maximum_travel = maximum_joint_gap = 0.0
    initial = None
    for index in range(LAST_FRAME):
        frame = start + index * stride
        scene.frame_set(int(frame), subframe=frame % 1)
        angles = [-obj.matrix_world.to_euler().z for obj in (front, rear)]
        travel = -server.matrix_world.translation.y
        join = arm_a.matrix_world @ Vector((LINK_LENGTH, 0, 0))
        tip = arm_b.matrix_world @ Vector((LINK_LENGTH, 0, 0))
        expected_tip = Vector((-0.16, 0.37 - travel, SERVER_Z + 0.082))
        expected_base = Vector((-0.16, 0.45, SERVER_Z + 0.082))
        gap = max((join - arm_b.matrix_world.translation).length,
                  (tip - expected_tip).length,
                  (arm_a.matrix_world.translation - expected_base).length)
        maximum_opening = [max(prior, current) for prior, current in zip(maximum_opening, angles)]
        maximum_travel = max(maximum_travel, travel)
        maximum_joint_gap = max(maximum_joint_gap, gap)
        if any(not -TOLERANCE <= angle <= DOOR_LIMIT + TOLERANCE for angle in angles):
            failures.append(f"Door range violation at frame {frame:g}")
        if not -TOLERANCE <= travel <= TRAVEL + TOLERANCE:
            failures.append(f"Tray travel violation at frame {frame:g}")
        if travel > 0.005 and min(angles) < DOOR_LIMIT - TOLERANCE:
            failures.append(f"Tray moving before doors reach the service angle at frame {frame:g}")
        if gap > TOLERANCE:
            failures.append(f"Cable arm joint gap {gap:.6g} m at frame {frame:g}")
        pose = [obj.matrix_world.copy() for obj in (front, rear, server, arm_a, arm_b)]
        if initial is None:
            initial = pose
        if index == LAST_FRAME - 1:
            if any(abs(a - b) > TOLERANCE for first, last in zip(initial, pose)
                   for first_row, last_row in zip(first, last) for a, b in zip(first_row, last_row)):
                failures.append("Final pose differs from the initial pose")
    if abs(maximum_travel - TRAVEL) > TOLERANCE:
        failures.append("Tray does not reach the service stop")
    if any(abs(angle - DOOR_LIMIT) > TOLERANCE for angle in maximum_opening):
        failures.append("A door does not reach its service angle")
    return {
        "samples": LAST_FRAME,
        "maximum_door_opening_deg": [round(degrees(angle), 4) for angle in maximum_opening],
        "maximum_tray_travel_m": round(maximum_travel, 6),
        "maximum_cable_arm_joint_gap_m": round(maximum_joint_gap, 8),
    }


def measure(scene, objects, start, stride):
    failures = []
    missing_names = sorted(set(REQUIRED_NAMES) - objects.keys())
    meshes = [obj for obj in objects.values() if obj.type == "MESH"]
    missing_materials = sorted(obj.name for obj in meshes if not obj.material_slots
                               or any(slot.material is None for slot in obj.material_slots))
    if missing_names:
        failures.append(f"Missing component names: {missing_names}")
    if missing_materials:
        failures.append(f"Missing materials: {missing_materials}")
    if not missing_names:
        scene.frame_set(int(start), subframe=start % 1)
        for name, expected in (("Rack top", (0.61, 0.98, 0.026)),
                               ("Server chassis", (0.452, 0.79, 0.079))):
            obj = objects.get(name)
            if obj is None or (obj.dimensions - Vector(expected)).length > TOLERANCE:
                failures.append(f"{name} dimensions differ from {expected} m")
        motion = frame_checks(scene, objects, start, stride, failures)
    else:
        motion = None
    return {"mesh_objects": len(meshes), "missing_names": missing_names,
            "missing_materials": missing_materials, "motion": motion, "findings": failures}


def manifest(path):
    with path.open("rb") as stream:
        magic, version, size, length, chunk = struct.unpack("<4sIII4s", stream.read(20))
        if (magic, version, size, chunk) != (b"glTF", 2, path.stat().st_size, b"JSON"):
            raise ValueError("Invalid GLB header")
        return json.loads(stream.read(length))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    root = args.root.resolve()

    bpy.ops.wm.open_mainfile(filepath=str(root / "assets" / "DC-07.blend"))
    source = measure(bpy.context.scene, get_objects(), 1, 1)
    path = root / "assets" / "DC-07.glb"
    gltf = manifest(path)
    clips = gltf.get("animations", [])
    failures = []
    if len(clips) != 1:
        raise ValueError(f"Expected one maintenance clip, found {len(clips)}")
    times = [gltf["accessors"][item["input"]] for item in clips[0]["samplers"]]
    seconds = max(time["max"][0] for time in times) - min(time["min"][0] for time in times)
    animated_names = {gltf["nodes"][channel["target"]["node"]]["name"]
                      for channel in clips[0]["channels"]}
    if animated_names != set(RIG_NAMES) or abs(seconds - (LAST_FRAME - 1) / FPS) > TOLERANCE:
        failures.append("Unexpected clip targets or duration")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = FPS
    bpy.ops.import_scene.gltf(filepath=str(path))
    objects = get_objects()
    action_starts = [bpy.data.actions[name].frame_range[0] for name in bpy.data.actions.keys()]
    if not action_starts:
        raise ValueError("No reimported animation")
    imported = measure(scene, objects, min(action_starts), 1)
    if source["mesh_objects"] != imported["mesh_objects"]:
        failures.append("The GLB round-trip changed mesh object count")
    result = {
        "result": "fail" if failures or source["findings"] or imported["findings"] else "pass",
        "blender": bpy.app.version_string,
        "source": source,
        "glb_reimport": imported,
        "clip": {"name": clips[0]["name"], "duration_s": round(seconds, 4),
                 "animated_objects": sorted(animated_names)},
        "findings": failures,
    }
    (root / "reports").mkdir(exist_ok=True)
    report = root / "reports" / "asset-quality.json"
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if result["result"] != "pass":
        raise RuntimeError(f"Validation failed. See {report}")


if __name__ == "__main__":
    main()
