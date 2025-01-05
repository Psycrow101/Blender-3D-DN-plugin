import bpy
import bmesh

from math import radians
from mathutils import Euler, Matrix

from .common import oriented_matrix, translation_matrix, rotation_matrix, scale_matrix
from ..gui import gui
from ..types.msh import MSH, CollisionType


class MshImporter:

    def import_data(self, context, options):
        view_layer = context.view_layer
        collection = view_layer.active_layer_collection.collection

        append_armature = options.get("append_armature")

        if append_armature:
            arm_obj = append_armature
            arm = arm_obj.data

            bone_matrices = {}

            # create bones
            bpy.ops.object.mode_set(mode='EDIT')
            for msh_bone in self.msh.bones:
                if arm.edit_bones.get(msh_bone.name):
                    continue

                mat = oriented_matrix(Matrix(msh_bone.matrix.unpack()).transposed().inverted_safe())

                bone = arm.edit_bones.new(msh_bone.name)
                bone.head = (0, 0, 0)
                bone.tail = (0, 0, 1)
                bone.matrix = mat

                bone_matrices[bone.name] = mat

            # apply custom scale
            bpy.ops.object.mode_set(mode='OBJECT')
            for bone_name, mat in bone_matrices.items():
                arm.bones[bone_name].dragon_nest.scale = mat.to_scale()

        else:
            arm = bpy.data.armatures.new("Scene Root")

            arm_obj = bpy.data.objects.new("Scene Root", arm)
            arm_obj.dragon_nest.type = 'OBJ'
            arm_obj.dragon_nest.bbox_min = (self.msh.bb_min.x, self.msh.bb_min.z, self.msh.bb_min.y)
            arm_obj.dragon_nest.bbox_max = (self.msh.bb_max.x, self.msh.bb_max.z, self.msh.bb_max.y)
            arm_obj.show_in_front = True

            collection.objects.link(arm_obj)
            view_layer.objects.active = arm_obj

            bone_matrices = {}

            # create bones
            bpy.ops.object.mode_set(mode='EDIT')
            for msh_bone in self.msh.bones:
                mat = oriented_matrix(Matrix(msh_bone.matrix.unpack()).transposed().inverted_safe())

                bone = arm.edit_bones.new(msh_bone.name)
                bone.head = (0, 0, 0)
                bone.tail = (0, 0, 1)
                bone.matrix = mat

                bone_matrices[bone.name] = mat

            # apply custom scale
            bpy.ops.object.mode_set(mode='OBJECT')
            for bone_name, mat in bone_matrices.items():
                arm.bones[bone_name].dragon_nest.scale = mat.to_scale()

        # create meshes
        for msh_mesh in self.msh.meshes:
            mesh = bpy.data.meshes.new(msh_mesh.name)

            vertices = tuple((v[0], v[2], v[1]) for v in msh_mesh.vertices)
            faces = tuple((f[0], f[2], f[1]) for f in msh_mesh.faces)
            normals = tuple((n[0], n[2], n[1]) for n in msh_mesh.normals)

            mesh.from_pydata(vertices, [], faces)
            if bpy.app.version < (4, 1, 0):
                mesh.use_auto_smooth = True
            mesh.normals_split_custom_set_from_vertices(normals)

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
            mesh_obj.dragon_nest.type = 'OBJ'
            mesh_obj.dragon_nest.parent_name = msh_mesh.parent_name
            mesh_obj.dragon_nest.use_tristrip = msh_mesh.use_tristrip
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
            dummy_obj.dragon_nest.type = 'OBJ'
            collection.objects.link(dummy_obj)

            if self.msh.version > 12:
                matrix = oriented_matrix(Matrix(msh_dummy.transformation.unpack()).transposed())
            else:
                location = msh_dummy.transformation
                matrix = translation_matrix((location.x, location.z, location.y))

            dummy_obj.matrix_local = matrix
            dummy_obj.parent = arm_obj
            dummy_obj.dragon_nest.parent_name = msh_dummy.parent_name

            self.dummy_objects.append(dummy_obj)

        # create collisions
        if self.msh.collisions:
            col_collection = bpy.data.collections.new("DN Collisions")
            collection.children.link(col_collection)

            for idx, msh_collision in enumerate(self.msh.collisions):
                primitive = msh_collision.primitive

                if self.msh.version > 10:
                    col_name = msh_collision.name
                else:
                    col_name = "Collision %d" % idx

                if msh_collision.type == CollisionType.BOX:
                    loc_mat = translation_matrix(primitive.location.unpack())
                    rot_mat = Matrix(primitive.axis.unpack()).transposed().to_4x4()
                    scl_mat = scale_matrix(primitive.extent.unpack())

                    col_obj = bpy.data.objects.new(col_name, None)
                    col_obj.matrix_local = oriented_matrix(loc_mat @ rot_mat @ scl_mat)

                elif msh_collision.type == CollisionType.SPHERE:
                    col_obj = bpy.data.objects.new(col_name, None)
                    col_obj.location = (primitive.location.x, primitive.location.z, primitive.location.y)
                    col_obj.scale = (primitive.radius,) * 3

                elif msh_collision.type == CollisionType.CAPSULE:
                    rot = primitive.rotation

                    loc_mat = translation_matrix(primitive.location.unpack())
                    rot_mat = rotation_matrix(Euler((radians(rot.x), radians(rot.y), radians(rot.z))))
                    scl_mat = scale_matrix((primitive.radius,) * 3)

                    col_obj = bpy.data.objects.new(col_name, None)
                    col_obj.matrix_local = oriented_matrix(loc_mat @ rot_mat @ scl_mat)

                elif msh_collision.type == CollisionType.TRIANGLE_LIST:
                    vertices, faces = [], []
                    vertex_idx = 0

                    for triangle in primitive.triangles:
                        v1 = (triangle.location.x, triangle.location.z, triangle.location.y)
                        v2 = (v1[0] + triangle.edge_a.x, v1[1] + triangle.edge_a.z, v1[2] + triangle.edge_a.y)
                        v3 = (v1[0] + triangle.edge_b.x, v1[1] + triangle.edge_b.z, v1[2] + triangle.edge_b.y)
                        vertices.extend((v1, v2, v3))
                        faces.append((vertex_idx, vertex_idx + 2, vertex_idx + 1))
                        vertex_idx += 3

                    col_data = bpy.data.meshes.new(col_name)
                    col_data.from_pydata(vertices, [], faces)

                    col_obj = bpy.data.objects.new(col_name, col_data)

                else:
                    col_obj = bpy.data.objects.new(col_name, None)

                col_obj.dragon_nest.type = 'COL'
                col_obj.dragon_nest.collision.type = str(msh_collision.type)
                col_obj.parent = arm_obj
                col_collection.objects.link(col_obj)
                col_obj.hide_set(True)

                self.collision_objects.append(col_obj)

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
        self.dummy_objects = []
        self.collision_objects = []
        self.imported = False


def load(context, filepath, *, append_to_target, global_matrix=None):
    append_armature = None
    if append_to_target:
        append_armature = context.view_layer.objects.active
        if append_armature and type(append_armature.data) != bpy.types.Armature:
            append_armature = None

    msh_options = {
        "append_armature": append_armature,
    }

    msh_importer = MshImporter()
    if msh_importer.load_file(context, filepath):
        msh_importer.import_data(context, msh_options)

    if not msh_importer.imported:
        return None

    return msh_importer
