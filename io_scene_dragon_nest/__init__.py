import bpy
from bpy.props import (
        BoolProperty,
        StringProperty,
        EnumProperty,
        )
from bpy_extras.io_utils import (
        ImportHelper,
        orientation_helper,
        axis_conversion,
        )

bl_info = {
    "name": "Import Dragon Nest Model / Animation",
    "author": "Psycrow",
    "version": (0, 2, 0),
    "blender": (2, 80, 0),
    "location": "File > Import-Export",
    "description": "Import Dragon Nest Model / Animation (.msh, .ani, .anim)",
    "warning": "",
    "wiki_url": "",
    "support": 'COMMUNITY',
    "category": "Import-Export"
}

if "bpy" in locals():
    import importlib
    if "import_dn_msh" in locals():
        importlib.reload(import_dn_msh)
    if "import_dn_ani" in locals():
        importlib.reload(import_dn_ani)


class DN_AnimChooserBox(bpy.types.Operator):
    bl_idname = "dialog.anim_chooser_box"
    bl_label = "Choose animation for import"
    bl_options = {'REGISTER'}

    def anim_enum_callback(self, context):
        global ani_importer

        items = [("0", "*All*", "", 0)]
        for i, name in enumerate(ani_importer.ani.names):
            items.append((str(i+1), name, "", i+1))

        return items

    anim_list: EnumProperty(items=anim_enum_callback, name="Animation Name")

    def execute(self, context):
        global ani_importer

        if not self.anim_list:
            return {'CANCELLED'}

        options = {
            "animation_id": int(self.anim_list) - 1,
        }

        ani_importer.import_data(context, options)
        imported = ani_importer.imported

        ani_importer = None
        return {'FINISHED'} if imported else {'CANCELLED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def cancel(self, context):
        global ani_importer
        ani_importer = None


@orientation_helper(axis_forward='-Z', axis_up='Y')
class ImportDragonNest(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.dragon_nest"
    bl_label = "Import Dragon Nest Model / Animation"
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = ".msh"
    filter_glob: StringProperty(default="*.msh;*.ani;*.anim", options={'HIDDEN'})

    append_to_target: BoolProperty(
        name="Append to Target Armature",
        description="Attach the imported mesh to the selected armature",
        default=False,
    )

    def execute(self, context):
        from . import import_dn_msh, import_dn_ani

        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "filter_glob",
                                            ))
        keywords["global_matrix"] = axis_conversion(from_forward=self.axis_forward,
                                                    from_up=self.axis_up,
                                                    ).to_4x4()

        filepath = keywords["filepath"]
        if filepath.lower().endswith(".msh"):
            msh_importer = import_dn_msh.load(context, **keywords)
            return {'FINISHED'} if msh_importer else {'CANCELLED'}

        global ani_importer
        ani_importer = import_dn_ani.load(context, filepath)
        if not ani_importer:
            return {'CANCELLED'}

        if not ani_importer.imported:
            bpy.ops.dialog.anim_chooser_box('INVOKE_DEFAULT')
        return {'FINISHED'}


def menu_func_import(self, context):
    self.layout.operator(ImportDragonNest.bl_idname,
                         text="Dragon Nest Model (.msh, .ani, .anim)")


classes = (
    ImportDragonNest,
    DN_AnimChooserBox,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
