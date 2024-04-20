bl_info = {
  "name": "Pokémon Switch V2 Armature (.trskl)",
  "author": "Scarlett/SomeKitten & ElChicoEevee",
  "version": (0, 0, 2),
  "blender": (4, 0, 0),
  "location": "File > Import",
  "description": "Blender addon for importing Pokémon Switch trskl",
  "warning": "",
  "category": "Import",
}

import os
from os import path
import os.path
import random
import struct
from pathlib import Path
from bpy.props import (BoolProperty,
             FloatProperty,
             StringProperty,
             EnumProperty,
             CollectionProperty
             )
from bpy_extras.io_utils import ImportHelper
from bpy.types import (
    Operator,
    OperatorFileListElement,
    )
import bpy
import mathutils
import math
import glob
import shutil
import sys


# READ THIS: change to True when running in Blender, False when running using fake-bpy-module-latest
IN_BLENDER_ENV = True

class PokeSVSkelImport(bpy.types.Operator, ImportHelper):
  bl_idname = "custom_import_armature.pokeskelscarletviolet"
  bl_label = "Import"
  bl_options = {'PRESET', 'UNDO'}
  filename_ext = ".trskl"
  filter_glob: StringProperty(
      default="*.trskl",
      options={'HIDDEN'},
      maxlen=255,
  )
  filepath = bpy.props.StringProperty(subtype='FILE_PATH',)
  files = CollectionProperty(type=bpy.types.PropertyGroup)
  bonestructh: BoolProperty(
      name="Bone Extras (WIP)",
      description="Bone Extras (WIP)",
      default=False,
      )
  def draw(self, context):
    layout = self.layout

    box = layout.box()
    box.prop(self, 'bonestructh')
    
    
  def execute(self, context):
    directory = os.path.dirname(self.filepath)
    if self.multiple == False:
      filename = os.path.basename(self.filepath)    
      f = open(os.path.join(directory, filename), "rb")
      from_trsklsv(directory, f, self.bonestructh)
      f.close()
      return {'FINISHED'}  
    else:
      file_list = sorted(os.listdir(directory))
      obj_list = [item for item in file_list if item.endswith('.trskl')]
      for item in obj_list:
        f = open(os.path.join(directory, item), "rb")
        from_trsklsv(directory, f, self.bonestructh)
        f.close()
      return {'FINISHED'}

def from_trsklsv(filep, trskl, bonestructh):
  # make collection
  if IN_BLENDER_ENV:
    new_collection = bpy.data.collections.new(os.path.basename(trskl.name[:-6]))
    bpy.context.scene.collection.children.link(new_collection)

  bone_structure = None

  bone_array = []
  bone_id_map = {}
  bone_rig_array = []
  trskl_bone_adjust = 0

  print("Parsing TRSKL...")

  if trskl is not None:
    print("Parsing TRSKL...")
    trskl_file_start = readlong(trskl)
    fseek(trskl, trskl_file_start)
    trskl_struct = ftell(trskl) - readlong(trskl); fseek(trskl, trskl_struct)
    trskl_struct_len = readshort(trskl)
    if trskl_struct_len == 0x000C:
      trskl_struct_section_len = readshort(trskl)
      trskl_struct_start = readshort(trskl)
      trskl_struct_bone = readshort(trskl)
      trskl_struct_b = readshort(trskl)
      trskl_struct_c = readshort(trskl)
      trskl_struct_bone_adjust = 0
    elif trskl_struct_len == 0x000E:
      trskl_struct_section_len = readshort(trskl)
      trskl_struct_start = readshort(trskl)
      trskl_struct_bone = readshort(trskl)
      trskl_struct_b = readshort(trskl)
      trskl_struct_c = readshort(trskl)
      trskl_struct_bone_adjust = readshort(trskl)
    else:
      raise AssertionError("Unexpected TRSKL header struct length!")

    if trskl_struct_bone_adjust != 0:
      fseek(trskl, trskl_file_start + trskl_struct_bone_adjust)
      trskl_bone_adjust = readlong(trskl); print(f"Mesh node IDs start at {trskl_bone_adjust}")

    if trskl_struct_bone != 0:
      fseek(trskl, trskl_file_start + trskl_struct_bone)
      trskl_bone_start = ftell(trskl) + readlong(trskl); fseek(trskl, trskl_bone_start)
      bone_count = readlong(trskl)

      if IN_BLENDER_ENV:
        new_armature = bpy.data.armatures.new(os.path.basename(trskl.name))
        bone_structure = bpy.data.objects.new(os.path.basename(trskl.name), new_armature)
        new_collection.objects.link(bone_structure)
        bpy.context.view_layer.objects.active = bone_structure
        bpy.ops.object.editmode_toggle()
      
      for x in range(bone_count):
        bone_offset = ftell(trskl) + readlong(trskl)
        bone_ret = ftell(trskl)
        fseek(trskl, bone_offset)
        print(f"Bone {x} start: {hex(bone_offset)}")
        trskl_bone_struct = ftell(trskl) - readlong(trskl); fseek(trskl, trskl_bone_struct)
        trskl_bone_struct_len = readshort(trskl)

        if trskl_bone_struct_len == 0x0012:
          trskl_bone_struct_ptr_section_len = readshort(trskl)
          trskl_bone_struct_ptr_string = readshort(trskl)
          trskl_bone_struct_ptr_bone = readshort(trskl)
          trskl_bone_struct_ptr_c = readshort(trskl)
          trskl_bone_struct_ptr_d = readshort(trskl)
          trskl_bone_struct_ptr_parent = readshort(trskl)
          trskl_bone_struct_ptr_rig_id = readshort(trskl)
          trskl_bone_struct_ptr_bone_merge = readshort(trskl)
          trskl_bone_struct_ptr_h = 0
        elif trskl_bone_struct_len == 0x0014:
          trskl_bone_struct_ptr_section_len = readshort(trskl)
          trskl_bone_struct_ptr_string = readshort(trskl)
          trskl_bone_struct_ptr_bone = readshort(trskl)
          trskl_bone_struct_ptr_c = readshort(trskl)
          trskl_bone_struct_ptr_d = readshort(trskl)
          trskl_bone_struct_ptr_parent = readshort(trskl)
          trskl_bone_struct_ptr_rig_id = readshort(trskl)
          trskl_bone_struct_ptr_bone_merge = readshort(trskl)
          trskl_bone_struct_ptr_h = readshort(trskl)
        else:
          trskl_bone_struct_ptr_section_len = readshort(trskl)
          trskl_bone_struct_ptr_string = readshort(trskl)
          trskl_bone_struct_ptr_bone = readshort(trskl)
          trskl_bone_struct_ptr_c = readshort(trskl)
          trskl_bone_struct_ptr_d = readshort(trskl)
          trskl_bone_struct_ptr_parent = readshort(trskl)
          trskl_bone_struct_ptr_rig_id = readshort(trskl)
          trskl_bone_struct_ptr_bone_merge = readshort(trskl)
          trskl_bone_struct_ptr_h = readshort(trskl)

        if trskl_bone_struct_ptr_bone_merge != 0:
          fseek(trskl, bone_offset + trskl_bone_struct_ptr_bone_merge)
          bone_merge_start = ftell(trskl) + readlong(trskl); fseek(trskl, bone_merge_start)
          bone_merge_string_len = readlong(trskl)
          if bone_merge_string_len != 0:
            bone_merge_string = readfixedstring(trskl, bone_merge_string_len)
            print(f"BoneMerge to {bone_merge_string}")
          else: bone_merge_string = ""

        

        if trskl_bone_struct_ptr_bone != 0:
          fseek(trskl, bone_offset + trskl_bone_struct_ptr_bone)
          bone_pos_start = ftell(trskl) + readlong(trskl); fseek(trskl, bone_pos_start)
          bone_pos_struct = ftell(trskl) - readlong(trskl); fseek(trskl, bone_pos_struct)
          bone_pos_struct_len = readshort(trskl)

          if bone_pos_struct_len != 0x000A:
            raise AssertionError("Unexpected bone position struct length!")

          bone_pos_struct_section_len = readshort(trskl)
          bone_pos_struct_ptr_scl = readshort(trskl)
          bone_pos_struct_ptr_rot = readshort(trskl)
          bone_pos_struct_ptr_trs = readshort(trskl)

          fseek(trskl, bone_pos_start + bone_pos_struct_ptr_trs)
          bone_tx = readfloat(trskl); bone_ty = readfloat(trskl); bone_tz = readfloat(trskl)
          # TODO ArceusScale
          # LINE 1797
          fseek(trskl, bone_pos_start + bone_pos_struct_ptr_rot)
          bone_rx = readfloat(trskl); bone_ry = readfloat(trskl); bone_rz = readfloat(trskl)
          fseek(trskl, bone_pos_start + bone_pos_struct_ptr_scl)
          bone_sx = readfloat(trskl); bone_sy = readfloat(trskl); bone_sz = readfloat(trskl)

          if trskl_bone_struct_ptr_string != 0:
            fseek(trskl, bone_offset + trskl_bone_struct_ptr_string)
            bone_string_start = ftell(trskl) + readlong(trskl); fseek(trskl, bone_string_start)
            bone_str_len = readlong(trskl); bone_name = readfixedstring(trskl, bone_str_len)
          if trskl_bone_struct_ptr_parent != 0x00:
            fseek(trskl, bone_offset + trskl_bone_struct_ptr_parent)
            bone_parent = readlong(trskl) + 1
          else:
            bone_parent = 0
          print(bone_parent)
          if trskl_bone_struct_ptr_rig_id != 0:
            fseek(trskl, bone_offset + trskl_bone_struct_ptr_rig_id)
            bone_rig_id = readlong(trskl) + trskl_bone_adjust

            while len(bone_rig_array) <= bone_rig_id:
              bone_rig_array.append("")
            bone_rig_array[bone_rig_id] = bone_name

          bone_matrix = mathutils.Matrix.LocRotScale(
            (bone_tx, bone_ty, bone_tz),
            mathutils.Euler((bone_rx, bone_ry, bone_rz)),
            (bone_sx, bone_sy, bone_sz))

          if IN_BLENDER_ENV:
            new_bone = new_armature.edit_bones.new(bone_name)

            new_bone.use_connect = False
            new_bone.use_inherit_rotation = True
            
            if bonestructh == True:
              if trskl_bone_struct_ptr_h == 0:
                new_bone.use_inherit_scale = True
              else:
                new_bone.use_inherit_scale = False
            
            new_bone.use_local_location = True

            new_bone.head = (0, 0, 0)
            new_bone.tail = (0, 0, 0.1)
            new_bone.matrix = bone_matrix

            if bone_parent != 0:
              new_bone.parent = new_armature.edit_bones[bone_parent - 1]
              new_bone.matrix = new_armature.edit_bones[bone_parent - 1].matrix @ bone_matrix

            if bone_name in bone_rig_array:
              bone_id_map[bone_rig_array.index(bone_name)] = bone_name
            else:
              bone_rig_array.append(bone_name)
              bone_id_map[len(bone_rig_array) - 1] = bone_name
            
            bone_array.append(new_bone)
        fseek(trskl, bone_ret)
    fclose(trskl)
    if IN_BLENDER_ENV:
      bpy.ops.object.editmode_toggle()


class PokeArcSkelImport(bpy.types.Operator, ImportHelper):
  bl_idname = "custom_import_scene.pokeskellegendsarceus"
  bl_label = "Import"
  bl_options = {'PRESET', 'UNDO'}
  filename_ext = ".trskl"
  filter_glob: StringProperty(
      default="*.trskl",
      options={'HIDDEN'},
      maxlen=255,
  )
  filepath = bpy.props.StringProperty(subtype='FILE_PATH',)
  files = CollectionProperty(type=bpy.types.PropertyGroup)
  rare: BoolProperty(
      name="Load Shiny",
      description="Uses rare material instead of normal one",
      default=False,
      )
  multiple: BoolProperty(
      name="Load All Folder",
      description="Uses rare material instead of normal one",
      default=False,
      )
  loadlods: BoolProperty(
      name="Load LODS",
      description="Uses rare material instead of normal one",
      default=False,
      )
  def draw(self, context):
    layout = self.layout

    box = layout.box()
    box.prop(self, 'rare')
    
    box = layout.box()
    box.prop(self, 'multiple')
    
    box = layout.box()
    box.prop(self, 'loadlods')
    
  def execute(self, context):
    directory = os.path.dirname(self.filepath)
    if self.multiple == False:
      filename = os.path.basename(self.filepath)    
      f = open(os.path.join(directory, filename), "rb")
      from_trskl(directory, f, self.rare, self.loadlods)
      f.close()
      return {'FINISHED'}  
    else:
      file_list = sorted(os.listdir(directory))
      obj_list = [item for item in file_list if item.endswith('.trskl')]
      for item in obj_list:
        f = open(os.path.join(directory, item), "rb")
        from_trskl(directory, f, self.rare, self.loadlods)
        f.close()
      return {'FINISHED'}

def from_trskl(filep, trskl):
  # make collection
  if IN_BLENDER_ENV:
    new_collection = bpy.data.collections.new(os.path.basename(trskl.name))
    bpy.context.scene.collection.children.link(new_collection)

  bone_structure = None
  
  bone_array = []
  bone_id_map = {}
  bone_rig_array = []
  trskl_bone_adjust = 0
  print("Parsing TRSKL...")

  trskl_file_start = readlong(trskl); fseek(trskl, trskl_file_start)
  trskl_struct = ftell(trskl) - readlong(trskl); fseek(trskl, trskl_struct)
  trskl_struct_len = readshort(trskl)

  if trskl is not None:
    print("Parsing TRSKL...")
    trskl_file_start = readlong(trskl)
    fseek(trskl, trskl_file_start)
    trskl_struct = ftell(trskl) - readlong(trskl); fseek(trskl, trskl_struct)
    trskl_struct_len = readshort(trskl)
    if trskl_struct_len == 0x000C:
      trskl_struct_section_len = readshort(trskl)
      trskl_struct_start = readshort(trskl)
      trskl_struct_bone = readshort(trskl)
      trskl_struct_b = readshort(trskl)
      trskl_struct_c = readshort(trskl)
      trskl_struct_bone_adjust = 0
    elif trskl_struct_len == 0x000E:
      trskl_struct_section_len = readshort(trskl)
      trskl_struct_start = readshort(trskl)
      trskl_struct_bone = readshort(trskl)
      trskl_struct_b = readshort(trskl)
      trskl_struct_c = readshort(trskl)
      trskl_struct_bone_adjust = readshort(trskl)
    else:
      raise AssertionError("Unexpected TRSKL header struct length!")

    if trskl_struct_bone_adjust != 0:
      fseek(trskl, trskl_file_start + trskl_struct_bone_adjust)
      trskl_bone_adjust = readlong(trskl); print(f"Mesh node IDs start at {trskl_bone_adjust}")

    if trskl_struct_bone != 0:
      fseek(trskl, trskl_file_start + trskl_struct_bone)
      trskl_bone_start = ftell(trskl) + readlong(trskl); fseek(trskl, trskl_bone_start)
      bone_count = readlong(trskl)

      if IN_BLENDER_ENV:
        new_armature = bpy.data.armatures.new(os.path.basename(trskl.name))
        bone_structure = bpy.data.objects.new(os.path.basename(trskl.name), new_armature)
        new_collection.objects.link(bone_structure)
        bpy.context.view_layer.objects.active = bone_structure
        bpy.ops.object.editmode_toggle()
      
      for x in range(bone_count):
        bone_offset = ftell(trskl) + readlong(trskl)
        bone_ret = ftell(trskl)
        fseek(trskl, bone_offset)
        print(f"Bone {x} start: {hex(bone_offset)}")
        trskl_bone_struct = ftell(trskl) - readlong(trskl); fseek(trskl, trskl_bone_struct)
        trskl_bone_struct_len = readshort(trskl)

        if trskl_bone_struct_len == 0x0012:
          trskl_bone_struct_ptr_section_len = readshort(trskl)
          trskl_bone_struct_ptr_string = readshort(trskl)
          trskl_bone_struct_ptr_bone = readshort(trskl)
          trskl_bone_struct_ptr_c = readshort(trskl)
          trskl_bone_struct_ptr_d = readshort(trskl)
          trskl_bone_struct_ptr_parent = readshort(trskl)
          trskl_bone_struct_ptr_rig_id = readshort(trskl)
          trskl_bone_struct_ptr_bone_merge = readshort(trskl)
          trskl_bone_struct_ptr_h = 0
        elif trskl_bone_struct_len == 0x0014:
          trskl_bone_struct_ptr_section_len = readshort(trskl)
          trskl_bone_struct_ptr_string = readshort(trskl)
          trskl_bone_struct_ptr_bone = readshort(trskl)
          trskl_bone_struct_ptr_c = readshort(trskl)
          trskl_bone_struct_ptr_d = readshort(trskl)
          trskl_bone_struct_ptr_parent = readshort(trskl)
          trskl_bone_struct_ptr_rig_id = readshort(trskl)
          trskl_bone_struct_ptr_bone_merge = readshort(trskl)
          trskl_bone_struct_ptr_h = readshort(trskl)
        else:
          trskl_bone_struct_ptr_section_len = readshort(trskl)
          trskl_bone_struct_ptr_string = readshort(trskl)
          trskl_bone_struct_ptr_bone = readshort(trskl)
          trskl_bone_struct_ptr_c = readshort(trskl)
          trskl_bone_struct_ptr_d = readshort(trskl)
          trskl_bone_struct_ptr_parent = readshort(trskl)
          trskl_bone_struct_ptr_rig_id = readshort(trskl)
          trskl_bone_struct_ptr_bone_merge = readshort(trskl)
          trskl_bone_struct_ptr_h = readshort(trskl)

        if trskl_bone_struct_ptr_bone_merge != 0:
          fseek(trskl, bone_offset + trskl_bone_struct_ptr_bone_merge)
          bone_merge_start = ftell(trskl) + readlong(trskl); fseek(trskl, bone_merge_start)
          bone_merge_string_len = readlong(trskl)
          if bone_merge_string_len != 0:
            bone_merge_string = readfixedstring(trskl, bone_merge_string_len)
            print(f"BoneMerge to {bone_merge_string}")
          else: bone_merge_string = ""

        if trskl_bone_struct_ptr_bone != 0:
          fseek(trskl, bone_offset + trskl_bone_struct_ptr_bone)
          bone_pos_start = ftell(trskl) + readlong(trskl); fseek(trskl, bone_pos_start)
          bone_pos_struct = ftell(trskl) - readlong(trskl); fseek(trskl, bone_pos_struct)
          bone_pos_struct_len = readshort(trskl)

          if bone_pos_struct_len != 0x000A:
            raise AssertionError("Unexpected bone position struct length!")

          bone_pos_struct_section_len = readshort(trskl)
          bone_pos_struct_ptr_scl = readshort(trskl)
          bone_pos_struct_ptr_rot = readshort(trskl)
          bone_pos_struct_ptr_trs = readshort(trskl)

          fseek(trskl, bone_pos_start + bone_pos_struct_ptr_trs)
          bone_tx = readfloat(trskl); bone_ty = readfloat(trskl); bone_tz = readfloat(trskl)
          # TODO ArceusScale
          # LINE 1797
          fseek(trskl, bone_pos_start + bone_pos_struct_ptr_rot)
          bone_rx = readfloat(trskl); bone_ry = readfloat(trskl); bone_rz = readfloat(trskl)
          fseek(trskl, bone_pos_start + bone_pos_struct_ptr_scl)
          bone_sx = readfloat(trskl); bone_sy = readfloat(trskl); bone_sz = readfloat(trskl)

          if trskl_bone_struct_ptr_string != 0:
            fseek(trskl, bone_offset + trskl_bone_struct_ptr_string)
            bone_string_start = ftell(trskl) + readlong(trskl); fseek(trskl, bone_string_start)
            bone_str_len = readlong(trskl); bone_name = readfixedstring(trskl, bone_str_len)
          if trskl_bone_struct_ptr_parent != 0x00:
            fseek(trskl, bone_offset + trskl_bone_struct_ptr_parent)
            bone_parent = readlong(trskl) + 1
          else:
            bone_parent = 0
          if trskl_bone_struct_ptr_rig_id != 0:
            fseek(trskl, bone_offset + trskl_bone_struct_ptr_rig_id)
            bone_rig_id = readlong(trskl) + trskl_bone_adjust

            while len(bone_rig_array) <= bone_rig_id:
              bone_rig_array.append("")
            bone_rig_array[bone_rig_id] = bone_name

          bone_matrix = mathutils.Matrix.LocRotScale(
            (bone_tx, bone_ty, bone_tz),
            mathutils.Euler((bone_rx, bone_ry, bone_rz)),
            (bone_sx, bone_sy, bone_sz))

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
              new_bone.matrix = bone_array[bone_parent - 1].matrix @ bone_matrix

            if bone_name in bone_rig_array:
              bone_id_map[bone_rig_array.index(bone_name)] = bone_name
            else:
              print(f"Bone {bone_name} not found in bone rig array!")
            bone_array.append(new_bone)
        fseek(trskl, bone_ret)
    fclose(trskl)
    if IN_BLENDER_ENV:
      bpy.ops.object.editmode_toggle()

def readbyte(file):
  return int.from_bytes(file.read(1), byteorder='little')

def readshort(file):
  return int.from_bytes(file.read(2), byteorder='little')

def readlong(file): # SIGNED!!!!
  bytes_data = file.read(4)
  # print(f"readlong: {bytes_data}")
  return int.from_bytes(bytes_data, byteorder='little', signed=True)

def readfloat(file):
  return struct.unpack('<f', file.read(4))[0]

def readhalffloat(file):
  return struct.unpack('<e', file.read(2))[0]

def readfixedstring(file, length):
  bytes_data = file.read(length)
  # print(f"readfixedstring ({length}): {bytes_data}")
  return bytes_data.decode('utf-8')

def fseek(file, offset):
  # print(f"Seeking to {offset}")
  file.seek(offset)

def ftell(file):
  return file.tell()

def fclose(file):
  file.close()

def check_if_menu_item_exists(menu, item):
    for func in menu._dyn_ui_initialize():
        if func.__name__ == item.__name__:
            return True
    return False

def ImportTRSKL_menu_func_import(self, context):
  self.layout.operator(PokeArcSkelImport.bl_idname, text="PLA Armature (.trskl)")
  self.layout.operator(PokeSVSkelImport.bl_idname, text="ScVi Armature (.trskl)")
    
def register():
  bpy.utils.register_class(PokeArcSkelImport)
  bpy.utils.register_class(PokeSVSkelImport)
  if not check_if_menu_item_exists(bpy.types.TOPBAR_MT_file_import, ImportTRSKL_menu_func_import):
    bpy.types.TOPBAR_MT_file_import.append(ImportTRSKL_menu_func_import)
  
def unregister():
  bpy.utils.unregister_class(PokeArcSkelImport)
  bpy.utils.unregister_class(PokeSVSkelImport)
  if check_if_menu_item_exists(bpy.types.TOPBAR_MT_file_import, ImportTRSKL_menu_func_import):
    bpy.types.TOPBAR_MT_file_import.remove(ImportTRSKL_menu_func_import)

if __name__ == "__main__":
  register()