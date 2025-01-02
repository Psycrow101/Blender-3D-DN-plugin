import bpy


class DN_CollisionObjectProps(bpy.types.PropertyGroup):

    def type_changed(self, context):
        obj = self.id_data
        settings = obj.dragon_nest.collision

        if settings.type == '0':
            obj.empty_display_type = 'CUBE'

        elif settings.type in ('1', '2'):
            obj.empty_display_type = 'SPHERE'

    type: bpy.props.EnumProperty(
        name = "Type",
        items = (
            ('0', 'Box', 'Box'),
            ('1', 'Sphere', 'Sphere'),
            ('2', 'Capsule', 'Capsule'),
            ('3', 'Mesh', 'Mesh'),
        ),
        update = type_changed
    )

class DN_ObjectProps(bpy.types.PropertyGroup):

    type: bpy.props.EnumProperty(
        name = "Type",
        items = (
            ('OBJ', 'Object', 'Object is a mesh, scene root or dummy'),
            ('COL', 'Collision Object', 'Object is a collision object'),
        )
    )

    collision: bpy.props.PointerProperty(type=DN_CollisionObjectProps)

    def register():
        bpy.types.Object.dragon_nest = bpy.props.PointerProperty(type=DN_ObjectProps)


class DN_MaterialProps(bpy.types.PropertyGroup):

    def alpha_value_changed(self, context):
        material = self.id_data
        settings = material.dragon_nest

        if material.use_nodes:
            bsdf_node = material.node_tree.nodes.get('Principled BSDF')
            if bsdf_node:
                bsdf_node.inputs['Alpha'].default_value = settings.alpha_value

    def material_diffuse_changed(self, context):
        material = self.id_data
        settings = material.dragon_nest

        if material.use_nodes:
            bsdf_node = material.node_tree.nodes.get('Principled BSDF')
            if bsdf_node:
                bsdf_node.inputs['Base Color'].default_value = settings.material_diffuse

    effect: bpy.props.StringProperty(
        name = "Effect"
    )

    alpha_value: bpy.props.FloatProperty(
        name = "Alpha Value",
        min = 0,
        max = 1,
        update = alpha_value_changed
    )

    enable_alpha_blend: bpy.props.BoolProperty(
        name = "Enable Alpha Blend"
    )

    enable_colors: bpy.props.BoolProperty(
        name = "Enable Colors"
    )

    material_diffuse: bpy.props.FloatVectorProperty(
        name = "Material Diffuse",
        size = 4,
        subtype = 'COLOR',
        default = [0.68, 0.68, 0.68, 1.0],
        update = material_diffuse_changed
    )

    material_ambient: bpy.props.FloatVectorProperty(
        name = "Material Ambient",
        size = 4,
        subtype = 'COLOR',
        default = [0.68, 0.68, 0.68, 1.0]
    )

    emissive_power: bpy.props.FloatProperty(
        name = "Emissive Power"
    )

    emissive_power_range: bpy.props.FloatProperty(
        name = "Emissive Power Range"
    )

    emissive_ani_speed: bpy.props.FloatProperty(
        name = "Emissive Animation Speed"
    )

    diffuse_texture: bpy.props.StringProperty(
        name = "Diffuse Texture"
    )

    emissive_texture: bpy.props.StringProperty(
        name = "Emissive Texture"
    )

    mask_texture: bpy.props.StringProperty(
        name = "Mask Texture"
    )

    def register():
        bpy.types.Material.dragon_nest = bpy.props.PointerProperty(type=DN_MaterialProps)


class DN_EditBoneProps(bpy.types.PropertyGroup):

    scale: bpy.props.FloatVectorProperty(
        size = 3,
        default = (0.0, 0.0, 0.0),
    )

    def register():
        bpy.types.EditBone.dragon_nest = bpy.props.PointerProperty(type=DN_EditBoneProps)
