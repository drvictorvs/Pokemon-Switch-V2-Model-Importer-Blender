# credits for trmsh/trmbf exporting go to @mv at Pokémon Switch Modding Discord Server

import bpy
from statistics import mean
from mathutils import Vector, Euler
import os, json, struct


TRMSH = ".trmsh"
TRSKL = ".trskl"
TRMDL = ".trmdl"

vertFormat = struct.Struct("<fff")
normFormat = struct.Struct("<eeee")
uvFormat = struct.Struct("<ff")
colorFormat = struct.Struct("bbbb")
mtFormat = struct.Struct("<BBBB")
wtFormat = struct.Struct("<HHHH")
polyFormat = struct.Struct("<HHH")

def get_poly_count_for_mat(obj, material_name):
  polyCount = 0
  for poly in obj.data.polygons:
    if obj.data.materials[poly.material_index].name == material_name:
        polyCount += 1
  return polyCount

def get_mesh_data(context, obj, settings):
  if obj.type != "MESH":
    return -1

  bboxco = [Vector(co) for co in obj.bound_box]

  minbbox = min(bboxco)
  maxbbox = max(bboxco)

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

  vtx_size = vertFormat.size
  vtx_attrs = [
    {
      "attr_0" : 0,
      "attribute": "POSITION",
      "attribute_layer": 0,
      "type": "RGB_32_FLOAT",
      "position": 0,
    }
  ]

  if settings["normal"] == 1:
    vtx_attrs.append(
      {
        "attr_0" : 0,
        "attribute": "NORMAL",
        "attribute_layer": 0,
        "type": "RGBA_16_FLOAT",
        "position": vtx_size,
      }
    )
    vtx_size += normFormat.size

  if settings["tangent"] == 1:
    vtx_attrs.append(
      {
        "attr_0" : 0,
        "attribute": "TANGENT",
        "attribute_layer": 0,
        "type": "RGBA_16_FLOAT",
        "position": vtx_size,
      }
    )
    vtx_size += normFormat.size

  if settings["uv"] == 1:
    for i in range(settings["uv_count"]):
      vtx_attrs.append(
        {
          "attr_0" : 0,
          "attribute": "TEXCOORD",
          "attribute_layer": i,
          "type": "RG_32_FLOAT",
          "position": vtx_size,
        },
      )
      vtx_size += uvFormat.size

  if settings["color"] == 1:
    for i in range(settings["color_count"]):
      vtx_attrs.append(
        {
          "attr_0" : 0,
          "attribute": "COLOR",
          "attribute_layer": i,
          "type": "RGBA_8_UNORM",
          "position": vtx_size,
        },
      )
      vtx_size += uvFormat.size

  if settings["skinning"] == 1:
    vtx_attrs.append(
      {
        "attr_0" : 0,
        "attribute": "BLEND_INDICES",
        "attribute_layer": 0,
        "type": "RGBA_8_UNSIGNED",
        "position": vtx_size,
      }
    )
    vtx_size += mtFormat.size
    vtx_attrs.append(
      {
        "attr_0" : 0,
        "attribute": "BLEND_WEIGHTS",
        "attribute_layer": 0,
        "type": "RGBA_16_UNORM",
        "position": vtx_size,
      }
    )
    vtx_size += wtFormat.size

  attributes = [{
    "attrs": vtx_attrs,
    "size": [{"size": vtx_size}],
  }]
  materials = []
  for index, material in enumerate(obj.material_slots):
    if material.name != "":
      if (get_poly_count_for_mat(obj, material.name)) > 0:
        new_material = {
          "material_name": material.name,
          "poly_offset": 0,
          #"poly_count": len(obj.data.polygons) * 3,
          "poly_count": get_poly_count_for_mat(obj, material.name) * 3,
          "sh_unk3": 0,
          "sh_unk4": 0,
        }
        if len(materials) == 1:
          new_material['poly_offset'] = materials[len(materials) - 1]['poly_count']
        if len(materials) > 1:
          new_material['poly_offset'] = materials[len(materials) - 1]['poly_count'] + materials[len(materials) - 1]['poly_offset']
        materials.append(new_material)

  mesh = {
    "mesh_shape_name": obj.name,
    "bounds": bbox,
    "polygon_type": "UINT16",
    "attributes": attributes,
    "materials": materials,
    "clip_sphere": clip_sphere,
    "res0": 0,
    "res1": 0,
    "res2": 0,
    "res3": 0,
    "influence": [
						{
							"index": 1,
							"scale": 36.0
        		}
      ],
    "vis_shapes": [],
    "mesh_name": obj.name,
    "unk13": 0
  }

  return mesh


def get_buffer_data(context, obj, settings):
  if obj.type != "MESH":
    return -1

  mesh = obj.data
  mesh.calc_tangents()

  vert_data = [None] * len(mesh.vertices)
  poly_data = []

  material_data = []
  
  if settings["armature"]:
    bone_dict = bpy.context.selected_objects[0].find_armature()

  ## Accumulate all the relevant data
  ## TODO: make it possible later for different presets
  ## for trainers, pokemon, buildings

  # uvs = []
  uv = mesh.uv_layers.active.data

  # if settings["uv"] == 1:
  # uv = mesh.uv_layers.active.data

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
    poly_bytes += polyFormat.pack(poly[0], poly[1], poly[2])

  ## Write vert bytes
  ## TODO: make it possible later for using different presets
  ## Such as extra UVs for Buildings, extra vertex colors, etc.
  vert_bytes = b""

  for vert in vert_data:
    cursor = 0
    co = vert[cursor]
    vert_bytes += vertFormat.pack(co[0], co[1], co[2])
    cursor += 1

    if settings["normal"] == 1:
      norm = vert[cursor]
      vert_bytes += normFormat.pack(norm[0], norm[1], norm[2], 0.0)
      cursor += 1

    if settings["tangent"] == 1:
      tan = vert[cursor]
      vert_bytes += normFormat.pack(tan[0], tan[1], tan[2], 0.0)
      cursor += 1

    if settings["uv"] == 1:
      tex = vert[cursor]
      vert_bytes += uvFormat.pack(tex[0], tex[1])
      cursor += 1

    if settings["skinning"] == 1:
      grps = list([x[0] for x in vert[cursor]])
      vert_bytes += mtFormat.pack(grps[0], grps[1], grps[2], grps[3])

      wgts = list([int(x[1] * 0xFFFF) for x in vert[cursor]])
      vert_bytes += wtFormat.pack(wgts[0], wgts[1], wgts[2], wgts[3])

  data = {
    "index_buffer": [
      {
        "buffer": list(poly_bytes)
      }
    ],
    "vertex_buffer": [
      {
        "buffer": list(vert_bytes)
      }
    ],
    "morphs": []
  }

  return data


def get_model_data(collection_name, meshes, settings):
  
  def find_bounds(array):
    min_bound = array[0]['bounds']['min'].copy()
    max_bound = array[0]['bounds']['max'].copy()
    for item in array:
        min_bound['x'] = min(min_bound['x'], item['bounds']['min']['x'])
        min_bound['y'] = min(min_bound['y'], item['bounds']['min']['y'])
        min_bound['z'] = min(min_bound['z'], item['bounds']['min']['z'])
        max_bound['x'] = max(max_bound['x'], item['bounds']['max']['x'])
        max_bound['y'] = max(max_bound['y'], item['bounds']['max']['y'])
        max_bound['z'] = max(max_bound['z'], item['bounds']['max']['z'])
        
    max_bound['x'] = max(max_bound['x'],  min_bound['x'] * -1) # somehow this seems to happen

    # Return the new bounds struct
    return {'min': min_bound, 'max': max_bound}
    
  def find_texture_space():
    array = bpy.context.selected_objects
    euler_angles = array[0].to_mesh().texspace_location.copy()
    euler = Euler((euler_angles.x, euler_angles.y, euler_angles.z), 'XYZ')
    # TODO I have no idea what I'm doing here
    for item in array:
        euler.x = mean([euler.x, item.to_mesh().texspace_location.x])
        euler.y = mean([euler.y, item.to_mesh().texspace_location.y])
        euler.z = mean([euler.z, item.to_mesh().texspace_location.z])
    quat = euler.to_quaternion()
    return quat
  
  texture_space = find_texture_space()

  export_model = {
          "unk0": 0,
          "meshes": [
            {
              "filename": collection_name + TRMSH
            },
            {
              "filename": collection_name + "_lod1" + TRMSH
            },
            {
              "filename": collection_name + "_lod2" + TRMSH
            }
          ],
          "skeleton": [],
          "materials": [
             collection_name + ".trmtr"
          ],
          "lods": [
            {
              "index": [
                {
                  "unk0": 0
                },
                {
                  "unk0": 1
                },
                {
                  "unk0": 2
                }
              ],
              "lod_type": "Custom"
            }
          ],
          "bounds": find_bounds(meshes),
          "texture_space": {
            "x": round(texture_space.x,6),
            "y": round(texture_space.w,6), # don't ask me why
            "z": round(texture_space.z,6),
            "w": round(texture_space.y,6)
            #"x": -0.0,
            #"y": 0.978069,
            #"z": 0.013804,
            #"w": 0.585692
          },
          "unk8": 0,
          "unk9": 2
        }
        
  if settings["incl_armature"]:
    export_model["skeleton"] = [bpy.context.selected_objects[0].find_armature().name + ".trskl"]
        
  return export_model

# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, IntProperty
from bpy.types import Operator


class ExportTRMeshJsons(Operator, ExportHelper):
  """This appears in the tooltip of the operator and in the generated docs"""

  bl_idname = "export_test.some_data"  # important since its how bpy.ops.import_test.some_data is constructed
  bl_label = "Export Here"

  # ExportHelper mixin class uses this
  filename_ext = ".json"

  filter_glob: StringProperty(
    default="*.trskl",
    options={"HIDDEN"},
    maxlen=255,  # Max internal buffer length, longer would be clamped.
  )

  # List of operator properties, the attributes will be assigned
  # to the class instance from the operator settings before calling.

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

  use_skinning: BoolProperty(name="Use Skinning", default=True)

  def execute(self, context):
    dest_dir = os.path.dirname(self.filepath)

    export_settings = {
      "armature": self.use_obj_armature,
      "incl_armature": self.include_armature,
      "normal": self.use_normal,
      "tangent": self.use_tangent,
      "binormal": self.use_binormal,
      "uv": self.use_uv,
      "uv_count": self.uv_count,
      "color": self.use_color,
      "color_count": self.color_count,
      "skinning": self.use_skinning,
    }
    
    collection_name = bpy.context.selected_objects[0].users_collection[0].name
    
    buffers = []
    meshes = []

    for obj in bpy.context.selected_objects:
      buffers.append(get_buffer_data(context,obj,export_settings))
      meshes.append(get_mesh_data(context,obj,export_settings))
    
    export_buffers = {
      "unused": 0,
      "buffers": buffers,
      }
      
    export_meshes = {
      "unk0": 0,
      "meshes": meshes,
      "buffer_name": collection_name + TRMBF
      }
      
    export_model = get_model_data(collection_name, meshes, export_settings)
      
    meshes_filepath = os.path.join(dest_dir, collection_name + TRMSH + self.filename_ext)
    with open(meshes_filepath, "w", encoding="utf-8") as f:
      f.write(json.dumps(export_meshes, indent=2))
      
    buffers_filepath = os.path.join(dest_dir, collection_name + TRMBF + self.filename_ext)
    with open(buffers_filepath, "w", encoding="utf-8") as f:
      f.write(json.dumps(export_buffers, indent=2))
      
    model_filepath = os.path.join(dest_dir, collection_name + TRMDL + self.filename_ext)
    with open(model_filepath, "w", encoding="utf-8") as f:
      f.write(json.dumps(export_model, indent=2))
      
    return {"FINISHED"}


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
  self.layout.operator(ExportTRMeshJsons.bl_idname, text="TR JSONs (.trm**.json)")


# Register and add to the "file selector" menu (required to use F3 search "Text Export Operator" for quick access)
def register():
  bpy.utils.register_class(ExportTRMeshJsons)
  bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
  bpy.utils.unregister_class(ExportTRMeshJsons)
  bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
  register()
  bpy.ops.export_test.some_data("INVOKE_DEFAULT")
  # unregister()
