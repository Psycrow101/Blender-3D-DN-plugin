import bmesh
import bpy

from math import degrees

from .common import unoriented_matrix, scale_matrix
from ..gui import gui
from ..types import common
from ..types.msh import MSH, Bone, Collision, Dummy, Mesh, CollisionType
from ..types.msh import PrimitiveBox, PrimitiveSphere, PrimitiveCapsule, PrimitiveTriangleList, PrimitiveTriangle


class MshExportException(Exception):
    pass


class MshExporter:

    @staticmethod
    def convert_to_mesh(context, obj):

        # Temporarily disable armature
        disabled_modifiers = []
        for modifier in obj.modifiers:
            if modifier.type == 'ARMATURE':
                modifier.show_viewport = False
                disabled_modifiers.append(modifier)

        depsgraph = context.evaluated_depsgraph_get()
        object_eval = obj.evaluated_get(depsgraph)
        mesh = object_eval.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)

        # Re enable disabled modifiers
        for modifier in disabled_modifiers:
            modifier.show_viewport = True

        return mesh

    @staticmethod
    def triangulate_mesh(mesh):
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()

    @staticmethod
    def export_dummy(context, obj, version) -> Dummy:
        parent_name = obj.dragon_nest.parent_name
        matrix = unoriented_matrix(obj.matrix_basis)

        if version > 12:
            matrix.transpose()
            transformation = common.Matrix4x4(
                common.Vector4D(*matrix[0]),
                common.Vector4D(*matrix[1]),
                common.Vector4D(*matrix[2]),
                common.Vector4D(*matrix[3]),
            )

            if not parent_name:
                parent_name = "Scene Root"

        else:
            translation = matrix.to_translation()
            transformation = common.Vector3D(*translation)

        return Dummy(obj.name, parent_name, transformation)

    @staticmethod
    def export_collision(context, obj) -> Collision:
        collision = Collision()
        collision.name = obj.name
        collision.type = int(obj.dragon_nest.collision.type)

        matrix = unoriented_matrix(obj.matrix_local)

        if collision.type == CollisionType.BOX:
            rotation_matrix = matrix.normalized().to_3x3().transposed()

            location = common.Vector3D(*matrix.to_translation())
            axis = common.Matrix3x3(
                common.Vector3D(*rotation_matrix[0]),
                common.Vector3D(*rotation_matrix[1]),
                common.Vector3D(*rotation_matrix[2]),
            )
            extent = common.Vector3D(*matrix.to_scale())
            collision.primitive = PrimitiveBox(location, axis, extent)

        elif collision.type == CollisionType.SPHERE:
            location = common.Vector3D(*matrix.to_translation())
            radius = max(matrix.to_scale())
            collision.primitive = PrimitiveSphere(location, radius)

        elif collision.type == CollisionType.CAPSULE:
            euler = matrix.to_euler()

            location = common.Vector3D(*matrix.to_translation())
            rotation = common.Vector3D(degrees(euler.x), degrees(euler.y), degrees(euler.z))
            radius = max(matrix.to_scale())
            collision.primitive = PrimitiveCapsule(location, rotation, radius)

        elif collision.type == CollisionType.TRIANGLE_LIST:
            triangles = []

            if obj.type == "MESH":
                mesh = MshExporter.convert_to_mesh(context, obj)
                MshExporter.triangulate_mesh(mesh)
                mesh.transform(obj.matrix_local)

                for polygon in mesh.polygons:
                    co1 = mesh.vertices[polygon.vertices[0]].co
                    co2 = mesh.vertices[polygon.vertices[1]].co - co1
                    co3 = mesh.vertices[polygon.vertices[2]].co - co1

                    triangles.append(PrimitiveTriangle(
                        common.Vector3D(co1.x, co1.z, co1.y),
                        common.Vector3D(co3.x, co3.z, co3.y),
                        common.Vector3D(co2.x, co2.z, co2.y),
                    ))

            collision.primitive = PrimitiveTriangleList(triangles)

        return collision

    @staticmethod
    def export_mesh(context, obj, arm_obj) -> Mesh:
        msh_mesh = Mesh()
        msh_mesh.name = obj.name
        msh_mesh.parent_name = obj.dragon_nest.parent_name
        msh_mesh.use_tristrip = obj.dragon_nest.use_tristrip

        if not msh_mesh.parent_name:
            msh_mesh.parent_name = "Scene Root"

        mesh = MshExporter.convert_to_mesh(context, obj)
        MshExporter.triangulate_mesh(mesh)

        # Check for vertices once before exporting to report instanstly
        if len(mesh.vertices) > 0xFFFF:
            raise MshExportException(f"Too many vertices in mesh ({obj.name}): {len(mesh.vertices)}/65535")

        # NOTE: Mesh.calc_normals is no longer needed and has been removed
        if bpy.app.version < (4, 0, 0):
            mesh.calc_normals()

        # NOTE: Mesh.calc_normals_split is no longer needed and has been removed
        if bpy.app.version < (4, 1, 0):
            mesh.calc_normals_split()

        for _ in range(len(mesh.uv_layers)):
            msh_mesh.uvs.append([])

        vertex_group_indices = {}
        for idx, vg in enumerate(obj.vertex_groups):
            if vg.name in arm_obj.data.bones:
                vertex_group_indices[idx] = len(msh_mesh.rig_names)
                msh_mesh.rig_names.append(vg.name)

        vertices_indices = {}

        for polygon in mesh.polygons:
            face = []

            for loop_index in polygon.loop_indices:
                loop = mesh.loops[loop_index]
                vertex = mesh.vertices[loop.vertex_index]
                uvs = [tuple(uv_layer.data[loop_index].uv) for uv_layer in mesh.uv_layers]
                normal = loop.normal

                key = (loop.vertex_index,
                       tuple(round(n / 0.3) * 0.3 for n in normal),
                       tuple(uv for uv in uvs))

                if key not in vertices_indices:
                    vertex_index = len(msh_mesh.vertices)
                    msh_mesh.vertices.append((vertex.co.x, vertex.co.z, vertex.co.y))
                    msh_mesh.normals.append((normal.x, normal.z, normal.y))

                    for uv_idx, uv in enumerate(uvs):
                        msh_mesh.uvs[uv_idx].append((uv[0], 1 - uv[1]))

                    if vertex_group_indices:
                        rig_indices, rig_weights = [], []
                        for group in vertex.groups:
                            # Only upto 4 vertices per group are supported
                            if len(rig_indices) >= 4:
                                break

                            if group.weight > 0:
                                rig_indices.append(vertex_group_indices[group.group])
                                rig_weights.append(group.weight)

                        while len(rig_indices) < 4:
                            rig_indices.append(0)
                            rig_weights.append(0)

                        msh_mesh.rig_indices.append(rig_indices)
                        msh_mesh.rig_weights.append(rig_weights)

                    face.append(vertex_index)
                    vertices_indices[key] = vertex_index

                else:
                    face.append(vertices_indices[key])

            msh_mesh.faces.append((face[0], face[2], face[1]))

        # Check vertices count again since duplicate vertices may have increased
        # vertices count above the limit
        if len(vertices_indices) > 0xFFFF:
            raise MshExportException(f"Too many vertices in mesh ({obj.name}): {len(vertices_indices)}/65535")

        return msh_mesh

    def export_data(self, context, options):
        arm_obj, version = options["armature_object"], options["version"]

        self.msh.file_type = "Eternity Engine Mesh File 0.%d" % version
        self.msh.version = version

        bbox_min = arm_obj.dragon_nest.bbox_min
        bbox_max = arm_obj.dragon_nest.bbox_max

        self.msh.bb_min = common.Vector3D(bbox_min[0], bbox_min[2], bbox_min[1])
        self.msh.bb_max = common.Vector3D(bbox_max[0], bbox_max[2], bbox_max[1])

        for bone in arm_obj.data.bones:
            matrix = bone.matrix_local @ scale_matrix(bone.dragon_nest.scale)
            matrix = unoriented_matrix(matrix).inverted_safe().transposed()
            bone_matrix = common.Matrix4x4(
                common.Vector4D(*matrix[0]),
                common.Vector4D(*matrix[1]),
                common.Vector4D(*matrix[2]),
                common.Vector4D(*matrix[3]),
            )

            msh_bone = Bone(bone.name, bone_matrix)
            self.msh.bones.append(msh_bone)

        for obj in arm_obj.children:
            if obj.dragon_nest.type == 'OBJ':

                # mesh
                if obj.type == 'MESH':
                    mesh = MshExporter.export_mesh(context, obj, arm_obj)
                    self.msh.meshes.append(mesh)
                    self.mesh_objects.append(obj)

                # dummy
                elif obj.type == 'EMPTY':
                    dummy = MshExporter.export_dummy(context, obj, version)
                    self.msh.dummies.append(dummy)

            # collision
            elif obj.dragon_nest.type == 'COL':
                collision = MshExporter.export_collision(context, obj)
                self.msh.collisions.append(collision)

    def __init__(self):
        self.msh = MSH()
        self.mesh_objects = []


def get_active_armature_object(context):
    arm_obj = context.object
    if not arm_obj:
        return

    if arm_obj.type == 'ARMATURE':
        return arm_obj

    arm_obj = arm_obj.parent
    if arm_obj and arm_obj.type == 'ARMATURE':
        return arm_obj


def save(context, filepath, options):
    arm_obj = get_active_armature_object(context)
    if not arm_obj:
        context.window_manager.popup_menu(gui.need_armature_to_export, title='Error', icon='ERROR')
        return

    msh_options = {
        "version": options["msh_version"],
        "armature_object": arm_obj,
    }

    msh_exporter = MshExporter()
    msh_exporter.export_data(context, msh_options)
    msh_exporter.msh.save_file(filepath)

    return msh_exporter
