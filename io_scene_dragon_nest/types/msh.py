from dataclasses import dataclass
from enum import IntEnum
from typing import List, Union

from .common import *
from .pyffi.utils import tristrip
from .reader import Reader
from .writer import Writer


class CollisionType(IntEnum):
    BOX           = 0
    SPHERE        = 1
    CAPSULE       = 2
    TRIANGLE_LIST = 3


@dataclass
class Bone:
    name: str
    matrix: Matrix4x4

    @classmethod
    def read(cls, reader: Reader):
        return cls(
            reader.read_string(256),
            Matrix4x4.read(reader),
        )

    def write(self, writer: Writer):
        writer.write_string(self.name, 256)
        self.matrix.write(writer)


@dataclass
class Dummy:
    name: str
    parent_name: str
    transformation: Union[Matrix4x4, Vector3D]

    @classmethod
    def read(cls, reader: Reader, version: int):
        if version > 12:
            name = reader.read_string(256)
            parent_name = reader.read_string(256)
            transformation = Matrix4x4.read(reader)

        else:
            name = reader.read_string(256)
            parent_name = ""
            transformation = Vector3D.read(reader)

            if name[0] == "L":
                name = name[1:]
                parent_name = reader.read_string(256)

        return cls(
            name,
            parent_name,
            transformation,
        )

    def write(self, writer: Writer, version: int):
        if version > 12:
            writer.write_string(self.name, 256)
            writer.write_string(self.parent_name, 256)
            self.transformation.write(writer)

        else:
            if self.parent_name:
                writer.write_string("L" + self.name, 256)
                self.transformation.write(writer)
                writer.write_string(self.parent_name, 256)
            else:
                writer.write_string(self.name, 256)
                self.transformation.write(writer)


class Mesh:

    @classmethod
    def read(cls, reader: Reader):
        self = cls()

        # header
        self.parent_name = reader.read_string(256)
        self.name = reader.read_string(256)

        verts_num, indices_num, uvs_num = reader.read_int(3)
        self.use_tristrip, use_rig, use_vert_color, _ = reader.read_bytes(4)

        reader.read_bytes(512 - 16)

        # faces
        if self.use_tristrip:
            v1, v2 = reader.read_ushort(2)
            direct = -1
            for _ in range(indices_num - 2):
                v3 = reader.read_ushort()
                direct *= -1
                if v1 != v2 and v2 != v3 and v1 != v3:
                    self.faces.append([v1, v2, v3] if direct > 0 else [v1, v3, v2])
                v1, v2 = v2, v3
        else:
            self.faces = [reader.read_ushort(3) for _ in range(indices_num // 3)]

        # vertices, normals, uvs
        self.vertices = [reader.read_float(3) for _ in range(verts_num)]
        self.normals = [reader.read_float(3) for _ in range(verts_num)]

        self.uvs = []
        for _ in range(uvs_num):
            self.uvs.append([reader.read_float(2) for _ in range(verts_num)])

        # vertex colors
        if use_vert_color:
            self.vertex_colors = [reader.read_float() for _ in range(verts_num)]

        # rig
        if use_rig:
            self.rig_indices = [reader.read_short(4) for _ in range(verts_num)]
            self.rig_weights = [reader.read_float(4) for _ in range(verts_num)]

            bones_num = reader.read_int()
            self.rig_names = [reader.read_string(256) for _ in range(bones_num)]

        return self

    def write(self, writer: Writer):
        writer.write_string(self.parent_name, 256)
        writer.write_string(self.name, 256)

        use_tristrip = self.use_tristrip
        use_rig = len(self.rig_indices) > 0
        use_vert_color = len(self.vertex_colors) > 0

        if use_tristrip:
            indices = tristrip.stripify(self.faces, True)[0]
        else:
            indices = []
            for f in self.faces:
                indices += f

        verts_num = len(self.vertices)
        indices_num = len(indices)
        uvs_num = len(self.uvs)

        writer.write_int((verts_num, indices_num, uvs_num))
        writer.write_int8((use_tristrip, use_rig, use_vert_color, 0))
        writer.write_bytes(b'\0' * (512 - 16))

        # faces
        writer.write_ushort(indices)

        # vertices
        for vec in self.vertices:
            writer.write_float(vec)

        # normals
        for vec in self.normals:
            writer.write_float(vec)

        # uvs
        for uv in self.uvs:
            for vec in uv:
                writer.write_float(vec)

        # vertex colors
        if use_vert_color:
            writer.write_float(self.vertex_colors)

        # rig
        if use_rig:
            for vec in self.rig_indices:
                writer.write_short(vec)

            for vec in self.rig_weights:
                writer.write_float(vec)

            writer.write_int(len(self.rig_names))
            for rig_name in self.rig_names:
                writer.write_string(rig_name, 256)

    def __init__(self):
        self.parent_name = ""
        self.name = ""
        self.use_tristrip = False
        self.faces = []
        self.vertices = []
        self.normals = []
        self.uvs = []
        self.vertex_colors = []
        self.rig_indices = []
        self.rig_weights = []
        self.rig_names = []


@dataclass
class PrimitiveBox:
    location: Vector3D
    axis: Matrix3x3
    extent: Vector3D

    @classmethod
    def read(cls, reader: Reader):
        return cls(
            Vector3D.read(reader),
            Matrix3x3.read(reader),
            Vector3D.read(reader),
        )

    def write(self, writer: Writer):
        self.location.write(writer)
        self.axis.write(writer)
        self.extent.write(writer)


@dataclass
class PrimitiveSphere:
    location: Vector3D
    radius: float

    @classmethod
    def read(cls, reader: Reader):
        return cls(
            Vector3D.read(reader),
            reader.read_float(),
        )

    def write(self, writer: Writer):
        self.location.write(writer)
        writer.write_float(self.radius)


@dataclass
class PrimitiveCapsule:
    location: Vector3D
    direction: Vector3D
    radius: float

    @classmethod
    def read(cls, reader: Reader):
        return cls(
            Vector3D.read(reader),
            Vector3D.read(reader),
            reader.read_float(),
        )

    def write(self, writer: Writer):
        self.location.write(writer)
        self.direction.write(writer)
        writer.write_float(self.radius)


@dataclass
class PrimitiveTriangle:
    location: Vector3D
    edge_a: Vector3D
    edge_b: Vector3D

    @classmethod
    def read(cls, reader: Reader):
        return cls(
            Vector3D.read(reader),
            Vector3D.read(reader),
            Vector3D.read(reader),
        )

    def write(self, writer: Writer):
        self.location.write(writer)
        self.edge_a.write(writer)
        self.edge_b.write(writer)


@dataclass
class PrimitiveTriangleList:
    triangles: List[PrimitiveTriangle]

    @classmethod
    def read(cls, reader: Reader):
        triangles_num = reader.read_int()
        triangles = [PrimitiveTriangle.read(reader) for _ in range(triangles_num)]
        return cls(triangles)

    def write(self, writer: Writer):
        writer.write_int(len(self.triangles))
        for triangle in self.triangles:
            triangle.write(writer)


class Collision:

    @classmethod
    def read(cls, reader: Reader, version: int):
        self = cls()

        self.type = reader.read_int()
        if version > 10:
            self.name = reader.read_string(reader.read_int())

        if self.type == CollisionType.BOX:
            self.primitive = PrimitiveBox.read(reader)

        elif self.type == CollisionType.SPHERE:
           self.primitive = PrimitiveSphere.read(reader)

        elif self.type == CollisionType.CAPSULE:
            self.primitive = PrimitiveCapsule.read(reader)

        elif self.type == CollisionType.TRIANGLE_LIST:
            self.primitive = PrimitiveTriangleList.read(reader)

        return self

    def write(self, writer: Writer, version: int):
        writer.write_int(self.type)
        if version > 10:
            writer.write_int(len(self.name) + 1)
            writer.write_string(self.name)
        self.primitive.write(writer)

    def __init__(self):
        self.type = 0
        self.name = ""
        self.primitive = None


class MSH:

    def load_memory(self, data: bytes):
        reader = Reader(data)

        self.file_type = reader.read_string(256)
        if not self.file_type.startswith("Eternity Engine Mesh File"):
            return

        self.version = reader.read_int()

        meshes_num, lods_num = reader.read_int(2)
        uv_ani = reader.read_bytes(4)[0]

        self.bb_max = Vector3D.read(reader)
        self.bb_min = Vector3D.read(reader)

        bones_num, cols_num, dummies_num = reader.read_int(3)

        reader._pos = 1024

        self.bones = [Bone.read(reader) for _ in range(bones_num)]
        self.meshes = [Mesh.read(reader) for _ in range(meshes_num)]
        self.collisions = [Collision.read(reader, self.version) for _ in range(cols_num)]
        self.dummies = [Dummy.read(reader, self.version) for _ in range(dummies_num)]

    def save_memory(self) -> bytes:
        writer = Writer()

        writer.write_string(self.file_type, 256)
        writer.write_int(self.version)

        writer.write_int((len(self.meshes), 1, 0))

        self.bb_max.write(writer)
        self.bb_min.write(writer)

        writer.write_int((len(self.bones), len(self.collisions), len(self.dummies)))
        writer.write_bytes(b'\0' * (1024 - len(writer.data)))

        for bone in self.bones:
            bone.write(writer)

        for mesh in self.meshes:
            mesh.write(writer)

        for collision in self.collisions:
            collision.write(writer, self.version)

        for dummy in self.dummies:
            dummy.write(writer, self.version)

        return writer.data

    def load_file(self, filename: str):
        with open(filename, mode="rb") as file:
            data = file.read()
            self.load_memory(data)

    def save_file(self, filename: str):
        with open(filename, mode="wb") as file:
            data = self.save_memory()
            file.write(data)

    def clear(self):
        self.file_type = ""
        self.version = 0
        self.bb_max = Vector3D(0, 0, 0)
        self.bb_min = Vector3D(0, 0, 0)
        self.bones: List[Bone] = []
        self.meshes: List[Mesh] = []
        self.collisions: List[Collision] = []
        self.dummies: List[Dummy] = []

    def __init__(self):
        self.clear()
