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
