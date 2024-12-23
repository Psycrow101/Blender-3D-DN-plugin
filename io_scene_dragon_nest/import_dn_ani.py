import bpy
import os

from mathutils import Quaternion, Vector, Matrix
from typing import List

from .types.ani import ANI, ANIM, AnimationBone

ANIM_ID_ALL = -1


def invalid_ani_type(self, context):
    self.layout.label(text='Invalid ani type')


def invalid_armature(self, context):
    self.layout.label(text='Invalid armature')


def trans_matrix(v):
    return Matrix.Translation(v)


def rotation_matrix(v):
    return v.to_matrix().to_4x4()


def scale_matrix(v):
    mat = Matrix.Identity(4)
    mat[0][0], mat[1][1], mat[2][2] = v[0], v[1], v[2]
    return mat


def set_posebone_matrix(bone, matrix):
    if bone.parent:
        bone.matrix = bone.parent.matrix @ matrix
    else:
        bone.matrix = matrix


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


def connect_armature_bones(context, armature, animation_bones: List[AnimationBone]) -> bool:
    bpy.ops.object.mode_set(mode='EDIT')

    for ani_bone in animation_bones:
        arm_bone = armature.edit_bones.get(ani_bone.name) or armature.edit_bones.get(ani_bone.name[:-2])
        if not arm_bone:
            context.window_manager.popup_menu(invalid_armature, title='Error', icon='ERROR')
            bpy.ops.object.mode_set(mode='OBJECT')
            return False

        arm_bone.parent = armature.edit_bones.get(ani_bone.parent_name)

    return True


def create_actions(context, armature_object, animation_bones: List[AnimationBone], anim_id=ANIM_ID_ALL):
    bpy.ops.object.mode_set(mode='POSE')

    actions = {}

    for ani_bone in animation_bones:
        bone = armature_object.pose.bones.get(ani_bone.name) or armature_object.pose.bones.get(ani_bone.name[:-2])

        for act_idx, anim in enumerate(ani_bone.animations):
            if anim_id not in (ANIM_ID_ALL, act_idx):
                continue

            act = actions.get(act_idx)
            if not act:
                act = bpy.data.actions.new("dn_animation %d" % act_idx)
                actions[act_idx] = act

            base_location = Vector(anim.base_location.unpack())
            base_rotation = Quaternion((
                anim.base_rotation.w,
                anim.base_rotation.x,
                anim.base_rotation.y,
                anim.base_rotation.z,
            ))
            base_scale = Vector(anim.base_scale.unpack())
            base_mat = trans_matrix(base_location) @ rotation_matrix(base_rotation) @ scale_matrix(base_scale)
            set_posebone_matrix(bone, base_mat)

            group = act.groups.new(name=bone.name)
            path_prefix = f'pose.bones["{bone.name}"].'

            # location
            fcurves = [act.fcurves.new(data_path=path_prefix + "location", index=i) for i in range(3)]
            for fc in fcurves:
                 fc.group = group

            if anim.locations:
                for kf in anim.locations:
                    set_posebone_matrix(bone, trans_matrix(kf.value.unpack()))
                    set_keyframe(fcurves, kf.frame, bone.location)
            else:
                set_posebone_matrix(bone, base_mat)
                set_keyframe(fcurves, 0, bone.location)

            # roation
            fcurves = [act.fcurves.new(data_path=path_prefix + "rotation_quaternion", index=i) for i in range(4)]
            for fc in fcurves:
                 fc.group = group

            if anim.rotations:
                for kf in anim.rotations:
                    rotation = Quaternion((kf.value.w, kf.value.x, kf.value.y, kf.value.z))
                    set_posebone_matrix(bone, rotation_matrix(rotation))
                    set_keyframe(fcurves, kf.frame, bone.rotation_quaternion)

            else:
                set_posebone_matrix(bone, base_mat)
                set_keyframe(fcurves, 0, bone.rotation_quaternion)

            # scale
            fcurves = [act.fcurves.new(data_path=path_prefix + "scale", index=i) for i in range(3)]
            for c in fcurves:
                 c.group = group

            if anim.scales:
                for kf in anim.scales:
                    set_keyframe(fcurves, kf.frame, kf.value.unpack())
            else:
                set_keyframe(fcurves, 0, base_scale)

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

        actions = create_actions(context, arm_obj, self.ani.bones, anim_id)
        for act_idx in sorted(actions):
            act = actions[act_idx]
            act.name = self.ani.names[act_idx]
            self.actions.append(act)

        animation_data = arm_obj.animation_data or arm_obj.animation_data_create()
        animation_data.action = self.actions[-1]

        bpy.ops.object.mode_set(mode='OBJECT')

        context.scene.frame_start = 0
        context.scene.frame_end = find_last_keyframe_time(animation_data.action)

        self.imported = True

    def load_file(self, context, filename) -> bool:
        self.ani = ANI()
        self.ani.load_file(filename)

        if not self.ani.file_type.startswith("Eternity Engine Ani File"):
            context.window_manager.popup_menu(invalid_ani_type, title='Error', icon='ERROR')
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

        actions = create_actions(context, arm_obj, self.anim.bones)
        self.action = actions[0]

        animation_data = arm_obj.animation_data or arm_obj.animation_data_create()
        animation_data.action = self.action

        bpy.ops.object.mode_set(mode='OBJECT')

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
