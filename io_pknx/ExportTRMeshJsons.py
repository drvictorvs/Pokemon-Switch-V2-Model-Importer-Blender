# credits for trmsh/trmbf exporting go to @mv at Pokémon Switch Modding 
# Discord Server
import json
import os
import re
import struct
from statistics import mean

import bpy
from mathutils import Euler, Vector

from .utils import exportutils, fileutils

if "FLATC_PATH" in os.environ:
  FLATC_PATH = os.environ["FLATC_PATH"]
else:
  FLATC_PATH = "PATH TO FLATC.EXE HERE"

TRMSH = ".trmsh"
TRSKL = ".trskl"
TRMDL = ".trmdl"
TRMBF = ".trmbf"

VertFormat = struct.Struct("<fff")
NormFormat = struct.Struct("<eeee")
UVFormat = struct.Struct("<ff")
ColorFormat = struct.Struct("bbbb")
MTFormat = struct.Struct("<BBBB")
WTFormat = struct.Struct("<HHHH")
PolyFormat = struct.Struct("<HHH")

def get_mesh_data(context, obj, settings):
  if obj.type != "MESH":
    return -1

  bbox, clip_sphere = exportutils.get_bounds(obj)
  attributes = exportutils.get_mesh_attributes(settings)
  materials = exportutils.get_materials(obj)
  shapes = exportutils.get_shapes()

  mesh = {
    "mesh_shape_name": re.sub(r'^[\d*] ','',obj.name),
    "bounds": bbox,
    "polygon_type": "UINT16",
    "attributes": attributes,
    "materials": materials,
    "clip_sphere": clip_sphere,
    "res0": 0,
    "res1": 0,
    "res2": 0,
    "res3": 0,
    "influence": [{"index": 1, "scale": 36.0}],
    "vis_shapes": shapes,
    "mesh_name": re.sub(r'^[\d*] ','',obj.name),
    "unk13": 0,
    "morph_shape": []
  }

  return mesh

def get_buffer_data(context, obj, settings, armature):
  if obj.type != "MESH":
    return -1

  mesh = obj.data
  mesh.calc_tangents()

  vert_data = [Euler] * len(mesh.vertices)
  poly_data = []

  bone_dict = {}

  if settings["armature"]:
    for bone_name, bone_object in armature.pose.bones.items():
      bone_dict[bone_object.name] = armature.pose.bones.find(bone_name)

  ## Accumulate all the relevant data
  ## TODO: make it possible later for different presets
  ## for trainers, pokemon, buildings

  # uvs = []
  uv = mesh.uv_layers.active.data

  # if settings["uv"] == 1:
  # uv = mesh.uv_layers.active.data

  poly_bytes = exportutils.get_poly_bytes(obj, settings, mesh, vert_data, poly_data, bone_dict, uv)

  ## Write vert bytes
  ## TODO: make it possible later for using different presets
  ## Such as extra UVs for Buildings, extra vertex colors, etc.
  vert_bytes = exportutils.get_vertex_bytes(settings, vert_data)


  data = {
    "index_buffer": [{"buffer": list(poly_bytes)}],
    "vertex_buffer": [{"buffer": list(vert_bytes)}],
    "morphs": [],
  }

  return data

def get_model_data(collection_name, armature_name, meshes, array, settings):

  def find_bounds(array):
    min_bound = array[0]["bounds"]["min"].copy()
    max_bound = array[0]["bounds"]["max"].copy()
    for item in array:
      min_bound["x"] = min(min_bound["x"], item["bounds"]["min"]["x"])
      min_bound["y"] = min(min_bound["y"], item["bounds"]["min"]["y"])
      min_bound["z"] = min(min_bound["z"], item["bounds"]["min"]["z"])
      max_bound["x"] = max(max_bound["x"], item["bounds"]["max"]["x"])
      max_bound["y"] = max(max_bound["y"], item["bounds"]["max"]["y"])
      max_bound["z"] = max(max_bound["z"], item["bounds"]["max"]["z"])

    # Return the new bounds struct
    return {"min": min_bound, "max": max_bound}

  def find_texture_space(array):
    euler_angles = array[0].to_mesh().texspace_location.copy()
    euler = Euler(Vector((euler_angles.x, euler_angles.y, euler_angles.z)), "XYZ")
    # TODO I have no idea what I'm doing here
    for item in array:
      euler.x = mean([euler.x, item.to_mesh().texspace_location.x])
      euler.y = mean([euler.y, item.to_mesh().texspace_location.y])
      euler.z = mean([euler.z, item.to_mesh().texspace_location.z])
    quat = euler.to_quaternion()
    return quat

  texture_space = find_texture_space(array)

  export_model = {
    "unk0": 0,
    "meshes": [
      {"filename": collection_name + TRMSH},
      {"filename": collection_name + "_lod1" + TRMSH},
      {"filename": collection_name + "_lod2" + TRMSH},
    ],
    "skeleton": {"filename": ""},
    "materials": [collection_name + ".trmtr"],
    "lods": [
      {"index": [{"unk0": 0}, {"unk0": 1}, {"unk0": 2}], "lod_type": "Custom"}
    ],
    "bounds": find_bounds(meshes),
    "texture_space": {
      "x": round(texture_space.x, 6),
      "y": round(texture_space.w, 6),  # don't ask me why
      "z": round(texture_space.z, 6),
      "w": round(texture_space.y, 6),
      # "x": -0.0,
      # "y": 0.978069,
      # "z": 0.013804,
      # "w": 0.585692
    },
    "unk8": 0,
    "unk9": 2,
  }

  if settings["incl_armature"]:
    export_model["skeleton"]["filename"] = armature_name

  return export_model

def save_and_convert_jsons(self, context, dest_dir, export_settings):
  meshes_filepath, buffers_filepath, model_filepath = save_jsons(self, context, dest_dir, export_settings)

  fileutils.to_binary(meshes_filepath, TRMSH)
  fileutils.to_binary(buffers_filepath, TRMBF)
  fileutils.to_binary(model_filepath, TRMDL)

def save_jsons(self, context, dest_dir, export_settings):
      objs = []
      collections = []
      armatures = []
      for obj in bpy.context.selected_objects:
        if obj.type == "ARMATURE":
          armatures.append(obj.data.name)
        if obj.type == "MESH":
          objs.append(obj)
          continue
        if hasattr(obj, "users_collection"):
          if len(obj.users_collection) != 1:
            raise(Exception("Please select objects in only one collection."))
          else:
            for collection in obj.users_collection:
              collections.append(collection.name)
        if hasattr(obj, "children"):
          if obj.children != ():
            for child in obj.children:
              if child.type == "MESH":
                objs.append(child)
              elif child.type == "ARMATURE":
                armatures.append(child.data.name)

      if len(collections) > 1:
        raise(Exception("Please select objects in only one collection."))
      
      if len(armatures) > 1:
        raise(Exception("Please select objects with only one armature."))
    
      if len(collections) > 0:
          collection_name = collections[0]
      else:
          collection_name = objs[0].name
          if len(armatures) == 0:
              armatures = [obj.find_armature()]

      buffers = []
      meshes = []
      for obj in objs:
        buffers.append(
        get_buffer_data(context, obj, export_settings,
                obj.find_armature())
      )
        meshes.append(get_mesh_data(context, obj, export_settings))
      export_buffers = {
      "unused": 0,
      "buffers": buffers,
    }
      export_meshes = {
      "unk0": 0,
      "meshes": meshes,
      "buffer_name": collection_name + TRMBF,
    }
      export_model = get_model_data(
      collection_name, armatures[0], meshes, objs, export_settings
    )
    
      meshes_filepath = os.path.join(
      dest_dir, collection_name + TRMSH + self.filename_ext
    )
      with open(meshes_filepath, "w", encoding="utf-8") as f:
        f.write(json.dumps(export_meshes, indent=2))
      
      buffers_filepath = os.path.join(
      dest_dir, collection_name + TRMBF + self.filename_ext
    )
      with open(buffers_filepath, "w", encoding="utf-8") as f:
        f.write(json.dumps(export_buffers, indent=2))
      
      model_filepath = os.path.join(
      dest_dir, collection_name + TRMDL + self.filename_ext
    )
      with open(model_filepath, "w", encoding="utf-8") as f:
        f.write(json.dumps(export_model, indent=2))
      return meshes_filepath,buffers_filepath,model_filepath