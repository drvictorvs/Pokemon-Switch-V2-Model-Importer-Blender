# SPDX-FileCopyrightText: 2024 Dr. Victor Vasconcelos
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Provide means of importing and exporting Pokémon Switch models.
"""

__all__ = (
    "ExportTRMeshJsons",
    "ExportTRSKLJsons",
    "ImportTRMDL",
    "ImportTRSKL"
)

import ExportTRMeshJsons, ExportTRSKLJsons, ImportTRMDL, ImportTRSKL
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

def register():
  ExportTRMeshJsons.register()
  ExportTRSKLJsons.register()
  ImportTRMDL.register()
  ImportTRSKL.register()


if __name__ == "__main__":
  register()
