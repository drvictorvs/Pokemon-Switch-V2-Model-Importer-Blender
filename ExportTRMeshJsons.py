bl_info = {
  "name": "Pokémon Switch Model Exporter (.TR***.json)",
  "author": "mv & drvictorvs",
  "version": (0, 0, 1),
  "blender": (4, 0, 0),
  "location": "File > Export",
  "description": "Exports TRMDL, TRMBF, TRMSH JSON armatures for Pokémon "
  "Switch",
  "warning": "",
  "doc_url": "",
  "tracker_url": "",
  "category": "Export",
}

# credits for trmsh/trmbf exporting go to @mv at Pokémon Switch Modding 
# Discord Server

import os, bpy, json, re, struct, subprocess
from statistics import mean
from mathutils import Vector, Euler # type: ignore

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


def get_poly_count_for_mat(obj, material_name):
  polyCount = 0
  for poly in obj.data.polygons:
    if obj.data.materials[poly.material_index].name == material_name:
      polyCount += 1
  return polyCount

def get_mesh_data(context, obj, settings):
  if obj.type != "MESH":
    return -1

  bbox, clip_sphere = get_bounds(obj)
  attributes = get_mesh_attributes(settings)
  materials = get_materials(obj)
  shapes = get_shapes()

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

def get_shapes():
    shapes = []
  
    for shape in bpy.data.shape_keys['Key'].key_blocks:
      if shape.name != "Basis":
          shapes.append({
        "index": bpy.data.shape_keys['Key'].key_blocks.find(shape.name), 
        "name": shape.name
        })
          
    return shapes

def get_materials(obj):
    materials = []
    for index, material in enumerate(obj.material_slots):
      if material.name != "":
        if (get_poly_count_for_mat(obj, material.name)) > 0:
          new_material = {
          "material_name": material.name,
          "poly_offset": 0,
          # "poly_count": len(obj.data.polygons) * 3,
          "poly_count": get_poly_count_for_mat(obj, material.name) * 3,
          "sh_unk3": 0,
          "sh_unk4": 0,
        }
          if len(materials) == 1:
            new_material["poly_offset"] = materials[len(materials) - 1][
            "poly_count"
          ]
          if len(materials) > 1:
            new_material["poly_offset"] = (
            materials[len(materials) - 1]["poly_count"]
            + materials[len(materials) - 1]["poly_offset"]
          )
          materials.append(new_material)
    return materials

def get_bounds(obj):
    bboxco_x = [Vector(co).x for co in obj.bound_box]
    bboxco_y = [Vector(co).y for co in obj.bound_box]
    bboxco_z = [Vector(co).z for co in obj.bound_box]

    minbbox = Vector((min(bboxco_x),  min(bboxco_y), min(bboxco_z)))
    maxbbox = Vector((max(bboxco_x),  max(bboxco_y), max(bboxco_z)))

    bbox = {
    "min": {
      "x": round(minbbox.x, 6),
      "y": round(minbbox.y, 6),
      "z": round(minbbox.z, 6),
    },
    "max": {
      "x": round(maxbbox.x, 6),
      "y": round(maxbbox.y, 6),
      "z": round(maxbbox.z, 6),
    },
  }

    clip_sphere_pos = (minbbox + maxbbox) / 2
    clip_sphere_radius = (maxbbox - minbbox).length / 2

    clip_sphere = {
    "x": round(clip_sphere_pos.x, 6),
    "y": round(clip_sphere_pos.y, 6),
    "z": round(clip_sphere_pos.z, 6),
    "radius": round(clip_sphere_radius, 6),
  }
    
    return bbox,clip_sphere

def get_mesh_attributes(settings):
    vtx_size = VertFormat.size
    vtx_attrs = [
    {
      "attr_0": 0,
      "attribute": "POSITION",
      "attribute_layer": 0,
      "type": "RGB_32_FLOAT",
      "position": 0,
    }
  ]

    if settings["normal"] == 1:
      vtx_attrs.append(
      {
        "attr_0": 0,
        "attribute": "NORMAL",
        "attribute_layer": 0,
        "type": "RGBA_16_FLOAT",
        "position": vtx_size,
      }
    )
      vtx_size += NormFormat.size

    if settings["tangent"] == 1:
      vtx_attrs.append(
      {
        "attr_0": 0,
        "attribute": "TANGENT",
        "attribute_layer": 0,
        "type": "RGBA_16_FLOAT",
        "position": vtx_size,
      }
    )
      vtx_size += NormFormat.size

    if settings["uv"] == 1:
      for i in range(settings["uv_count"]):
        vtx_attrs.append(
        {
          "attr_0": 0,
          "attribute": "TEXCOORD",
          "attribute_layer": i,
          "type": "RG_32_FLOAT",
          "position": vtx_size,
        },
      )
        vtx_size += UVFormat.size

    if settings["color"] == 1:
      for i in range(settings["color_count"]):
        vtx_attrs.append(
        {
          "attr_0": 0,
          "attribute": "COLOR",
          "attribute_layer": i,
          "type": "RGBA_8_UNORM",
          "position": vtx_size,
        },
      )
        vtx_size += UVFormat.size

    if settings["skinning"] == 1:
      vtx_attrs.append(
      {
        "attr_0": 0,
        "attribute": "BLEND_INDICES",
        "attribute_layer": 0,
        "type": "RGBA_8_UNSIGNED",
        "position": vtx_size,
      }
    )
      vtx_size += MTFormat.size
      vtx_attrs.append(
      {
        "attr_0": 0,
        "attribute": "BLEND_WEIGHTS",
        "attribute_layer": 0,
        "type": "RGBA_16_UNORM",
        "position": vtx_size,
      }
    )
      vtx_size += WTFormat.size

    attributes = [
    {
      "attrs": vtx_attrs,
      "size": [{"size": vtx_size}],
    }
  ]
    
    return attributes


def get_buffer_data(context, obj, settings, armature):
  if obj.type != "MESH":
    return -1

  mesh = obj.data
  mesh.calc_tangents()

  vert_data = [Euler] * len(mesh.vertices)
  poly_data = []

  material_data = []

  bone_dict = {}

  if settings["armature"]:
    for bone_name, bone_object in armature.pose.bones.items():
      bone_dict[bone_object.name] = armature.pose.bones.find(bone_name)

  # if settings["armature"]:
  #  bone_dict = bpy.context.selected_objects[0].find_armature()

  ## Accumulate all the relevant data
  ## TODO: make it possible later for different presets
  ## for trainers, pokemon, buildings

  # uvs = []
  uv = mesh.uv_layers.active.data

  # if settings["uv"] == 1:
  # uv = mesh.uv_layers.active.data

  poly_bytes = get_poly_bytes(obj, settings, mesh, vert_data, poly_data, bone_dict, uv)

  ## Write vert bytes
  ## TODO: make it possible later for using different presets
  ## Such as extra UVs for Buildings, extra vertex colors, etc.
  vert_bytes = get_vertex_bytes(settings, vert_data)


  data = {
    "index_buffer": [{"buffer": list(poly_bytes)}],
    "vertex_buffer": [{"buffer": list(vert_bytes)}],
    "morphs": [],
  }

  return data

def get_vertex_bytes(settings, vert_data):
    vert_bytes = b""

    for vert in vert_data:
      cursor = 0
      co = vert[cursor]
      vert_bytes += VertFormat.pack(co[0], co[1], co[2])
      cursor += 1

      if settings["normal"] == 1:
        norm = vert[cursor]
        vert_bytes += NormFormat.pack(norm[0], norm[1], norm[2], 0.0)
        cursor += 1

      if settings["tangent"] == 1:
        tan = vert[cursor]
        vert_bytes += NormFormat.pack(tan[0], tan[1], tan[2], 0.0)
        cursor += 1

      if settings["uv"] == 1:
        tex = vert[cursor]
        vert_bytes += UVFormat.pack(tex[0], tex[1])
        cursor += 1

      if settings["skinning"] == 1:
        grps = [x[0] for x in vert[cursor]]
        vert_bytes += MTFormat.pack(grps[0], grps[1], grps[2], grps[3])

        wgts = [int(x[1] * 0xFFFF) for x in vert[cursor]]
        vert_bytes += WTFormat.pack(wgts[0], wgts[1], wgts[2], wgts[3])
    return vert_bytes

def get_poly_bytes(obj, settings, mesh, vert_data, poly_data, bone_dict, uv):
    for poly in mesh.polygons:
      pol = []
      for loop_index in poly.loop_indices:
        vert_d = []

        loop = mesh.loops[loop_index]
        vidx = loop.vertex_index
        pol.append(loop.vertex_index)

        vert = mesh.vertices[vidx]
        pos = (vert.co[0], vert.co[1], vert.co[2])
        vert_d.append(pos)

        if settings["normal"] == 1:
          nor = (loop.normal[0], loop.normal[1], loop.normal[2])
          vert_d.append(nor)
        if settings["tangent"] == 1:
          tan = (loop.tangent[0], loop.tangent[1], loop.tangent[2])
          vert_d.append(tan)
        if settings["uv"] == 1:
          tex = (uv[loop_index].uv[0], uv[loop_index].uv[1])
          vert_d.append(tex)

        if settings["skinning"] == 1:
          grp = []

          for gp in vert.groups:
            group_name = obj.vertex_groups[gp.group].name
            if group_name in bone_dict:
              bone_id = bone_dict[group_name]
              print("Bone ID:", bone_id)
              grp.append((bone_id, gp.weight))
            else:
              print("Bone not found.")

          while len(grp) < 4:
            grp.append((0, 0.0))

          grp = grp[0:4]
          vert_d.append(grp)

        vert_data[vidx] = vert_d
      poly_data.append(pol)

  ## Write poly bytes
  ## TODO: make it possible later for different polytypes
    poly_bytes = b""

    for poly in poly_data:
      poly_bytes += PolyFormat.pack(poly[0], poly[1], poly[2])
    return poly_bytes


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
    euler = Euler((euler_angles.x, euler_angles.y, euler_angles.z), "XYZ")
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


### Blender Integration ###
from bpy_extras.io_utils import ExportHelper
from bpy.props import BoolProperty, IntProperty # type: ignore
from bpy.types import Operator # type: ignore


class ExportTRMeshJsons(Operator, ExportHelper):
  """Saves TRMDL, TRMSH and TRMBF JSONs for Pokémon Scarlet and Violet."""

  bl_idname = "pokemonswitch.exporttrmesh"
  bl_label = "Export Here"
  filename_ext = ".json"
  filepath: bpy.props.StringProperty(subtype="FILE_PATH")
  use_obj_armature: BoolProperty(
    name="Use Armature from Blender",
    default=True,
  )
  include_armature: BoolProperty(
    name="Include Armature",
    default=True,
  )
  use_normal: BoolProperty(
    name="Use Normal",
    default=True,
  )
  use_tangent: BoolProperty(
    name="Use Normal",
    default=True,
  )
  use_tangent: BoolProperty(
    name="Use Tangent",
    default=True,
  )
  use_binormal: BoolProperty(
    name="Use Binormal",
    default=False,
  )
  use_uv: BoolProperty(
    name="Use UVs",
    default=True,
  )
  uv_count: IntProperty(
    name="UV Layer Count",
    default=1,
  )
  use_color: BoolProperty(
    name="Use Vertex Colors",
    default=False,
  )
  color_count: IntProperty(
    name="Color Layer Count",
    default=1,
  )
  use_skinning: BoolProperty(
    name="Use Skinning",
    default=True,
  )

  def execute(self, context):
    self.save_and_convert_jsons(context)
    return {"FINISHED"}

  def save_and_convert_jsons(self, context):
      meshes_filepath, buffers_filepath, model_filepath = self.save_jsons(context)

      to_binary(meshes_filepath, TRMSH)
      to_binary(buffers_filepath, TRMBF)
      to_binary(model_filepath, TRMDL)

  def save_jsons(self, context):
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





def ExportTRMesh_menu_func_export(self, context):
  self.layout.separator()
  self.layout.operator(
    "pokemonswitch.exporttrmesh", text="ScVi Mesh JSONs (.trm**.json)"
  )


def replace_current_menu_item(menu, item):
  for func in menu._dyn_ui_initialize():
    if func.__name__ == item.__name__:
      menu.remove(func)
  menu.append(item)


def register():
  bpy.utils.register_class(ExportTRMeshJsons)
  replace_current_menu_item(
    bpy.types.TOPBAR_MT_file_export, ExportTRMesh_menu_func_export
  )


def unregister():
  bpy.utils.unregister_class(ExportTRMeshJsons)


if __name__ == "__main__":
  register()
