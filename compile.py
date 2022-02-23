from modulefinder import LOAD_CONST
import struct
from typing import BinaryIO, Sequence, Union

from bfops import Context, OpCode

REF_FLAG = 0x80
REFLIST = []


def module_header(f: BinaryIO):
    """
    reference: https://www.python.org/dev/peps/pep-0552/#specification
    """
    MAGIC_PY = b"\x6f\x0d\x0d\x0a"
    BIT_FIELD = 0
    TIMESTAMP = 0  # can be zeroed
    SIZE = 0  # can be zeroed
    fields = [MAGIC_PY, BIT_FIELD, TIMESTAMP, SIZE]  # 0 for padding
    f.write(struct.pack("<4sLLL", *fields))


def code_header(f: BinaryIO) -> int:
    """
    reference code from https://github.com/python/cpython/blob/3.10/Python/marshal.c#L509
    ```c
    W_TYPE      TYPE_CODE
    w_long      co_argcount
    w_long      co_posonlyargcount
    w_long      co_kwonlyargcount
    w_long      co_nlocals
    w_long      co_stacksize
    w_long      co_flags
    w_object    co_code
    w_object    co_consts
    w_object    co_names
    w_object    co_varnames
    w_object    co_freevars
    w_object    co_cellvars
    w_object    co_filename
    w_object    co_name
    w_long      co_firstlineno
    w_object    co_linetable
    ```
    """

    CODE_OBJECT_TYPE = 0x63 | REF_FLAG

    fields = [
        CODE_OBJECT_TYPE,
        0,  # co_argcount
        0,  # co_posonlyargcount
        0,  # co_kwonlyargcount
        0,  # co_nlocals
        4,  # co_stacksize
        64,  # co_flags
    ]
    f.write(struct.pack("<BLLLLLL", *fields))
    REFLIST.append(CODE_OBJECT_TYPE)
    return len(REFLIST) - 1  # return reflist index


def write_bytes(f: BinaryIO, b: bytes):
    """
    ╥
    ╠═ W_TYPE(TYPE_STRING, p);
    ╠═ w_pstring(PyBytes_AS_STRING(v), PyBytes_GET_SIZE(v), p)
    ╠─── W_SIZE(PyBytes_GET_SIZE(v), p);
    ╠─── w_string(PyBytes_AS_STRING(v), PyBytes_GET_SIZE(v), p);
    ╨
    """
    TYPE_STRING = 0x73
    SIZE = len(b)
    static_fields = [TYPE_STRING, SIZE]
    f.write(struct.pack("<BL", *static_fields))
    f.write(b)


def write_code(f: BinaryIO, ops: Sequence[OpCode]):
    byte_list = [op.as_byte() for op in ops]
    write_bytes(f, b"".join(byte_list))


def write_none(f: BinaryIO):
    TYPE_NONE = b"N"  # 0x4e
    f.write(TYPE_NONE)


def write_false(f: BinaryIO):
    TYPE_FALSE = b"F"
    f.write(TYPE_FALSE)


def write_true(f: BinaryIO):
    TYPE_TRUE = b"T"
    f.write(TYPE_TRUE)


def write_bool(f: BinaryIO, value: bool):
    if value:
        write_true(f)
    else:
        write_false(f)


def write_long(f: BinaryIO, value: int):
    """
    ╥
    ╠═ W_TYPE TYPE_INT
    ╠═ w_long value
    ╨
    """
    TYPE_LONG = 0x69
    statis_fields = [TYPE_LONG, value]
    f.write(struct.pack("<BL", *statis_fields))


def write_short_interned_string(f: BinaryIO, string: str) -> int:
    if len(string) > 255:
        raise ValueError("too long string")
    TYPE_SHORT_ASCII_INTERNED = 0x5A | REF_FLAG
    SIZE = len(string)
    static_fields = [TYPE_SHORT_ASCII_INTERNED, SIZE]
    f.write(struct.pack("<BB", *static_fields))
    f.write(string.encode())

    REFLIST.append(TYPE_SHORT_ASCII_INTERNED)
    return len(REFLIST) - 1  # return reflist index


def write_short_string(f: BinaryIO, string: str) -> int:
    if len(string) > 255:
        raise ValueError("too long string")
    TYPE_SHORT_ASCII = 0x7A | REF_FLAG
    SIZE = len(string)
    static_fields = [TYPE_SHORT_ASCII, SIZE]
    f.write(struct.pack("<BB", *static_fields))
    f.write(string.encode())
    REFLIST.append(TYPE_SHORT_ASCII)
    return len(REFLIST) - 1  # return reflist index


SIMPLE_TYPE = Union[int, str, bytes, bool, None]


def write_simple_tuple(f: BinaryIO, elements: Sequence[SIMPLE_TYPE], flag=0x00) -> int:
    """
    ╥
    ╠═  W_TYPE TYPE_SMALL_TUPLE
    ╠═  w_byte PyTuple_GET_SIZE(v)
    for i in range(PyTuple_GET_SIZE(v)):
    ╠═  w_object v[i]
    ╨
    """
    if len(elements) > 255:
        raise ValueError("too many consts")

    TYPE_SMALL_TUPLE = 0x29 | flag
    SIZE = len(elements)
    static_fields = [TYPE_SMALL_TUPLE, SIZE]
    f.write(struct.pack("<BB", *static_fields))
    for element in elements:
        if isinstance(element, int):
            write_long(f, element)
        elif isinstance(element, bytes):
            write_bytes(f, element)
        elif isinstance(element, str):
            write_short_interned_string(f, element)
        elif isinstance(element, bool):
            write_bool(f, element)
        elif element == None:
            write_none(f)
        else:
            raise ValueError("unsupported type")
    if flag == 0:
        return -1
    REFLIST.append(TYPE_SMALL_TUPLE)
    return len(REFLIST) - 1  # return reflist index


def write_ref(f: BinaryIO, ref: int):
    """
    ╥
    ╠═ W_TYPE TYPE_REF
    ╠═ w_long ref
    ╨
    """
    TYPE_REF = 0x72
    static_fields = [TYPE_REF, ref]
    f.write(struct.pack("<BL", *static_fields))


def write_consts(f: BinaryIO, consts: Sequence[SIMPLE_TYPE]):
    write_simple_tuple(f, consts)


def write_names(f: BinaryIO, names: Sequence[SIMPLE_TYPE]):
    write_simple_tuple(f, names)


def write_tail(f: BinaryIO):
    """
    w_object    co_varnames
    w_object    co_freevars
    w_object    co_cellvars
    w_object    co_filename
    w_object    co_name
    w_long      co_firstlineno
    w_object    co_linetable
    """
    write_simple_tuple(f, [])
    write_simple_tuple(f, [])
    write_simple_tuple(f, [])
    write_short_string(f, ".\\1line.py")
    write_short_interned_string(f, "<module>")
    f.write(struct.pack("<l", -1))
    write_bytes(f, b"")


def compile_context(file: BinaryIO, ctx: Context):
    module_header(file)
    code_header(file)
    write_code(file, ctx.ops)
    write_consts(file, ctx.constants)
    write_names(file, ctx.names)
    write_tail(file)
