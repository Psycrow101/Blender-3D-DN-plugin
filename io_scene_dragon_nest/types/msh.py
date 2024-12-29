from dataclasses import dataclass
from enum import IntEnum
from typing import List, Union

from .common import *
from .reader import Reader


class CollisionType(IntEnum):
    BOX           = 0
    SPHERE        = 1
    CAPSULE       = 2
    TRIANGLE      = 3
    TRIANGLE_LIST = 4


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


@dataclass
class Dummy:
    name: str
    parent_name: str
    transformation: Union[Matrix4x4, Vector3D]

    @classmethod
    def read(cls, reader: Reader, version: int):
        if version > 12:
            return cls(
                reader.read_string(256),
                reader.read_string(256),
                Matrix4x4.read(reader),
            )

        else:
            name = reader.read_string(256)
            transformation = Vector3D.read(reader)
            parent_name = reader.read_string(256) if name[0] == "L" else ""
            return cls(
                name,
                parent_name,
                transformation,
            )


class Mesh:

    @classmethod
    def read(cls, reader: Reader):
        self = cls()

        # header
        self.parent_name = reader.read_string(256)
        self.name = reader.read_string(256)

        verts_num, indices_num, uvs_num = reader.read_int(3)
        use_tristrip, use_rig, use_vert_color, _ = reader.read_bytes(4)

        reader.read_bytes(512 - 16)

        # faces
        if use_tristrip:
            v1, v2 = reader.read_short(2)
            direct = -1
            for _ in range(indices_num - 2):
                v3 = reader.read_short()
                direct *= -1
                if v1 != v2 and v2 != v3 and v1 != v3:
                    self.faces.append([v1, v2, v3] if direct > 0 else [v1, v3, v2])
                v1, v2 = v2, v3
        else:
            self.faces = [reader.read_short(3) for _ in range(indices_num // 3)]

        # vertices, normals, uvs
        self.vertices = [reader.read_float(3) for _ in range(verts_num)]
        self.normals = [reader.read_float(3) for _ in range(verts_num)]

        self.uvs = []
        for _ in range(uvs_num):
            self.uvs.append([reader.read_float(2) for _ in range(verts_num)])

        # vertex colors
        if use_vert_color:
            self.vertex_colors = [reader.read_float() for _ in range(verts_num)]

        # skin
        if use_rig:
            self.rig_indices = [reader.read_short(4) for _ in range(verts_num)]
            self.rig_weights = [reader.read_float(4) for _ in range(verts_num)]

            bones_num = reader.read_int()
            self.rig_names = [reader.read_string(256) for _ in range(bones_num)]

        return self

    def __init__(self):
        self.parent_name = ""
        self.name = ""
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
    center: Vector3D
    axis: Matrix3x3
    extent: Vector3D

    @classmethod
    def read(cls, reader: Reader):
        return cls(
            Vector3D.read(reader),
            Matrix3x3.read(reader),
            Vector3D.read(reader),
        )


@dataclass
class PrimitiveSphere:
    center: Vector3D
    radius: float

    @classmethod
    def read(cls, reader: Reader):
        return cls(
            Vector3D.read(reader),
            reader.read_float(),
        )


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


@dataclass
class PrimitiveTriangleList:
    triangles: List[PrimitiveTriangle]


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

        elif self.type == CollisionType.TRIANGLE:
            num = reader.read_int()
            self.primitive = [reader.read_float(9) for _ in range(num)]

        elif self.type == CollisionType.TRIANGLE_LIST:
            triangles_num = reader.read_int()
            triangles = [PrimitiveTriangle.read(reader) for _ in range(triangles_num)]
            self.primitive = PrimitiveTriangleList(triangles)

        return self

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

    def load_file(self, filename: str):
        with open(filename, mode="rb") as file:
            data = file.read()
            self.load_memory(data)

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
