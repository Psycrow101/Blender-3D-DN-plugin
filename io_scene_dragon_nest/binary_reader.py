import struct
import mathutils


def read_string(file, strlen=0):
    if strlen > 0:
        return file.read(strlen).decode('cp949').replace('\x00', '')
    data = ''
    byte = file.read(1)
    while byte != b'\x00':
        data += (byte.decode('cp949'))
        byte = file.read(1)
    return data


def read_int(file, num=1):
    data = struct.unpack('<{}l'.format(num), file.read(4 * num))
    if num == 1:
        data = data[0]
    return data


def read_short(file, num=1):
    data = struct.unpack('<{}h'.format(num), file.read(2 * num))
    if num == 1:
        data = data[0]
    return data


def read_float(file, num=1):
    data = struct.unpack('<{}f'.format(num), file.read(4 * num))
    if num == 1:
        data = data[0]
    return data


def read_matrix(file):
    return mathutils.Matrix(tuple(struct.unpack('<4f', file.read(16)) for _ in range(4)))
