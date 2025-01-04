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

EFFECT_NAMES = (
    'BG_Diffuse.fx', 'BG_DiffuseEmissive.fx', 'BG_DiffuseEmissiveSphericalMap.fx',
    'BG_DiffuseSpecSphericalMap.fx', 'BG_DiffuseSpecSphericalNormalScroll.fx',
    'BG_DiffuseSpecSphericalScroll.fx', 'BG_DiffuseSphericalMap.fx',
    'BG_Diffuse_IceBlending.fx', 'BG_Diffuse_SnowBlending.fx',
    'BG_EmissiveNormalScroll.fx', 'BG_Foliage.fx', 'BG_Hologram.fx',
    'BG_NormalSpecular.fx', 'BG_Tree.fx', 'BG_WaterObject.fx', 'CellularRim.fx',
    'DNToonEmissiveRim.fx', 'Default.fx', 'Diffuse.fx', 'DiffuseAvatar.fx',
    'DiffuseAvatarFace.fx', 'DiffuseAvatarFaceTatoo.fx',
    'DiffuseAvatarFaceTatoo_Head.fx', 'DiffuseCustomColor.fx',
    'DiffuseCustomColor_Hair.fx', 'DiffuseDistance.fx', 'DiffuseEmissive.fx',
    'DiffuseEmissiveCustomColor.fx', 'DiffuseEmissiveGhostFire.fx',
    'DiffuseEmissiveRim.fx', 'DiffuseEmissiveSphericalMap.fx',
    'DiffuseEmissiveSphericalMapParts.fx', 'DiffuseEmissiveSphericalMapSSD.fx',
    'DiffuseEmissiveSphericalMapSSDM.fx', 'DiffuseEmissiveUVScroll.fx',
    'DiffuseEmissiveUVScrollRim.fx', 'DiffuseEmissiveVolumeTex.fx',
    'DiffuseRimCloud.fx', 'DiffuseSpecularAvatar.fx', 'DiffuseSphericalMap.fx',
    'DiffuseUVScroll.fx', 'DiffuseUVScrollTiling.fx', 'DiffuseUVScrollTilingRim.fx',
    'DiffuseVolumeTex.fx', 'DiffuseVolumeTexHologram.fx', 'Flat.fx',
    'FlatUVScroll.fx', 'FlatUVScrollTiling.fx', 'Hologram.fx', 'LimLight.fx',
    'NormalEmissiveSpecular.fx', 'NormalEmissiveSpecularSphericalMapRim.fx',
    'NormalIridescent.fx', 'NormalSpecularReflect.fx', 'RimUVScroll.fx',
    'SkyBox.fx', 'SkyBoxAni.fx', 'SkyBoxAurora.fx', 'SkyBoxCloud.fx',
    'StandardFX11.fx', 'TextureSheetAnimation.fx'
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
                scale_matrix = Matrix.Identity(4)
                scale_matrix[0][0] = bone.dragon_nest.scale[0]
                scale_matrix[1][1] = bone.dragon_nest.scale[1]
                scale_matrix[2][2] = bone.dragon_nest.scale[2]

                obj.parent_bone = bone.name
                obj.parent_type = 'BONE'
                obj.matrix_parent_inverse = scale_matrix @ Matrix.Translation((0, -bone.length, 0))
            else:
                obj.parent_type = 'OBJECT'
                obj.matrix_parent_inverse = Matrix.Identity(4)

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

    use_tristrip: bpy.props.BoolProperty(
        name = "Use Triangle Strip",
        description="Use Triangle Strip instead of Triangle List",
        default = True
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

    def effect_search_func(props, context, edit_text):
        return EFFECT_NAMES

    def texture_search_func(props, context, edit_text):
        return [img.name for img in bpy.data.images]

    alpha_value: bpy.props.FloatProperty(
        name = "Alpha Value",
        min = 0,
        max = 1,
        default = 1,
        update = alpha_value_changed
    )

    enable_alpha_blend: bpy.props.BoolProperty(
        name = "Enable Alpha Blend"
    )

    enable_colors: bpy.props.BoolProperty(
        name = "Enable Colors",
        default = True
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

    # NOTE: bpy.props.StringProperty supports a search argument since version 3.3
    if bpy.app.version < (3, 3, 0):
        effect: bpy.props.StringProperty(
            name = "Effect",
            default = "Diffuse.fx"
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
    else:
        effect: bpy.props.StringProperty(
            name = "Effect",
            default = "Diffuse.fx",
            search = effect_search_func
        )

        diffuse_texture: bpy.props.StringProperty(
            name = "Diffuse Texture",
            search = texture_search_func
        )

        emissive_texture: bpy.props.StringProperty(
            name = "Emissive Texture",
            search = texture_search_func
        )

        mask_texture: bpy.props.StringProperty(
            name = "Mask Texture",
            search = texture_search_func
        )

    def register():
        bpy.types.Material.dragon_nest = bpy.props.PointerProperty(type=DN_MaterialProps)


class DN_BoneProps(bpy.types.PropertyGroup):

    scale: bpy.props.FloatVectorProperty(
        size = 3,
        default = (1.0, 1.0, 1.0),
    )

    def register():
        bpy.types.Bone.dragon_nest = bpy.props.PointerProperty(type=DN_BoneProps)
