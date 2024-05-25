import os

from typing import Optional
from io import BufferedReader
from pathlib import Path
from typing import Tuple

import bpy
from bpy.types import Armature, Material  # type: ignore
from bpy_types import Bone, Collection
from mathutils import Euler, Matrix, Vector

from .utils.fileutils import (fclose, fseek, ftell, readbyte, readfixedstring,
                              readfloat, readhalffloat, readlong, readshort)
from .utils.exceptions import TRMSHError

IN_BLENDER_ENV = True

TEXTEXT = ".png"

class TRMDLProcessor:
  def __init__(self, filep: str, trmdl: BufferedReader, settings: dict):
    
    self.filep = filep
    self.trmdl = trmdl
    self.settings = settings
    self.new_collection: Optional[Collection] = None
    self.trskl: Optional[BufferedReader] = None
    self.trmsh: Optional[BufferedReader] = None
    self.trmtr: Optional[BufferedReader] = None
    self.bone_structure: Optional[Armature] = None
    self.bone_id_map: Optional[dict] = None
    self.materials: Optional[list[Material]] = None
    self.mat_data_array: Optional[list[dict]] = None
    self.trmsh_count: Optional[int] = None
    self.poly_group_count: Optional[int] = None
    self.trmsh_lods_array: Optional[list] = None
    self.chara_check: Optional[str] = None

    if IN_BLENDER_ENV:
      self.create_collection()

    self.process_trmdl()

  def create_collection(self):
    self.new_collection = bpy.data.collections.new(os.path.basename(self.trmdl.name))
    
    bpy.context.scene.collection.children.link(self.new_collection)

  def process_trmdl(self):
    self.process_trmdl_pla()
    self.process_trskl_pla()
    self.process_trmtr_pla()

    if not self.settings["loadlods"]:
      self.trmsh_count = 1

    if self.trmsh_count is None or self.trmsh_lods_array is None:
      raise TRMSHError()

    self.process_trmsh_pla()
    self.process_trmbf_pla()
    return {"FINISHED"}


  def process_trmsh_pla(self):
    
    for w in range(self.trmsh_count):
      if os.path.exists(os.path.join(self.filep, self.trmsh_lods_array[w])):
        self.trmsh = open(os.path.join(self.filep, self.trmsh_lods_array[w]), "rb")
        trmsh_file_start = readlong(self.trmsh)
        print("Parsing TRMSH...")
        fseek(self.trmsh, trmsh_file_start)
        trmsh_struct = ftell(self.trmsh) - readlong(self.trmsh)
        fseek(self.trmsh, trmsh_struct)
        trmsh_struct_len = readshort(self.trmsh)

        if trmsh_struct_len != 0x000A:
          raise AssertionError("Unexpected TRMSH header struct length!")
        trmsh_struct_section_len = readshort(self.trmsh)
        trmsh_struct_start = readshort(self.trmsh)
        trmsh_struct_poly_group = readshort(self.trmsh)
        trmsh_struct_trmbf = readshort(self.trmsh)

        if trmsh_struct_trmbf != 0:
          fseek(self.trmsh, trmsh_file_start + trmsh_struct_trmbf)
          trmbf_filename_start = ftell(self.trmsh) + readlong(self.trmsh)
          fseek(self.trmsh, trmbf_filename_start)
          trmbf_filename_len = readlong(self.trmsh)
          trmbf_filename = readfixedstring(self.trmsh, trmbf_filename_len)
          print(trmbf_filename)

          self.trmbf = None
          if os.path.exists(os.path.join(self.filep, trmbf_filename)):
            self.trmbf = open(os.path.join(self.filep, trmbf_filename), "rb")
          else:
            raise AssertionError(f"Can't find {trmbf_filename}!")

          if self.trmbf != None:
            print("Parsing TRMBF...")
            trmbf_file_start = readlong(self.trmbf)
            fseek(self.trmbf, trmbf_file_start)
            trmbf_struct = ftell(self.trmbf) - readlong(self.trmbf)
            fseek(self.trmbf, trmbf_struct)
            trmbf_struct_len = readshort(self.trmbf)

            if trmbf_struct_len != 0x0008:
              raise AssertionError("Unexpected TRMBF header struct length!")
            trmbf_struct_section_len = readshort(self.trmbf)
            trmbf_struct_start = readshort(self.trmbf)
            trmbf_struct_buffer = readshort(self.trmbf)

            if trmsh_struct_poly_group != 0:
              fseek(self.trmsh, trmsh_file_start + trmsh_struct_poly_group)
              poly_group_start = ftell(self.trmsh) + readlong(self.trmsh)
              fseek(self.trmsh, poly_group_start)
              poly_group_count = readlong(self.trmsh)

              fseek(self.trmbf, trmbf_file_start + trmbf_struct_buffer)
              vert_buffer_start = ftell(self.trmbf) + readlong(self.trmbf)
              vert_buffer_count = readlong(self.trmbf)    
    return self.trmsh, self.trmbf, poly_group_count      


  def process_trmbf_pla(self):
      poly_group_array = []
      for x in range(self.poly_group_count):
        vert_array = []
        normal_array = []
        color_array = []
        alpha_array = []
        uv_array = []
        uv2_array = []
        uv3_array = []
        uv4_array = []
        face_array = []
        face_mat_id_array = []
        b1_array = []
        w1_array = []
        weight_array = []
        poly_group_name = ""
        vis_group_name = ""
        vert_buffer_stride = 0
        mat_id = 0
        positions_fmt = "None"
        normals_fmt = "None"
        tangents_fmt = "None"
        bitangents_fmt = "None"
        tritangents_fmt = "None"
        uvs_fmt = "None"
        uvs2_fmt = "None"
        uvs3_fmt = "None"
        uvs4_fmt = "None"
        colors_fmt = "None"
        colors2_fmt = "None"
        bones_fmt = "None"
        weights_fmt = "None"
        svunk_fmt = "None"

        poly_group_offset = ftell(self.trmsh) + readlong(self.trmsh)
        poly_group_ret = ftell(self.trmsh)
        fseek(self.trmsh, poly_group_offset)
        print(f"PolyGroup offset #{x}: {hex(poly_group_offset)}")
        poly_group_struct = ftell(self.trmsh) - readlong(self.trmsh)
        fseek(self.trmsh, poly_group_struct)
        poly_group_struct_len = readshort(self.trmsh)

        poly_group_struct_section_len = readshort(self.trmsh)
        poly_group_struct_ptr_poly_group_name = readshort(self.trmsh)
        poly_group_struct_ptr_bbbox = readshort(self.trmsh)
        poly_group_struct_ptp_unc_a = readshort(self.trmsh)
        poly_group_struct_ptr_vert_buff = readshort(self.trmsh)
        poly_group_struct_ptr_mat_list = readshort(self.trmsh)
        poly_group_struct_ptr_unk_b = readshort(self.trmsh)
        poly_group_struct_ptr_unk_c = readshort(self.trmsh)
        poly_group_struct_ptr_unk_d = readshort(self.trmsh)
        poly_group_struct_ptr_unk_e = readshort(self.trmsh)
        poly_group_struct_ptr_unk_float = readshort(self.trmsh)
        poly_group_struct_ptr_unk_g = readshort(self.trmsh)
        poly_group_struct_ptr_unk_h = readshort(self.trmsh)
        poly_group_struct_ptr_vis_group_name = readshort(self.trmsh)

        if poly_group_struct_ptr_mat_list != 0:
          fseek(
                    self.trmsh,
                    poly_group_offset + poly_group_struct_ptr_mat_list,
                  )
          mat_offset = ftell(self.trmsh) + readlong(self.trmsh)
          fseek(self.trmsh, mat_offset)
          mat_count = readlong(self.trmsh)
          for y in range(mat_count):
            mat_entry_offset = ftell(self.trmsh) + readlong(self.trmsh)
            mat_ret = ftell(self.trmsh)
            fseek(self.trmsh, mat_entry_offset)
            mat_struct = ftell(self.trmsh) - readlong(self.trmsh)
            fseek(self.trmsh, mat_struct)
            mat_struct_len = readshort(self.trmsh)

            if mat_struct_len != 0x000E:
              raise AssertionError(
                        "Unexpected material struct length!"
                      )
            mat_struct_section_len = readshort(self.trmsh)
            mat_struct_ptr_facepoint_count = readshort(self.trmsh)
            mat_struct_ptr_facepoint_start = readshort(self.trmsh)
            mat_struct_ptr_unk_c = readshort(self.trmsh)
            mat_struct_ptr_string = readshort(self.trmsh)
            mat_struct_ptr_unk_d = readshort(self.trmsh)

            if mat_struct_ptr_facepoint_count != 0:
              fseek(
                        self.trmsh,
                        mat_entry_offset
                        + mat_struct_ptr_facepoint_count,
                      )
              mat_facepoint_count = int(readlong(self.trmsh) / 3)

            if mat_struct_ptr_facepoint_start != 0:
              fseek(
                        self.trmsh,
                        mat_entry_offset
                        + mat_struct_ptr_facepoint_start,
                      )
              mat_facepoint_start = int(readlong(self.trmsh) / 3)
            else:
              mat_facepoint_start = 0

            if mat_struct_ptr_unk_c != 0:
              fseek(
                        self.trmsh,
                        mat_entry_offset + mat_struct_ptr_unk_c,
                      )
              mat_unk_c = readlong(self.trmsh)

            if mat_struct_ptr_string != 0:
              fseek(
                        self.trmsh,
                        mat_entry_offset + mat_struct_ptr_string,
                      )
              mat_name_offset = ftell(self.trmsh) + readlong(self.trmsh)
              fseek(self.trmsh, mat_name_offset)
              mat_name_len = readlong(self.trmsh)
              mat_name = readfixedstring(self.trmsh, mat_name_len)

            if mat_struct_ptr_unk_d != 0:
              fseek(
                        self.trmsh,
                        mat_entry_offset + mat_struct_ptr_unk_d,
                      )
              mat_unk_d = readlong(self.trmsh)

            mat_id = 0
            for z in range(len(self.mat_data_array)):
              if self.mat_data_array[z]["mat_name"] == mat_name:
                mat_id = z
                break

            for z in range(mat_facepoint_count):
              face_mat_id_array.append(mat_id)

            print(
                      f"Material {mat_name}: FaceCount = {mat_facepoint_count}, FaceStart = {mat_facepoint_start}"
                    )
            fseek(self.trmsh, mat_ret)

        if poly_group_struct_ptr_poly_group_name != 0:
          fseek(
                    self.trmsh,
                    poly_group_offset
                    + poly_group_struct_ptr_poly_group_name,
                  )
          poly_group_name_offset = ftell(self.trmsh) + readlong(self.trmsh)
          fseek(self.trmsh, poly_group_name_offset)
          poly_group_name_len = readlong(self.trmsh)
          poly_group_name = readfixedstring(
                    self.trmsh, poly_group_name_len
                  )
          print(f"Building {poly_group_name}...")
        if poly_group_struct_ptr_vis_group_name != 0:
          fseek(
                    self.trmsh,
                    poly_group_offset
                    + poly_group_struct_ptr_vis_group_name,
                  )
          vis_group_name_offset = ftell(self.trmsh) + readlong(self.trmsh)
          fseek(self.trmsh, vis_group_name_offset)
          vis_group_name_len = readlong(self.trmsh)
          vis_group_name = readfixedstring(
                    self.trmsh, vis_group_name_len
                  )
                  # changed the output variable because the original seems to be a typo
          print(f"VisGroup: {vis_group_name}")
        if poly_group_struct_ptr_vert_buff != 0:
          fseek(
                    self.trmsh,
                    poly_group_offset + poly_group_struct_ptr_vert_buff,
                  )
          poly_group_vert_buff_offset = ftell(self.trmsh) + readlong(
                    self.trmsh
                  )
          fseek(self.trmsh, poly_group_vert_buff_offset)
          vert_buff_count = readlong(self.trmsh)
          vert_buff_offset = ftell(self.trmsh) + readlong(self.trmsh)
          fseek(self.trmsh, vert_buff_offset)
          vert_buff_struct = ftell(self.trmsh) - readlong(self.trmsh)
          fseek(self.trmsh, vert_buff_struct)
          vert_buff_struct_len = readshort(self.trmsh)

          if vert_buff_struct_len != 0x0008:
            raise AssertionError(
                      "Unexpected VertexBuffer struct length!"
                    )
          vert_buff_struct_section_len = readshort(self.trmsh)
          vert_buff_struct_ptr_param = readshort(self.trmsh)
          vert_buff_struct_ptr_b = readshort(self.trmsh)

          if vert_buff_struct_ptr_param != 0:
            fseek(
                      self.trmsh,
                      vert_buff_offset + vert_buff_struct_ptr_param,
                    )
            vert_buff_param_offset = ftell(self.trmsh) + readlong(
                      self.trmsh
                    )
            fseek(self.trmsh, vert_buff_param_offset)
            vert_buff_param_count = readlong(self.trmsh)
            for y in range(vert_buff_param_count):
              vert_buff_param_offset = ftell(
                        self.trmsh
                      ) + readlong(self.trmsh)
              vert_buff_param_ret = ftell(self.trmsh)
              fseek(self.trmsh, vert_buff_param_offset)
              vert_buff_param_struct = ftell(
                        self.trmsh
                      ) - readlong(self.trmsh)
              fseek(self.trmsh, vert_buff_param_struct)
              vert_buff_param_struct_len = readshort(self.trmsh)

              if vert_buff_param_struct_len == 0x000C:
                vert_buff_param_struct_section_len = (
                          readshort(self.trmsh)
                        )
                vert_buff_param_ptr_unk_a = readshort(self.trmsh)
                vert_buff_param_ptr_type = readshort(self.trmsh)
                vert_buff_param_ptr_layer = readshort(self.trmsh)
                vert_buff_param_ptr_fmt = readshort(self.trmsh)
                vert_buff_param_ptr_position = 0
              elif vert_buff_param_struct_len == 0x000E:
                vert_buff_param_struct_section_len = (
                          readshort(self.trmsh)
                        )
                vert_buff_param_ptr_unk_a = readshort(self.trmsh)
                vert_buff_param_ptr_type = readshort(self.trmsh)
                vert_buff_param_ptr_layer = readshort(self.trmsh)
                vert_buff_param_ptr_fmt = readshort(self.trmsh)
                vert_buff_param_ptr_position = readshort(
                          self.trmsh
                        )
              else:
                raise AssertionError(
                          "Unknown vertex buffer parameter struct length!"
                        )

              vert_buff_param_layer = 0

              if vert_buff_param_ptr_type != 0:
                fseek(
                          self.trmsh,
                          vert_buff_param_offset
                          + vert_buff_param_ptr_type,
                        )
                vert_buff_param_type = readlong(self.trmsh)
              if vert_buff_param_ptr_layer != 0:
                fseek(
                          self.trmsh,
                          vert_buff_param_offset
                          + vert_buff_param_ptr_layer,
                        )
                vert_buff_param_layer = readlong(self.trmsh)
              if vert_buff_param_ptr_fmt != 0:
                fseek(
                          self.trmsh,
                          vert_buff_param_offset
                          + vert_buff_param_ptr_fmt,
                        )
                vert_buff_param_format = readlong(self.trmsh)
              if vert_buff_param_ptr_position != 0:
                fseek(
                          self.trmsh,
                          vert_buff_param_offset
                          + vert_buff_param_ptr_position,
                        )
                vert_buff_param_position = readlong(self.trmsh)
              else:
                vert_buff_param_position = 0

                      # -- Types:
                      # -- 0x01: = Positions
                      # -- 0x02 = Normals
                      # -- 0x03 = Tangents
                      # -- 0x05 = Colors
                      # -- 0x06 = UVs
                      # -- 0x07 = NodeIDs
                      # -- 0x08 = Weights
                      #
                      # -- Formats:
                      # -- 0x14 = 4 bytes as float
                      # -- 0x16 = 4 bytes
                      # -- 0x27 = 4 shorts as float
                      # -- 0x2B = 4 half-floats
                      # -- 0x30 = 2 floats
                      # -- 0x33 = 3 floats
                      # -- 0x36 = 4 floats

              if vert_buff_param_type == 0x01:
                if vert_buff_param_layer != 0:
                  raise AssertionError(
                            "Unexpected positions layer!"
                          )

                if vert_buff_param_format != 0x33:
                  raise AssertionError(
                            "Unexpected positions format!"
                          )

                positions_fmt = "3Floats"
                vert_buffer_stride = (
                          vert_buffer_stride + 0x0C
                        )
              elif vert_buff_param_type == 0x02:
                if vert_buff_param_layer != 0:
                  raise AssertionError(
                            "Unexpected normals layer!"
                          )

                if vert_buff_param_format != 0x2B:
                  raise AssertionError(
                            "Unexpected normals format!"
                          )

                normals_fmt = "4HalfFloats"
                vert_buffer_stride = (
                          vert_buffer_stride + 0x08
                        )
              elif vert_buff_param_type == 0x03:
                if vert_buff_param_layer == 0:
                  if vert_buff_param_format != 0x2B:
                    raise AssertionError(
                              "Unexpected tangents format!"
                            )

                  tangents_fmt = "4HalfFloats"
                  vert_buffer_stride = (
                            vert_buffer_stride + 0x08
                          )
                elif vert_buff_param_layer == 1:
                  if vert_buff_param_format != 0x2B:
                    raise AssertionError(
                              "Unexpected bitangents format!"
                            )

                  bitangents_fmt = "4HalfFloats"
                  vert_buffer_stride = (
                            vert_buffer_stride + 0x08
                          )
                elif vert_buff_param_layer == 2:
                  if vert_buff_param_format != 0x2B:
                    raise AssertionError(
                              "Unexpected tritangents format!"
                            )

                  tritangents_fmt = "4HalfFloats"
                  vert_buffer_stride = (
                            vert_buffer_stride + 0x08
                          )
                else:
                  raise AssertionError(
                            "Unexpected tangents layer!"
                          )
              elif vert_buff_param_type == 0x05:
                if vert_buff_param_layer == 0:
                  if vert_buff_param_format == 0x14:
                    colors_fmt = "4BytesAsFloat"
                    vert_buffer_stride = (
                              vert_buffer_stride + 0x04
                            )
                  elif vert_buff_param_format == 0x36:
                    colors_fmt = "4Floats"
                    vert_buffer_stride = (
                              vert_buffer_stride + 0x10
                            )
                  else:
                    raise AssertionError(
                              "Unexpected colors format!"
                            )
                elif vert_buff_param_layer == 1:
                  if vert_buff_param_format == 0x14:
                    colors2_fmt = "4BytesAsFloat"
                    vert_buffer_stride = (
                              vert_buffer_stride + 0x04
                            )
                  elif vert_buff_param_format == 0x36:
                    colors2_fmt = "4Floats"
                    vert_buffer_stride = (
                              vert_buffer_stride + 0x10
                            )
                  else:
                    raise AssertionError(
                              "Unexpected colors2 format!"
                            )
              elif vert_buff_param_type == 0x06:
                if vert_buff_param_layer == 0:
                  if vert_buff_param_format != 0x30:
                    raise AssertionError(
                              "Unexpected UVs format!"
                            )

                  uvs_fmt = "2Floats"
                  vert_buffer_stride = (
                            vert_buffer_stride + 0x08
                          )
                elif vert_buff_param_layer == 1:
                  if vert_buff_param_format != 0x30:
                    raise AssertionError(
                              "Unexpected UVs2 format!"
                            )

                  uvs2_fmt = "2Floats"
                  vert_buffer_stride = (
                            vert_buffer_stride + 0x08
                          )
                elif vert_buff_param_layer == 2:
                  if vert_buff_param_format != 0x30:
                    raise AssertionError(
                              "Unexpected UVs3 format!"
                            )

                  uvs3_fmt = "2Floats"
                  vert_buffer_stride = (
                            vert_buffer_stride + 0x08
                          )
                elif vert_buff_param_layer == 3:
                  if vert_buff_param_format != 0x30:
                    raise AssertionError(
                              "Unexpected UVs4 format!"
                            )

                  uvs4_fmt = "2Floats"
                  vert_buffer_stride = (
                            vert_buffer_stride + 0x08
                          )
                else:
                  raise AssertionError(
                            "Unexpected UVs layer!"
                          )
              elif vert_buff_param_type == 0x07:
                if vert_buff_param_layer != 0:
                  raise AssertionError(
                            "Unexpected node IDs layer!"
                          )

                if vert_buff_param_format != 0x16:
                  raise AssertionError(
                            "Unexpected node IDs format!"
                          )

                bones_fmt = "4Bytes"
                vert_buffer_stride = (
                          vert_buffer_stride + 0x04
                        )
              elif vert_buff_param_type == 0x08:
                if vert_buff_param_layer != 0:
                  raise AssertionError(
                            "Unexpected weights layer!"
                          )

                if vert_buff_param_format != 0x27:
                  raise AssertionError(
                            "Unexpected weights format!"
                          )

                weights_fmt = "4ShortsAsFloat"
                vert_buffer_stride = (
                          vert_buffer_stride + 0x08
                        )
              elif vert_buff_param_type == 0x09:
                if vert_buff_param_layer != 0:
                  raise AssertionError(
                            "Unexpected ?????? layer!"
                          )

                if vert_buff_param_format != 0x24:
                  raise AssertionError(
                            "Unexpected ?????? layer!"
                          )

                svunk_fmt = "1Long?"
                vert_buffer_stride = (
                          vert_buffer_stride + 0x04
                        )
              else:
                raise AssertionError("Unknown vertex type!")

              fseek(self.trmsh, vert_buff_param_ret)

        poly_group_array.append(
                  {
                    "poly_group_name": poly_group_name,
                    "vis_group_name": vis_group_name,
                    "vert_buffer_stride": vert_buffer_stride,
                    "positions_fmt": positions_fmt,
                    "normals_fmt": normals_fmt,
                    "tangents_fmt": tangents_fmt,
                    "bitangents_fmt": bitangents_fmt,
                    "tritangents_fmt": tritangents_fmt,
                    "uvs_fmt": uvs_fmt,
                    "uvs2_fmt": uvs2_fmt,
                    "uvs3_fmt": uvs3_fmt,
                    "uvs4_fmt": uvs4_fmt,
                    "colors_fmt": colors_fmt,
                    "colors2_fmt": colors2_fmt,
                    "bones_fmt": bones_fmt,
                    "weights_fmt": weights_fmt,
                    "svunk_fmt": svunk_fmt,
                  }
                )
        fseek(self.trmsh, poly_group_ret)

        vert_buffer_offset = ftell(self.trmbf) + readlong(self.trmbf)
        vert_buffer_ret = ftell(self.trmbf)
        fseek(self.trmbf, vert_buffer_offset)
        vert_buffer_struct = ftell(self.trmbf) - readlong(self.trmbf)
        fseek(self.trmbf, vert_buffer_struct)
        vert_buffer_struct_len = readshort(self.trmbf)

        vert_buffer_struct_section_length = readshort(self.trmbf)
        vert_buffer_struct_ptr_faces = readshort(self.trmbf)
        vert_buffer_struct_ptr_verts = readshort(self.trmbf)

        if vert_buffer_struct_ptr_verts != 0:
          fseek(
                    self.trmbf,
                    vert_buffer_offset + vert_buffer_struct_ptr_verts,
                  )
          vert_buffer_sub_start = ftell(self.trmbf) + readlong(self.trmbf)
          fseek(self.trmbf, vert_buffer_sub_start)
          vert_buffer_sub_count = readlong(self.trmbf)

          for y in range(vert_buffer_sub_count):
            vert_buffer_sub_offset = ftell(self.trmbf) + readlong(
                      self.trmbf
                    )
            vert_buffer_sub_ret = ftell(self.trmbf)
            fseek(self.trmbf, vert_buffer_sub_offset)
            if y == 0:
              print(
                        f"Vertex buffer {x} header: {hex(ftell(self.trmbf))}"
                      )
            else:
              print(
                        f"Vertex buffer {x} morph {y} header: {hex(ftell(self.trmbf))}"
                      )
            vert_buffer_sub_struct = ftell(self.trmbf) - readlong(
                      self.trmbf
                    )
            fseek(self.trmbf, vert_buffer_sub_struct)
            vert_buffer_sub_struct_len = readshort(self.trmbf)

            if vert_buffer_sub_struct_len != 0x0006:
              raise AssertionError(
                        "Unexpected vertex buffer struct length!"
                      )
            vert_buffer_sub_struct_section_length = readshort(
                      self.trmbf
                    )
            vert_buffer_sub_struct_ptr = readshort(self.trmbf)

            if vert_buffer_sub_struct_ptr != 0:
              fseek(
                        self.trmbf,
                        vert_buffer_sub_offset
                        + vert_buffer_sub_struct_ptr,
                      )
              vert_buffer_start = ftell(self.trmbf) + readlong(
                        self.trmbf
                      )
              fseek(self.trmbf, vert_buffer_start)
              vert_buffer_byte_count = readlong(self.trmbf)
              if y == 0:
                print(
                          f"Vertex buffer {x} start: {hex(ftell(self.trmbf))}"
                        )

                for v in range(
                          vert_buffer_byte_count
                          // poly_group_array[x][
                            "vert_buffer_stride"
                          ]
                        ):
                  if (
                            poly_group_array[x]["positions_fmt"]
                            == "4HalfFloats"
                          ):
                    vx = readhalffloat(self.trmbf)
                    vy = readhalffloat(self.trmbf)
                    vz = readhalffloat(self.trmbf)
                    vq = readhalffloat(self.trmbf)
                  elif (
                            poly_group_array[x]["positions_fmt"]
                            == "3Floats"
                          ):
                    vx = readfloat(self.trmbf)
                    vy = readfloat(self.trmbf)
                    vz = readfloat(self.trmbf)
                  else:
                    raise AssertionError(
                              "Unknown positions type!"
                            )

                  if (
                            poly_group_array[x]["normals_fmt"]
                            == "4HalfFloats"
                          ):
                    nx = readhalffloat(self.trmbf)
                    ny = readhalffloat(self.trmbf)
                    nz = readhalffloat(self.trmbf)
                    nq = readhalffloat(self.trmbf)
                  elif (
                            poly_group_array[x]["normals_fmt"]
                            == "3Floats"
                          ):
                    nx = readfloat(self.trmbf)
                    ny = readfloat(self.trmbf)
                    nz = readfloat(self.trmbf)
                  else:
                    raise AssertionError(
                              "Unknown normals type!"
                            )

                  if (
                            poly_group_array[x]["tangents_fmt"]
                            == "None"
                          ):
                    pass
                  elif (
                            poly_group_array[x]["tangents_fmt"]
                            == "4HalfFloats"
                          ):
                    tanx = readhalffloat(self.trmbf)
                    tany = readhalffloat(self.trmbf)
                    tanz = readhalffloat(self.trmbf)
                    tanq = readhalffloat(self.trmbf)
                  elif (
                            poly_group_array[x]["tangents_fmt"]
                            == "3Floats"
                          ):
                    tanx = readfloat(self.trmbf)
                    tany = readfloat(self.trmbf)
                    tanz = readfloat(self.trmbf)
                  else:
                    raise AssertionError(
                              "Unknown tangents type!"
                            )

                  if (
                            poly_group_array[x][
                              "bitangents_fmt"
                            ]
                            == "None"
                          ):
                    pass
                  elif (
                            poly_group_array[x][
                              "bitangents_fmt"
                            ]
                            == "4HalfFloats"
                          ):
                    bitanx = readhalffloat(self.trmbf)
                    bitany = readhalffloat(self.trmbf)
                    bitanz = readhalffloat(self.trmbf)
                    bitanq = readhalffloat(self.trmbf)
                  elif (
                            poly_group_array[x][
                              "bitangents_fmt"
                            ]
                            == "3Floats"
                          ):
                    bitanx = readfloat(self.trmbf)
                    bitany = readfloat(self.trmbf)
                    bitanz = readfloat(self.trmbf)
                  else:
                    raise AssertionError(
                              "Unknown bitangents type!"
                            )

                  if (
                            poly_group_array[x][
                              "tritangents_fmt"
                            ]
                            == "None"
                          ):
                    pass
                  elif (
                            poly_group_array[x][
                              "tritangents_fmt"
                            ]
                            == "4HalfFloats"
                          ):
                    tritanx = readhalffloat(self.trmbf)
                    tritany = readhalffloat(self.trmbf)
                    tritanz = readhalffloat(self.trmbf)
                    tritanq = readhalffloat(self.trmbf)
                  elif (
                            poly_group_array[x][
                              "tritangents_fmt"
                            ]
                            == "3Floats"
                          ):
                    tritanx = readfloat(self.trmbf)
                    tritany = readfloat(self.trmbf)
                    tritanz = readfloat(self.trmbf)
                  else:
                    raise AssertionError(
                              "Unknown bitangents type!"
                            )

                  if (
                            poly_group_array[x]["uvs_fmt"]
                            == "None"
                          ):
                    tu = 0
                    tv = 0
                  elif (
                            poly_group_array[x]["uvs_fmt"]
                            == "2Floats"
                          ):
                    tu = readfloat(self.trmbf)
                    tv = readfloat(self.trmbf)
                  else:
                    raise AssertionError(
                              "Unknown uvs type!"
                            )

                  if (
                            poly_group_array[x]["uvs2_fmt"]
                            == "None"
                          ):
                    pass
                  elif (
                            poly_group_array[x]["uvs2_fmt"]
                            == "2Floats"
                          ):
                    tu2 = readfloat(self.trmbf)
                    tv2 = readfloat(self.trmbf)
                    uv2_array.append((tu2, tv2))
                  else:
                    raise AssertionError(
                              "Unknown uvs2 type!"
                            )

                  if (
                            poly_group_array[x]["uvs3_fmt"]
                            == "None"
                          ):
                    pass
                  elif (
                            poly_group_array[x]["uvs3_fmt"]
                            == "2Floats"
                          ):
                    tu3 = readfloat(self.trmbf)
                    tv3 = readfloat(self.trmbf)
                    uv3_array.append((tu3, tv3))
                  else:
                    raise AssertionError(
                              "Unknown uvs3 type!"
                            )

                  if (
                            poly_group_array[x]["uvs4_fmt"]
                            == "None"
                          ):
                    pass
                  elif (
                            poly_group_array[x]["uvs4_fmt"]
                            == "2Floats"
                          ):
                    tu4 = readfloat(self.trmbf)
                    tv4 = readfloat(self.trmbf)
                    uv4_array.append((tu4, tv4))
                  else:
                    raise AssertionError(
                              "Unknown uvs4 type!"
                            )

                  if (
                            poly_group_array[x]["colors_fmt"]
                            == "None"
                          ):
                    colorr = 255
                    colorg = 255
                    colorb = 255
                    colora = 1
                  elif (
                            poly_group_array[x]["colors_fmt"]
                            == "4BytesAsFloat"
                          ):
                    colorr = readbyte(self.trmbf)
                    colorg = readbyte(self.trmbf)
                    colorb = readbyte(self.trmbf)
                    colora = (
                              float(readbyte(self.trmbf)) / 255
                            )
                  elif (
                            poly_group_array[x]["colors_fmt"]
                            == "4Floats"
                          ):
                    colorr = readfloat(self.trmbf) * 255
                    colorg = readfloat(self.trmbf) * 255
                    colorb = readfloat(self.trmbf) * 255
                    colora = readfloat(self.trmbf)
                  else:
                    raise AssertionError(
                              "Unknown colors type!"
                            )

                  if (
                            poly_group_array[x]["colors2_fmt"]
                            == "None"
                          ):
                    colorr2 = 255
                    colorg2 = 255
                    colorb2 = 255
                    colora2 = 1
                  elif (
                            poly_group_array[x]["colors2_fmt"]
                            == "4BytesAsFloat"
                          ):
                    colorr2 = readbyte(self.trmbf)
                    colorg2 = readbyte(self.trmbf)
                    colorb2 = readbyte(self.trmbf)
                    colora2 = readbyte(self.trmbf)
                  elif (
                            poly_group_array[x]["colors2_fmt"]
                            == "4Floats"
                          ):
                    colorr2 = readfloat(self.trmbf) * 255
                    colorg2 = readfloat(self.trmbf) * 255
                    colorb2 = readfloat(self.trmbf) * 255
                    colora2 = readfloat(self.trmbf)
                  else:
                    raise AssertionError(
                              "Unknown colors 2 type!"
                            )

                  if (
                            poly_group_array[x]["bones_fmt"]
                            == "None"
                          ):
                    bone1 = 0
                    bone2 = 0
                    bone3 = 0
                    bone4 = 0
                  elif (
                            poly_group_array[x]["bones_fmt"]
                            == "4Bytes"
                          ):
                    bone1 = readbyte(self.trmbf)
                    bone2 = readbyte(self.trmbf)
                    bone3 = readbyte(self.trmbf)
                    bone4 = readbyte(self.trmbf)
                  else:
                    raise AssertionError(
                              "Unknown bones type!"
                            )

                  if (
                            poly_group_array[x]["weights_fmt"]
                            == "None"
                          ):
                    weight1 = 0
                    weight2 = 0
                    weight3 = 0
                    weight4 = 0
                  elif (
                            poly_group_array[x]["weights_fmt"]
                            == "4ShortsAsFloat"
                          ):
                    weight1 = readshort(self.trmbf) / 65535
                    weight2 = readshort(self.trmbf) / 65535
                    weight3 = readshort(self.trmbf) / 65535
                    weight4 = readshort(self.trmbf) / 65535
                  else:
                    raise AssertionError(
                              "Unknown weights type!"
                            )

                  vert_array.append((vx, vy, vz))
                  normal_array.append((nx, ny, nz))
                  color_array.append(
                            (colorr, colorg, colorb)
                          )
                  alpha_array.append(colora)
                  uv_array.append((tu, tv))
                  if self.trskl is not None:
                    w1_array.append(
                              {
                                "weight1": weight1,
                                "weight2": weight2,
                                "weight3": weight3,
                                "weight4": weight4,
                              }
                            )
                    b1_array.append(
                              {
                                "bone1": bone1,
                                "bone2": bone2,
                                "bone3": bone3,
                                "bone4": bone4,
                              }
                            )

                print(
                          f"Vertex buffer {x} end: {hex(ftell(self.trmbf))}"
                        )
              else:
                print(
                          f"Vertex buffer {x} morph {y} start: {hex(ftell(self.trmbf))}"
                        )
                        # MorphVert_array = #()
                        # MorphNormal_array = #()
                for v in range(
                          int(vert_buffer_byte_count / 0x1C)
                        ):
                          # Morphs always seem to use this setup.
                  vx = readlong(self.trmbf)
                  vy = readlong(self.trmbf)
                  vz = readlong(self.trmbf)
                  nx = readhalffloat(self.trmbf)
                  ny = readhalffloat(self.trmbf)
                  nz = readhalffloat(self.trmbf)
                  nq = readhalffloat(self.trmbf)
                  tanx = readhalffloat(self.trmbf)
                  tany = readhalffloat(self.trmbf)
                  tanz = readhalffloat(self.trmbf)
                  tanq = readhalffloat(self.trmbf)
                          # append MorphVert_array [vx,vy,vz]
                          # append MorphNormal_array [nx,ny,nz]
                print(
                          f"Vertex buffer {x} morph {y} end: {hex(ftell(self.trmbf))}"
                        )
                        # TODO: Continue implementing after line 3814
            fseek(self.trmbf, vert_buffer_sub_ret)

        if vert_buffer_struct_ptr_faces != 0:
          fseek(
                    self.trmbf,
                    vert_buffer_offset + vert_buffer_struct_ptr_faces,
                  )
          face_buffer_start = ftell(self.trmbf) + readlong(self.trmbf)
          fseek(self.trmbf, face_buffer_start)
          face_buffer_count = readlong(self.trmbf)

          for y in range(face_buffer_count):
            face_buff_offset = ftell(self.trmbf) + readlong(self.trmbf)
            face_buff_ret = ftell(self.trmbf)
            fseek(self.trmbf, face_buff_offset)
            print(f"Facepoint {x} header: {hex(ftell(self.trmbf))}")
            face_buff_struct = ftell(self.trmbf) - readlong(self.trmbf)
            fseek(self.trmbf, face_buff_struct)
            face_buff_struct_len = readshort(self.trmbf)

            if face_buff_struct_len != 0x0006:
              raise AssertionError(
                        "Unexpected face buffer struct length!"
                      )
            face_buffer_struct_section_length = readshort(self.trmbf)
            face_buffer_struct_ptr = readshort(self.trmbf)

            if face_buffer_struct_ptr != 0:
              fseek(
                        self.trmbf,
                        face_buff_offset + face_buffer_struct_ptr,
                      )
              facepoint_start = ftell(self.trmbf) + readlong(self.trmbf)
              fseek(self.trmbf, facepoint_start)
              facepoint_byte_count = readlong(self.trmbf)
              print(
                        f"Facepoint {x} start: {hex(ftell(self.trmbf))}"
                      )

              if (
                        len(vert_array) > 65536
                      ):  # is this a typo? I would imagine it to be 65535
                for v in range(facepoint_byte_count // 12):
                  fa = readlong(self.trmbf)
                  fb = readlong(self.trmbf)
                  fc = readlong(self.trmbf)
                  face_array.append([fa, fb, fc])
              else:
                for v in range(facepoint_byte_count // 6):
                  fa = readshort(self.trmbf)
                  fb = readshort(self.trmbf)
                  fc = readshort(self.trmbf)
                  face_array.append([fa, fb, fc])
              print(f"Facepoint {x} end: {hex(ftell(self.trmbf))}")
            fseek(self.trmbf, face_buff_ret)
        fseek(self.trmbf, vert_buffer_ret)

        print("Making object...")

        for b in range(len(w1_array)):
          w = {"boneids": [], "weights": []}
          maxweight = (
                    w1_array[b]["weight1"]
                    + w1_array[b]["weight2"]
                    + w1_array[b]["weight3"]
                    + w1_array[b]["weight4"]
                  )

          if maxweight > 0:
            if w1_array[b]["weight1"] > 0:
              w["boneids"].append(b1_array[b]["bone1"])
              w["weights"].append(w1_array[b]["weight1"])
            if w1_array[b]["weight2"] > 0:
              w["boneids"].append(b1_array[b]["bone2"])
              w["weights"].append(w1_array[b]["weight2"])
            if w1_array[b]["weight3"] > 0:
              w["boneids"].append(b1_array[b]["bone3"])
              w["weights"].append(w1_array[b]["weight3"])
            if w1_array[b]["weight4"] > 0:
              w["boneids"].append(b1_array[b]["bone4"])
              w["weights"].append(w1_array[b]["weight4"])

          weight_array.append(w)

        if IN_BLENDER_ENV:
                  # LINE 3257
          new_mesh = bpy.data.meshes.new(
                    f"{poly_group_name}_mesh"
                  )
          new_mesh.from_pydata(vert_array, [], face_array)
          new_mesh.update()
          new_object = bpy.data.objects.new(
                    poly_group_name, new_mesh
                  )

          if self.bone_structure != None:
            new_object.parent = self.bone_structure
            new_object.modifiers.new(
                      name="Skeleton", type="ARMATURE"
                    )
            new_object.modifiers["Skeleton"].object = (
                      self.bone_structure
                    )

            for face in new_object.data.polygons:
              for vert_idx, loop_idx in zip(
                        face.vertices, face.loop_indices
                      ):
                w = weight_array[vert_idx]

                for i in range(len(w["boneids"])):
                  bone_id = self.bone_id_map[w["boneids"][i]]
                  weight = w["weights"][i]

                  group = None
                  if (
                            new_object.vertex_groups.get(
                              bone_id
                            )
                            == None
                          ):
                    group = (
                              new_object.vertex_groups.new(
                                name=bone_id
                              )
                            )
                  else:
                    group = new_object.vertex_groups[
                              bone_id
                            ]

                  group.add([vert_idx], weight, "REPLACE")

          color_layer = new_object.data.vertex_colors.new(
                    name="Color"
                  )
          new_object.data.vertex_colors.active = color_layer
                  # print(f"color_array: {len(color_array)}")
                  # print(f"polygons: {len(new_object.data.polygons)}")
          for i, poly in enumerate(new_object.data.polygons):
                    # print(f"poly: {i}")
            for v, vert in enumerate(poly.vertices):
              loop_index = poly.loop_indices[v]

                      # print(f"loop_index: {loop_index}")
                      # print((color_array[vert][0], color_array[vert][1], color_array[vert][2], 1))

              color_layer.data[loop_index].color = (
                        color_array[vert][0] / alpha_array[vert],
                        color_array[vert][1] / alpha_array[vert],
                        color_array[vert][2] / alpha_array[vert],
                        alpha_array[vert],
                      )

          for mat in self.materials:
            new_object.data.materials.append(mat)

                  # self.materials
          for i, poly in enumerate(new_object.data.polygons):
            poly.material_index = face_mat_id_array[i]

                  # uvs
          uv_layers = new_object.data.uv_layers
          uv_layer = uv_layers.new(name="UVMap")
          if len(uv2_array) > 0:
            uv2_layer = uv_layers.new(name="UV2Map")
          if len(uv3_array) > 0:
            uv3_layer = uv_layers.new(name="UV3Map")
          if len(uv4_array) > 0:
            uv4_layer = uv_layers.new(name="UV4Map")
          uv_layers.active = uv_layer

          for face in new_object.data.polygons:
            for vert_idx, loop_idx in zip(
                      face.vertices, face.loop_indices
                    ):
              uv_layer.data[loop_idx].uv = uv_array[vert_idx]
              if len(uv2_array) > 0:
                uv2_layer.data[loop_idx].uv = uv2_array[
                          vert_idx
                        ]
              if len(uv3_array) > 0:
                uv3_layer.data[loop_idx].uv = uv3_array[
                          vert_idx
                        ]
              if len(uv4_array) > 0:
                uv4_layer.data[loop_idx].uv = uv4_array[
                          vert_idx
                        ]

                  # normals
          if bpy.app.version < (4, 1, 0):
            new_object.data.use_auto_smooth = True
          new_object.data.normals_split_custom_set_from_vertices(
                    normal_array
                  )
                  # add object to scene collection
          self.new_collection.objects.link(new_object)


  def process_trmtr_pla(self):
    self.materials = []
    if self.trmtr is not None:
      print("Parsing TRMTR...")
      trmtr_file_start = readlong(self.trmtr)
      self.mat_data_array = []
      fseek(self.trmtr, trmtr_file_start)
      trmtr_struct = ftell(self.trmtr) - readlong(self.trmtr)
      fseek(self.trmtr, trmtr_struct)
      trmtr_struct_len = readshort(self.trmtr)

      if trmtr_struct_len != 0x0008:
        raise AssertionError("Unexpected TRMTR header struct length!")
      trmtr_struct_section_len = readshort(self.trmtr)
      trmtr_struct_start = readshort(self.trmtr)
      trmtr_struct_material = readshort(self.trmtr)

      if trmtr_struct_material != 0:
        fseek(self.trmtr, trmtr_file_start + trmtr_struct_material)
        mat_start = ftell(self.trmtr) + readlong(self.trmtr)
        fseek(self.trmtr, mat_start)
        mat_count = readlong(self.trmtr)
        for x in range(mat_count):
          mat_shader = "Standard"
          mat_col0 = ""
          mat_lym0 = ""
          mat_nrm0 = ""
          mat_ao0 = ""
          mat_emi0 = ""
          mat_rgh0 = ""
          mat_mtl0 = ""
          mat_msk0 = ""
          mat_highmsk0 = ""
          mat_uv_scale_u = 1.0
          mat_uv_scale_v = 1.0
          mat_uv_trs_u = 0
          mat_uv_trs_v = 0
          mat_uv_scale2_u = 1.0
          mat_uv_scale2_v = 1.0
          mat_uv_trs2_u = 0
          mat_uv_trs2_v = 0
          mat_color1_r = 1.0
          mat_color1_g = 1.0
          mat_color1_b = 1.0
          mat_color2_r = 1.0
          mat_color2_g = 1.0
          mat_color2_b = 1.0
          mat_color3_r = 1.0
          mat_color3_g = 1.0
          mat_color3_b = 1.0
          mat_color4_r = 1.0
          mat_color4_g = 1.0
          mat_color4_b = 1.0

          mat_emcolor1_r = 1.0
          mat_emcolor1_g = 1.0
          mat_emcolor1_b = 1.0
          mat_emcolor2_r = 1.0
          mat_emcolor2_g = 1.0
          mat_emcolor2_b = 1.0
          mat_emcolor3_r = 1.0
          mat_emcolor3_g = 1.0
          mat_emcolor3_b = 1.0
          mat_emcolor4_r = 1.0
          mat_emcolor4_g = 1.0
          mat_emcolor4_b = 1.0
          mat_emcolor5_r = 1.0
          mat_emcolor5_g = 1.0
          mat_emcolor5_b = 1.0
          mat_rgh_layer0 = 1.0
          mat_rgh_layer1 = 1.0
          mat_rgh_layer2 = 1.0
          mat_rgh_layer3 = 1.0
          mat_rgh_layer4 = 1.0
          mat_mtl_layer0 = 0.0
          mat_mtl_layer1 = 0.0
          mat_mtl_layer2 = 0.0
          mat_mtl_layer3 = 0.0
          mat_mtl_layer4 = 0.0
          mat_reflectance = 0.0
          mat_emm_intensity = 1.0
          mat_offset = ftell(self.trmtr) + readlong(self.trmtr)
          mat_ret = ftell(self.trmtr)

          mat_enable_base_color_map = False
          mat_enable_normal_map = False
          mat_enable_ao_map = False
          mat_enable_emission_color_map = False
          mat_enable_roughness_map = False
          mat_enable_metallic_map = False
          mat_enable_displacement_map = False
          mat_enable_highlight_map = False

          fseek(self.trmtr, mat_offset)
          print("--------------------")
          mat_struct = ftell(self.trmtr) - readlong(self.trmtr)
          fseek(self.trmtr, mat_struct)
          mat_struct_len = readshort(self.trmtr)

          if mat_struct_len != 0x0024:
            raise AssertionError("Unexpected material struct length!")
          mat_struct_section_len = readshort(self.trmtr)
          mat_struct_ptr_param_a = readshort(self.trmtr)
          mat_struct_ptr_param_b = readshort(self.trmtr)
          mat_struct_ptr_param_c = readshort(self.trmtr)
          mat_struct_ptr_param_d = readshort(self.trmtr)
          mat_struct_ptr_param_e = readshort(self.trmtr)
          mat_struct_ptr_param_f = readshort(self.trmtr)
          mat_struct_ptr_param_g = readshort(self.trmtr)
          mat_struct_ptr_param_h = readshort(self.trmtr)
          mat_struct_ptr_param_i = readshort(self.trmtr)
          mat_struct_ptr_param_j = readshort(self.trmtr)
          mat_struct_ptr_param_k = readshort(self.trmtr)
          mat_struct_ptr_param_l = readshort(self.trmtr)
          mat_struct_ptr_param_m = readshort(self.trmtr)
          mat_struct_ptr_param_n = readshort(self.trmtr)
          mat_struct_ptr_param_o = readshort(self.trmtr)
          mat_struct_ptr_param_p = readshort(self.trmtr)

          if mat_struct_ptr_param_a != 0:
            fseek(self.trmtr, mat_offset + mat_struct_ptr_param_a)
            mat_param_a_start = ftell(self.trmtr) + readlong(self.trmtr)
            fseek(self.trmtr, mat_param_a_start)
            mat_name_len = readlong(self.trmtr)
            mat_name = readfixedstring(self.trmtr, mat_name_len)
            print(f"Material properties for {mat_name}:")
          if mat_struct_ptr_param_b != 0:
            fseek(self.trmtr, mat_offset + mat_struct_ptr_param_b)
            mat_param_b_start = ftell(self.trmtr) + readlong(self.trmtr)
            fseek(self.trmtr, mat_param_b_start)
            mat_param_b_section_count = readlong(self.trmtr)
            for z in range(mat_param_b_section_count):
              mat_param_b_offset = ftell(self.trmtr) + readlong(self.trmtr)
              mat_param_b_ret = ftell(self.trmtr)
              fseek(self.trmtr, mat_param_b_offset)
              mat_param_b_struct = ftell(self.trmtr) - readlong(self.trmtr)
              fseek(self.trmtr, mat_param_b_struct)
              mat_param_b_struct_len = readshort(self.trmtr)

              if mat_param_b_struct_len != 0x0008:
                raise AssertionError(
                  "Unexpected material param b struct length!"
                )
              mat_param_b_struct_section_len = readshort(self.trmtr)
              mat_param_b_struct_ptr_string = readshort(self.trmtr)
              mat_param_b_struct_ptr_params = readshort(self.trmtr)

              if mat_param_b_struct_ptr_string != 0:
                fseek(
                  self.trmtr,
                  mat_param_b_offset + mat_param_b_struct_ptr_string,
                )
                mat_param_b_shader_start = ftell(self.trmtr) + readlong(self.trmtr)
                fseek(self.trmtr, mat_param_b_shader_start)
                mat_param_b_shader_len = readlong(self.trmtr)
                mat_param_b_shader_string = readfixedstring(
                  self.trmtr, mat_param_b_shader_len
                )
                print(f"Shader: {mat_param_b_shader_string}")
                mat_shader = mat_param_b_shader_string
              if mat_param_b_struct_ptr_params != 0:
                fseek(
                  self.trmtr,
                  mat_param_b_offset + mat_param_b_struct_ptr_params,
                )
                mat_param_b_sub_start = ftell(self.trmtr) + readlong(self.trmtr)
                fseek(self.trmtr, mat_param_b_sub_start)
                mat_param_b_sub_count = readlong(self.trmtr)
                for y in range(mat_param_b_sub_count):
                  mat_param_b_sub_offset = ftell(self.trmtr) + readlong(self.trmtr)
                  mat_param_b_sub_ret = ftell(self.trmtr)
                  fseek(self.trmtr, mat_param_b_sub_offset)
                  mat_param_b_sub_struct = ftell(self.trmtr) - readlong(self.trmtr)
                  fseek(self.trmtr, mat_param_b_sub_struct)
                  mat_param_b_sub_struct_len = readshort(self.trmtr)

                  if mat_param_b_sub_struct_len != 0x0008:
                    raise AssertionError(
                      "Unexpected material param b sub struct length!"
                    )
                  mat_param_b_sub_struct_section_len = readshort(self.trmtr)
                  mat_param_b_sub_struct_ptr_string = readshort(self.trmtr)
                  mat_param_b_sub_struct_ptr_value = readshort(self.trmtr)

                  if mat_param_b_sub_struct_ptr_string != 0:
                    fseek(
                      self.trmtr,
                      mat_param_b_sub_offset
                      + mat_param_b_sub_struct_ptr_string,
                    )
                    mat_param_b_sub_string_start = ftell(
                      self.trmtr
                    ) + readlong(self.trmtr)
                    fseek(self.trmtr, mat_param_b_sub_string_start)
                    mat_param_b_sub_string_len = readlong(self.trmtr)
                    mat_param_b_sub_string = readfixedstring(
                      self.trmtr, mat_param_b_sub_string_len
                    )
                  if mat_param_b_sub_struct_ptr_value != 0:
                    fseek(
                      self.trmtr,
                      mat_param_b_sub_offset
                      + mat_param_b_sub_struct_ptr_value,
                    )
                    mat_param_b_sub_value_start = ftell(
                      self.trmtr
                    ) + readlong(self.trmtr)
                    fseek(self.trmtr, mat_param_b_sub_value_start)
                    mat_param_b_sub_value_len = readlong(self.trmtr)
                    mat_param_b_sub_value = readfixedstring(
                      self.trmtr, mat_param_b_sub_value_len
                    )
                    print(
                      f"(param_b) {mat_param_b_sub_string}: {mat_param_b_sub_value}"
                    )

                  if mat_param_b_sub_string == "EnableBaseColorMap":
                    mat_enable_base_color_map = (
                      mat_param_b_sub_value == "True"
                    )
                  if mat_param_b_sub_string == "EnableNormalMap":
                    mat_enable_normal_map = (
                      mat_param_b_sub_value == "True"
                    )
                  if mat_param_b_sub_string == "EnableAOMap":
                    mat_enable_ao_map = mat_param_b_sub_value == "True"
                  if mat_param_b_sub_string == "EnableEmissionColorMap":
                    mat_enable_emission_color_map = (
                      mat_param_b_sub_value == "True"
                    )
                  if mat_param_b_sub_string == "EnableRoughnessMap":
                    mat_enable_roughness_map = (
                      mat_param_b_sub_value == "True"
                    )
                  if mat_param_b_sub_string == "EnableMetallicMap":
                    mat_enable_metallic_map = (
                      mat_param_b_sub_value == "True"
                    )
                  if mat_param_b_sub_string == "EnableDisplacementMap":
                    mat_enable_displacement_map = (
                      mat_param_b_sub_value == "True"
                    )
                  if mat_param_b_sub_string == "EnableHighlight":
                    mat_enable_highlight_map = (
                      mat_param_b_sub_value == "True"
                    )
                  if mat_param_b_sub_string == "EnableOverrideColor":
                    mat_enable_override_color = (
                      mat_param_b_sub_value == "True"
                    )
                  fseek(self.trmtr, mat_param_b_sub_ret)
              fseek(self.trmtr, mat_param_b_ret)

          if mat_struct_ptr_param_c != 0:
            fseek(self.trmtr, mat_offset + mat_struct_ptr_param_c)
            mat_param_c_start = ftell(self.trmtr) + readlong(self.trmtr)
            fseek(self.trmtr, mat_param_c_start)
            mat_param_c_count = readlong(self.trmtr)

            for z in range(mat_param_c_count):
              mat_param_c_offset = ftell(self.trmtr) + readlong(self.trmtr)
              mat_param_c_ret = ftell(self.trmtr)
              fseek(self.trmtr, mat_param_c_offset)
              mat_param_c_struct = ftell(self.trmtr) - readlong(self.trmtr)
              fseek(self.trmtr, mat_param_c_struct)
              mat_param_c_struct_len = readshort(self.trmtr)

              if mat_param_c_struct_len == 0x0008:
                mat_param_c_struct_section_len = readshort(self.trmtr)
                mat_param_c_struct_ptr_string = readshort(self.trmtr)
                mat_param_c_struct_ptr_value = readshort(self.trmtr)
                mat_param_c_struct_ptr_id = 0
              elif mat_param_c_struct_len == 0x000A:
                mat_param_c_struct_section_len = readshort(self.trmtr)
                mat_param_c_struct_ptr_string = readshort(self.trmtr)
                mat_param_c_struct_ptr_value = readshort(self.trmtr)
                mat_param_c_struct_ptr_id = readshort(self.trmtr)
              else:
                raise AssertionError(
                  "Unexpected material param c struct length!"
                )

              if mat_param_c_struct_ptr_string != 0:
                fseek(
                  self.trmtr,
                  mat_param_c_offset + mat_param_c_struct_ptr_string,
                )
                mat_param_c_string_start = ftell(self.trmtr) + readlong(self.trmtr)
                fseek(self.trmtr, mat_param_c_string_start)
                mat_param_c_string_len = readlong(self.trmtr)
                mat_param_c_string = readfixedstring(
                  self.trmtr, mat_param_c_string_len
                )
              if mat_param_c_struct_ptr_value != 0:
                fseek(
                  self.trmtr, mat_param_c_offset + mat_param_c_struct_ptr_value
                )
                mat_param_c_value_start = ftell(self.trmtr) + readlong(self.trmtr)
                fseek(self.trmtr, mat_param_c_value_start)
                mat_param_c_value_len = readlong(
                  self.trmtr
                )  # - 5 # Trimming the ".bntx" from the end.
                mat_param_c_value = readfixedstring(
                  self.trmtr, mat_param_c_value_len
                )
              if mat_param_c_struct_ptr_id != 0:
                fseek(self.trmtr, mat_param_c_offset + mat_param_c_struct_ptr_id)
                mat_param_c_id = readlong(self.trmtr)
              else:
                mat_param_c_id = 0

              if mat_param_c_string == "BaseColorMap":
                mat_col0 = mat_param_c_value
              elif mat_param_c_string == "LayerMaskMap":
                mat_lym0 = mat_param_c_value
              elif mat_param_c_string == "NormalMap":
                mat_nrm0 = mat_param_c_value
              elif mat_param_c_string == "AOMap":
                mat_ao0 = mat_param_c_value
              elif mat_param_c_string == "EmissionColorMap":
                mat_emi0 = mat_param_c_value
              elif mat_param_c_string == "RoughnessMap":
                mat_rgh0 = mat_param_c_value
              elif mat_param_c_string == "MetallicMap":
                mat_mtl0 = mat_param_c_value
              elif mat_param_c_string == "DisplacementMap":
                mat_msk0 = mat_param_c_value
              elif mat_param_c_string == "HighlightMaskMap":
                mat_highmsk0 = mat_param_c_value

              # -- There's also all of the following, which aren't automatically assigned to keep things simple.
              # -- "AOMap"
              # -- "AOMap1"
              # -- "AOMap2"
              # -- "BaseColorMap1"
              # -- "DisplacementMap"
              # -- "EyelidShadowMaskMap"
              # -- "FlowMap"
              # -- "FoamMaskMap"
              # -- "GrassCollisionMap"
              # -- "HighlightMaskMap"
              # -- "LowerEyelidColorMap"
              # -- "NormalMap1"
              # -- "NormalMap2"
              # -- "PackedMap"
              # -- "UpperEyelidColorMap"
              # -- "WeatherLayerMaskMap"
              # -- "WindMaskMap"

              print(
                f"(param_c) {mat_param_c_string}: {mat_param_c_value} [{mat_param_c_id}]"
              )
              fseek(self.trmtr, mat_param_c_ret)

          if mat_struct_ptr_param_d != 0:
            fseek(self.trmtr, mat_offset + mat_struct_ptr_param_d)
            mat_param_d_start = ftell(self.trmtr) + readlong(self.trmtr)
            fseek(self.trmtr, mat_param_d_start)
            mat_param_d_count = readlong(self.trmtr)

            for z in range(mat_param_d_count):
              mat_param_d_offset = ftell(self.trmtr) + readlong(self.trmtr)
              mat_param_d_ret = ftell(self.trmtr)
              fseek(self.trmtr, mat_param_d_offset)
              mat_param_d_struct = ftell(self.trmtr) - readlong(self.trmtr)
              fseek(self.trmtr, mat_param_d_struct)
              mat_param_d_struct_len = readshort(self.trmtr)

              if mat_param_d_struct_len != 0x001E:
                raise AssertionError(
                  "Unexpected material param d struct length!"
                )
              mat_param_d_struct_section_len = readshort(self.trmtr)
              mat_param_d_struct_ptr_a = readshort(self.trmtr)
              mat_param_d_struct_ptr_b = readshort(self.trmtr)
              mat_param_d_struct_ptr_c = readshort(self.trmtr)
              mat_param_d_struct_ptr_d = readshort(self.trmtr)
              mat_param_d_struct_ptr_e = readshort(self.trmtr)
              mat_param_d_struct_ptr_f = readshort(self.trmtr)
              mat_param_d_struct_ptr_g = readshort(self.trmtr)
              mat_param_d_struct_ptr_h = readshort(self.trmtr)
              mat_param_d_struct_ptr_i = readshort(self.trmtr)
              mat_param_d_struct_ptr_j = readshort(self.trmtr)
              mat_param_d_struct_ptr_k = readshort(self.trmtr)
              mat_param_d_struct_ptr_l = readshort(self.trmtr)
              mat_param_d_struct_ptr_m = readshort(self.trmtr)

              if mat_param_d_struct_ptr_a != 0:
                fseek(self.trmtr, mat_param_d_offset + mat_param_d_struct_ptr_a)
                mat_param_d_value_a = readlong(self.trmtr)
              else:
                mat_param_d_value_a = 0
              if mat_param_d_struct_ptr_b != 0:
                fseek(self.trmtr, mat_param_d_offset + mat_param_d_struct_ptr_b)
                mat_param_d_value_b = readlong(self.trmtr)
              else:
                mat_param_d_value_b = 0
              if mat_param_d_struct_ptr_c != 0:
                fseek(self.trmtr, mat_param_d_offset + mat_param_d_struct_ptr_c)
                mat_param_d_value_c = readlong(self.trmtr)
              else:
                mat_param_d_value_c = 0
              if mat_param_d_struct_ptr_d != 0:
                fseek(self.trmtr, mat_param_d_offset + mat_param_d_struct_ptr_d)
                mat_param_d_value_d = readlong(self.trmtr)
              else:
                mat_param_d_value_d = 0
              if mat_param_d_struct_ptr_e != 0:
                fseek(self.trmtr, mat_param_d_offset + mat_param_d_struct_ptr_e)
                mat_param_d_value_e = readlong(self.trmtr)
              else:
                mat_param_d_value_e = 0
              if mat_param_d_struct_ptr_f != 0:
                fseek(self.trmtr, mat_param_d_offset + mat_param_d_struct_ptr_f)
                mat_param_d_value_f = readlong(self.trmtr)
              else:
                mat_param_d_value_f = 0
              if mat_param_d_struct_ptr_g != 0:
                fseek(self.trmtr, mat_param_d_offset + mat_param_d_struct_ptr_g)
                mat_param_d_value_g = readlong(self.trmtr)
              else:
                mat_param_d_value_g = 0
              if mat_param_d_struct_ptr_h != 0:
                fseek(self.trmtr, mat_param_d_offset + mat_param_d_struct_ptr_h)
                mat_param_d_value_h = readlong(self.trmtr)
              else:
                mat_param_d_value_h = 0
              if mat_param_d_struct_ptr_i != 0:
                fseek(self.trmtr, mat_param_d_offset + mat_param_d_struct_ptr_i)
                mat_param_d_value_i = readlong(self.trmtr)
              else:
                mat_param_d_value_i = 0
              if mat_param_d_struct_ptr_j != 0:
                fseek(self.trmtr, mat_param_d_offset + mat_param_d_struct_ptr_j)
                mat_param_d_value_j = readlong(self.trmtr)
              else:
                mat_param_d_value_j = 0
              if mat_param_d_struct_ptr_k != 0:
                fseek(self.trmtr, mat_param_d_offset + mat_param_d_struct_ptr_k)
                mat_param_d_value_k = readlong(self.trmtr)
              else:
                mat_param_d_value_k = 0
              if mat_param_d_struct_ptr_l != 0:
                fseek(self.trmtr, mat_param_d_offset + mat_param_d_struct_ptr_l)
                mat_param_d_value_l = readlong(self.trmtr)
              else:
                mat_param_d_value_l = 0
              if mat_param_d_struct_ptr_m != 0:
                fseek(self.trmtr, mat_param_d_offset + mat_param_d_struct_ptr_m)
                mat_param_d_value_m1 = readfloat(self.trmtr)
                mat_param_d_value_m2 = readfloat(self.trmtr)
                mat_param_d_value_m3 = readfloat(self.trmtr)
              else:
                mat_param_d_value_m1 = 0
                mat_param_d_value_m2 = 0
                mat_param_d_value_m3 = 0

              print(
                f"Flags #{z}: {mat_param_d_value_a} | {mat_param_d_value_b} | {mat_param_d_value_c} | {mat_param_d_value_d} | {mat_param_d_value_e} | {mat_param_d_value_f} | {mat_param_d_value_g} | {mat_param_d_value_h} | {mat_param_d_value_i} | {mat_param_d_value_j} | {mat_param_d_value_k} | {mat_param_d_value_l} | {mat_param_d_value_m1} | {mat_param_d_value_m2} | {mat_param_d_value_m3}"
              )
              fseek(self.trmtr, mat_param_d_ret)

          if mat_struct_ptr_param_e != 0:
            fseek(self.trmtr, mat_offset + mat_struct_ptr_param_e)
            mat_param_e_start = ftell(self.trmtr) + readlong(self.trmtr)
            fseek(self.trmtr, mat_param_e_start)
            mat_param_e_count = readlong(self.trmtr)

            for z in range(mat_param_e_count):
              mat_param_e_offset = ftell(self.trmtr) + readlong(self.trmtr)
              mat_param_e_ret = ftell(self.trmtr)
              fseek(self.trmtr, mat_param_e_offset)
              mat_param_e_struct = ftell(self.trmtr) - readlong(self.trmtr)
              fseek(self.trmtr, mat_param_e_struct)
              mat_param_e_struct_len = readshort(self.trmtr)

              if mat_param_e_struct_len == 0x0006:
                mat_param_e_struct_section_len = readshort(self.trmtr)
                mat_param_e_struct_ptr_string = readshort(self.trmtr)
                mat_param_e_struct_ptr_value = 0
              elif mat_param_e_struct_len == 0x0008:
                mat_param_e_struct_section_len = readshort(self.trmtr)
                mat_param_e_struct_ptr_string = readshort(self.trmtr)
                mat_param_e_struct_ptr_value = readshort(self.trmtr)
              else:
                raise Exception(f"Unknown mat_param_e struct length!")

              if mat_param_e_struct_ptr_string != 0:
                fseek(
                  self.trmtr,
                  mat_param_e_offset + mat_param_e_struct_ptr_string,
                )
                mat_param_e_string_start = ftell(self.trmtr) + readlong(self.trmtr)
                fseek(self.trmtr, mat_param_e_string_start)
                mat_param_e_string_len = readlong(self.trmtr)
                mat_param_e_string = readfixedstring(
                  self.trmtr, mat_param_e_string_len
                )

              if mat_param_e_struct_ptr_value != 0:
                fseek(
                  self.trmtr, mat_param_e_offset + mat_param_e_struct_ptr_value
                )
                mat_param_e_value = readfloat(self.trmtr)
              else:
                mat_param_e_value = 0

              if mat_param_e_string == "Roughness":
                mat_rgh_layer0 = mat_param_e_value
              elif mat_param_e_string == "RoughnessLayer1":
                mat_rgh_layer1 = mat_param_e_value
              elif mat_param_e_string == "RoughnessLayer2":
                mat_rgh_layer2 = mat_param_e_value
              elif mat_param_e_string == "RoughnessLayer3":
                mat_rgh_layer3 = mat_param_e_value
              elif mat_param_e_string == "RoughnessLayer4":
                mat_rgh_layer4 = mat_param_e_value
              elif mat_param_e_string == "Metallic":
                mat_mtl_layer0 = mat_param_e_value
              elif mat_param_e_string == "MetallicLayer1":
                mat_mtl_layer1 = mat_param_e_value
              elif mat_param_e_string == "MetallicLayer2":
                mat_mtl_layer2 = mat_param_e_value
              elif mat_param_e_string == "MetallicLayer3":
                mat_mtl_layer3 = mat_param_e_value
              elif mat_param_e_string == "MetallicLayer4":
                mat_mtl_layer4 = mat_param_e_value
              elif mat_param_e_string == "Reflectance":
                mat_reflectance = mat_param_e_value
              elif mat_param_e_string == "EmissionIntensity":
                mat_emm_intensity = mat_param_e_value

              print(f"(param_e) {mat_param_e_string}: {mat_param_e_value}")
              fseek(self.trmtr, mat_param_e_ret)

          if mat_struct_ptr_param_f != 0:
            fseek(self.trmtr, mat_offset + mat_struct_ptr_param_f)
            mat_param_f_start = ftell(self.trmtr) + readlong(self.trmtr)
            fseek(self.trmtr, mat_param_f_start)
            mat_param_f_count = readlong(self.trmtr)

            for z in range(mat_param_f_count):
              mat_param_f_offset = ftell(self.trmtr) + readlong(self.trmtr)
              mat_param_f_ret = ftell(self.trmtr)
              fseek(self.trmtr, mat_param_f_offset)
              mat_param_f_struct = ftell(self.trmtr) - readlong(self.trmtr)
              fseek(self.trmtr, mat_param_f_struct)
              mat_param_f_struct_len = readlong(self.trmtr)

              if mat_param_f_struct_len != 0x0008:
                raise Exception(f"Unknown mat_param_f struct length!")
              mat_param_f_struct_section_len = readshort(self.trmtr)
              mat_param_f_struct_ptr_string = readshort(self.trmtr)
              mat_param_f_struct_ptr_values = readshort(self.trmtr)

              if mat_param_f_struct_ptr_string != 0:
                fseek(
                  self.trmtr,
                  mat_param_f_offset + mat_param_f_struct_ptr_string,
                )
                mat_param_f_string_start = ftell(self.trmtr) + readlong(self.trmtr)
                fseek(self.trmtr, mat_param_f_string_start)
                mat_param_f_string_len = readlong(self.trmtr)
                mat_param_f_string = readfixedstring(
                  self.trmtr, mat_param_f_string_len
                )

              if mat_param_f_struct_ptr_values != 0:
                fseek(
                  self.trmtr,
                  mat_param_f_offset + mat_param_f_struct_ptr_values,
                )
                mat_param_f_value1 = readfloat(self.trmtr)
                mat_param_f_value2 = readfloat(self.trmtr)
              else:
                mat_param_f_value1 = mat_param_f_value2 = 0

              print(
                f"(param_f) {mat_param_f_string}: {mat_param_f_value1}, {mat_param_f_value2}"
              )
              fseek(self.trmtr, mat_param_f_ret)

          if mat_struct_ptr_param_g != 0:
            fseek(self.trmtr, mat_offset + mat_struct_ptr_param_g)
            mat_param_g_start = ftell(self.trmtr) + readlong(self.trmtr)
            fseek(self.trmtr, mat_param_g_start)
            mat_param_g_count = readlong(self.trmtr)

            for z in range(mat_param_g_count):
              mat_param_g_offset = ftell(self.trmtr) + readlong(self.trmtr)
              mat_param_g_ret = ftell(self.trmtr)
              fseek(self.trmtr, mat_param_g_offset)
              mat_param_g_struct = ftell(self.trmtr) - readlong(self.trmtr)
              fseek(self.trmtr, mat_param_g_struct)
              mat_param_g_struct_len = readlong(self.trmtr)

              if mat_param_g_struct_len != 0x0008:
                raise Exception(f"Unknown mat_param_g struct length!")
              mat_param_g_struct_section_len = readshort(self.trmtr)
              mat_param_g_struct_ptr_string = readshort(self.trmtr)
              mat_param_g_struct_ptr_values = readshort(self.trmtr)

              if mat_param_g_struct_ptr_string != 0:
                fseek(
                  self.trmtr,
                  mat_param_g_offset + mat_param_g_struct_ptr_string,
                )
                mat_param_g_string_start = ftell(self.trmtr) + readlong(self.trmtr)
                fseek(self.trmtr, mat_param_g_string_start)
                mat_param_g_string_len = readlong(self.trmtr)
                mat_param_g_string = readfixedstring(
                  self.trmtr, mat_param_g_string_len
                )

              if mat_param_g_struct_ptr_values != 0:
                fseek(
                  self.trmtr,
                  mat_param_g_offset + mat_param_g_struct_ptr_values,
                )
                mat_param_g_value1 = readfloat(self.trmtr)
                mat_param_g_value2 = readfloat(self.trmtr)
                mat_param_g_value3 = readfloat(self.trmtr)
              else:
                mat_param_g_value1 = mat_param_g_value2 = (
                  mat_param_g_value3
                ) = 0

              print(
                f"(param_g) {mat_param_g_string}: {mat_param_g_value1}, {mat_param_g_value2}, {mat_param_g_value3}"
              )
              fseek(self.trmtr, mat_param_g_ret)

          if mat_struct_ptr_param_h != 0:
            fseek(self.trmtr, mat_offset + mat_struct_ptr_param_h)
            mat_param_h_start = ftell(self.trmtr) + readlong(self.trmtr)
            fseek(self.trmtr, mat_param_h_start)
            mat_param_h_count = readlong(self.trmtr)

            for z in range(mat_param_h_count):
              mat_param_h_offset = ftell(self.trmtr) + readlong(self.trmtr)
              mat_param_h_ret = ftell(self.trmtr)
              fseek(self.trmtr, mat_param_h_offset)
              mat_param_h_struct = ftell(self.trmtr) - readlong(self.trmtr)
              fseek(self.trmtr, mat_param_h_struct)
              mat_param_h_struct_len = readshort(self.trmtr)

              if mat_param_h_struct_len != 0x0008:
                raise Exception(f"Unknown mat_param_h struct length!")
              mat_param_h_struct_section_len = readshort(self.trmtr)
              mat_param_h_struct_ptr_string = readshort(self.trmtr)
              mat_param_h_struct_ptr_values = readshort(self.trmtr)

              if mat_param_h_struct_ptr_string != 0:
                fseek(
                  self.trmtr,
                  mat_param_h_offset + mat_param_h_struct_ptr_string,
                )
                mat_param_h_string_start = ftell(self.trmtr) + readlong(self.trmtr)
                fseek(self.trmtr, mat_param_h_string_start)
                mat_param_h_string_len = readlong(self.trmtr)
                mat_param_h_string = readfixedstring(
                  self.trmtr, mat_param_h_string_len
                )

              if mat_param_h_struct_ptr_values != 0:
                fseek(
                  self.trmtr,
                  mat_param_h_offset + mat_param_h_struct_ptr_values,
                )
                mat_param_h_value1 = readfloat(self.trmtr)
                mat_param_h_value2 = readfloat(self.trmtr)
                mat_param_h_value3 = readfloat(self.trmtr)
                mat_param_h_value4 = readfloat(self.trmtr)
              else:
                mat_param_h_value1 = mat_param_h_value2 = (
                  mat_param_h_value3
                ) = mat_param_h_value4 = 0

              if mat_param_h_string == "UVScaleOffset":
                mat_uv_scale_u = mat_param_h_value1
                mat_uv_scale_v = mat_param_h_value2
                mat_uv_trs_u = mat_param_h_value3
                mat_uv_trs_v = mat_param_h_value4
              elif mat_param_h_string == "UVScaleOffset1":
                mat_uv_scale2_u = mat_param_h_value1
                mat_uv_scale2_v = mat_param_h_value2
                mat_uv_trs2_u = mat_param_h_value3
                mat_uv_trs2_v = mat_param_h_value4
              elif mat_param_h_string == "BaseColorLayer1":
                mat_color1_r = mat_param_h_value1
                mat_color1_g = mat_param_h_value2
                mat_color1_b = mat_param_h_value3
              elif mat_param_h_string == "BaseColorLayer2":
                mat_color2_r = mat_param_h_value1
                mat_color2_g = mat_param_h_value2
                mat_color2_b = mat_param_h_value3
              elif mat_param_h_string == "BaseColorLayer3":
                mat_color3_r = mat_param_h_value1
                mat_color3_g = mat_param_h_value2
                mat_color3_b = mat_param_h_value3
              elif mat_param_h_string == "BaseColorLayer4":
                mat_color4_r = mat_param_h_value1
                mat_color4_g = mat_param_h_value2
                mat_color4_b = mat_param_h_value3
              elif mat_param_h_string == "EmissionColorLayer1":
                mat_emcolor1_r = mat_param_h_value1
                mat_emcolor1_g = mat_param_h_value2
                mat_emcolor1_b = mat_param_h_value3
              elif mat_param_h_string == "EmissionColorLayer2":
                mat_emcolor2_r = mat_param_h_value1
                mat_emcolor2_g = mat_param_h_value2
                mat_emcolor2_b = mat_param_h_value3
              elif mat_param_h_string == "EmissionColorLayer3":
                mat_emcolor3_r = mat_param_h_value1
                mat_emcolor3_g = mat_param_h_value2
                mat_emcolor3_b = mat_param_h_value3
              elif mat_param_h_string == "EmissionColorLayer4":
                mat_emcolor4_r = mat_param_h_value1
                mat_emcolor4_g = mat_param_h_value2
                mat_emcolor4_b = mat_param_h_value3
              elif mat_param_h_string == "EmissionColorLayer5":
                mat_emcolor5_r = mat_param_h_value1
                mat_emcolor5_g = mat_param_h_value2
                mat_emcolor5_b = mat_param_h_value3
              else:
                print(f"Unknown mat_param_h: {mat_param_h_string}")

              print(
                f"(param_h) {mat_param_h_string}: {mat_param_h_value1}, {mat_param_h_value2}, {mat_param_h_value3}, {mat_param_h_value4}"
              )
              fseek(self.trmtr, mat_param_h_ret)

          if mat_struct_ptr_param_i != 0:
            fseek(self.trmtr, mat_offset + mat_struct_ptr_param_i)
            mat_param_i_start = ftell(self.trmtr) + readlong(self.trmtr)
            fseek(self.trmtr, mat_param_i_start)
            mat_param_i_struct = ftell(self.trmtr) - readlong(self.trmtr)
            fseek(self.trmtr, mat_param_i_struct)
            mat_param_i_struct_len = readlong(self.trmtr)

            if mat_param_i_struct_len != 0x0000:
              raise Exception(f"Unknown mat_param_i struct length!")

          if mat_struct_ptr_param_j != 0:
            fseek(self.trmtr, mat_offset + mat_struct_ptr_param_j)
            mat_param_j_start = ftell(self.trmtr) + readlong(self.trmtr)
            fseek(self.trmtr, mat_param_j_start)
            mat_param_j_count = readlong(self.trmtr)

            for y in range(mat_param_j_count):
              mat_param_j_offset = ftell(self.trmtr) + readlong(self.trmtr)
              mat_param_j_ret = ftell(self.trmtr)
              fseek(self.trmtr, mat_param_j_offset)
              mat_param_j_struct = ftell(self.trmtr) - readlong(self.trmtr)
              fseek(self.trmtr, mat_param_j_struct)
              mat_param_j_struct_len = readshort(self.trmtr)

              if mat_param_j_struct_len == 0x0006:
                mat_param_j_struct_section_len = readshort(self.trmtr)
                mat_param_j_struct_ptr_string = readshort(self.trmtr)
                mat_param_j_struct_ptr_value = 0
              elif mat_param_j_struct_len == 0x0008:
                mat_param_j_struct_section_len = readshort(self.trmtr)
                mat_param_j_struct_ptr_string = readshort(self.trmtr)
                mat_param_j_struct_ptr_value = readshort(self.trmtr)
              else:
                raise Exception(f"Unknown mat_param_j struct length!")

              if mat_param_j_struct_ptr_string != 0:
                fseek(
                  self.trmtr,
                  mat_param_j_offset + mat_param_j_struct_ptr_string,
                )
                mat_param_j_string_start = ftell(self.trmtr) + readlong(self.trmtr)
                fseek(self.trmtr, mat_param_j_string_start)
                mat_param_j_string_len = readlong(self.trmtr)
                mat_param_j_string = readfixedstring(
                  self.trmtr, mat_param_j_string_len
                )

              if mat_param_j_struct_ptr_value != 0:
                fseek(
                  self.trmtr, mat_param_j_offset + mat_param_j_struct_ptr_value
                )
                mat_param_j_value = readlong(self.trmtr)
              else:
                mat_param_j_value = "0"  # why is this a string?

              print(f"(param_j) {mat_param_j_string}: {mat_param_j_value}")
              fseek(self.trmtr, mat_param_j_ret)

          if mat_struct_ptr_param_k != 0:
            fseek(self.trmtr, mat_offset + mat_struct_ptr_param_k)
            mat_param_k_start = ftell(self.trmtr) + readlong(self.trmtr)
            fseek(self.trmtr, mat_param_k_start)
            mat_param_k_struct = ftell(self.trmtr) - readlong(self.trmtr)
            fseek(self.trmtr, mat_param_k_struct)
            mat_param_k_struct_len = readlong(self.trmtr)

            if mat_param_k_struct_len != 0x0000:
              raise Exception(f"Unexpected mat_param_k struct length!")

          if mat_struct_ptr_param_l != 0:
            fseek(self.trmtr, mat_offset + mat_struct_ptr_param_l)
            mat_param_l_start = ftell(self.trmtr) + readlong(self.trmtr)
            fseek(self.trmtr, mat_param_l_start)
            mat_param_l_struct = ftell(self.trmtr) - readlong(self.trmtr)
            fseek(self.trmtr, mat_param_l_struct)
            mat_param_l_struct_len = readlong(self.trmtr)

            if mat_param_l_struct_len != 0x0000:
              raise Exception(f"Unexpected mat_param_l struct length!")

          if mat_struct_ptr_param_m != 0:
            fseek(self.trmtr, mat_offset + mat_struct_ptr_param_m)
            mat_param_m_start = ftell(self.trmtr) + readlong(self.trmtr)
            fseek(self.trmtr, mat_param_m_start)
            mat_param_m_struct = ftell(self.trmtr) - readlong(self.trmtr)
            fseek(self.trmtr, mat_param_m_struct)
            mat_param_m_struct_len = readlong(self.trmtr)

            if mat_param_m_struct_len != 0x0000:
              raise Exception(f"Unexpected mat_param_m struct length!")

          if mat_struct_ptr_param_n != 0:
            fseek(self.trmtr, mat_offset + mat_struct_ptr_param_n)
            mat_param_n_start = ftell(self.trmtr) + readlong(self.trmtr)
            fseek(self.trmtr, mat_param_n_start)
            mat_param_n_struct = ftell(self.trmtr) - readlong(self.trmtr)
            fseek(self.trmtr, mat_param_n_struct)
            mat_param_n_struct_len = readshort(self.trmtr)

            if mat_param_n_struct_len == 0x0004:
              mat_param_n_struct_section_len = readshort(self.trmtr)
              mat_param_n_struct_unk = 0
            elif mat_param_n_struct_len == 0x0006:
              mat_param_n_struct_section_len = readshort(self.trmtr)
              mat_param_n_struct_unk = readshort(self.trmtr)
            else:
              raise Exception(f"Unexpected mat_param_n struct length!")

            if mat_param_n_struct_unk != 0:
              fseek(self.trmtr, mat_param_n_start + mat_param_n_struct_unk)
              mat_param_n_value = readbyte(self.trmtr)
              print(f"Unknown value A = {mat_param_n_value}")

          if mat_struct_ptr_param_o != 0:
            fseek(self.trmtr, mat_offset + mat_struct_ptr_param_o)
            mat_param_o_start = ftell(self.trmtr) + readlong(self.trmtr)
            fseek(self.trmtr, mat_param_o_start)
            mat_param_o_struct = ftell(self.trmtr) - readlong(self.trmtr)
            fseek(self.trmtr, mat_param_o_struct)
            mat_param_o_struct_len = readshort(self.trmtr)

            if mat_param_o_struct_len == 0x0004:
              mat_param_o_struct_section_len = readshort(self.trmtr)
              mat_param_o_struct_unk = 0
              mat_param_o_struct_value = 0
            elif mat_param_o_struct_len == 0x0008:
              mat_param_o_struct_section_len = readshort(self.trmtr)
              mat_param_o_struct_unk = readshort(self.trmtr)
              mat_param_o_struct_value = readshort(self.trmtr)
            else:
              raise Exception(f"Unexpected mat_param_o struct length!")

            if mat_param_o_struct_unk != 0:
              fseek(self.trmtr, mat_param_o_start + mat_param_o_struct_unk)
              mat_param_o_value = readbyte(self.trmtr)
              print(f"Unknown value B = {mat_param_o_value}")

          if mat_struct_ptr_param_p != 0:
            fseek(self.trmtr, mat_offset + mat_struct_ptr_param_p)
            mat_param_p_start = ftell(self.trmtr) + readlong(self.trmtr)
            fseek(self.trmtr, mat_param_p_start)
            mat_param_p_string_len = readlong(self.trmtr)
            mat_param_p_string = readfixedstring(self.trmtr, mat_param_p_string_len)
            print(mat_param_p_string)

          self.mat_data_array.append(
            {
              "mat_name": mat_name,
              "mat_shader": mat_shader,
              "mat_col0": mat_col0,
              "mat_lym0": mat_lym0,
              "mat_nrm0": mat_nrm0,
              "mat_ao0": mat_ao0,
              "mat_emi0": mat_emi0,
              "mat_rgh0": mat_rgh0,
              "mat_mtl0": mat_mtl0,
              "mat_msk0": mat_msk0,
              "mat_highmsk0": mat_highmsk0,
              "mat_color1_r": mat_color1_r,
              "mat_color1_g": mat_color1_g,
              "mat_color1_b": mat_color1_b,
              "mat_color2_r": mat_color2_r,
              "mat_color2_g": mat_color2_g,
              "mat_color2_b": mat_color2_b,
              "mat_color3_r": mat_color3_r,
              "mat_color3_g": mat_color3_g,
              "mat_color3_b": mat_color3_b,
              "mat_color4_r": mat_color4_r,
              "mat_color4_g": mat_color4_g,
              "mat_color4_b": mat_color4_b,
              "mat_emcolor1_r": mat_emcolor1_r,
              "mat_emcolor1_g": mat_emcolor1_g,
              "mat_emcolor1_b": mat_emcolor1_b,
              "mat_emcolor2_r": mat_emcolor2_r,
              "mat_emcolor2_g": mat_emcolor2_g,
              "mat_emcolor2_b": mat_emcolor2_b,
              "mat_emcolor3_r": mat_emcolor3_r,
              "mat_emcolor3_g": mat_emcolor3_g,
              "mat_emcolor3_b": mat_emcolor3_b,
              "mat_emcolor4_r": mat_emcolor4_r,
              "mat_emcolor4_g": mat_emcolor4_g,
              "mat_emcolor4_b": mat_emcolor4_b,
              "mat_emcolor5_r": mat_emcolor5_r,
              "mat_emcolor5_g": mat_emcolor5_g,
              "mat_emcolor5_b": mat_emcolor5_b,
              "mat_rgh_layer0": mat_rgh_layer0,
              "mat_rgh_layer1": mat_rgh_layer1,
              "mat_rgh_layer2": mat_rgh_layer2,
              "mat_rgh_layer3": mat_rgh_layer3,
              "mat_rgh_layer4": mat_rgh_layer4,
              "mat_mtl_layer0": mat_mtl_layer0,
              "mat_mtl_layer1": mat_mtl_layer1,
              "mat_mtl_layer2": mat_mtl_layer2,
              "mat_mtl_layer3": mat_mtl_layer3,
              "mat_mtl_layer4": mat_mtl_layer4,
              "mat_reflectance": mat_reflectance,
              "mat_emm_intensity": mat_emm_intensity,
              "mat_uv_scale_u": mat_uv_scale_u,
              "mat_uv_scale_v": mat_uv_scale_v,
              "mat_uv_scale2_u": mat_uv_scale2_u,
              "mat_uv_scale2_v": mat_uv_scale2_v,
              "mat_enable_base_color_map": mat_enable_base_color_map,
              "mat_enable_normal_map": mat_enable_normal_map,
              "mat_enable_ao_map": mat_enable_ao_map,
              "mat_enable_emission_color_map": mat_enable_emission_color_map,
              "mat_enable_roughness_map": mat_enable_roughness_map,
              "mat_enable_metallic_map": mat_enable_metallic_map,
              "mat_enable_displacement_map": mat_enable_displacement_map,
              "mat_enable_highlight_map": mat_enable_highlight_map,
            }
          )
          fseek(self.trmtr, mat_ret)
        print("--------------------")

      fclose(self.trmtr)

      if IN_BLENDER_ENV:
        # process self.materials
        for m, mat in enumerate(self.mat_data_array):
          material = bpy.data.materials.new(name=mat["mat_name"])
          material.use_nodes = True
          self.materials.append(material)

          blend_type = "MIX"

          material_output = material.node_tree.nodes.get("Material Output")
          principled_bsdf = material.node_tree.nodes.get("Principled BSDF")
          material.node_tree.links.new(
            principled_bsdf.outputs[0], material_output.inputs[0]
          )

          print(f"mat_shader = {mat['mat_shader']}")

          material.blend_method = "HASHED"
          material.show_transparent_back = False
          material.shadow_method = "OPAQUE"

          color_output = principled_bsdf.inputs[0]
          if mat["mat_shader"] == "Unlit":
            color_output = material_output.inputs[0]
          if mat["mat_shader"] == "Transparent":
            material.blend_method = "BLEND"
            reflectionpart1 = material.node_tree.nodes.new("ShaderNodeMath")
            reflectionpart1.operation = "SQRT"
            reflectionpart1.inputs[0].default_value = mat["mat_reflectance"]

            reflectionpart2 = material.node_tree.nodes.new("ShaderNodeMath")
            reflectionpart2.inputs[0].default_value = 1.0
            reflectionpart2.operation = "ADD"

            reflectionpart3 = material.node_tree.nodes.new("ShaderNodeMath")
            reflectionpart3.inputs[0].default_value = 1.0
            reflectionpart3.operation = "SUBTRACT"

            reflectionpart4 = material.node_tree.nodes.new("ShaderNodeMath")
            reflectionpart4.operation = "DIVIDE"

            reflectionpart5 = material.node_tree.nodes.new("ShaderNodeFresnel")

            reflectionpart6 = material.node_tree.nodes.new("ShaderNodeMath")
            reflectionpart6.inputs[0].default_value = 0.25
            reflectionpart6.operation = "SUBTRACT"

            material.node_tree.links.new(
              reflectionpart1.outputs[0], reflectionpart2.inputs[1]
            )
            material.node_tree.links.new(
              reflectionpart1.outputs[0], reflectionpart3.inputs[1]
            )
            material.node_tree.links.new(
              reflectionpart2.outputs[0], reflectionpart4.inputs[0]
            )
            material.node_tree.links.new(
              reflectionpart3.outputs[0], reflectionpart4.inputs[1]
            )
            material.node_tree.links.new(
              reflectionpart4.outputs[0], reflectionpart5.inputs[0]
            )

          material.use_backface_culling = True

          if self.chara_check == "Pokemon" or mat["mat_name"] == "eye":
            # LAYER MASK MAP
            lym_image_texture = material.node_tree.nodes.new(
              "ShaderNodeTexImage"
            )
            if (
              os.path.exists(
                os.path.join(self.filep, mat["mat_lym0"][:-5] + TEXTEXT)
              )
              is True
            ):
              lym_image_texture.image = bpy.data.images.load(
                os.path.join(self.filep, mat["mat_lym0"][:-5] + TEXTEXT)
              )
              lym_image_texture.image.colorspace_settings.name = "Non-Color"
            huesaturationvalue = material.node_tree.nodes.new(
              "ShaderNodeHueSaturation"
            )
            huesaturationvalue.inputs[2].default_value = 2.0
            huesaturationvalue2 = material.node_tree.nodes.new(
              "ShaderNodeHueSaturation"
            )
            huesaturationvalue2.inputs[2].default_value = 2.0

            color1 = (
              mat["mat_color1_r"],
              mat["mat_color1_g"],
              mat["mat_color1_b"],
              1.0,
            )
            color2 = (
              mat["mat_color2_r"],
              mat["mat_color2_g"],
              mat["mat_color2_b"],
              1.0,
            )
            color3 = (
              mat["mat_color3_r"],
              mat["mat_color3_g"],
              mat["mat_color3_b"],
              1.0,
            )
            color4 = (
              mat["mat_color4_r"],
              mat["mat_color4_g"],
              mat["mat_color4_b"],
              1.0,
            )

            emcolor1 = (
              mat["mat_emcolor1_r"],
              mat["mat_emcolor1_g"],
              mat["mat_emcolor1_b"],
              1.0,
            )
            emcolor2 = (
              mat["mat_emcolor2_r"],
              mat["mat_emcolor2_g"],
              mat["mat_emcolor2_b"],
              1.0,
            )
            emcolor3 = (
              mat["mat_emcolor3_r"],
              mat["mat_emcolor3_g"],
              mat["mat_emcolor3_b"],
              1.0,
            )
            emcolor4 = (
              mat["mat_emcolor4_r"],
              mat["mat_emcolor4_g"],
              mat["mat_emcolor4_b"],
              1.0,
            )
            if (
              emcolor1 == (1.0, 1.0, 1.0, 1.0)
              and emcolor2 == (1.0, 1.0, 1.0, 1.0)
              and emcolor3 == (1.0, 1.0, 1.0, 1.0)
              and emcolor4 == (1.0, 1.0, 1.0, 1.0)
            ):
              emcolor1 = (0.0, 0.0, 0.0, 0.0)
              emcolor2 = (0.0, 0.0, 0.0, 0.0)
              emcolor3 = (0.0, 0.0, 0.0, 0.0)
              emcolor4 = (0.0, 0.0, 0.0, 0.0)
            print(f'Material {mat["mat_name"]}:')
            print(f"Color 1: {color1}")
            print(f"Color 2: {color2}")
            print(f"Color 3: {color3}")
            print(f"Color 4: {color4}")
            print(f"Emission Color 1: {emcolor1}")
            print(f"Emission Color 2: {emcolor2}")
            print(f"Emission Color 3: {emcolor3}")
            print(f"Emission Color 4: {emcolor4}")
            print("---")

            mix_color1 = material.node_tree.nodes.new("ShaderNodeMixRGB")
            mix_color1.blend_type = blend_type
            mix_color1.inputs[1].default_value = (1, 1, 1, 1)
            mix_color1.inputs[2].default_value = color1
            mix_color2 = material.node_tree.nodes.new("ShaderNodeMixRGB")
            mix_color2.blend_type = blend_type
            mix_color2.inputs[1].default_value = (0, 0, 0, 0)
            mix_color2.inputs[2].default_value = color2
            mix_color3 = material.node_tree.nodes.new("ShaderNodeMixRGB")
            mix_color3.blend_type = blend_type
            mix_color3.inputs[1].default_value = (0, 0, 0, 0)
            mix_color3.inputs[2].default_value = color3
            mix_color4 = material.node_tree.nodes.new("ShaderNodeMixRGB")
            mix_color4.blend_type = blend_type
            mix_color4.inputs[1].default_value = (0, 0, 0, 0)
            mix_color4.inputs[2].default_value = color4
            mix_color5 = material.node_tree.nodes.new("ShaderNodeMixRGB")
            mix_color5.blend_type = blend_type
            mix_color5.inputs[0].default_value = 0.0
            mix_color5.inputs[1].default_value = (0, 0, 0, 0)
            mix_color5.inputs[2].default_value = (1, 1, 1, 1)

            mix_emcolor1 = material.node_tree.nodes.new("ShaderNodeMixRGB")
            mix_emcolor1.blend_type = blend_type
            mix_emcolor1.inputs[1].default_value = (0, 0, 0, 0)
            mix_emcolor1.inputs[2].default_value = emcolor1
            mix_emcolor2 = material.node_tree.nodes.new("ShaderNodeMixRGB")
            mix_emcolor2.blend_type = blend_type
            mix_emcolor2.inputs[1].default_value = (0, 0, 0, 0)
            mix_emcolor2.inputs[2].default_value = emcolor2
            mix_emcolor3 = material.node_tree.nodes.new("ShaderNodeMixRGB")
            mix_emcolor3.blend_type = blend_type
            mix_emcolor3.inputs[1].default_value = (0, 0, 0, 0)
            mix_emcolor3.inputs[2].default_value = emcolor3
            mix_emcolor4 = material.node_tree.nodes.new("ShaderNodeMixRGB")
            mix_emcolor4.blend_type = blend_type
            mix_emcolor4.inputs[1].default_value = (0, 0, 0, 0)
            mix_emcolor4.inputs[2].default_value = emcolor4

            material.node_tree.links.new(
              mix_color1.outputs[0], mix_color2.inputs[1]
            )
            material.node_tree.links.new(
              mix_color2.outputs[0], mix_color3.inputs[1]
            )
            material.node_tree.links.new(
              mix_color3.outputs[0], mix_color4.inputs[1]
            )
            material.node_tree.links.new(
              mix_color3.outputs[0], mix_color4.inputs[1]
            )
            material.node_tree.links.new(mix_color4.outputs[0], color_output)

            material.node_tree.links.new(
              mix_emcolor1.outputs[0], mix_emcolor2.inputs[1]
            )
            material.node_tree.links.new(
              mix_emcolor2.outputs[0], mix_emcolor3.inputs[1]
            )
            material.node_tree.links.new(
              mix_emcolor3.outputs[0], mix_emcolor4.inputs[1]
            )
            material.node_tree.links.new(
              mix_emcolor3.outputs[0], mix_emcolor4.inputs[1]
            )
            material.node_tree.links.new(
              mix_emcolor4.outputs[0], principled_bsdf.inputs[26]
            )

            separate_color = material.node_tree.nodes.new(
              "ShaderNodeSeparateRGB"
            )
            material.node_tree.links.new(
              lym_image_texture.outputs[0], huesaturationvalue.inputs[4]
            )
            material.node_tree.links.new(
              huesaturationvalue.outputs[0], separate_color.inputs[0]
            )
            material.node_tree.links.new(
              separate_color.outputs[0], mix_color1.inputs[0]
            )
            material.node_tree.links.new(
              separate_color.outputs[1], mix_color2.inputs[0]
            )
            material.node_tree.links.new(
              separate_color.outputs[2], mix_color3.inputs[0]
            )
            material.node_tree.links.new(
              lym_image_texture.outputs[1], huesaturationvalue2.inputs[4]
            )
            material.node_tree.links.new(
              huesaturationvalue2.outputs[0], mix_color4.inputs[0]
            )

            material.node_tree.links.new(
              separate_color.outputs[0], mix_emcolor1.inputs[0]
            )
            material.node_tree.links.new(
              separate_color.outputs[1], mix_emcolor2.inputs[0]
            )
            material.node_tree.links.new(
              separate_color.outputs[2], mix_emcolor3.inputs[0]
            )
            material.node_tree.links.new(
              huesaturationvalue2.outputs[0], mix_emcolor4.inputs[0]
            )

            if (
              os.path.exists(
                os.path.join(self.filep, mat["mat_col0"][:-5] + TEXTEXT)
              )
              is True
            ):
              alb_image_texture = material.node_tree.nodes.new(
                "ShaderNodeTexImage"
              )
              alb_image_texture.image = bpy.data.images.load(
                os.path.join(self.filep, mat["mat_col0"][:-5] + TEXTEXT)
              )
              material.node_tree.links.new(
                alb_image_texture.outputs[0], mix_color1.inputs[1]
              )
              material.node_tree.links.new(
                alb_image_texture.outputs[1], principled_bsdf.inputs[4]
              )

            if mat["mat_enable_highlight_map"]:
              highlight_image_texture = material.node_tree.nodes.new(
                "ShaderNodeTexImage"
              )
              if (
                os.path.exists(
                  os.path.join(self.filep, mat["mat_highmsk0"][:-5] + ".png")
                )
                is True
              ):
                highlight_image_texture.image = bpy.data.images.load(
                  os.path.join(self.filep, mat["mat_highmsk0"][:-5] + ".png")
                )
                highlight_image_texture.image.colorspace_settings.name = (
                  "Non-Color"
                )
              elif (
                os.path.exists(
                  os.path.join(self.filep, mat["mat_col0"][:-8] + "msk.png")
                )
                is True
              ):
                highlight_image_texture.image = bpy.data.images.load(
                  os.path.join(self.filep, mat["mat_col0"][:-8] + "msk.png")
                )
                highlight_image_texture.image.colorspace_settings.name = (
                  "Non-Color"
                )
              elif (
                os.path.exists(
                  os.path.join(self.filep, mat["mat_col0"][:-8] + "msk.png")
                )
                is True
              ):
                highlight_image_texture.image = bpy.data.images.load(
                  os.path.join(self.filep, mat["mat_col0"][:-8] + "msk.png")
                )
                highlight_image_texture.image.colorspace_settings.name = (
                  "Non-Color"
                )
              elif (
                os.path.exists(
                  os.path.join(
                    self.filep, mat["mat_col0"][:-12] + "r_eye_msk.png"
                  )
                )
                is True
              ):
                highlight_image_texture.image = bpy.data.images.load(
                  os.path.join(
                    self.filep, mat["mat_col0"][:-12] + "r_eye_msk.png"
                  )
                )
                highlight_image_texture.image.colorspace_settings.name = (
                  "Non-Color"
                )
              elif (
                os.path.exists(
                  os.path.join(
                    self.filep, mat["mat_col0"][:-12] + "l_eye_msk.png"
                  )
                )
                is True
              ):
                highlight_image_texture.image = bpy.data.images.load(
                  os.path.join(
                    self.filep, mat["mat_col0"][:-12] + "l_eye_msk.png"
                  )
                )
                highlight_image_texture.image.colorspace_settings.name = (
                  "Non-Color"
                )
              else:
                print("No Highlight")
              material.node_tree.links.new(
                highlight_image_texture.outputs[0], mix_color5.inputs[0]
              )
              material.node_tree.links.new(
                mix_color4.outputs[0], mix_color5.inputs[1]
              )
              material.node_tree.links.new(
                mix_color5.outputs[0], color_output
              )

            if mat["mat_enable_normal_map"]:
              normal_image_texture = material.node_tree.nodes.new(
                "ShaderNodeTexImage"
              )
              if (
                os.path.exists(
                  os.path.join(
                    self.filep, mat["mat_nrm0"][:-5] + TEXTEXT
                  )
                )
                is True
              ):
                normal_image_texture.image = bpy.data.images.load(
                  os.path.join(
                    self.filep, mat["mat_nrm0"][:-5] + TEXTEXT
                  )
                )
                normal_image_texture.image.colorspace_settings.name = (
                  "Non-Color"
                )
              separate_color2 = material.node_tree.nodes.new(
                "ShaderNodeSeparateRGB"
              )
              combine_color2 = material.node_tree.nodes.new(
                "ShaderNodeCombineColor"
              )
              normal_map2 = material.node_tree.nodes.new(
                "ShaderNodeNormalMap"
              )
              material.node_tree.links.new(
                normal_image_texture.outputs[0], separate_color2.inputs[0]
              )
              material.node_tree.links.new(
                separate_color2.outputs[0], combine_color2.inputs[0]
              )
              material.node_tree.links.new(
                separate_color2.outputs[1], combine_color2.inputs[1]
              )
              material.node_tree.links.new(
                normal_image_texture.outputs[1], combine_color2.inputs[2]
              )
              material.node_tree.links.new(
                combine_color2.outputs[0], normal_map2.inputs[1]
              )
              material.node_tree.links.new(
                normal_map2.outputs[0], principled_bsdf.inputs[5]
              )
              if mat["mat_shader"] == "Transparent":
                material.node_tree.links.new(
                  normal_map2.outputs[0], reflectionpart5.inputs[1]
                )
                material.node_tree.links.new(
                  reflectionpart5.outputs[0], reflectionpart6.inputs[1]
                )
                material.node_tree.links.new(
                  reflectionpart6.outputs[0], principled_bsdf.inputs[4]
                )

            if mat["mat_enable_metallic_map"]:
              metalness_image_texture = material.node_tree.nodes.new(
                "ShaderNodeTexImage"
              )
              if (
                os.path.exists(
                  os.path.join(
                    self.filep, mat["mat_mtl0"][:-5] + TEXTEXT
                  )
                )
                is True
              ):
                metalness_image_texture.image = bpy.data.images.load(
                  os.path.join(
                    self.filep, mat["mat_mtl0"][:-5] + TEXTEXT
                  )
                )
                metalness_image_texture.image.colorspace_settings.name = (
                  "Non-Color"
                )
              material.node_tree.links.new(
                metalness_image_texture.outputs[0],
                principled_bsdf.inputs[1],
              )

            if mat["mat_enable_emission_color_map"]:
              emission_image_texture = material.node_tree.nodes.new(
                "ShaderNodeTexImage"
              )
              if (
                os.path.exists(
                  os.path.join(
                    self.filep, mat["mat_emi0"][:-5] + TEXTEXT
                  )
                )
                is True
              ):
                emission_image_texture.image = bpy.data.images.load(
                  os.path.join(
                    self.filep, mat["mat_emi0"][:-5] + TEXTEXT
                  )
                )
              material.node_tree.links.new(
                emission_image_texture.outputs[0],
                principled_bsdf.inputs[26],
              )

            if mat["mat_enable_roughness_map"]:
              roughness_image_texture = material.node_tree.nodes.new(
                "ShaderNodeTexImage"
              )
              if (
                os.path.exists(
                  os.path.join(
                    self.filep, mat["mat_rgh0"][:-5] + TEXTEXT
                  )
                )
                is True
              ):
                roughness_image_texture.image = bpy.data.images.load(
                  os.path.join(
                    self.filep, mat["mat_rgh0"][:-5] + TEXTEXT
                  )
                )
                roughness_image_texture.image.colorspace_settings.name = (
                  "Non-Color"
                )
              material.node_tree.links.new(
                roughness_image_texture.outputs[0],
                principled_bsdf.inputs[2],
              )

            if mat["mat_enable_ao_map"]:
              ambientocclusion_image_texture = material.node_tree.nodes.new(
                "ShaderNodeTexImage"
              )
              if (
                os.path.exists(
                  os.path.join(
                    self.filep, mat["mat_ao0"][:-5] + TEXTEXT
                  )
                )
                is True
              ):
                ambientocclusion_image_texture.image = bpy.data.images.load(
                  os.path.join(
                    self.filep, mat["mat_ao0"][:-5] + TEXTEXT
                  )
                )
                ambientocclusion_image_texture.image.colorspace_settings.name = (
                  "Non-Color"
                )
              mix_color6 = material.node_tree.nodes.new("ShaderNodeMixRGB")
              mix_color6.blend_type = "MULTIPLY"
              if (
                mat["mat_ao0"][:-5]
                == "../../glb_share_tex/texture_white_ao/texture_white_ao"
              ):
                mix_color6.inputs[0].default_value = 0
              else:
                mix_color6.inputs[0].default_value = 1.0
              if mix_color5 is not None:
                material.node_tree.links.new(
                  mix_color5.outputs[0], mix_color6.inputs[0]
                )
                material.node_tree.links.new(
                  ambientocclusion_image_texture.outputs[0],
                  mix_color6.inputs[1],
                )
                material.node_tree.links.new(
                  mix_color6.outputs[0], color_output
                )
              else:
                material.node_tree.links.new(
                  mix_color4.outputs[0], mix_color6.inputs[1]
                )
                material.node_tree.links.new(
                  ambientocclusion_image_texture.outputs[0],
                  mix_color6.inputs[2],
                )
                material.node_tree.links.new(
                  mix_color6.outputs[0], color_output
                )
            if (
              os.path.exists(
                os.path.join(self.filep, mat["mat_col0"][:-5] + TEXTEXT)
              )
              is True
            ):
              if (
                color1 == (1.0, 1.0, 1.0, 1.0)
                and color2 == (1.0, 1.0, 1.0, 1.0)
                and color3 == (1.0, 1.0, 1.0, 1.0)
                and color4 == (1.0, 1.0, 1.0, 1.0)
              ):
                if mat["mat_enable_ao_map"]:
                  material.node_tree.links.new(
                    alb_image_texture.outputs[0], mix_color6.inputs[1]
                  )
                else:
                  material.node_tree.links.new(
                    alb_image_texture.outputs[0], mix_color5.inputs[1]
                  )

          else:
            if mat["mat_enable_base_color_map"]:
              alb_image_texture = material.node_tree.nodes.new(
                "ShaderNodeTexImage"
              )
              if (
                os.path.exists(
                  os.path.join(
                    self.filep, mat["mat_col0"][:-5] + TEXTEXT
                  )
                )
                is True
              ):
                alb_image_texture.image = bpy.data.images.load(
                  os.path.join(
                    self.filep, mat["mat_col0"][:-5] + TEXTEXT
                  )
                )
              material.node_tree.links.new(
                alb_image_texture.outputs[0], color_output
              )
              material.node_tree.links.new(
                alb_image_texture.outputs[1], principled_bsdf.inputs[4]
              )

            if mat["mat_enable_highlight_map"]:
              highlight_image_texture = material.node_tree.nodes.new(
                "ShaderNodeTexImage"
              )
              if (
                os.path.exists(
                  os.path.join(self.filep, mat["mat_highmsk0"][:-5] + ".png")
                )
                is True
              ):
                highlight_image_texture.image = bpy.data.images.load(
                  os.path.join(self.filep, mat["mat_highmsk0"][:-5] + ".png")
                )
                highlight_image_texture.image.colorspace_settings.name = (
                  "Non-Color"
                )
              else:
                highlight_image_texture.image = bpy.data.images.load(
                  os.path.join(self.filep, mat["mat_col0"][:-8] + "msk.png")
                )
                highlight_image_texture.image.colorspace_settings.name = (
                  "Non-Color"
                )
              material.node_tree.links.new(
                highlight_image_texture.outputs[0], mix_color5.inputs[0]
              )
              material.node_tree.links.new(
                mix_color4.outputs[0], mix_color5.inputs[1]
              )
              material.node_tree.links.new(
                mix_color5.outputs[0], color_output
              )

            if mat["mat_enable_normal_map"]:
              normal_image_texture = material.node_tree.nodes.new(
                "ShaderNodeTexImage"
              )
              if (
                os.path.exists(
                  os.path.join(
                    self.filep, mat["mat_nrm0"][:-5] + TEXTEXT
                  )
                )
                is True
              ):
                normal_image_texture.image = bpy.data.images.load(
                  os.path.join(
                    self.filep, mat["mat_nrm0"][:-5] + TEXTEXT
                  )
                )
                normal_image_texture.image.colorspace_settings.name = (
                  "Non-Color"
                )
              separate_color2 = material.node_tree.nodes.new(
                "ShaderNodeSeparateRGB"
              )
              combine_color2 = material.node_tree.nodes.new(
                "ShaderNodeCombineColor"
              )
              normal_map2 = material.node_tree.nodes.new(
                "ShaderNodeNormalMap"
              )
              material.node_tree.links.new(
                normal_image_texture.outputs[0], separate_color2.inputs[0]
              )
              material.node_tree.links.new(
                separate_color2.outputs[0], combine_color2.inputs[0]
              )
              material.node_tree.links.new(
                separate_color2.outputs[1], combine_color2.inputs[1]
              )
              material.node_tree.links.new(
                normal_image_texture.outputs[1], combine_color2.inputs[2]
              )
              material.node_tree.links.new(
                combine_color2.outputs[0], normal_map2.inputs[1]
              )
              material.node_tree.links.new(
                normal_map2.outputs[0], principled_bsdf.inputs[5]
              )
              if mat["mat_shader"] == "Transparent":
                material.node_tree.links.new(
                  normal_map2.outputs[0], reflectionpart5.inputs[1]
                )
                material.node_tree.links.new(
                  reflectionpart5.outputs[0], principled_bsdf.inputs[4]
                )

            if mat["mat_enable_emission_color_map"]:
              emission_image_texture = material.node_tree.nodes.new(
                "ShaderNodeTexImage"
              )
              if (
                os.path.exists(
                  os.path.join(
                    self.filep, mat["mat_emi0"][:-5] + TEXTEXT
                  )
                )
                is True
              ):
                emission_image_texture.image = bpy.data.images.load(
                  os.path.join(
                    self.filep, mat["mat_emi0"][:-5] + TEXTEXT
                  )
                )
              material.node_tree.links.new(
                emission_image_texture.outputs[0],
                principled_bsdf.inputs[26],
              )

            if mat["mat_enable_metallic_map"]:
              metalness_image_texture = material.node_tree.nodes.new(
                "ShaderNodeTexImage"
              )
              if (
                os.path.exists(
                  os.path.join(
                    self.filep, mat["mat_mtl0"][:-5] + TEXTEXT
                  )
                )
                is True
              ):
                metalness_image_texture.image = bpy.data.images.load(
                  os.path.join(
                    self.filep, mat["mat_mtl0"][:-5] + TEXTEXT
                  )
                )
                metalness_image_texture.image.colorspace_settings.name = (
                  "Non-Color"
                )
              material.node_tree.links.new(
                metalness_image_texture.outputs[0],
                principled_bsdf.inputs[1],
              )

            if mat["mat_enable_roughness_map"]:
              roughness_image_texture = material.node_tree.nodes.new(
                "ShaderNodeTexImage"
              )
              if (
                os.path.exists(
                  os.path.join(
                    self.filep, mat["mat_rgh0"][:-5] + TEXTEXT
                  )
                )
                is True
              ):
                roughness_image_texture.image = bpy.data.images.load(
                  os.path.join(
                    self.filep, mat["mat_rgh0"][:-5] + TEXTEXT
                  )
                )
                roughness_image_texture.image.colorspace_settings.name = (
                  "Non-Color"
                )
              material.node_tree.links.new(
                roughness_image_texture.outputs[0],
                principled_bsdf.inputs[2],
              )

            if mat["mat_enable_ao_map"]:
              ambientocclusion_image_texture = material.node_tree.nodes.new(
                "ShaderNodeTexImage"
              )
              if (
                os.path.exists(
                  os.path.join(
                    self.filep, mat["mat_ao0"][:-5] + TEXTEXT
                  )
                )
                is True
              ):
                ambientocclusion_image_texture.image = bpy.data.images.load(
                  os.path.join(
                    self.filep, mat["mat_ao0"][:-5] + TEXTEXT
                  )
                )
                ambientocclusion_image_texture.image.colorspace_settings.name = (
                  "Non-Color"
                )
              mix_color6 = material.node_tree.nodes.new("ShaderNodeMixRGB")
              mix_color6.blend_type = "MULTIPLY"
              if (
                mat["mat_ao0"][:-5]
                == "../../glb_share_tex/texture_white_ao/texture_white_ao"
              ):
                mix_color6.inputs[0].default_value = 0
              else:
                mix_color6.inputs[0].default_value = 1.0
              material.node_tree.links.new(
                alb_image_texture.outputs[0], mix_color6.inputs[1]
              )
              material.node_tree.links.new(
                ambientocclusion_image_texture.outputs[0],
                mix_color6.inputs[2],
              )
              material.node_tree.links.new(
                mix_color6.outputs[0], color_output
              )
              
        if not self.materials or isinstance(self.materials[0], Material):
          raise ValueError("No materials found.")
    return


  def process_trskl_pla(self):
    bone_array = []
    self.bone_id_map = {}
    bone_rig_array = []
    trskl_bone_adjust = 0
    if self.trskl is not None:
      print("Parsing TRSKL...")
      trskl_file_start = readlong(self.trskl)
      fseek(self.trskl, trskl_file_start)
      trskl_struct = ftell(self.trskl) - readlong(self.trskl)
      fseek(self.trskl, trskl_struct)
      trskl_struct_len = readshort(self.trskl)
      if trskl_struct_len == 0x000C:
        trskl_struct_section_len = readshort(self.trskl)
        trskl_struct_start = readshort(self.trskl)
        trskl_struct_bone = readshort(self.trskl)
        trskl_struct_b = readshort(self.trskl)
        trskl_struct_c = readshort(self.trskl)
        trskl_struct_bone_adjust = 0
      elif trskl_struct_len == 0x000E:
        trskl_struct_section_len = readshort(self.trskl)
        trskl_struct_start = readshort(self.trskl)
        trskl_struct_bone = readshort(self.trskl)
        trskl_struct_b = readshort(self.trskl)
        trskl_struct_c = readshort(self.trskl)
        trskl_struct_bone_adjust = readshort(self.trskl)
      else:
        raise AssertionError("Unexpected TRSKL header struct length!")

      if trskl_struct_bone_adjust != 0:
        fseek(self.trskl, trskl_file_start + trskl_struct_bone_adjust)
        trskl_bone_adjust = readlong(self.trskl)
        print(f"Mesh node IDs start at {trskl_bone_adjust}")

      if trskl_struct_bone != 0:
        fseek(self.trskl, trskl_file_start + trskl_struct_bone)
        trskl_bone_start = ftell(self.trskl) + readlong(self.trskl)
        fseek(self.trskl, trskl_bone_start)
        bone_count = readlong(self.trskl)

        if IN_BLENDER_ENV:
          new_armature = bpy.data.armatures.new(os.path.basename(self.trmdl.name))
          self.bone_structure = bpy.data.objects.new(
            os.path.basename(self.trmdl.name), new_armature
          )
          self.new_collection.objects.link(self.bone_structure)
          bpy.context.view_layer.objects.active = self.bone_structure
          bpy.ops.object.editmode_toggle()

        for x in range(bone_count):
          bone_offset = ftell(self.trskl) + readlong(self.trskl)
          bone_ret = ftell(self.trskl)
          fseek(self.trskl, bone_offset)
          print(f"Bone {x} start: {hex(bone_offset)}")
          trskl_bone_struct = ftell(self.trskl) - readlong(self.trskl)
          fseek(self.trskl, trskl_bone_struct)
          trskl_bone_struct_len = readshort(self.trskl)

          if trskl_bone_struct_len == 0x0012:
            trskl_bone_struct_ptr_section_len = readshort(self.trskl)
            trskl_bone_struct_ptr_string = readshort(self.trskl)
            trskl_bone_struct_ptr_bone = readshort(self.trskl)
            trskl_bone_struct_ptr_c = readshort(self.trskl)
            trskl_bone_struct_ptr_d = readshort(self.trskl)
            trskl_bone_struct_ptr_parent = readshort(self.trskl)
            trskl_bone_struct_ptr_rig_id = readshort(self.trskl)
            trskl_bone_struct_ptr_bone_merge = readshort(self.trskl)
            trskl_bone_struct_ptr_h = 0
          elif trskl_bone_struct_len == 0x0014:
            trskl_bone_struct_ptr_section_len = readshort(self.trskl)
            trskl_bone_struct_ptr_string = readshort(self.trskl)
            trskl_bone_struct_ptr_bone = readshort(self.trskl)
            trskl_bone_struct_ptr_c = readshort(self.trskl)
            trskl_bone_struct_ptr_d = readshort(self.trskl)
            trskl_bone_struct_ptr_parent = readshort(self.trskl)
            trskl_bone_struct_ptr_rig_id = readshort(self.trskl)
            trskl_bone_struct_ptr_bone_merge = readshort(self.trskl)
            trskl_bone_struct_ptr_h = readshort(self.trskl)
          else:
            trskl_bone_struct_ptr_section_len = readshort(self.trskl)
            trskl_bone_struct_ptr_string = readshort(self.trskl)
            trskl_bone_struct_ptr_bone = readshort(self.trskl)
            trskl_bone_struct_ptr_c = readshort(self.trskl)
            trskl_bone_struct_ptr_d = readshort(self.trskl)
            trskl_bone_struct_ptr_parent = readshort(self.trskl)
            trskl_bone_struct_ptr_rig_id = readshort(self.trskl)
            trskl_bone_struct_ptr_bone_merge = readshort(self.trskl)
            trskl_bone_struct_ptr_h = readshort(self.trskl)

          if trskl_bone_struct_ptr_bone_merge != 0:
            fseek(self.trskl, bone_offset + trskl_bone_struct_ptr_bone_merge)
            bone_merge_start = ftell(self.trskl) + readlong(self.trskl)
            fseek(self.trskl, bone_merge_start)
            bone_merge_string_len = readlong(self.trskl)
            if bone_merge_string_len != 0:
              bone_merge_string = readfixedstring(
                self.trskl, bone_merge_string_len
              )
              print(f"BoneMerge to {bone_merge_string}")
            else:
              bone_merge_string = ""

          if trskl_bone_struct_ptr_bone != 0:
            fseek(self.trskl, bone_offset + trskl_bone_struct_ptr_bone)
            bone_pos_start = ftell(self.trskl) + readlong(self.trskl)
            fseek(self.trskl, bone_pos_start)
            bone_pos_struct = ftell(self.trskl) - readlong(self.trskl)
            fseek(self.trskl, bone_pos_struct)
            bone_pos_struct_len = readshort(self.trskl)

            if bone_pos_struct_len != 0x000A:
              raise AssertionError("Unexpected bone position struct length!")

            bone_pos_struct_section_len = readshort(self.trskl)
            bone_pos_struct_ptr_scl = readshort(self.trskl)
            bone_pos_struct_ptr_rot = readshort(self.trskl)
            bone_pos_struct_ptr_trs = readshort(self.trskl)

            fseek(self.trskl, bone_pos_start + bone_pos_struct_ptr_trs)
            bone_tx = readfloat(self.trskl)
            bone_ty = readfloat(self.trskl)
            bone_tz = readfloat(self.trskl)
            # TODO ArceusScale
            # LINE 1797
            fseek(self.trskl, bone_pos_start + bone_pos_struct_ptr_rot)
            bone_rx = readfloat(self.trskl)
            bone_ry = readfloat(self.trskl)
            bone_rz = readfloat(self.trskl)
            fseek(self.trskl, bone_pos_start + bone_pos_struct_ptr_scl)
            bone_sx = readfloat(self.trskl)
            bone_sy = readfloat(self.trskl)
            bone_sz = readfloat(self.trskl)

            if trskl_bone_struct_ptr_string != 0:
              fseek(self.trskl, bone_offset + trskl_bone_struct_ptr_string)
              bone_string_start = ftell(self.trskl) + readlong(self.trskl)
              fseek(self.trskl, bone_string_start)
              bone_str_len = readlong(self.trskl)
              bone_name = readfixedstring(self.trskl, bone_str_len)
            if trskl_bone_struct_ptr_parent != 0x00:
              fseek(self.trskl, bone_offset + trskl_bone_struct_ptr_parent)
              bone_parent = readlong(self.trskl) + 1
            else:
              bone_parent = 0
            if trskl_bone_struct_ptr_rig_id != 0:
              fseek(self.trskl, bone_offset + trskl_bone_struct_ptr_rig_id)
              bone_rig_id = readlong(self.trskl) + trskl_bone_adjust

              while len(bone_rig_array) <= bone_rig_id:
                bone_rig_array.append("")
              bone_rig_array[bone_rig_id] = bone_name

            bone_matrix = Matrix.LocRotScale(
              Vector((bone_tx, bone_ty, bone_tz)),
              Vector((bone_rx, bone_ry, bone_rz)),
              Vector((bone_sx, bone_sy, bone_sz)),
            )

            if IN_BLENDER_ENV:
              new_bone = new_armature.edit_bones.new(bone_name)

              new_bone.use_connect = False
              new_bone.use_inherit_rotation = True
              new_bone.use_inherit_scale = True
              new_bone.use_local_location = True

              new_bone.head = (0, 0, 0)
              new_bone.tail = (0, 0, 0.1)
              new_bone.matrix = bone_matrix

              if bone_parent != 0:
                new_bone.parent = bone_array[bone_parent - 1]
                new_bone.matrix = (
                  bone_array[bone_parent - 1].matrix @ bone_matrix
                )

              if bone_name in bone_rig_array:
                self.bone_id_map[bone_rig_array.index(bone_name)] = bone_name
              else:
                print(f"Bone {bone_name} not found in bone rig array!")
              bone_array.append(new_bone)
          fseek(self.trskl, bone_ret)
      fclose(self.trskl)
      if IN_BLENDER_ENV:
        bpy.ops.object.editmode_toggle()
    return


  def process_trmdl_pla(self):
    print("Parsing TRMDL...")
    trmsh_lods_array = []

    trmdl_file_start = readlong(self.trmdl)
    fseek(self.trmdl, trmdl_file_start)
    trmdl_struct = ftell(self.trmdl) - readlong(self.trmdl)
    fseek(self.trmdl, trmdl_struct)
    trmdl_struct_len = readshort(self.trmdl)

    if trmdl_struct_len == 0x0012:
      trmdl_struct_section_len = readshort(self.trmdl)
      trmdl_struct_start = readshort(self.trmdl)
      trmdl_struct_trmsh = readshort(self.trmdl)
      trmdl_struct_trskl = readshort(self.trmdl)
      trmdl_struct_trmtr = readshort(self.trmdl)
      trmdl_struct_custom = readshort(self.trmdl)
      trmdl_struct_bound_box = readshort(self.trmdl)
      trmdl_struct_float = readshort(self.trmdl)
    elif trmdl_struct_len == 0x0014:  # ScarletViolet Only
      trmdl_struct_section_len = readshort(self.trmdl)
      trmdl_struct_start = readshort(self.trmdl)
      trmdl_struct_trmsh = readshort(self.trmdl)
      trmdl_struct_trskl = readshort(self.trmdl)
      trmdl_struct_trmtr = readshort(self.trmdl)
      trmdl_struct_custom = readshort(self.trmdl)
      trmdl_struct_bound_box = readshort(self.trmdl)
      trmdl_struct_float = readshort(self.trmdl)
      trmdl_struct_trltt = readshort(self.trmdl)
    elif trmdl_struct_len == 0x0018:  # ScarletViolet Only
      trmdl_struct_section_len = readshort(self.trmdl)
      trmdl_struct_start = readshort(self.trmdl)
      trmdl_struct_trmsh = readshort(self.trmdl)
      trmdl_struct_trskl = readshort(self.trmdl)
      trmdl_struct_trmtr = readshort(self.trmdl)
      trmdl_struct_custom = readshort(self.trmdl)
      trmdl_struct_bound_box = readshort(self.trmdl)
      trmdl_struct_float = readshort(self.trmdl)
      trmdl_struct_trltt = readshort(self.trmdl)
      trmdl_struct_unka = readshort(self.trmdl)
      trmdl_struct_unkb = readshort(self.trmdl)
    else:
      raise AssertionError("Unexpected TRMDL header struct length!")

    if trmdl_struct_trmsh != 0:
      fseek(self.trmdl, trmdl_file_start + trmdl_struct_trmsh)
      trmsh_start = ftell(self.trmdl) + readlong(self.trmdl)
      fseek(self.trmdl, trmsh_start)
      trmsh_count = readlong(self.trmdl)
      for x in range(trmsh_count):
        trmsh_offset = ftell(self.trmdl) + readlong(self.trmdl)
        trmsh_ret = ftell(self.trmdl)
        fseek(self.trmdl, trmsh_offset)
        trmsh_struct = ftell(self.trmdl) - readlong(self.trmdl)
        fseek(self.trmdl, trmsh_struct)
        trmsh_struct_len = readshort(self.trmdl)

        if trmsh_struct_len != 0x0006:
          raise AssertionError("Unexpected TRMSH struct length!")

        trmsh_struct_section_len = readshort(self.trmdl)
        trmsh_struct_ptr_name = readshort(self.trmdl)

        if trmsh_struct_ptr_name != 0:
          fseek(self.trmdl, trmsh_offset + trmsh_struct_ptr_name)
          trmsh_name_offset = ftell(self.trmdl) + readlong(self.trmdl)
          fseek(self.trmdl, trmsh_name_offset)
          trmsh_name_len = readlong(self.trmdl)
          self.chara_check = readfixedstring(self.trmdl, 3)
          fseek(self.trmdl, ftell(self.trmdl) - 3)

          self.chara_check = "None"

          if self.chara_check.startswith(("au_")):
            self.chara_check = "CommonNPC"
          elif self.chara_check.startswith(("bu_")):
            self.chara_check = "CommonNPC"
          elif self.chara_check.startswith(("cf_")):
            self.chara_check = "CommonNPC"
          elif self.chara_check.startswith(("cm_")):
            self.chara_check = "CommonNPC"
          elif self.chara_check.startswith(("df_")):
            self.chara_check = "CommonNPC"
          elif self.chara_check.startswith(("dm_")):
            self.chara_check = "CommonNPC"
          elif self.chara_check.startswith(("p1_")):
            self.chara_check = "Rei"
          elif self.chara_check.startswith(("p2_")):
            self.chara_check = "Akari"
          elif self.chara_check.startswith(("pm")):
            self.chara_check = "Pokemon"
          else:
            self.chara_check = "None"

          if self.chara_check == "Rei" or self.chara_check == "Akari":
            self.trskl = self.trskl = open(os.path.join(self.filep, "p0_base.trskl"), "rb")

          trmsh_name = readfixedstring(self.trmdl, trmsh_name_len)
          print(trmsh_name)
          print(self.chara_check)
          trmsh_lods_array.append(trmsh_name)
        fseek(self.trmdl, trmsh_ret)

    if trmdl_struct_trskl != 0:
      fseek(self.trmdl, trmdl_file_start + trmdl_struct_trskl)
      trskl_start = ftell(self.trmdl) + readlong(self.trmdl)
      fseek(self.trmdl, trskl_start)
      trskl_struct = ftell(self.trmdl) - readlong(self.trmdl)
      fseek(self.trmdl, trskl_struct)
      trskl_struct_len = readshort(self.trmdl)

      if trskl_struct_len != 0x0006:
        raise AssertionError("Unexpected TRSKL struct length!")

      trskl_struct_section_len = readshort(self.trmdl)
      trskl_struct_ptr_name = readshort(self.trmdl)

      if trskl_struct_ptr_name != 0:
        fseek(self.trmdl, trskl_start + trskl_struct_ptr_name)
        trskl_name_offset = ftell(self.trmdl) + readlong(self.trmdl)
        fseek(self.trmdl, trskl_name_offset)
        trskl_name_len = readlong(self.trmdl)
        trskl_name = readfixedstring(self.trmdl, trskl_name_len)
        print(trskl_name)

        if os.path.exists(os.path.join(self.filep, trskl_name)):
          self.trskl = open(os.path.join(self.filep, trskl_name), "rb")
        else:
          print(f"Can't find {trskl_name}!")

    if trmdl_struct_trmtr != 0:
      fseek(self.trmdl, trmdl_file_start + trmdl_struct_trmtr)
      trmtr_start = ftell(self.trmdl) + readlong(self.trmdl)
      fseek(self.trmdl, trmtr_start)
      trmtr_count = readlong(self.trmdl)
      for x in range(trmtr_count):
        trmtr_offset = ftell(self.trmdl) + readlong(self.trmdl)
        trmtr_ret = ftell(self.trmdl)
        fseek(self.trmdl, trmtr_offset)
        trmtr_name_len = readlong(
          self.trmdl
        )  #  - 6 -- dunno why the extension was excluded
        trmtr_name = readfixedstring(self.trmdl, trmtr_name_len)
        # TODO ArceusShiny
        # LINE 1227
        print(trmtr_name)
        if x == 0:
          if self.settings["rare"] is True:
            self.trmtr = open(
              os.path.join(self.filep, Path(trmtr_name).stem + "_rare.trmtr"), "rb"
            )
          else:
            self.trmtr = open(os.path.join(self.filep, trmtr_name), "rb")
        fseek(self.trmdl, trmtr_ret)
    fclose(self.trmdl)

    return


