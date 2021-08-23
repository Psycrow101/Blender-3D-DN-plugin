import bpy
from bpy.props import (
        BoolProperty,
        StringProperty,
        CollectionProperty,
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
    "version": (0, 1, 0),
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


class DN_AnimList(bpy.types.PropertyGroup):
    anim_name: StringProperty(name="DN Anim Name", options={'HIDDEN'})


class DN_AnimChooserBox(bpy.types.Operator):
    bl_idname = "dialog.anim_chooser_box"
    bl_label = "Choose animation for import"
    bl_options = {'REGISTER'}

    filepath: StringProperty(options={'HIDDEN'})

    def anim_enum_callback(self, context):
        items = []

        armature_obj = context.view_layer.objects.active
        if armature_obj:
            for i, n in enumerate(armature_obj.dn_anim_list):
                anim_name = n.anim_name.encode('ascii', errors='ignore').decode()
                items.append((str(i), anim_name, '', i))

        return items

    anim_list: EnumProperty(items=anim_enum_callback, name='Animation Name')

    def execute(self, context):
        from . import import_dn_ani
        if not self.anim_list:
            return {'CANCELLED'}
        anim_id = int(self.anim_list) - 1
        return import_dn_ani.load_anim(context, self.filepath, anim_id)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


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

        if keywords["filepath"].lower().endswith(".msh"):
            return import_dn_msh.load(context, **keywords)

        return import_dn_ani.load(context, **keywords)


def menu_func_import(self, context):
    self.layout.operator(ImportDragonNest.bl_idname,
                         text="Dragon Nest Model (.msh, .ani, .anim)")


classes = (
    ImportDragonNest,
    DN_AnimList,
    DN_AnimChooserBox,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Object.dn_anim_list = CollectionProperty(type=DN_AnimList, options={'HIDDEN'})
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
