import bpy


class DN_CollisionObjectProps(bpy.types.PropertyGroup):

    def type_changed(self, context):
        obj = self.id_data
        settings = obj.dragon_nest.collision

        if settings.type == '0':
            obj.empty_display_type = 'CUBE'

        elif settings.type in ('1', '2'):
            obj.empty_display_type = 'SPHERE'

    type : bpy.props.EnumProperty(
        items = (
            ('0', 'Box', 'Box'),
            ('1', 'Sphere', 'Sphere'),
            ('2', 'Capsule', 'Capsule'),
            ('3', 'Mesh', 'Mesh'),
        ),
        update = type_changed
    )

class DN_ObjectProps(bpy.types.PropertyGroup):

    type : bpy.props.EnumProperty(
        items = (
            ('OBJ', 'Object', 'Object is a mesh, scene root or dummy'),
            ('COL', 'Collision Object', 'Object is a collision object'),
        )
    )

    collision : bpy.props.PointerProperty(type=DN_CollisionObjectProps)

    def register():
        bpy.types.Object.dragon_nest = bpy.props.PointerProperty(type=DN_ObjectProps)


class DN_EditBoneProps(bpy.types.PropertyGroup):

    scale : bpy.props.FloatVectorProperty(
        size = 3,
        default = (0.0, 0.0, 0.0),
    )

    def register():
        bpy.types.EditBone.dragon_nest = bpy.props.PointerProperty(type=DN_EditBoneProps)
