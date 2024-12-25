import bpy
import bmesh
import os

from bpy_extras.image_utils import load_image
from bpy_extras import node_shader_utils
from mathutils import Matrix

from .types.msh import MSH
from .types.skn import SKN, MatPropType


def invalid_skn_type(self, context):
    self.layout.label(text='Invalid skn type')


def missing_skn(self, context):
    self.layout.label(text='SKN File not found')


def invalid_msh_type(self, context):
    self.layout.label(text='Invalid msh type')


def invalid_msh_version(self, context):
    self.layout.label(text='Invalid msh version')


def missing_append_bones(self, context):
    self.layout.label(text='Append armature does not have some bones')


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
            mat = bpy.data.materials.get(skn_mat.name)
            if not mat:
                mat = bpy.data.materials.new(name=skn_mat.name)
                mat_wrap = node_shader_utils.PrincipledBSDFWrapper(mat, is_readonly=False)

                for prop in skn_mat.properties:
                    if prop.type == MatPropType.TEXTURE:
                        tex = bpy.data.textures.get(prop.value) or bpy.data.textures.new(prop.value, type='IMAGE')
                        self.diffuse_textures.append(tex)

                        if tex.image:
                            continue

                        img = bpy.data.images.get(prop.value) or load_image(prop.value, options['directory'])
                        if not img:
                            continue

                        tex.image = img

                        if "Diffuse" in prop.name:
                            nodetex = mat_wrap.base_color_texture
                            nodetex.image = img
                            nodetex.texcoords = 'UV'

                            if img.depth in {32, 128}:
                                mat.blend_method = 'HASHED'
                                add_transparent_node(mat.node_tree)

            self.materials.append(mat)

        self.imported = True

    def load_file(self, context, filename) -> bool:
        self.skn = SKN()
        self.skn.load_file(filename)

        if not self.skn.file_type.startswith("Eternity Engine Skin File"):
            context.window_manager.popup_menu(invalid_skn_type, title='Warning', icon='ERROR')
            return False

        return True

    def __init__(self):
        self.skn = None
        self.materials = []
        self.diffuse_textures = []
        self.imported = False


class MshImporter:

    def import_data(self, context, options):
        view_layer = context.view_layer
        collection = view_layer.active_layer_collection.collection

        append_armature = options.get("append_armature")
        global_matrix = options.get("global_matrix")

        if append_armature:
            arm_obj = append_armature
            arm = arm_obj.data

            bpy.ops.object.mode_set(mode='EDIT')

            has_missing_bones = False

            for msh_bone in self.msh.bones:
                if not arm.edit_bones.get(msh_bone.name):
                    has_missing_bones = True

            if has_missing_bones:
                context.window_manager.popup_menu(missing_append_bones, title="Warning", icon='ERROR')

        else:
            arm = bpy.data.armatures.new("bind")

            arm_obj = bpy.data.objects.new("obj", arm)
            arm_obj.show_in_front = True

            if global_matrix:
                arm_obj.matrix_world = global_matrix

            collection.objects.link(arm_obj)
            view_layer.objects.active = arm_obj

            bpy.ops.object.mode_set(mode='EDIT')

            # create bones
            for msh_bone in self.msh.bones:
                mat = Matrix(msh_bone.matrix.unpack()).transposed().inverted_safe()

                bone = arm.edit_bones.new(msh_bone.name)
                bone.head = (0, 0, 0)
                bone.tail = (0, 0, 1)
                bone.matrix = mat
                bone.dragon_nest.scale = mat.to_scale()

        # create meshes
        for msh_mesh in self.msh.meshes:
            bpy.ops.object.mode_set(mode='OBJECT')
            mesh = bpy.data.meshes.new(msh_mesh.name)

            mesh.from_pydata(msh_mesh.vertices, [], msh_mesh.faces)
            if bpy.app.version < (4, 1, 0):
                mesh.use_auto_smooth = True
            mesh.normals_split_custom_set_from_vertices(msh_mesh.normals)

            bm = bmesh.new()
            bm.from_mesh(mesh)
            bm.faces.ensure_lookup_table()

            for uvs in msh_mesh.uvs:
                uv_layer = bm.loops.layers.uv.new()

                for face in bm.faces:
                    for loop in face.loops:
                        vert_index = loop.vert.index
                        uv = uvs[vert_index]
                        loop[uv_layer].uv = (uv[0], 1 - uv[1])

            bm.to_mesh(mesh)
            mesh.validate()
            mesh.update()

            mesh_obj = bpy.data.objects.new(msh_mesh.name, mesh)
            mesh_obj.parent = arm_obj
            collection.objects.link(mesh_obj)

            if msh_mesh.rig_indices:
                modifier = mesh_obj.modifiers.new(type='ARMATURE', name="Armature")
                modifier.object = arm_obj

                rig_indices = msh_mesh.rig_indices
                rig_weights = msh_mesh.rig_weights

                vert_groups = [mesh_obj.vertex_groups.new(name=name) for name in msh_mesh.rig_names]
                for i in range(len(msh_mesh.vertices)):
                    for j in range(4):
                        if rig_weights[i][j] > 0.0:
                            vert_groups[rig_indices[i][j]].add([i], rig_weights[i][j], 'REPLACE')

            self.mesh_objects.append(mesh_obj)

        for obj in view_layer.objects:
            obj.select_set(obj == arm_obj)

        self.armature_object = arm_obj
        self.imported = True

    def load_file(self, context, filename) -> bool:
        self.msh = MSH()
        self.msh.load_file(filename)

        if not self.msh.file_type.startswith("Eternity Engine Mesh File"):
            context.window_manager.popup_menu(invalid_msh_type, title="Error", icon='ERROR')
            return False

        if self.msh.version not in range(10, 14):
            context.window_manager.popup_menu(invalid_msh_version, title="Error", icon='ERROR')
            return False

        return True

    def __init__(self):
        self.msh = None
        self.armature_object = None
        self.mesh_objects = []
        self.imported = False


def load(context, filepath, *, append_to_target, global_matrix=None):
    append_armature = None
    if append_to_target:
        append_armature = context.view_layer.objects.active
        if append_armature and type(append_armature.data) != bpy.types.Armature:
            append_armature = None

    directory = os.path.dirname(filepath)
    base_name = os.path.basename(filepath)[:-4]
    skn_path = os.path.join(directory, base_name + '.skn')

    msh_options = {
        "append_armature": append_armature,
        "global_matrix": global_matrix,
    }

    skn_options = {
        "directory": directory,
    }

    msh_importer = MshImporter()
    if msh_importer.load_file(context, filepath):
        msh_importer.import_data(context, msh_options)

    if not msh_importer.imported:
        return None

    skn_importer = SknImporter()
    if os.path.isfile(skn_path):
        if skn_importer.load_file(context, skn_path):
            skn_importer.import_data(context, skn_options)

            for mesh_idx, mesh_obj in enumerate(msh_importer.mesh_objects):
                mesh_obj.data.materials.append(skn_importer.materials[mesh_idx])

    else:
        context.window_manager.popup_menu(missing_skn, title="Warning", icon='ERROR')

    return msh_importer
