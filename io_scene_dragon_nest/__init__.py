import bpy

from .gui import gui

bl_info = {
    "name": "Import Dragon Nest Model / Animation",
    "author": "Psycrow",
    "version": (0, 2, 2),
    "blender": (2, 80, 0),
    "location": "File > Import-Export",
    "description": "Import Dragon Nest Model / Animation (.msh, .ani, .anim)",
    "warning": "",
    "wiki_url": "",
    "support": 'COMMUNITY',
    "category": "Import-Export"
}

classes = (
    gui.DN_Import,
    gui.DN_ExportSKN,
    gui.DN_ExportMSH,
    gui.DN_ExportANI,
    gui.DN_AddExtraPropItem,
    gui.DN_RemoveExtraPropItem,
    gui.DN_MT_ExportChoice,
    gui.DN_AnimChooserBox,
    gui.DN_CollisionObjectProps,
    gui.DN_ObjectProps,
    gui.DN_MaterialExtraProps,
    gui.DN_MaterialProps,
    gui.DN_BoneProps,
    gui.OBJECT_PT_DNObjects,
    gui.MATERIAL_PT_DNMaterials,
)

_draw_3d_handler = None


def draw_3d_callback():
    context = bpy.context
    gui.DN_ObjectProps.draw_bbox(context)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(gui.menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(gui.menu_func_export)

    global _draw_3d_handler
    _draw_3d_handler = bpy.types.SpaceView3D.draw_handler_add(draw_3d_callback, (), 'WINDOW', 'POST_VIEW')


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(gui.menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(gui.menu_func_export)

    bpy.types.SpaceView3D.draw_handler_remove(_draw_3d_handler, 'WINDOW')

    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
