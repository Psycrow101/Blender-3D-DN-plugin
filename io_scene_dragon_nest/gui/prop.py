import bpy
import gpu

from gpu_extras.batch import batch_for_shader
from mathutils import Matrix

BOX_INDICES = (
    (0, 1), (1, 3), (3, 2), (2, 0),
    (2, 3), (3, 7), (7, 6), (6, 2),
    (6, 7), (7, 5), (5, 4), (4, 6),
    (4, 5), (5, 1), (1, 0), (0, 4),
    (2, 6), (6, 4), (4, 0), (0, 2),
    (7, 3), (3, 1), (1, 5), (5, 7),
)


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

    def parent_name_changed(self, context):
        obj = self.id_data
        settings = obj.dragon_nest

        arm_obj = obj.parent
        if not arm_obj or arm_obj.type != 'ARMATURE':
            return

        if obj.type == 'EMPTY':
            bone = arm_obj.data.bones.get(settings.parent_name)
            if bone:
                obj.parent_bone = bone.name
                obj.parent_type = 'BONE'
                obj.matrix_parent_inverse = Matrix.Translation((0, -bone.length, 0))

    def parent_name_search_func(props, context, edit_text):
        names = ["Scene Root"]

        arm_obj = context.object.parent
        if arm_obj and arm_obj.type == 'ARMATURE':
            names += [bone.name for bone in arm_obj.data.bones]

        return names

    type: bpy.props.EnumProperty(
        name = "Type",
        items = (
            ('OBJ', 'Object', 'Object is a mesh, scene root or dummy'),
            ('COL', 'Collision Object', 'Object is a collision object'),
            ('NONE', 'None', 'Do not export object'),
        )
    )

     # NOTE: bpy.props.StringProperty supports a search argument since version 3.3
    if bpy.app.version < (3, 3, 0):
        parent_name: bpy.props.StringProperty(
            name = "Parent Name",
            update = parent_name_changed
        )
    else:
        parent_name: bpy.props.StringProperty(
            name = "Parent Name",
            update = parent_name_changed,
            search = parent_name_search_func
        )

    collision: bpy.props.PointerProperty(type=DN_CollisionObjectProps)

    show_bbox: bpy.props.BoolProperty(
        name = "Show BBox"
    )

    bbox_min: bpy.props.FloatVectorProperty(
        name = "BBox Min",
        size = 3,
        default = [-1.0, -1.0, -1.0]
    )

    bbox_max: bpy.props.FloatVectorProperty(
        name = "BBox Max",
        size = 3,
        default = [1.0, 1.0, 1.0]
    )

    def draw_bbox(context):
        obj = context.object
        if not obj:
            return

        settings = obj.dragon_nest
        if settings.type == 'OBJ' and obj.type == 'ARMATURE' and settings.show_bbox:
            matrix_world = obj.matrix_world
            bbox_min = settings.bbox_min
            bbox_max = settings.bbox_max

            coords = (
                (matrix_world @ Matrix.Translation((bbox_min[0], bbox_min[1], bbox_min[2]))).to_translation(),
                (matrix_world @ Matrix.Translation((bbox_min[0], bbox_min[1], bbox_max[2]))).to_translation(),
                (matrix_world @ Matrix.Translation((bbox_min[0], bbox_max[1], bbox_min[2]))).to_translation(),
                (matrix_world @ Matrix.Translation((bbox_min[0], bbox_max[1], bbox_max[2]))).to_translation(),
                (matrix_world @ Matrix.Translation((bbox_max[0], bbox_min[1], bbox_min[2]))).to_translation(),
                (matrix_world @ Matrix.Translation((bbox_max[0], bbox_min[1], bbox_max[2]))).to_translation(),
                (matrix_world @ Matrix.Translation((bbox_max[0], bbox_max[1], bbox_min[2]))).to_translation(),
                (matrix_world @ Matrix.Translation((bbox_max[0], bbox_max[1], bbox_max[2]))).to_translation(),
            )

            shader = gpu.shader.from_builtin('UNIFORM_COLOR')
            batch = batch_for_shader(shader, 'LINES', {"pos": coords}, indices=BOX_INDICES)

            shader.uniform_float("color", (1, 1, 0, 1))
            batch.draw(shader)

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
