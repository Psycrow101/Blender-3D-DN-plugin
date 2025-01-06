from dataclasses import dataclass

from .reader import Reader
from .writer import Writer


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

    def write(self, writer: Writer):
        writer.write_float(self.unpack())


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

    def write(self, writer: Writer):
        writer.write_float(self.unpack())

    def write_short(self, writer: Writer):
        vals = tuple(round(v * 0x7fff) for v in self.unpack())
        writer.write_short(vals)


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

    @classmethod
    def identity(cls):
        return cls(
            Vector3D(1, 0, 0),
            Vector3D(0, 1, 0),
            Vector3D(0, 0, 1),
        )

    def unpack(self) -> tuple:
        return (
            self.v1.unpack(),
            self.v2.unpack(),
            self.v3.unpack(),
        )

    def write(self, writer: Writer):
        self.v1.write(writer)
        self.v2.write(writer)
        self.v3.write(writer)


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

    @classmethod
    def identity(cls):
        return cls(
            Vector4D(1, 0, 0, 0),
            Vector4D(0, 1, 0, 0),
            Vector4D(0, 0, 1, 0),
            Vector4D(0, 0, 0, 1),
        )

    def unpack(self) -> tuple:
        return (
            self.v1.unpack(),
            self.v2.unpack(),
            self.v3.unpack(),
            self.v4.unpack(),
        )

    def write(self, writer: Writer):
        self.v1.write(writer)
        self.v2.write(writer)
        self.v3.write(writer)
        self.v4.write(writer)
