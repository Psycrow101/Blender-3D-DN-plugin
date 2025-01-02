import bpy


class OBJECT_PT_DNObjects(bpy.types.Panel):

    bl_idname      = "OBJECT_PT_DNObjects"
    bl_label       = "Dragon Nest"
    bl_space_type  = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context     = "object"

    def draw_obj_menu(self, context):
        layout = self.layout
        settings = context.object.dragon_nest

        layout.prop(settings, "type", text="Type")

        if settings.type == 'COL':
            self.draw_col_menu(context)

    def draw_col_menu(self, context):
        layout = self.layout
        settings = context.object.dragon_nest.collision

        box = layout.box()
        box.label(text="Collision")

        box.prop(settings, "type", text="Type")

    def draw(self, context):
        if not context.object.dragon_nest:
            return

        self.draw_obj_menu(context)


class MATERIAL_PT_DNMaterials(bpy.types.Panel):

    bl_idname      = "MATERIAL_PT_DNMaterials"
    bl_label       = "Dragon Nest"
    bl_space_type  = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context     = "material"

    def draw_material_menu(self, context):
        layout = self.layout
        settings = context.material.dragon_nest

        layout.prop(settings, "effect", text="Effect")
        layout.prop(settings, "alpha_value", text="Alpha Value")
        layout.prop(settings, "enable_alpha_blend", text="Enable Alpha Blend")

        box = layout.box()
        box.label(text="Textures")

        box.prop(settings, "diffuse_texture", text="Diffuse")
        box.prop(settings, "emissive_texture", text="Emissive")
        box.prop(settings, "mask_texture", text="Mask")

        box = layout.box()
        box.prop(settings, "enable_colors", text="Colors")
        if settings.enable_colors:
            box.prop(settings, "material_diffuse", text="Material Diffuse")
            box.prop(settings, "material_ambient", text="Material Ambient")

        if settings.emissive_texture:
            box = layout.box()
            box.label(text="Emissive")

            box.prop(settings, "emissive_power", text="Emissive Power")
            box.prop(settings, "emissive_power_range", text="Emissive Power Range")
            box.prop(settings, "emissive_ani_speed", text="Emissive Animation Speed")

    def draw(self, context):
        if not context.material or not context.material.dragon_nest:
            return

        self.draw_material_menu(context)
