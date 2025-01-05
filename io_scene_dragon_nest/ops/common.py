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
