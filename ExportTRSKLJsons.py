bl_info = {
    "name": "TRSKL JSON Armature Exporter (.TRSKL.json)",
    "author": "drvictorvs",
    "version": (0, 0, 1),
    "blender": (4, 0, 0),
    "location": "File > Export",
    "description": "Exports TRSKL JSON armatures for Pokémon Switch",
    "warning": "",
    "category": "Export",
}

import os, bpy, json, subprocess
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, IntProperty
from bpy.types import Operator

if hasattr(os.environ, "FLATC_PATH"):
    FLATC_PATH = os.environ["FLATC_PATH"]
else:
    FLATC_PATH = "PATH TO FLATC.EXE HERE"

class ExportTRSKLJsons(Operator, ExportHelper):
    """Save a TRSKL JSON for Pokémon Scarlet/Violet"""

    bl_idname = "pokemonswitch.exportarmature"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Export Armature"
    filename_ext = ".json"

    def execute(self, context):
        dest_dir = os.path.dirname(self.filepath)
        filedata = []
        for obj in bpy.context.selected_objects:
            if obj.type == "ARMATURE":
                save_skeleton_data(obj, dest_dir)
            elif obj.find_armature() is not None:
                save_skeleton_data(obj.find_armature(), dest_dir)
        return {"FINISHED"}

def to_binary(filepath, fileext):
    filetype = fileext.strip(".")
    schema_dir = os.path.dirname(FLATC_PATH) + f"\\Schemas\\Filetypes\\{filetype}.fbs"
    flatc_call = [
        FLATC_PATH,
        "--filename-ext",
        filetype,
        "-o",
        os.path.dirname(filepath) + "\\Modded\\",
        "-b",
        schema_dir,
        filepath,
    ]
    print(flatc_call)
    result = subprocess.run(flatc_call, check=True)
    if isinstance(result, subprocess.CalledProcessError):
        print(f"Failed to convert '{filepath}' to binary.")
    else:
        output_file = os.path.realpath(os.path.dirname(filepath) + 
                                       "\\Modded\\" + 
                                       os.path.basename(filepath).strip(".json") +
                                       fileext 
        )
        if os.path.exists(output_file):
            rename_call = ["powershell.exe", "-Command", 
            f"Move-Item '{output_file}' '{output_file.removesuffix(fileext)}' -Force"]
            subprocess.run(rename_call, check=True)
        print(f"Successfully converted '{filepath}' to binary.")

# Only needed if you want to add into a dynamic menu
def ExportTRSKL_menu_func_export(self, context):
    self.layout.operator(
        ExportTRSKLJsons.bl_idname, text="ScVi TRSKL JSON (.trskl.json)"
    )


def replace_current_menu_item(menu, item):
    for func in menu._dyn_ui_initialize():
        if func.__name__ == item.__name__:
            menu.remove(func)
    menu.append(item)


def register():
    bpy.utils.register_class(ExportTRSKLJsons)
    replace_current_menu_item(
        bpy.types.TOPBAR_MT_file_export, ExportTRSKL_menu_func_export
    )


def unregister():
    bpy.utils.unregister_class(ExportTRSKLJsons)


if __name__ == "__main__":
    register()


def get_pose_bone_transform(pose_bone):
    if pose_bone.parent:
        local_matrix = pose_bone.parent.matrix.inverted() @ pose_bone.matrix
    else:
        local_matrix = pose_bone.matrix
    loc, rot, scale = local_matrix.decompose()
    rot = rot.to_euler()
    return {
        "VecScale": {"x": scale.x, "y": scale.y, "z": scale.z},
        "VecRot": {"x": rot.x, "y": rot.y, "z": rot.z},
        "VecTranslate": {"x": loc.x, "y": loc.y, "z": loc.z},
    }


def get_pose_bone_pivot(pose_bone):
    if pose_bone.parent:
        pivot_tail = pose_bone.parent.matrix.inverted() @ pose_bone.bone.tail_local
        pivot_head = pose_bone.parent.matrix.inverted() @ pose_bone.bone.head_local
    else:
        pivot_tail = pose_bone.bone.tail_local
        pivot_head = pose_bone.bone.head_local
    return {
        "x": pivot_tail.x - pivot_head.x,
        "y": pivot_tail.y - pivot_head.y,
        "z": pivot_tail.z - pivot_head.z,
    }


def get_bone_matrix(bone):
    return {
        "x": {"x": bone.matrix[0][0], "y": bone.matrix[1][0], "z": bone.matrix[2][0]},
        "y": {"x": bone.matrix[0][1], "y": bone.matrix[1][1], "z": bone.matrix[2][1]},
        "z": {"x": bone.matrix[0][2], "y": bone.matrix[1][2], "z": bone.matrix[2][2]},
        "w": {"x": bone.head_local.x, "y": bone.head_local.y, "z": bone.head_local.z},
    }


# TODO
def get_ik_data(pose_bone):
    ik_data = []
    for constraint in pose_bone.constraints:
        if constraint.type == "IK":
            ik = {
                "ik_name": pose_bone.name,
                "ik_chain_start": pose_bone.name,
                "ik_chain_end": constraint.subtarget,
                "ik_type": "TwistBend",
                "res_4": 0,
                "ik_pos": {"x": 1.0, "y": 0.4, "z": 0.0},
                "ik_rot": {"w": 0.0, "x": -0.707107, "y": 0.0, "z": 0.707107},
            }
            ik_data.append(ik)
    return ik_data


def save_skeleton_data(armature, path):
    def serialize(o):
        if isinstance(o, float):
            if abs(o) < 1e-5:
                return float(0)
            return round(o, 6)
        if isinstance(o, dict):
            return {k: serialize(v) for k, v in o.items()}
        if isinstance(o, list):
            return [serialize(element) for element in o]
        return o

    if not armature or armature.type != "ARMATURE":
        print(f"Armature '{armature_name}' not found.")
        return
    transform_nodes = []
    iks = []
    bones = []
    for pose_bone in armature.pose.bones:
        pose_bone_data = {
            "name": pose_bone.name,
            "transform": get_pose_bone_transform(pose_bone),
            "scalePivot": {"x": 0.0, "y": 0.0, "z": 0.0},
            "rotatePivot": {"x": 0.0, "y": 0.0, "z": 0.0},
            # "scalePivot": get_pose_bone_pivot(pose_bone), TODO (all zero on character skeletons)
            # "rotatePivot": get_pose_bone_pivot(pose_bone), TODO (all zero on character skeletons)
            "parent_idx": (
                armature.pose.bones.find(pose_bone.parent.name)
                if pose_bone.parent
                else -1
            ),
            "rig_idx": max(-1, armature.pose.bones.find(pose_bone.name) - 2),
            "effect_node": "",
            "type": "Default",
        }
        transform_nodes.append(pose_bone_data)
        iks.extend(get_ik_data(pose_bone))
    for bone in armature.data.bones:
        bone_data = {
            "inherit_position": 1,
            "unk_bool_2": 1,
            "matrix": get_bone_matrix(bone),
        }
        bones.append(bone_data)
        pose_bone = armature.pose.bones.get(bone.name)

    data = serialize(
        {
            "res_0": 0,
            "transform_nodes": transform_nodes,
            "bones": bones,
            "iks": iks,
            "rig_offset": 0,
        }
    )

    dest_file = os.path.join(path, armature.data.name + ".json")

    with open(dest_file, "w") as f:
        json.dump(data, f, indent=2)
    
    to_binary(dest_file, ".trskl")

    print(f"Skeleton data saved to '{dest_file}'.")

    return {"FINISHED"}

