
import os, bpy, json, re, struct, subprocess

from statistics import mean
from mathutils import Vector, Euler # type: ignore


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
    vtx_size = vertFormat.size
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
      vtx_size += normFormat.size

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
      vtx_size += normFormat.size

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
        vtx_size += uvFormat.size

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
        vtx_size += uvFormat.size

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
      vtx_size += mtFormat.size
      vtx_attrs.append(
      {
        "attr_0": 0,
        "attribute": "BLEND_WEIGHTS",
        "attribute_layer": 0,
        "type": "RGBA_16_UNORM",
        "position": vtx_size,
      }
    )
      vtx_size += wtFormat.size

    attributes = [
    {
      "attrs": vtx_attrs,
      "size": [{"size": vtx_size}],
    }
  ]
    
    return attributes


def get_vertex_bytes(settings, vert_data):
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
        grps = [x[0] for x in vert[cursor]]
        vert_bytes += mtFormat.pack(grps[0], grps[1], grps[2], grps[3])

        wgts = [int(x[1] * 0xFFFF) for x in vert[cursor]]
        vert_bytes += wtFormat.pack(wgts[0], wgts[1], wgts[2], wgts[3])
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
      poly_bytes += polyFormat.pack(poly[0], poly[1], poly[2])
    return poly_bytes

def to_binary(filepath, fileext):
    filetype = fileext.strip(".")
    schema_dir = os.path.dirname(FLATC_PATH) + f"\\Schemas\\Filetypes\\{filetype}.fbs"
    output_folder = os.path.dirname(filepath) + "\\Modded\\"
    
    if not os.path.exists(output_folder):
      os.makedirs(output_folder)

    flatc_call = [
        FLATC_PATH,
        "--filename-ext",
        filetype,
        "-o",
        output_folder,
        "-b",
        schema_dir,
        filepath,
    ]
    print(flatc_call)
    result = subprocess.run(flatc_call, check=True)
    
    if isinstance(result, subprocess.CalledProcessError):
        print(f"Failed to convert '{filepath}' to binary.")
        print(result.stdout)
    else:
        output_file = os.path.realpath(
        output_folder +
        os.path.basename(filepath).strip(".json") +
        fileext 
        )
        if os.path.exists(output_file):
            rename_call = ["powershell.exe", "-Command", 
            f"Move-Item '{output_file}' '{output_file.removesuffix(fileext)}' -Force"]
            result2 = subprocess.run(rename_call, check=True)
            if isinstance(result, subprocess.CalledProcessError):
                print(f"Failed to rename binary.")
                print(result2.stdout)
        print(f"Successfully converted '{filepath}' to binary.")