import bpy


class DN_EditBoneProps(bpy.types.PropertyGroup):

    scale : bpy.props.FloatVectorProperty(
        size = 3,
        default = (0.0, 0.0, 0.0),
    )

    def register():
        bpy.types.EditBone.dragon_nest = bpy.props.PointerProperty(type=DN_EditBoneProps)
