import bpy
import bmesh
import mathutils
import os
from . binary_reader import *
from bpy_extras.image_utils import load_image
from bpy_extras import node_shader_utils


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


def import_skn(context, file, directory):
    skn_type = read_string(file, 256)

    # todo: check version
    if 'Eternity Engine Skin File' not in skn_type:
        context.window_manager.popup_menu(invalid_skn_type, title='Warning', icon='ERROR')
        return None

    skn_data = {
        'materials': [],
        'diffuse_textures': []
    }

    # todo: check with msh name
    msh_name = read_string(file, 256)

    # todo: what is it (maybe version)
    file.seek(4, os.SEEK_CUR)

    materials_num = read_int(file)

    # todo
    file.seek(4, os.SEEK_CUR)
    file.seek(4, os.SEEK_CUR)

    file.seek(0x400)

    for _ in range(materials_num):
        mat_name = read_string(file, 256)

        mat = bpy.data.materials.get(mat_name)
        mat_wrap = None
        if not mat:
            mat = bpy.data.materials.new(name=mat_name)
            mat_wrap = node_shader_utils.PrincipledBSDFWrapper(mat, is_readonly=False)

        # todo: other material types
        mat_type = read_string(file, 256)

        file.seek(0x200, os.SEEK_CUR)

        prop_num = read_int(file)
        for _ in range(prop_num):
            prop_section_name = read_string(file, read_int(file))
            prop = read_int(file)

            # todo
            if prop == 1:
                read_float(file)

            # todo
            elif prop == 2:
                read_float(file, 4)

            # todo: test
            elif prop == 3:
                prop_name = read_string(file, read_int(file))

                # new material
                if mat_wrap:
                    tex = bpy.data.textures.get(prop_name)
                    if not tex:
                        tex = bpy.data.textures.new(prop_name, type='IMAGE')
                        image = load_image(prop_name, directory)
                    else:
                        image = bpy.data.images.get(prop_name)

                    if 'Diffuse' in prop_section_name:
                        if image:
                            tex.image = image

                            nodetex = mat_wrap.base_color_texture
                            nodetex.image = image
                            nodetex.texcoords = 'UV'

                            if image.depth in {32, 128}:
                                mat.blend_method = 'HASHED'
                                add_transparent_node(mat.node_tree)

                        skn_data['diffuse_textures'].append(tex)

        skn_data['materials'].append(mat)

    return skn_data


def import_msh(context, file, skn_data, msh_size, append_armature):
    msh_type = read_string(file, 256)
    if 'Eternity Engine Mesh File' not in msh_type:
        context.window_manager.popup_menu(invalid_msh_type, title="Error", icon='ERROR')
        return None

    msh_version = read_int(file)
    if msh_version not in (11, 12, 13):
        context.window_manager.popup_menu(invalid_msh_version, title="Error", icon='ERROR')
        return None

    view_layer = context.view_layer
    collection = view_layer.active_layer_collection.collection

    meshes_num = read_int(file)

    # todo
    read_int(file, 2)

    bb_max = read_float(file, 3)
    bb_min = read_float(file, 3)

    bones_num = read_int(file)

    # todo
    read_int(file)

    # todo
    others_num = read_int(file)

    file.seek(0x400)

    if append_armature:
        arm_obj = append_armature
        arm = arm_obj.data

        bpy.ops.object.mode_set(mode='EDIT')

        has_missing_bones = False

        for _ in range(bones_num):
            bone_name = read_string(file, 256)
            file.seek(64, os.SEEK_CUR)

            if not arm.edit_bones.get(bone_name):
                has_missing_bones = True

            if has_missing_bones:
                context.window_manager.popup_menu(missing_append_bones, title="Warning", icon='ERROR')


    else:
        # todo: rename
        arm = bpy.data.armatures.new('bind')

        # todo: rename
        arm_obj = bpy.data.objects.new('obj', arm)
        arm_obj.show_in_front = True

        collection.objects.link(arm_obj)
        view_layer.objects.active = arm_obj

        bpy.ops.object.mode_set(mode='EDIT')

        # create bones
        for _ in range(bones_num):
            bone_name = read_string(file, 256)
            bone = arm.edit_bones.new(bone_name)
            bone.head = (0, 0, 0)
            bone.tail = (0, 0, 1)
            bone.matrix = read_matrix(file).transposed().inverted_safe()

    # create meshes
    for m in range(meshes_num):
        # todo: create and bind scene by name
        try:
            scene_root = read_string(file, 256)
            mesh_name = read_string(file, 256)
        except UnicodeDecodeError:
            break

        verts_num = read_int(file)
        indices_num = read_int(file)

        # todo
        read_int(file) # 0x1

        render_mode = read_int(file)

        file.seek(0x200 - 0x10, os.SEEK_CUR)

        bpy.ops.object.mode_set(mode='OBJECT')
        mesh = bpy.data.meshes.new(mesh_name)

        # faces
        # todo: test
        faces = []
        if render_mode & 0x1:
            v1 = read_short(file)
            v2 = read_short(file)
            direct = -1
            for _ in range(indices_num - 2):
                v3 = read_short(file)
                direct = -direct
                if v1 != v2 and v2 != v3 and v1 != v3:
                    if direct > 0:
                        faces.append([v1, v2, v3])
                    else:
                        faces.append([v1, v3, v2])
                v1 = v2
                v2 = v3
        else:
            # todo: test
            for _ in range(int(indices_num / 3)):
                faces.append(read_short(file, 3))

        # vertices, normals, uvs
        vertices = [read_float(file, 3) for _ in range(verts_num)]
        normals = [read_float(file, 3) for _ in range(verts_num)]
        uvs = [[read_float(file), 1.0 - read_float(file)] for _ in range(verts_num)]

        mesh.from_pydata(vertices, [], faces)
        mesh.use_auto_smooth = True
        mesh.normals_split_custom_set_from_vertices(normals)

        bm = bmesh.new()
        bm.from_mesh(mesh)

        uv_layer = bm.loops.layers.uv.new()
        bm.faces.ensure_lookup_table()
        for f in range(len(faces)):
            for i in range(3):
                bm.faces[f].loops[i][uv_layer].uv = uvs[faces[f][i]]
        bm.to_mesh(mesh)

        mesh_obj = bpy.data.objects.new(mesh_name, mesh)
        collection.objects.link(mesh_obj)

        # todo: test render modes
        if render_mode & 0x10000:
            unk = [read_float(file) for _ in range(verts_num)]

        bones_indices = [read_short(file, 4) for _ in range(verts_num)]
        bones_weights = [read_float(file, 4) for _ in range(verts_num)]

        mesh_bones_num = read_int(file)
        bones_names = [read_string(file, 256) for _ in range(mesh_bones_num)]

        mesh_obj.parent = arm_obj
        modifier = mesh_obj.modifiers.new(type='ARMATURE', name='Armature')
        modifier.object = arm_obj

        if bones_indices:
            vert_groups = [mesh_obj.vertex_groups.new(name=g) for g in bones_names]
            for i in range(verts_num):
                for j in range(4):
                    if bones_weights[i][j] > 0.0:
                        vert_groups[bones_indices[i][j]].add([i], bones_weights[i][j], 'REPLACE')

        if skn_data:
            mesh.materials.append(skn_data['materials'][m])

        mesh.validate()
        mesh.update()

        # todo: fix unexpected file completion
        if m + 1 == meshes_num:
            break
        sign = file.read(4)
        while sign != b'Scen':
            if file.tell() >= msh_size:
                 break
            file.seek(-3, os.SEEK_CUR)
            sign = file.read(4)
        file.seek(-4, os.SEEK_CUR)

    for o in view_layer.objects:
        o.select_set(o == arm_obj)

    return arm_obj


def load(context, filepath, *, append_to_target, global_matrix=None):
    append_armature = None
    if append_to_target:
        append_armature = context.view_layer.objects.active
        if append_armature and type(append_armature.data) != bpy.types.Armature:
            append_armature = None

    directory = os.path.dirname(filepath)
    base_name = os.path.basename(filepath)[:-4]
    skn_path = os.path.join(directory, base_name + '.skn')

    skn = None
    if os.path.isfile(skn_path):
        with open(skn_path, 'rb') as fw:
            skn = import_skn(context, fw, directory)

    if not skn:
        context.window_manager.popup_menu(missing_skn, title="Warning", icon='ERROR')

    msh_size = os.path.getsize(filepath)
    with open(filepath, 'rb') as fw:
        arm_obj = import_msh(context, fw, skn, msh_size, append_armature)
        if arm_obj:
            arm_obj.matrix_world = global_matrix
            return {'FINISHED'}

    return {'CANCELLED'}
