import bpy
from bpy.props import (
        BoolProperty,
        IntProperty,
        StringProperty,
        EnumProperty,
        )
from bpy_extras.io_utils import (
        ImportHelper,
        )


class DN_AnimChooserBox(bpy.types.Operator):
    bl_idname = "dialog.anim_chooser_box"
    bl_label = "Choose animation for import"
    bl_options = {'REGISTER'}

    def anim_enum_callback(self, context):
        global ani_imp

        if not ani_imp:
            return []

        items = [("0", "*All*", "", 0)]
        for i, name in enumerate(ani_imp.ani.names):
            items.append((str(i+1), name, "", i+1))

        return items

    anim_list: EnumProperty(items=anim_enum_callback, name="Animation Name")

    def execute(self, context):
        global ani_imp

        if not self.anim_list:
            return {'CANCELLED'}

        options = {
            "animation_id": int(self.anim_list) - 1,
        }

        ani_imp.import_data(context, options)
        imported = ani_imp.imported

        ani_imp = None
        return {'FINISHED'} if imported else {'CANCELLED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def cancel(self, context):
        global ani_imp
        ani_imp = None


class DN_Import(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.dragon_nest"
    bl_label = "Import Dragon Nest Model / Animation"
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = ".skn"
    filter_glob: StringProperty(default="*.skn;*.msh;*.ani;*.anim", options={'HIDDEN'})

    append_to_target: BoolProperty(
        name="Append to Target Armature",
        description="Attach the imported mesh to the selected armature",
        default=False,
    )

    def execute(self, context):
        keywords = self.as_keywords(ignore=("filter_glob",))

        filepath = keywords["filepath"]
        if filepath.lower().endswith(".skn"):
            from ..ops import skn_importer
            if not skn_importer.load(context, **keywords):
                return {'CANCELLED'}

        elif filepath.lower().endswith(".msh"):
            from ..ops import msh_importer
            if not msh_importer.load(context, **keywords):
                return {'CANCELLED'}

        else:
            from ..ops import ani_importer

            global ani_imp
            ani_imp = ani_importer.load(context, filepath)
            if not ani_imp:
                return {'CANCELLED'}

            if not ani_imp.imported:
                bpy.ops.dialog.anim_chooser_box('INVOKE_DEFAULT')

        return {'FINISHED'}


class DN_AddExtraPropItem(bpy.types.Operator):
    bl_label = "Add Item"
    bl_idname = "material.dragon_nest_add_extra_prop_item"

    def execute(self, context):
        material = context.material
        material.dragon_nest.extra.add()
        return {'FINISHED'}


class DN_RemoveExtraPropItem(bpy.types.Operator):
    bl_label = "Remove Item"
    bl_idname = "material.dragon_nest_remove_extra_prop_item"

    index: IntProperty()

    def execute(self, context):
        material = context.material
        material.dragon_nest.extra.remove(self.index)
        return {'FINISHED'}


def menu_func_import(self, context):
    self.layout.operator(DN_Import.bl_idname,
                         text="Dragon Nest Model (.skn, .msh, .ani, .anim)")
