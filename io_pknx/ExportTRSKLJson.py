import json
import os

from .utils.fileutils import to_binary

if "FLATC_PATH" in os.environ:
  FLATC_PATH = os.environ["FLATC_PATH"]
else:
  FLATC_PATH = "PATH TO FLATC.EXE HERE"


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
    print(f"Armature '{armature.data.name}' not found.")
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
  
  armature_name = armature.data.name.replace("trmdl", "trskl")

  dest_file = os.path.join(path, armature_name + ".json")

  with open(dest_file, "w") as f:
    json.dump(data, f, indent=2)
  
  to_binary(dest_file, ".trskl")

  print(f"Skeleton data saved to '{dest_file}'.")

  return {"FINISHED"}

