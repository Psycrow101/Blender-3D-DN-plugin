from dataclasses import dataclass

from .reader import Reader


@dataclass
class Vector3D:
    x: float
    y: float
    z: float

    @classmethod
    def read(cls, reader: Reader):
        return cls(*reader.read_float(3))

    def unpack(self) -> tuple:
        return (self.x, self.y, self.z)


@dataclass
class Vector4D:
    x: float
    y: float
    z: float
    w: float

    @classmethod
    def read(cls, reader: Reader):
        return cls(*reader.read_float(4))

    @classmethod
    def read_short(cls, reader: Reader):
        vals = reader.read_short(4)
        return cls(*(v * 2 ** -15 for v in vals))

    def unpack(self) -> tuple:
        return (self.x, self.y, self.z, self.w)


@dataclass
class Matrix3x3:
    v1: Vector3D
    v2: Vector3D
    v3: Vector3D

    @classmethod
    def read(cls, reader: Reader):
        return cls(
            Vector3D.read(reader),
            Vector3D.read(reader),
            Vector3D.read(reader),
        )

    def unpack(self) -> tuple:
        return (
            self.v1.unpack(),
            self.v2.unpack(),
            self.v3.unpack(),
        )


@dataclass
class Matrix4x4:
    v1: Vector4D
    v2: Vector4D
    v3: Vector4D
    v4: Vector4D

    @classmethod
    def read(cls, reader: Reader):
        return cls(
            Vector4D.read(reader),
            Vector4D.read(reader),
            Vector4D.read(reader),
            Vector4D.read(reader),
        )

    def unpack(self) -> tuple:
        return (
            self.v1.unpack(),
            self.v2.unpack(),
            self.v3.unpack(),
            self.v4.unpack(),
        )
