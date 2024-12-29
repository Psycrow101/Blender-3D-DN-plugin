import bpy
import os

from mathutils import Quaternion, Vector, Matrix
from typing import List

from ..gui import gui
from ..types.ani import ANI, ANIM, AnimationBone

ANIM_ID_ALL = -1


def translation_matrix(v):
    return Matrix.Translation(v)


def rotation_matrix(v):
    return v.to_matrix().to_4x4()


def scale_matrix(v):
    mat = Matrix.Identity(4)
    mat[0][0], mat[1][1], mat[2][2] = v[0], v[1], v[2]
    return mat


def set_keyframe(fcurves, frame, values):
    for i, fc in enumerate(fcurves):
        fc.keyframe_points.add(1)
        fc.keyframe_points[-1].co = frame, values[i]
        fc.keyframe_points[-1].interpolation = 'LINEAR'


def find_last_keyframe_time(action):
    last_frame = 0
    for fc in action.fcurves:
        for kf in fc.keyframe_points:
            frame = kf.co[0]
            if frame > last_frame:
                last_frame = frame
    return int(last_frame)


def get_active_armature(context):
    arm_obj = context.view_layer.objects.active
    if arm_obj and type(arm_obj.data) == bpy.types.Armature:
        return arm_obj


def get_armature_matrices(armature_object):
    bpy.ops.object.mode_set(mode='EDIT')

    matrices = {}
    for bone in armature_object.data.edit_bones:
        matrices[bone.name] = bone.matrix @ scale_matrix(bone.dragon_nest.scale)

    bpy.ops.object.mode_set(mode='OBJECT')
    return matrices


def local_to_basis_matrix(local_matrix, global_matrix, parent_matrix):
    return global_matrix.inverted() @ (parent_matrix @ local_matrix)


def connect_armature_bones(context, armature, animation_bones: List[AnimationBone]) -> bool:
    bpy.ops.object.mode_set(mode='EDIT')

    for ani_bone in animation_bones:
        arm_bone = armature.edit_bones.get(ani_bone.name) or armature.edit_bones.get(ani_bone.name[:-2])
        if not arm_bone:
            context.window_manager.popup_menu(gui.invalid_armature, title='Error', icon='ERROR')
            bpy.ops.object.mode_set(mode='OBJECT')
            return False

        arm_bone.parent = armature.edit_bones.get(ani_bone.parent_name)

    bpy.ops.object.mode_set(mode='OBJECT')
    return True


def create_actions(armature_object, animation_bones: List[AnimationBone], anim_id=ANIM_ID_ALL):
    def_matrices = get_armature_matrices(armature_object)
    actions = {}

    for ani_bone in animation_bones:
        bone = armature_object.data.bones.get(ani_bone.name) or armature_object.data.bones.get(ani_bone.name[:-2])
        def_mat = def_matrices[bone.name]
        parent_def_mat = def_matrices[bone.parent.name] if bone.parent else Matrix()

        for act_idx, anim in enumerate(ani_bone.animations):
            if anim_id not in (ANIM_ID_ALL, act_idx):
                continue

            act = actions.get(act_idx) or bpy.data.actions.new("dn_animation %d" % act_idx)
            actions[act_idx] = act

            group = act.groups.new(name=bone.name)
            path_prefix = f'pose.bones["{bone.name}"].'

            fcurves_location = [act.fcurves.new(data_path=path_prefix + "location", index=i) for i in range(3)]
            fcurves_rotation = [act.fcurves.new(data_path=path_prefix + "rotation_quaternion", index=i) for i in range(4)]
            fcurves_scale    = [act.fcurves.new(data_path=path_prefix + "scale", index=i) for i in range(3)]

            for fc in fcurves_location + fcurves_rotation + fcurves_scale:
                 fc.group = group

            loc = Vector(anim.base_location.unpack())
            rot = Quaternion((
                anim.base_rotation.w,
                anim.base_rotation.x,
                anim.base_rotation.y,
                anim.base_rotation.z,
            ))
            scl = Vector(anim.base_scale.unpack())

            mat = translation_matrix(loc) @ rotation_matrix(rot) @ scale_matrix(scl)
            mat_basis = local_to_basis_matrix(mat, def_mat, parent_def_mat)

            set_keyframe(fcurves_location, 0, mat_basis.to_translation())
            set_keyframe(fcurves_rotation, 0, mat_basis.to_quaternion())
            set_keyframe(fcurves_scale, 0, mat_basis.to_scale())

            for kf in anim.locations:
                loc = Vector(kf.value.unpack())
                mat = translation_matrix(loc)
                mat_basis = local_to_basis_matrix(mat, def_mat, parent_def_mat)
                set_keyframe(fcurves_location, kf.frame, mat_basis.to_translation())

            for kf in anim.rotations:
                rot = Quaternion((kf.value.w, kf.value.x, kf.value.y, kf.value.z))
                mat = rotation_matrix(rot)
                mat_basis = local_to_basis_matrix(mat, def_mat, parent_def_mat)
                set_keyframe(fcurves_rotation, kf.frame, mat_basis.to_quaternion())

            for kf in anim.scales:
                scl = Vector(kf.value.unpack())
                mat = scale_matrix(scl)
                mat_basis = local_to_basis_matrix(mat, def_mat, parent_def_mat)
                set_keyframe(fcurves_scale, kf.frame, mat_basis.to_scale())

    return actions


class AniImporter:

    def import_data(self, context, options):
        anim_id = options.get("animation_id")
        if anim_id is None:
            anim_id = ANIM_ID_ALL
        elif anim_id != ANIM_ID_ALL:
            anim_id = max(0, min(anim_id, len(self.ani.names) - 1))

        arm_obj = get_active_armature(context)
        if not arm_obj:
            return

        arm = arm_obj.data
        if not connect_armature_bones(context, arm, self.ani.bones):
            return

        actions = create_actions(arm_obj, self.ani.bones, anim_id)
        for act_idx in sorted(actions):
            act = actions[act_idx]
            act.name = self.ani.names[act_idx]
            self.actions.append(act)

        animation_data = arm_obj.animation_data or arm_obj.animation_data_create()
        animation_data.action = self.actions[-1]

        context.scene.frame_start = 0
        context.scene.frame_end = find_last_keyframe_time(animation_data.action)

        self.imported = True

    def load_file(self, context, filename) -> bool:
        self.ani = ANI()
        self.ani.load_file(filename)

        if not self.ani.file_type.startswith("Eternity Engine Ani File"):
            context.window_manager.popup_menu(gui.invalid_ani_type, title='Error', icon='ERROR')
            return False

        return True

    def __init__(self):
        self.ani = None
        self.actions = []
        self.imported = False


class AnimImporter:

    def import_data(self, context, options):
        arm_obj = get_active_armature(context)
        if not arm_obj:
            return

        arm = arm_obj.data
        if not connect_armature_bones(context, arm, self.anim.bones):
            return

        actions = create_actions(arm_obj, self.anim.bones)
        self.action = actions[0]

        animation_data = arm_obj.animation_data or arm_obj.animation_data_create()
        animation_data.action = self.action

        context.scene.frame_start = 0
        context.scene.frame_end = find_last_keyframe_time(animation_data.action)

        self.imported = True

    def load_file(self, context, filename) -> bool:
        self.anim = ANIM()
        self.anim.load_file(filename)
        return True

    def __init__(self):
        self.anim = None
        self.action = None
        self.imported = False


def load(context, filepath):
    arm_obj = get_active_armature(context)
    if not arm_obj:
        return None

    if filepath.lower().endswith(".ani"):
        importer = AniImporter()
        if not importer.load_file(context, filepath):
            return None

    if filepath.lower().endswith(".anim"):
        importer = AnimImporter()
        if not importer.load_file(context, filepath):
            return None

        importer.import_data(context, {})
        if not importer.action:
            return None

        importer.action.name = os.path.basename(filepath)[:-5]

    return importer
