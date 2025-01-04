from collections.abc import Iterable
from struct import pack
from typing import Tuple, Union


class Writer:

    def _write_value(self, data: Union[Union[float, int], Tuple[Union[float, int]]], fmt_char: str):
        if isinstance(data, Iterable):
            self.data += pack(f'<{len(data)}{fmt_char}', *data)
        else:
            self.data += pack(f'<{fmt_char}', data)

    def write_bytes(self, data: bytes):
        self.data += data

    def write_float(self, data: Union[float, Tuple[float]]):
        self._write_value(data, 'f')

    def write_int8(self, data: Union[int, Tuple[int]]):
        self._write_value(data, 'b')

    def write_int(self, data: Union[int, Tuple[int]]):
        self._write_value(data, 'l')

    def write_short(self, data: Union[int, Tuple[int]]):
        self._write_value(data, 'h')

    def write_ushort(self, data: Union[int, Tuple[int]]):
        self._write_value(data, 'H')

    def write_string(self, data: str, size=None):
        self.data += data.encode('cp949')
        null_size = 1 if size is None else size - len(data)
        self.data += b'\00' * null_size

    def __init__(self):
        self.data = b''
