bl_info = {
  "name": "Pokémon Switch Model Importer-Exporter",
  "author": "Scarlett/SomeKitten, ElChicoEevee, mv & drvictorvs",
  "version": (0, 0, 1),
  "blender": (4, 0, 0),
  "location": "File > Import-Export",
  "description": "Imports-Exports TRMDL, TRMBF, TRMSH JSON armatures for Pokémon "
  "Switch",
  "warning": "",
  "doc_url": "",
  "tracker_url": "",
  "category": "Import-Export",
}

"""
Provide means of importing and exporting Pokémon Switch models.
"""

__all__ = (
    "ExportTRMesh",
    "ExportTRMeshJsons",
    "ExportTRSKLJson",
    "ImportTRMDL",
    "ImportTRSKL",
    "TRMDLProcessor",
)

import os

import bpy
from bpy.props import (BoolProperty, CollectionProperty,  # type: ignore
                       EnumProperty, IntProperty, StringProperty)
from bpy.types import Operator, PropertyGroup  # type: ignore
from bpy_extras.io_utils import ExportHelper, ImportHelper
from .io_pknx import (ExportTRMeshJsons, ExportTRSKLJson, ImportTRMDL,
                      ImportTRSKL)
from .io_pknx.TRMDLProcessor import TRMDLProcessor


class ExportTRMesh(Operator, ExportHelper):
  """Saves TRMDL, TRMSH and TRMBF JSONs for Pokémon Scarlet and Violet."""

  bl_idname = "pokemonswitch.exporttrmesh"
  bl_label = "Export Here"
  filename_ext = ".json"
  filepath: StringProperty(subtype="FILE_PATH")
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
    ExportTRMeshJsons.save_and_convert_jsons(self, context, dest_dir, export_settings)
    return {"FINISHED"}


class ExportTRSKL(Operator, ExportHelper):
    """Save a TRSKL JSON for Pokémon Scarlet/Violet"""

    bl_idname = "pokemonswitch.exportskeleton"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Export Skeleton"
    filename_ext = ".json"

    def execute(self, context):
        dest_dir = os.path.dirname(self.filepath)
        filedata = []
        for obj in bpy.context.selected_objects:
            if obj.type == "ARMATURE":
                ExportTRSKLJson.save_skeleton_data(obj, dest_dir)
            elif obj.find_armature() is not None:
                ExportTRSKLJson.save_skeleton_data(obj.find_armature(), dest_dir)
        return {"FINISHED"}


class PokeSVImport(Operator, ImportHelper):
    """Import a TRMDL file from Pokémon Scarlet/Violet"""

    bl_idname = "custom_import_scene.pokemonscarletviolet"
    bl_label = "Import"
    bl_options = {"PRESET", "UNDO"}
    filename_ext = ".trmdl"
    filter_glob: StringProperty(
        default="*.trmdl",
        options={"HIDDEN"},
        maxlen=255,
    )
    filepath = StringProperty(
        subtype="FILE_PATH",
    )
    files = CollectionProperty(type=PropertyGroup)
    basearmature: EnumProperty(
        default='donothing',
        items=(('donothing','Load armature in .trmdl','Load armature in .trmdl'),
        ('loadbasearm',"Load base armature","Load base armature"),
        ('assigntobase',"Assign to base armature","Assign to base armature")),
        name="Uniforms"
        )
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
    bonestructh: BoolProperty(
        name="Bone Extras (WIP)",
        description="Bone Extras (WIP)",
        default=False,
    )
    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.prop(self, "rare")
        box = layout.box()
        box.prop(self, "multiple")
        box = layout.box()
        box.prop(self, "loadlods")
        box = layout.box()
        box.prop(self, "bonestructh")
        box = layout.box()
        box.prop(self, "basearmature")
        
    def execute(self, context):
        directory = os.path.dirname(self.filepath)
        
        export_settings = {
            "rare": self.rare,
            "loadlods": self.loadlods,
            "bonestructh": self.bonestructh,
            "basearmature": self.basearmature,
        }

        if self.multiple == False:
            filename = os.path.basename(self.filepath)
            f = open(os.path.join(directory, filename), "rb")
            ImportTRMDL.from_trmdl_scvi(directory, f, export_settings)
            f.close()
            return {"FINISHED"}
        else:
            file_list = sorted(os.listdir(directory))
            obj_list = [item for item in file_list if item.endswith(".trmdl")]
            for item in obj_list:
                f = open(os.path.join(directory, item), "rb")
                ImportTRMDL.from_trmdl_scvi(
                    directory,
                    f,
                    export_settings
                )
                f.close()
            return {"FINISHED"}


class PokeArcImport(Operator, ImportHelper):
    """Open a TRMDL file from Pokémon Legends Arceus"""
    bl_idname = "custom_import_scene.pokemonlegendsarceus"
    bl_label = "Import"
    bl_options = {"PRESET", "UNDO"}
    filename_ext = ".trmdl"
    filter_glob: StringProperty(
        default="*.trmdl",
        options={"HIDDEN"},
        maxlen=255,
    )
    filepath = bpy.props.StringProperty(
        subtype="FILE_PATH",
    )
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
        box.prop(self, "rare")
        box = layout.box()
        box.prop(self, "multiple")
        box = layout.box()
        box.prop(self, "loadlods")

    def execute(self, context):
        directory = os.path.dirname(self.filepath)
        export_settings = {
            "rare": self.rare,
            "loadlods": self.loadlods,
        }
        if self.multiple == False:
            filename = os.path.basename(self.filepath)
            f = open(os.path.join(directory, filename), "rb")
            TRMDLProcessor(directory, f, export_settings)
            f.close()
            return {"FINISHED"}
        else:
            file_list = sorted(os.listdir(directory))
            obj_list = [item for item in file_list if item.endswith(".trmdl")]
            for item in obj_list:
                f = open(os.path.join(directory, item), "rb")
                TRMDLProcessor(directory, f, export_settings)
                f.close()
            return {"FINISHED"}

#
#### Final Registration ####
#
def replace_current_menu_item(menu, item):
  for func in menu._dyn_ui_initialize():
    if func.__name__ == item.__name__:
      menu.remove(func)
  menu.append(item)

def menu_func_export(self, context):
  self.layout.separator()
  self.layout.operator(ExportTRMesh.bl_idname, text="ScVi Mesh JSONs (.trm**.json)")
  self.layout.operator(ExportTRMesh.bl_idname, text="ScVi Skeleton JSONs (.trskl.json)")

def menu_func_import(self, context):
  self.layout.separator()
  self.layout.operator(PokeArcImport.bl_idname, text="PLA Model (.trmdl)")
  self.layout.operator(PokeSVImport.bl_idname, text="ScVi Model (.trmdl)")

def register():
  bpy.utils.register_class(PokeSVImport)
  bpy.utils.register_class(PokeArcImport)
  bpy.utils.register_class(ExportTRMesh)
  bpy.utils.register_class(ExportTRSKL)
  replace_current_menu_item(bpy.types.TOPBAR_MT_file_export, menu_func_export)
  replace_current_menu_item(bpy.types.TOPBAR_MT_file_import, menu_func_import)

def unregister():
  bpy.utils.unregister_class(PokeSVImport)
  bpy.utils.unregister_class(PokeArcImport)
  bpy.utils.unregister_class(ExportTRMesh)
  bpy.utils.unregister_class(ExportTRSKL)

if __name__ == "__main__":
  register()
