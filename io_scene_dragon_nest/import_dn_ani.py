import bpy
import mathutils
import os
from . binary_reader import *

ANIM_ID_ALL = -1


def trans_matrix(v):
    return mathutils.Matrix.Translation(v)


def scale_matrix(v):
    mat = mathutils.Matrix.Identity(4)
    mat[0][0], mat[1][1], mat[2][2] = v[0], v[1], v[2]
    return mat


def short_to_angle(v):
    return v * 2 ** -15


def set_posebone_matrix(bone, matrix):
    if bone.parent:
        bone.matrix = bone.parent.matrix @ matrix
    else:
        bone.matrix = matrix


def set_keyframe(curves, frame, values):
    for i, c in enumerate(curves):
        c.keyframe_points.add(1)
        c.keyframe_points[-1].co = frame, values[i]
        c.keyframe_points[-1].interpolation = 'LINEAR'


def invalid_ani_type(self, context):
    self.layout.label(text='Invalid ani type')


def invalid_armature(self, context):
    self.layout.label(text='Invalid armature')


def get_anim_names(file):
    ani_type = read_string(file, 256)
    if 'Eternity Engine Ani File' not in ani_type:
        bpy.context.window_manager.popup_menu(invalid_ani_type, title='Error', icon='ERROR')
        return None

    # todo: check version
    ani_version = file.read(4)
    file.seek(4, os.SEEK_CUR)

    anims_num = read_int(file)

    file.seek(0x400)

    anim_names = tuple(read_string(file, 256) for _ in range(anims_num))
    return anim_names


def import_anim(context, file, arm_obj, anim_id, bones_num, anims_num):
    arm = arm_obj.data
    actions = {}

    end_pos = None

    is_anim = False
    if not bones_num:
        bones_num = len(arm.bones)
        anims_num = 1
        is_anim = True

        file.seek(0, os.SEEK_END)
        end_pos = file.tell()
        file.seek(0)

    last_frame = 0

    for b in range(bones_num):
        if end_pos and end_pos == file.tell():
            return actions

        bpy.ops.object.mode_set(mode='EDIT')

        if is_anim:
            bone_name = read_string(file)
            bone_parent_name = read_string(file)
        else:
            bone_name = read_string(file, 256)
            bone_parent_name = read_string(file, 256)

        arm_bone = arm.edit_bones.get(bone_name)
        if not arm_bone:
            context.window_manager.popup_menu(invalid_armature, title='Error', icon='ERROR')
            for act in actions.values():
                bpy.data.actions.remove(act)
            bpy.ops.object.mode_set(mode='OBJECT')
            return {}

        arm_bone_parent = arm.edit_bones.get(bone_parent_name)
        if arm_bone_parent:
            arm_bone.parent = arm_bone_parent

        if not is_anim:
            file.seek(0x200, os.SEEK_CUR)

        bpy.ops.object.mode_set(mode='POSE')

        for k in range(anims_num):
            if anim_id in (ANIM_ID_ALL, k):
                act = actions.get(k)
                if not act:
                    act = bpy.data.actions.new("dn_animation %d" % k)
                    actions[k] = act

                bone = arm_obj.pose.bones[bone_name]

                base_loc = read_float(file, 3)
                base_rot = read_float(file, 4)
                base_scale = read_float(file, 3)

                base_rot_quaternion = mathutils.Quaternion((base_rot[3], base_rot[0], base_rot[1], base_rot[2]))
                base_mat = trans_matrix(base_loc) @ base_rot_quaternion.to_matrix().to_4x4() @ scale_matrix(base_scale)
                set_posebone_matrix(bone, base_mat)

                group = act.groups.new(name=bone_name)
                bone_string = f'pose.bones["{bone_name}"].'

                # location
                curves = [act.fcurves.new(data_path=bone_string + "location", index=i) for i in (0, 1, 2)]
                for c in curves:
                    c.group = group

                loc_frames_num = read_int(file)
                for f in range(loc_frames_num):
                    frame = read_short(file)
                    if frame > last_frame:
                        last_frame = frame

                    set_posebone_matrix(bone, trans_matrix(read_float(file, 3)))
                    set_keyframe(curves, frame, bone.location)

                if not loc_frames_num:
                    set_posebone_matrix(bone, base_mat)
                    set_keyframe(curves, 0, bone.location)

                # roation
                curves = [act.fcurves.new(data_path=bone_string + "rotation_quaternion", index=i) for i in range(4)]
                for c in curves:
                    c.group = group

                rot_frames_num = read_int(file)
                for f in range(rot_frames_num):
                    frame = read_short(file)
                    if frame > last_frame:
                        last_frame = frame

                    rot = read_short(file, 4)
                    rot_quaternion = mathutils.Quaternion(tuple(short_to_angle(rot[i]) for i in (3, 0, 1, 2)))
                    set_posebone_matrix(bone, rot_quaternion.to_matrix().to_4x4())
                    set_keyframe(curves, frame, bone.rotation_quaternion)

                if not rot_frames_num:
                    set_posebone_matrix(bone, base_mat)
                    set_keyframe(curves, 0, bone.rotation_quaternion)

                # scale
                curves = [act.fcurves.new(data_path=bone_string + "scale", index=i) for i in (0, 1, 2)]
                for c in curves:
                    c.group = group

                scale_frames_num = read_int(file)
                for f in range(scale_frames_num):
                    frame = read_short(file)
                    if frame > last_frame:
                        last_frame = frame

                    set_keyframe(curves, frame, read_float(file, 3))

                if not scale_frames_num:
                    set_keyframe(curves, 0, base_scale)

            else:
                file.seek(40, os.SEEK_CUR)
                file.seek(read_int(file) * 14, os.SEEK_CUR)
                file.seek(read_int(file) * 10, os.SEEK_CUR)
                file.seek(read_int(file) * 14, os.SEEK_CUR)

    context.scene.frame_start = 0
    context.scene.frame_end = last_frame

    bpy.ops.object.mode_set(mode='OBJECT')
    return actions


def import_ani(context, file, arm_obj, anim_id):
    ani_type = read_string(file, 256)
    if 'Eternity Engine Ani File' not in ani_type:
        context.window_manager.popup_menu(invalid_ani_type, title='Error', icon='ERROR')
        return None

    # todo: check version
    ani_version = file.read(4)

    bones_num, anims_num = read_int(file, 2)

    file.seek(0x400)

    anim_names = tuple(read_string(file, 256) for _ in range(anims_num))
    anim_frames_num = read_int(file, anims_num)
    if anim_id != ANIM_ID_ALL:
        anim_id = max(0, min(anim_id, anims_num - 1))

    actions = import_anim(context, file, arm_obj, anim_id, bones_num, anims_num)
    for k, act in actions.items():
        act.name = anim_names[k]
    
    return actions


def load(context, filepath, *, append_to_target, global_matrix=None):
    arm_obj = context.view_layer.objects.active
    if not arm_obj or type(arm_obj.data) != bpy.types.Armature:
        return {'CANCELLED'}

    if filepath.lower().endswith('.ani'):
        anim_names = None
        arm_obj.dn_anim_list.clear()
        with open(filepath, 'rb') as fw:
            anim_names = get_anim_names(fw)

        if not anim_names:
            return {'CANCELLED'}

        arm_obj.dn_anim_list.add().anim_name = 'All'
        for n in anim_names:
            arm_obj.dn_anim_list.add().anim_name = n
        bpy.ops.dialog.anim_chooser_box('INVOKE_DEFAULT', filepath=filepath)

        return {'FINISHED'}

    if filepath.lower().endswith('.anim'):
        with open(filepath, 'rb') as fw:
            actions = import_anim(context, fw, arm_obj, 0, bones_num=0, anims_num=1)
            if not actions:
                return {'CANCELLED'}

            act = actions[0]
            act.name = os.path.basename(filepath)[:-5]
            arm_obj.animation_data_create().action = act
            return {'FINISHED'}

    return {'CANCELLED'}


def load_anim(context, filepath, anim_id):
    arm_obj = context.view_layer.objects.active
    if not arm_obj or type(arm_obj.data) != bpy.types.Armature:
        return {'CANCELLED'}

    with open(filepath, 'rb') as fw:
        actions = import_ani(context, fw, arm_obj, anim_id)
        if not actions:
            return {'CANCELLED'}

        for act in actions.values():
            arm_obj.animation_data_create().action = act
        return {'FINISHED'}

    return {'CANCELLED'}
