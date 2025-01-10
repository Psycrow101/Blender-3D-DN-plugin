import bpy

from dataclasses import dataclass
from mathutils import Euler, Matrix, Quaternion, Vector
from typing import Dict, List

from .common import unoriented_matrix, translation_matrix, rotation_matrix, scale_matrix
from .common import get_active_armature_object, get_armature_matrices
from ..gui import gui
from ..types import common
from ..types.ani import ANI, AnimationBone, Animation, KeyFrame


def basis_to_local_matrix(basis_matrix, global_matrix, parent_matrix):
    return parent_matrix.inverted() @ global_matrix @ basis_matrix


def convert_matrix(matrix, matrix_rest, matrix_parent):
    loc_mat = basis_to_local_matrix(matrix, matrix_rest, matrix_parent)
    return unoriented_matrix(loc_mat)


def convert_location(location, matrix_rest, matrix_parent, matrix_root):
    mat = translation_matrix(location)
    return (matrix_root @ convert_matrix(mat, matrix_rest, matrix_parent)).to_translation()


def convert_rotation(rotation, matrix_rest, matrix_parent, matrix_root):
    mat = rotation_matrix(rotation)
    return (matrix_root @ convert_matrix(mat, matrix_rest, matrix_parent)).to_quaternion()


def convert_scale(scale, matrix_rest, matrix_parent):
    mat = scale_matrix(scale)
    return convert_matrix(mat, matrix_rest, matrix_parent).to_scale()


@dataclass
class BoneBaseData:
    location: Vector
    rotation: Quaternion
    scale: Vector

    def to_matrix(self) -> Matrix:
        loc_mat = translation_matrix(self.location)
        rot_mat = rotation_matrix(self.rotation)
        scl_mat = scale_matrix(self.scale)
        return loc_mat @ rot_mat @ scl_mat


class BoneAnimData:
    def __init__(self):
        self.locations: Dict[int, Vector] = {}
        self.rotations_quat: Dict[int, Quaternion] = {}
        self.rotations_euler: Dict[int, Euler] = {}
        self.scales: Dict[int, Vector] = {}


class ActData:
    def __init__(self):
        self.bones_data: Dict[str, BoneAnimData] = {}
        self.frames_num: int = 0


class AniExporter:

    @staticmethod
    def get_action_data(arm_obj, act, bone_bases: Dict[str, BoneBaseData]) -> ActData:
        action_data = ActData()
        max_time = 0

        for curve in act.fcurves:
            if 'pose.bones' not in curve.data_path:
                continue

            bone_name = curve.data_path.split('"')[1]
            bone = arm_obj.pose.bones.get(bone_name)
            if not bone:
                continue

            bone_base = bone_bases[bone_name]
            anim_data = action_data.bones_data.get(bone_name) or BoneAnimData()

            for kp in curve.keyframe_points:
                time = int(kp.co[0])

                if curve.data_path == f'pose.bones["{bone_name}"].location':
                    loc = anim_data.locations.get(time) or bone_base.location.copy()
                    loc[curve.array_index] = kp.co[1]
                    anim_data.locations[time] = loc
                    max_time = max(time, max_time)

                elif curve.data_path == f'pose.bones["{bone_name}"].rotation_quaternion':
                    if bone.rotation_mode == 'QUATERNION':
                        rot = anim_data.rotations_quat.get(time) or bone_base.rotation.copy()
                        rot[curve.array_index] = kp.co[1]
                        anim_data.rotations_quat[time] = rot
                        max_time = max(time, max_time)

                elif curve.data_path == f'pose.bones["{bone_name}"].rotation_euler':
                    if bone.rotation_mode != 'QUATERNION':
                        rot = anim_data.rotations_euler.get(time) or bone_base.rotation.to_euler()
                        rot[curve.array_index] = kp.co[1]
                        anim_data.rotations_euler[time] = rot
                        max_time = max(time, max_time)

                elif curve.data_path == f'pose.bones["{bone_name}"].scale':
                    scl = anim_data.scales.get(time) or bone_base.scale.copy()
                    scl[curve.array_index] = kp.co[1]
                    anim_data.scales[time] = scl
                    max_time = max(time, max_time)

            action_data.bones_data[bone_name] = anim_data

        # convert euler to quat
        for anim_data in action_data.bones_data.values():
            if not anim_data.rotations_quat:
                for time, rot in anim_data.rotations_euler.items():
                    anim_data.rotations_quat[time] = rot.to_quaternion()

        action_data.frames_num = max_time + 1
        return action_data

    def export_data(self, context, options):
        arm_obj, version = options["armature_object"], options["version"]
        actions = options["actions"]
        apply_root_transform = options["apply_root_transform"]

        self.ani.file_type = "Eternity Engine Ani File 0.1"
        self.ani.version = version

        matrix_arm = unoriented_matrix(arm_obj.matrix_world) if apply_root_transform else Matrix.Identity(4)
        scale_arm = matrix_arm.to_scale()

        matrices = get_armature_matrices(arm_obj)

        bone_bases: Dict[str, BoneBaseData] = {}
        for bone in arm_obj.data.bones:
            mat = matrices[bone.name].copy()
            if bone.parent:
                mat = matrices[bone.parent.name].inverted() @ mat
            bone_bases[bone.name] = BoneBaseData(
                mat.to_translation(),
                mat.to_quaternion(),
                mat.to_scale()
            )

        action_data_list: List[ActData] = []
        for act in actions:
            ad = AniExporter.get_action_data(arm_obj, act, bone_bases)
            action_data_list.append(ad)

            self.ani.names.append(act.name)
            self.ani.frames_num.append(ad.frames_num)

        active_bone_names = set()
        for ad in action_data_list:
            for bone_name in ad.bones_data.keys():
                active_bone_names.add(bone_name)

        for bone in arm_obj.data.bones:
            bone_name = bone.name
            if not bone.children and not bone.parent and bone_name not in active_bone_names:
                continue

            matrix_rest = matrices[bone_name]
            matrix_parent = matrices[bone.parent.name] if bone.parent else Matrix.Identity(4)

            ani_animations = []
            matrix_base = unoriented_matrix(bone_bases[bone_name].to_matrix())
            matrix_root = scale_matrix(scale_arm) if bone.parent else matrix_arm

            for ad in action_data_list:
                bd = ad.bones_data.get(bone_name)
                bone_parent = bone.parent.name if bone.parent else "Scene Root"
                locations, rotations, scales = [], [], []

                # location
                frames = sorted(bd.locations) if bd else None
                if frames:
                    loc = convert_location(bd.locations[frames[0]], matrix_rest, matrix_parent, matrix_root)
                    base_location = common.Vector3D(*loc)

                    if len(frames) > 1:
                        for f in frames:
                            loc = convert_location(bd.locations[f], matrix_rest, matrix_parent, matrix_root)
                            locations.append(KeyFrame(f, common.Vector3D(*loc)))

                        if frames[-1] != ad.frames_num - 1:
                            f = frames[-1]
                            loc = convert_location(bd.locations[f], matrix_rest, matrix_parent, matrix_root)
                            locations.append(KeyFrame(f, common.Vector3D(*loc)))
                else:
                    loc = (matrix_root @ matrix_base).to_translation()
                    base_location = common.Vector3D(*loc)

                # rotation
                frames = sorted(bd.rotations_quat) if bd else None
                if frames:
                    rot = convert_rotation(bd.rotations_quat[frames[0]], matrix_rest, matrix_parent, matrix_root)
                    base_rotation = common.Vector4D(rot.x, rot.y, rot.z, rot.w)

                    if len(frames) > 1:
                        for f in frames:
                            rot = convert_rotation(bd.rotations_quat[f], matrix_rest, matrix_parent, matrix_root)
                            rotations.append(KeyFrame(f, common.Vector4D(rot.x, rot.y, rot.z, rot.w)))

                        if frames[-1] != ad.frames_num - 1:
                            f = frames[-1]
                            rot = convert_rotation(bd.rotations_quat[f], matrix_rest, matrix_parent, matrix_root)
                            rotations.append(KeyFrame(f, common.Vector4D(rot.x, rot.y, rot.z, rot.w)))
                else:
                    rot = (matrix_root @ matrix_base).to_quaternion()
                    base_rotation = common.Vector4D(rot.x, rot.y, rot.z, rot.w)

                # scale
                frames = sorted(bd.scales) if bd else None
                if frames:
                    scl = convert_scale(bd.scales[frames[0]], matrix_rest, matrix_parent)
                    base_scale = common.Vector3D(*scl)

                    if len(frames) > 1:
                        for f in frames:
                            scl = convert_scale(bd.scales[f], matrix_rest, matrix_parent)
                            scales.append(KeyFrame(f, common.Vector3D(*scl)))

                        if frames[-1] != ad.frames_num - 1:
                            f = frames[-1]
                            scl = convert_scale(bd.scales[f], matrix_rest, matrix_parent)
                            scales.append(KeyFrame(f, common.Vector3D(*scl)))
                else:
                    scl = matrix_base.to_scale()
                    base_scale = common.Vector3D(*scl)

                ani_animations.append(Animation(
                    base_location,
                    base_rotation,
                    base_scale,
                    locations,
                    rotations,
                    scales
                ))

            self.ani.bones.append(AnimationBone(bone_name, bone_parent, ani_animations))

    def __init__(self):
        self.ani = ANI()
        self.mesh_objects = []


def save(context, filepath, options):
    arm_obj = get_active_armature_object(context)
    if not arm_obj:
        context.window_manager.popup_menu(gui.need_armature_to_export, title='Error', icon='ERROR')
        return

    actions = [act for act in bpy.data.actions if act.dragon_nest.use_export]

    ani_options = {
        "version": options["ani_version"],
        "armature_object": arm_obj,
        "actions": actions,
        "apply_root_transform": options["apply_root_transform"],
    }

    ani_exporter = AniExporter()
    ani_exporter.export_data(context, ani_options)
    ani_exporter.ani.save_file(filepath)

    return ani_exporter
