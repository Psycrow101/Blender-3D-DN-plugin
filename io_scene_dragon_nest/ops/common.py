from mathutils import Matrix

ORIENTATION_MATRIX = Matrix(((1.0, 0.0, 0.0, 0.0),
                             (0.0, 0.0, 1.0, 0.0),
                             (0.0, 1.0, 0.0, 0.0),
                             (0.0, 0.0, 0.0, 1.0)))


def oriented_matrix(mat: Matrix) -> Matrix:
    return ORIENTATION_MATRIX @ mat @ ORIENTATION_MATRIX


def unoriented_matrix(mat: Matrix) -> Matrix:
    return ORIENTATION_MATRIX.inverted() @ mat @ ORIENTATION_MATRIX.inverted()


def translation_matrix(v):
    return Matrix.Translation(v)


def rotation_matrix(v):
    return v.to_matrix().to_4x4()


def scale_matrix(v):
    mat = Matrix.Identity(4)
    mat[0][0], mat[1][1], mat[2][2] = v[0], v[1], v[2]
    return mat


def get_active_armature_object(context):
    arm_obj = context.object
    if not arm_obj:
        return

    if arm_obj.type == 'ARMATURE':
        return arm_obj

    arm_obj = arm_obj.parent
    if arm_obj and arm_obj.type == 'ARMATURE':
        return arm_obj


def get_armature_matrices(armature_object):
    matrices = {}
    for bone in armature_object.data.bones:
        matrices[bone.name] = bone.matrix_local @ scale_matrix(bone.dragon_nest.scale)
    return matrices
