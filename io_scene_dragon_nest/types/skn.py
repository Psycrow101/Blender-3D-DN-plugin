from dataclasses import dataclass
from enum import IntEnum
from typing import Any, List

from .common import *
from .reader import Reader


class MatPropType(IntEnum):
    INT     = 0
    FLOAT   = 1
    VECTOR  = 2
    TEXTURE = 3
    MATRIX  = 4


@dataclass
class MaterialProperty:
    name: str
    type: 0
    value: Any

    @classmethod
    def read(cls, reader: Reader):
        name = reader.read_string(reader.read_int())
        prop_type = reader.read_int()

        if prop_type == MatPropType.INT:
            value = reader.read_int()

        elif prop_type == MatPropType.FLOAT:
            value = reader.read_float()

        elif prop_type == MatPropType.VECTOR:
            value = Vector4D.read(reader)

        elif prop_type == MatPropType.TEXTURE:
            value = reader.read_string(reader.read_int())

        else:
            value = None

        return cls(
            name,
            prop_type,
            value,
        )


@dataclass
class Material:
    name: str
    effect: str
    alpha: float
    alpha_blend: int
    properties: List[MaterialProperty]

    @classmethod
    def read(cls, reader: Reader):
        name = reader.read_string(256)
        effect = reader.read_string(256)

        alpha = reader.read_float()
        alpha_blend = reader.read_int()

        reader.read_bytes(512 - 8)

        props_num = reader.read_int()
        props = [MaterialProperty.read(reader) for _ in range(props_num)]

        return cls(
            name,
            effect,
            alpha,
            alpha_blend,
            props,
        )


class SKN:

    def load_memory(self, data: bytes):
        reader = Reader(data)

        self.file_type = reader.read_string(256)
        if not self.file_type.startswith("Eternity Engine Skin File"):
            return

        self.name = reader.read_string(256)
        self.version = reader.read_int()

        materials_num = reader.read_int()

        reader._pos = 1024

        self.materials = [Material.read(reader) for _ in range(materials_num)]

    def load_file(self, filename: str):
        with open(filename, mode="rb") as file:
            data = file.read()
            self.load_memory(data)

    def clear(self):
        self.file_type = ""
        self.name = ""
        self.version = 0
        self.materials: List[Material] = []

    def __init__(self):
        self.clear()
