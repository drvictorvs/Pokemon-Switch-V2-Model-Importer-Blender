
from ast import Bytes
from typing import Dict, List, Union
import bpy
from struct import Struct
from mathutils import Vector, Euler
from bpy_types import Mesh 


VERT_FORMAT = Struct("<fff")
NORM_FORMAT = Struct("<eeee")
UV_FORMAT = Struct("<ff")
COLOR_FORMAT = Struct("bbbb")
MT_FORMAT = Struct("<BBBB")
WT_FORMAT = Struct("<HHHH")
POLY_FORMAT = Struct("<HHH")


def get_poly_count_for_mat(obj: Mesh, mat_name: str):
  poly_count = 0
  for poly in obj.data.polygons:
    if obj.data.materials[poly.material_index].name == mat_name:
      poly_count += 1
  return poly_count


def get_shapes():
    shapes = []
    
    if 'Key' in bpy.data.shape_keys:
      if hasattr(bpy.data.shape_keys['Key'], 'key_blocks'):
        for shape in bpy.data.shape_keys['Key'].key_blocks:
          if shape.name != "Basis":
              shapes.append({
            "index": bpy.data.shape_keys['Key'].key_blocks.find(shape.name), 
            "name": shape.name
            })
          
    return shapes

def get_materials(obj):
    if not hasattr(obj, "mat_slots"):
      return {}
    mats = []
    for index, mat in enumerate(obj.mat_slots):
      if mat.name != "":
        if (get_poly_count_for_mat(obj, mat.name)) > 0:
          new_mat = {
          "mat_name": mat.name,
          "poly_offset": 0,
          "poly_count": get_poly_count_for_mat(obj, mat.name) * 3,
          "sh_unk3": 0,
          "sh_unk4": 0,
        }
          if len(mats) == 1:
            new_mat["poly_offset"] = mats[len(mats) - 1]["poly_count"]
          if len(mats) > 1:
            new_mat["poly_offset"] = (mats[len(mats) - 1]["poly_count"] + \
                                      mats[len(mats) - 1]["poly_offset"])
          mats.append(new_mat)
    return mats


def map_to_dict(v: Vector, format: str = "XYZ"):
    result_dict = {
        "x": v.x,
        "y": v.y,
        "z": v.z,
        "w": v.w if format.find("W") != -1 else "",
    }
    out = {}
    for l in format.lower():
        out[l] = result_dict.get(l, "")
    return out


def get_bounds(obj: Mesh):

    minbbox = Vector((min([Vector(co).x for co in obj.bound_box]),
                      min([Vector(co).y for co in obj.bound_box]),
                      min([Vector(co).z for co in obj.bound_box])))
    maxbbox = Vector((max([Vector(co).x for co in obj.bound_box]),
                      max([Vector(co).y for co in obj.bound_box]),
                      max([Vector(co).z for co in obj.bound_box])))
    
    bbox = {
      "min": map_to_dict(minbbox),
      "max": map_to_dict(maxbbox),
    }
    
    clip_sphere_pos = (minbbox + maxbbox) / 2
    clip_sphere_radius = (maxbbox - minbbox).length / 2
    
    clip_sphere = {
      "x": clip_sphere_pos.x,
      "y": clip_sphere_pos.y,
      "z": clip_sphere_pos.z,
      "radius": clip_sphere_radius,
    }
    
    return bbox,clip_sphere


def get_attr_dict(attribute: str, position: int, attribute_layer: int = 0) -> Dict[str, Union[str, int]]:
  data = {"POSITION": "RGB_32_FLOAT",
          "NORMAL": "RGBA_16_FLOAT",
          "TANGENT": "RGBA_16_FLOAT",
          "TEXCOORD": "RG_32_FLOAT",
          "COLOR": "RGBA_8_UNORM",
          "BLEND_INDICES": "RGBA_8_UNSIGNED",
          "BLEND_WEIGHTS": "RGBA_16_UNORM"
          }
  return {
          "attr_0": 0,
          "attribute": attribute,
          "attribute_layer": attribute_layer,
          "type": data[attribute],
          "position": position,
          }


def get_mesh_attributes(settings: dict):

  vtx_size = VERT_FORMAT.size
  vtx_attrs = get_attr_dict("POSITION", vtx_size)

  if settings["normal"] is True:
    vtx_attrs = get_attr_dict("NORMAL", vtx_size)
    vtx_size += NORM_FORMAT.size

  if settings["tangent"] is True:
    vtx_attrs = get_attr_dict("TANGENT", vtx_size)
    vtx_size += NORM_FORMAT.size

  if settings["uv"] is True:
    for i in range(settings["uv_count"]):
      vtx_attrs = get_attr_dict("TEXCOORD", vtx_size)
      vtx_size += UV_FORMAT.size

  if settings["color"] is True:
    for i in range(settings["color_count"]):
      vtx_attrs = get_attr_dict("COLOR", vtx_size, attribute_layer=i)
      vtx_size += UV_FORMAT.size

  if settings["skinning"] is True:
    vtx_attrs = get_attr_dict("BLEND_INDICES", vtx_size)
    vtx_size += MT_FORMAT.size
    vtx_attrs = get_attr_dict("BLEND_WEIGHTS", vtx_size)
    vtx_size += WT_FORMAT.size

  attributes = [
    {
      "attrs": vtx_attrs,
      "size": [{"size": vtx_size}],
    }
  ]
  
  return attributes

def get_vertex_bytes(settings: dict, vert_data: list) -> bytes:
    vert_bytes = b""

    for vert in vert_data:
      cursor = 0
      co = vert[cursor]
      vert_bytes += VERT_FORMAT.pack(co[0], co[1], co[2])
      cursor += 1

      if settings["normal"] == 1:
        norm = vert[cursor]
        vert_bytes += NORM_FORMAT.pack(norm[0], norm[1], norm[2], 0.0)
        cursor += 1

      if settings["tangent"] == 1:
        tan = vert[cursor]
        vert_bytes += NORM_FORMAT.pack(tan[0], tan[1], tan[2], 0.0)
        cursor += 1

      if settings["uv"] == 1:
        tex = vert[cursor]
        vert_bytes += UV_FORMAT.pack(tex[0], tex[1])
        cursor += 1

      if settings["skinning"] == 1:
        grps = [x[0] for x in vert[cursor]]
        vert_bytes += MT_FORMAT.pack(grps[0], grps[1], grps[2], grps[3])

        wgts = [int(x[1] * 0xFFFF) for x in vert[cursor]]
        vert_bytes += WT_FORMAT.pack(wgts[0], wgts[1], wgts[2], wgts[3])
    return vert_bytes

def get_poly_bytes(obj, settings, mesh, vert_data, poly_data, bone_dict, uv) -> bytes:
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
      poly_bytes += POLY_FORMAT.pack(poly[0], poly[1], poly[2])
    return poly_bytes
