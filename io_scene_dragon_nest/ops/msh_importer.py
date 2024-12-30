import bpy
import bmesh

from mathutils import Matrix

from ..gui import gui
from ..types.msh import MSH


def set_parent_bone(obj, arm_obj, bone_name):
    obj.parent = arm_obj

    bone = arm_obj.data.bones.get(bone_name)
    if not bone:
        return

    obj.parent_bone = bone_name
    obj.parent_type = 'BONE'
    obj.matrix_parent_inverse = Matrix.Translation((0, -bone.length, 0))


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

            # create bones
            for msh_bone in self.msh.bones:
                if arm.edit_bones.get(msh_bone.name):
                    continue

                mat = Matrix(msh_bone.matrix.unpack()).transposed().inverted_safe()

                bone = arm.edit_bones.new(msh_bone.name)
                bone.head = (0, 0, 0)
                bone.tail = (0, 0, 1)
                bone.matrix = mat
                bone.dragon_nest.scale = mat.to_scale()

        else:
            arm = bpy.data.armatures.new("Scene Root")

            arm_obj = bpy.data.objects.new("Scene Root", arm)
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

        # create dummies
        for msh_dummy in self.msh.dummies:
            dummy_obj = bpy.data.objects.new(msh_dummy.name, None)
            collection.objects.link(dummy_obj)

            if self.msh.version > 12:
                matrix = Matrix(msh_dummy.transformation.unpack()).transposed()

            else:
                matrix = Matrix.Translation(msh_dummy.transformation.unpack())

                if dummy_obj.name[0] == "L":
                    dummy_obj.name = dummy_obj.name[1:]

            dummy_obj.matrix_local = matrix
            set_parent_bone(dummy_obj, arm_obj, msh_dummy.parent_name)

            self.dummies_objects.append(dummy_obj)

        for obj in view_layer.objects:
            obj.select_set(obj == arm_obj)

        self.armature_object = arm_obj
        self.imported = True

    def load_file(self, context, filename) -> bool:
        self.msh = MSH()
        self.msh.load_file(filename)

        if not self.msh.file_type.startswith("Eternity Engine Mesh File"):
            context.window_manager.popup_menu(gui.invalid_msh_type, title="Error", icon='ERROR')
            return False

        return True

    def __init__(self):
        self.msh = None
        self.armature_object = None
        self.mesh_objects = []
        self.dummies_objects = []
        self.imported = False


def load(context, filepath, *, append_to_target, global_matrix=None):
    append_armature = None
    if append_to_target:
        append_armature = context.view_layer.objects.active
        if append_armature and type(append_armature.data) != bpy.types.Armature:
            append_armature = None

    msh_options = {
        "append_armature": append_armature,
        "global_matrix": global_matrix,
    }

    msh_importer = MshImporter()
    if msh_importer.load_file(context, filepath):
        msh_importer.import_data(context, msh_options)

    if not msh_importer.imported:
        return None

    return msh_importer
