import bpy
import os

from bpy_extras.image_utils import load_image
from bpy_extras import node_shader_utils

from ..gui import gui
from .msh_importer import MshImporter
from ..types.skn import SKN, MatPropType


def add_transparent_node(node_tree):
    nodes = node_tree.nodes

    output_node = nodes.get('Material Output')
    bsdf_node = nodes.get('Principled BSDF')
    texture_node = nodes.get(bpy.app.translations.pgettext('Image Texture'))

    mix_shader_node = nodes.new('ShaderNodeMixShader')
    transparent_node = nodes.new('ShaderNodeBsdfTransparent')

    node_tree.links.new(texture_node.outputs[1], mix_shader_node.inputs[0])
    node_tree.links.new(transparent_node.outputs[0], mix_shader_node.inputs[1])
    node_tree.links.new(bsdf_node.outputs[0], mix_shader_node.inputs[2])

    node_tree.links.new(mix_shader_node.outputs[0], output_node.inputs[0])


class SknImporter:

    def import_data(self, context, options):
        for skn_mat in self.skn.materials:
            material = bpy.data.materials.get(skn_mat.name)
            if not material:
                material = bpy.data.materials.new(name=skn_mat.name)
                mat_wrap = node_shader_utils.PrincipledBSDFWrapper(material, is_readonly=False)
                mat_wrap.roughness = 1.0

                material.dragon_nest.effect = skn_mat.effect
                material.dragon_nest.alpha_value = skn_mat.alpha
                material.dragon_nest.enable_alpha_blend = skn_mat.alpha_blend
                material.dragon_nest.enable_colors = False

                for prop in skn_mat.properties:
                    if prop.type == MatPropType.TEXTURE and prop.value[-4:].lower() == ".dds":
                        texture = bpy.data.textures.get(prop.value) or bpy.data.textures.new(prop.value, type='IMAGE')
                        texture.image = bpy.data.images.get(prop.value) or load_image(prop.value, options['directory'])

                    if prop.name == "g_MaterialAmbient":
                        material.dragon_nest.enable_colors = True
                        material.dragon_nest.material_ambient = prop.value.unpack()

                    elif prop.name == "g_MaterialDiffuse":
                        material.dragon_nest.material_diffuse = prop.value.unpack()

                    elif prop.name == "g_EmissivePower":
                        material.dragon_nest.emissive_power = prop.value

                    elif prop.name == "g_EmissivePowerRange":
                        material.dragon_nest.emissive_power_range = prop.value

                    elif prop.name == "g_EmissiveAniSpeed":
                        material.dragon_nest.emissive_ani_speed = prop.value

                    elif prop.name == "g_DiffuseTex":
                        material.dragon_nest.diffuse_texture = prop.value

                        node_texture = mat_wrap.base_color_texture
                        node_texture.image = texture.image
                        node_texture.texcoords = 'UV'

                        material.blend_method = 'HASHED'
                        add_transparent_node(material.node_tree)

                    elif prop.name == "g_EmissiveTex":
                        material.dragon_nest.emissive_texture = prop.value

                        node_emission_texture = mat_wrap.emission_color_texture
                        node_emission_texture.image = texture.image
                        node_emission_texture.texcoords = 'UV'

                        mat_wrap.emission_strength = 1.0

                    elif prop.name == "g_MaskTex":
                        material.dragon_nest.mask_texture = prop.value

                    else:
                        extra_prop = material.dragon_nest.extra.add()
                        extra_prop.name = prop.name
                        extra_prop.type = str(prop.type)

                        if prop.type == MatPropType.INT:
                            extra_prop.integer_value = prop.value
                        elif prop.type == MatPropType.FLOAT:
                            extra_prop.float_value = prop.value
                        elif prop.type == MatPropType.VECTOR:
                            extra_prop.vector_value = prop.value.unpack()
                        elif prop.type == MatPropType.TEXTURE:
                            extra_prop.string_value = prop.value

            self.materials.append(material)

        self.imported = True

    def load_file(self, context, filename) -> bool:
        self.skn = SKN()
        self.skn.load_file(filename)

        if not self.skn.file_type.startswith("Eternity Engine Skin File"):
            context.window_manager.popup_menu(gui.invalid_skn_type, title='Warning', icon='ERROR')
            return False

        return True

    def __init__(self):
        self.skn = None
        self.materials = []
        self.imported = False
        self.msh_importer = None


def load(context, filepath, *, append_to_target, global_matrix=None):
    append_armature = None
    if append_to_target:
        append_armature = context.view_layer.objects.active
        if append_armature and type(append_armature.data) != bpy.types.Armature:
            append_armature = None

    directory = os.path.dirname(filepath)

    skn_options = {
        "directory": directory,
    }

    skn_importer = SknImporter()
    if skn_importer.load_file(context, filepath):
        skn_importer.import_data(context, skn_options)

    if not skn_importer.imported:
        return None

    msh_path = os.path.join(directory, skn_importer.skn.name)

    if not os.path.isfile(msh_path):
        context.window_manager.popup_menu(gui.missing_msh, title="Warning", icon='ERROR')
        return skn_importer

    msh_options = {
        "append_armature": append_armature,
    }

    msh_importer = MshImporter()
    if msh_importer.load_file(context, msh_path):
        msh_importer.import_data(context, msh_options)

    if msh_importer.imported:
        for mesh_idx, mesh_obj in enumerate(msh_importer.mesh_objects):
            mesh_obj.data.materials.append(skn_importer.materials[mesh_idx])

    skn_importer.msh_importer = msh_importer
    return skn_importer
