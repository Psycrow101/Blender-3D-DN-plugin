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
    gui.DN_AnimChooserBox,
    gui.DN_CollisionObjectProps,
    gui.DN_ObjectProps,
    gui.DN_MaterialProps,
    gui.DN_EditBoneProps,
    gui.OBJECT_PT_DNObjects,
    gui.MATERIAL_PT_DNMaterials,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(gui.menu_func_import)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(gui.menu_func_import)

    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
