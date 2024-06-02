import bpy


def get_type_items(type: str):
    items = []
    for obj in bpy.data.objects:
        if obj.type == type:
            items.append((obj.name, obj.name, ""))
    return items

