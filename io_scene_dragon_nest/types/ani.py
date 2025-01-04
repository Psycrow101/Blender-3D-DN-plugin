from dataclasses import dataclass
from typing import List, Union

from .common import *
from .reader import Reader


@dataclass
class KeyFrame:
    frame: int
    value: Union[Vector3D, Vector4D]


@dataclass
class Animation:
    base_location: Vector3D
    base_rotation: Vector4D
    base_scale: Vector3D

    locations: List[KeyFrame]
    rotations: List[KeyFrame]
    scales: List[KeyFrame]

    @classmethod
    def read(cls, reader: Reader, read_frame_func, read_rotation_func):
        base_location = Vector3D.read(reader)
        base_rotation = Vector4D.read(reader)
        base_scale = Vector3D.read(reader)
        locations, rotations, scales = [], [], []

        # locations
        frames_num = reader.read_int()
        for _ in range(frames_num):
            frame, value = read_frame_func(), Vector3D.read(reader)
            locations.append(KeyFrame(frame, value))

        # rotations
        frames_num = reader.read_int()
        for _ in range(frames_num):
            frame, value = read_frame_func(), read_rotation_func(reader)
            rotations.append(KeyFrame(frame, value))

        # scales
        frames_num = reader.read_int()
        for _ in range(frames_num):
            frame, value = read_frame_func(), Vector3D.read(reader)
            scales.append(KeyFrame(frame, value))

        return cls(
            base_location, base_rotation, base_scale,
            locations, rotations, scales,
        )

    def write(self, writer: Writer, write_frame_func, write_rotation_func):
        self.base_location.write(writer)
        self.base_rotation.write(writer)
        self.base_scale.write(writer)

        # locations
        writer.write_int(len(self.locations))
        for kf in self.locations:
            write_frame_func(kf.frame)
            kf.value.write(writer)

        # rotations
        writer.write_int(len(self.rotations))
        for kf in self.rotations:
            write_frame_func(kf.frame)
            write_rotation_func(kf.value)

        # scales
        writer.write_int(len(self.scales))
        for kf in self.scales:
            write_frame_func(kf.frame)
            kf.value.write(writer)


@dataclass
class AnimationBone:
    name: str
    parent_name: str
    animations: List[Animation]


class ANIM:

    def load_memory(self, data: bytes):
        reader = Reader(data)

        while reader.buffered() > 0:
            bone_name = reader.read_string()
            bone_parent_name = reader.read_string()
            bone_anims = [Animation.read(reader, reader.read_short, Vector4D.read_short)]

            bone = AnimationBone(bone_name, bone_parent_name, bone_anims)
            self.bones.append(bone)

    def load_file(self, filename: str):
        with open(filename, mode="rb") as file:
            data = file.read()
            self.load_memory(data)

    def clear(self):
        self.bones: List[AnimationBone] = []

    def __init__(self):
        self.clear()


class ANI:

    def load_memory(self, data: bytes):
        reader = Reader(data)

        self.file_type = reader.read_string(256)
        if not self.file_type.startswith("Eternity Engine Ani File"):
            return

        self.version = reader.read_int()
        bones_num, anims_num = reader.read_int(2)

        reader._pos = 1024

        self.names = [reader.read_string(256) for _ in range(anims_num)]
        self.frames_num = list(reader.read_int(anims_num))

        if self.version < 11:
            read_frame_func = reader.read_int
            read_rotation_func = Vector4D.read
        else:
            read_frame_func = reader.read_short
            read_rotation_func = Vector4D.read_short

        self.bones = []
        for _ in range(bones_num):
            bone_name = reader.read_string(256)
            bone_parent_name = reader.read_string(256)

            reader.read_bytes(512)

            bone_anims = []
            for _ in range(anims_num):
                anim = Animation.read(reader, read_frame_func, read_rotation_func)
                bone_anims.append(anim)

            bone = AnimationBone(bone_name, bone_parent_name, bone_anims)
            self.bones.append(bone)

    def save_memory(self) -> bytes:
        writer = Writer()

        writer.write_string(self.file_type, 256)
        writer.write_int(self.version)

        bones_num = len(self.bones)
        anims_num = len(self.names)

        writer.write_int((bones_num, anims_num))
        writer.write_bytes(b'\0' * (1024 - len(writer.data)))

        for name in self.names:
            writer.write_string(name, 256)

        writer.write_int(self.frames_num)

        if self.version < 11:
            write_frame_func = writer.write_int
            write_rotation_func = Vector4D.write
        else:
            write_frame_func = writer.write_short
            write_rotation_func = Vector4D.write_short

        for bone in self.bones:
            writer.write_string(bone.name, 256)
            writer.write_string(bone.parent_name, 256)

            writer.write_bytes(b'\0' * 512)

            for anim in bone.animations:
                anim.write(writer, write_frame_func, write_rotation_func)

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
        self.names: List[str] = []
        self.frames_num: List[int] = []
        self.bones: List[AnimationBone] = []

    def __init__(self):
        self.clear()
