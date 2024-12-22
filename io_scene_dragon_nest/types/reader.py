from struct import unpack, unpack_from

class Reader:

    # buffered returns the number of bytes that can be read from the current reader
    def buffered(self) -> int:
        return len(self._data) - self._pos

    def read_bytes(self, size: int) -> bytes:
        data = self._data[self._pos:self._pos+size]
        self._pos += len(data)
        return data

    def read_float(self, num=1) -> float | tuple[float]:
        data = unpack_from(f'<{num}f', self._data, self._pos)
        if num == 1:
            data = data[0]
        self._pos += 4 * num
        return data

    def read_int(self, num=1) -> int | tuple[int]:
        data = unpack_from(f'<{num}l', self._data, self._pos)
        if num == 1:
            data = data[0]
        self._pos += 4 * num
        return data

    def read_short(self, num=1) -> int | tuple[int]:
        data = unpack_from(f'<{num}h', self._data, self._pos)
        if num == 1:
            data = data[0]
        self._pos += 2 * num
        return data

    def read_string(self, size=None) -> str:
        if size is None:
            pos, size = self._pos, 1
            while self._data[pos] != 0:
                pos += 1
                size += 1

        return self.read_bytes(size).decode('cp949').replace('\x00', '')

    def __init__(self, data):
        self._pos = 0
        self._data = data
