from asyncio import constants
from dataclasses import dataclass, field
from enum import Enum
import enum
from typing import MutableSequence, Sequence, Union, overload
import struct

from sys import stdin

SIMPLE_TYPE = Union[int, str, bytes, None]


class PyCmpOp(Enum):
    SMALLER = 0
    SMALLER_EQUAL = 1
    EQUAL = 2
    NOT_EQUAL = 3
    GREATER = 4
    GREATER_EQUAL = 5


class PyOpCode(Enum):
    POP_TOP = 1
    ROT_TWO = 2
    ROT_THREE = 3
    DUP_TOP = 4
    DUP_TOP_TWO = 5
    ROT_FOUR = 6
    NOP = 9
    UNARY_POSITIVE = 10
    UNARY_NEGATIVE = 11
    UNARY_NOT = 12
    UNARY_INVERT = 15
    BINARY_MATRIX_MULTIPLY = 16
    INPLACE_MATRIX_MULTIPLY = 17
    BINARY_POWER = 19
    BINARY_MULTIPLY = 20
    BINARY_MODULO = 22
    BINARY_ADD = 23
    BINARY_SUBTRACT = 24
    BINARY_SUBSCR = 25
    BINARY_FLOOR_DIVIDE = 26
    BINARY_TRUE_DIVIDE = 27
    INPLACE_FLOOR_DIVIDE = 28
    INPLACE_TRUE_DIVIDE = 29
    GET_LEN = 30
    MATCH_MAPPING = 31
    MATCH_SEQUENCE = 32
    MATCH_KEYS = 33
    COPY_DICT_WITHOUT_KEYS = 34
    WITH_EXCEPT_START = 49
    GET_AITER = 50
    GET_ANEXT = 51
    BEFORE_ASYNC_WITH = 52
    END_ASYNC_FOR = 54
    INPLACE_ADD = 55
    INPLACE_SUBTRACT = 56
    INPLACE_MULTIPLY = 57
    INPLACE_MODULO = 59
    STORE_SUBSCR = 60  # TOS1[TOS] = TOS2
    DELETE_SUBSCR = 61
    BINARY_LSHIFT = 62
    BINARY_RSHIFT = 63
    BINARY_AND = 64
    BINARY_XOR = 65
    BINARY_OR = 66
    INPLACE_POWER = 67
    GET_ITER = 68
    GET_YIELD_FROM_ITER = 69
    PRINT_EXPR = 70
    LOAD_BUILD_CLASS = 71
    YIELD_FROM = 72
    GET_AWAITABLE = 73
    LOAD_ASSERTION_ERROR = 74
    INPLACE_LSHIFT = 75
    INPLACE_RSHIFT = 76
    INPLACE_AND = 77
    INPLACE_XOR = 78
    INPLACE_OR = 79
    LIST_TO_TUPLE = 82
    RETURN_VALUE = 83
    IMPORT_STAR = 84
    SETUP_ANNOTATIONS = 85
    YIELD_VALUE = 86
    POP_BLOCK = 87
    POP_EXCEPT = 89
    STORE_NAME = 90
    DELETE_NAME = 91
    UNPACK_SEQUENCE = 92
    FOR_ITER = 93
    UNPACK_EX = 94
    STORE_ATTR = 95
    DELETE_ATTR = 96
    STORE_GLOBAL = 97
    DELETE_GLOBAL = 98
    ROT_N = 99
    LOAD_CONST = 100
    LOAD_NAME = 101
    BUILD_TUPLE = 102
    BUILD_LIST = 103
    BUILD_SET = 104
    BUILD_MAP = 105
    LOAD_ATTR = 106
    COMPARE_OP = 107
    IMPORT_NAME = 108
    IMPORT_FROM = 109
    JUMP_FORWARD = 110
    JUMP_IF_FALSE_OR_POP = 111
    JUMP_IF_TRUE_OR_POP = 112
    JUMP_ABSOLUTE = 113
    POP_JUMP_IF_FALSE = 114
    POP_JUMP_IF_TRUE = 115
    LOAD_GLOBAL = 116
    IS_OP = 117
    CONTAINS_OP = 118
    RERAISE = 119
    JUMP_IF_NOT_EXC_MATCH = 121
    SETUP_FINALLY = 122
    LOAD_FAST = 124
    STORE_FAST = 125
    DELETE_FAST = 126
    GEN_START = 129
    RAISE_VARARGS = 130
    CALL_FUNCTION = 131
    MAKE_FUNCTION = 132
    BUILD_SLICE = 133
    LOAD_CLOSURE = 135
    LOAD_DEREF = 136
    STORE_DEREF = 137
    DELETE_DEREF = 138
    CALL_FUNCTION_KW = 141
    CALL_FUNCTION_EX = 142
    SETUP_WITH = 143
    EXTENDED_ARG = 144
    LIST_APPEND = 145
    SET_ADD = 146
    MAP_ADD = 147
    LOAD_CLASSDEREF = 148
    MATCH_CLASS = 152
    SETUP_ASYNC_WITH = 154
    FORMAT_VALUE = 155
    BUILD_CONST_KEY_MAP = 156
    BUILD_STRING = 157
    LOAD_METHOD = 160
    CALL_METHOD = 161
    LIST_EXTEND = 162
    SET_UPDATE = 163
    DICT_MERGE = 164
    DICT_UPDATE = 165


@dataclass
class OpCode:
    op: PyOpCode
    value: int = 0

    def as_byte(self) -> bytes:
        # TODO: check if this is correct
        if 0 <= self.value <= 255:
            return struct.pack("<BB", self.op.value, self.value)
        if 256 <= self.value < 65536:  # not sure if `<` is correct
            top_two_bytes = self.value >> 8
            bottom_byte = self.value & 0xFF
            extend = OpCode(PyOpCode.EXTENDED_ARG, top_two_bytes)
            this = OpCode(self.op, bottom_byte)
            return extend.as_byte() + this.as_byte()
        raise ValueError(f"{self.value} is not a valid value for an opcode")


@dataclass
class Context:
    constants: MutableSequence[SIMPLE_TYPE] = field(default_factory=list)
    names: MutableSequence[str] = field(default_factory=list)
    ops: list[OpCode] = field(default_factory=list)
    _jump_stack: list[int] = field(default_factory=list)

    def consti(self, value: SIMPLE_TYPE) -> int:
        if value not in self.constants:
            self.constants.append(value)
        return self.constants.index(value)

    def load_const(self, value: SIMPLE_TYPE):
        self.append_op(PyOpCode.LOAD_CONST, self.consti(value))

    def append_name(self, name: str):
        if name in self.names:
            return
        self.names.append(name)

    def namei(self, name: str) -> int:
        self.append_name(name)
        return self.names.index(name)

    def load_name(self, name: str):
        self.append_op(PyOpCode.LOAD_NAME, self.namei(name))

    def store_name(self, name: str):
        self.append_op(PyOpCode.STORE_NAME, self.namei(name))

    @overload
    def append_op(self, op: OpCode):
        ...

    @overload
    def append_op(self, op: PyOpCode, value: int = 0):
        ...

    def append_op(self, op: Union[OpCode, PyOpCode], value: int = 0):
        if isinstance(op, OpCode):
            self.ops.append(op)
        else:
            self.ops.append(OpCode(op, value))

    def extends_ops(self, ops: Sequence[OpCode]):
        self.ops.extend(ops)

    def nop(self):
        self.append_op(PyOpCode.NOP)

    def pop_top(self):
        """TOS --"""
        self.append_op(PyOpCode.POP_TOP)

    def dup_top(self):
        """TOS -- TOS TOS"""
        self.append_op(PyOpCode.DUP_TOP)

    def dup_top_two(self):
        """TOS1 TOS -- TOS1 TOS TOS1 TOS"""
        self.append_op(PyOpCode.DUP_TOP_TWO)

    def compare_op(self, op: PyCmpOp):
        """TOS1 TOS -- RESULT"""
        self.append_op(PyOpCode.COMPARE_OP, op.value)

    def binary_add(self):
        """TOS = TOS1 + TOS

        TOS1 TOS -- RESULT
        """
        self.append_op(PyOpCode.BINARY_ADD)

    def binary_subscr(self):
        """TOS = TOS1[TOS]"""
        self.append_op(PyOpCode.BINARY_SUBSCR)

    def store_subscr(self):
        """TOS1[TOS] = TOS2

        TOS2 TOS1 TOS --
        """
        self.append_op(PyOpCode.STORE_SUBSCR)

    def load_method(self, name: str):
        self.append_op(PyOpCode.LOAD_METHOD, self.namei(name))

    def call_method(self, argc: int = 1):
        self.append_op(PyOpCode.CALL_METHOD, argc)

    def call_function(self, argc: int = 1):
        """TOS = TOS1(TOS)"""
        self.append_op(PyOpCode.CALL_FUNCTION, argc)

    def import_stdin_stdout(self):
        self.load_const(0)  # 0
        self.load_const("stdin")  # 0, "stdin"
        self.load_const("stdout")  # 0, "stdin", "stdout"
        self.append_op(PyOpCode.BUILD_TUPLE, 2)  # 0, ("stdin", "stdout")
        self.append_op(PyOpCode.IMPORT_NAME, self.namei("sys"))  # sys
        self.append_op(PyOpCode.IMPORT_FROM, self.namei("stdin"))  # sys, sys.stdin
        self.store_name("stdin")  # sys
        self.append_op(PyOpCode.IMPORT_FROM, self.namei("stdout"))  # sys, sys.stdout
        self.store_name("stdout")  # sys
        self.pop_top()  #

    def init_memory(self):
        self.load_const(0)  # 0
        self.append_op(PyOpCode.BUILD_LIST, 1)  #  [0]
        self.load_const(2 ** 9)  # [0], 2 ** 9
        self.append_op(PyOpCode.BINARY_MULTIPLY)  # [0] * 2 ** 9
        self.store_name("memory")  #

    def init_pointer(self):
        self.load_const(0)  # 0
        self.store_name("pointer")  #

    def init_program(self):
        self.import_stdin_stdout()
        self.init_memory()
        self.init_pointer()

    def raise_if_true(self, message: str):
        """
        TODO: doesn't work, needs to be fixed
        if TOS: raise Exception(message)
        TOS --
        """
        self.append_op(PyOpCode.POP_JUMP_IF_FALSE, len(self.ops) + 5)
        self.load_name("Exception")  # Exception
        self.load_const(message)  # Exception, message
        self.call_function()  # Exception
        self.append_op(PyOpCode.RAISE_VARARGS, 1)

    def increment_pointer(self, increment: int = 1):
        self.nop()
        self.load_name("pointer")  # pointer
        self.load_const(increment)  # pointer, increment
        self.append_op(PyOpCode.INPLACE_ADD)  # pointer + increment
        self.store_name("pointer")  #

    def decrement_pointer(self, decrement: int = 1):
        self.nop()
        self.load_name("pointer")  # pointer
        self.load_const(decrement)  # pointer, decrement
        self.append_op(PyOpCode.INPLACE_SUBTRACT)  # pointer - decrement
        # self.dup_top()
        # self.load_const(0)  # pointer - decrement, pointer - decrement, 0
        # self.compare_op(
        #     PyCmpOp.SMALLER
        # )  # pointer - decrement, (pointer - decrement) < 0
        # self.raise_if_true("pointer underflow")  # pointer - decrement
        self.store_name("pointer")  #

    def increment_cell(self, increment: int = 1):
        self.nop()
        self.load_name("memory")  # memory
        self.load_name("pointer")  # memory, pointer
        self.dup_top_two()  # memory, pointer, pointer, pointer
        self.binary_subscr()  # memory, pointer, memory[pointer]
        self.load_const(increment)  # memory, pointer, memory[pointer], increment
        self.append_op(
            PyOpCode.INPLACE_ADD
        )  # memory, pointer, memory[pointer] + increment
        self.load_const(256)  # memory, pointer, memory[pointer] + increment, 256
        self.append_op(
            PyOpCode.INPLACE_MODULO
        )  # memory, pointer, (memory[pointer] + increment) % 256
        # push TOS behind TOS2
        self.append_op(
            PyOpCode.ROT_THREE
        )  # (memory[pointer] + increment) % 256, memory, pointer
        self.store_subscr()  #

    def decrement_cell(self, decrement: int = 1):
        self.nop()
        self.load_name("memory")  # memory
        self.load_name("pointer")  # memory, pointer
        self.dup_top_two()  # memory, pointer, pointer, pointer
        self.binary_subscr()  # memory, pointer, memory[pointer]
        self.load_const(decrement)  # memory, pointer, memory[pointer], decrement
        self.append_op(
            PyOpCode.INPLACE_SUBTRACT
        )  # memory, pointer, memory[pointer] - decrement
        self.load_const(256)  # memory, pointer, memory[pointer] - increment, 256
        self.append_op(
            PyOpCode.INPLACE_MODULO
        )  # memory, pointer, (memory[pointer] - increment) % 256
        # push TOS behind TOS2
        self.append_op(
            PyOpCode.ROT_THREE
        )  # memory[pointer] - decrement, memory, pointer
        self.store_subscr()  #

    def stdout_print_cell(self):
        self.nop()
        self.load_name("stdout")  # stdout
        self.load_method("write")  # write()
        self.load_name("chr")  # write(), chr()
        self.load_name("memory")  # write(), chr(), memory
        self.load_name("pointer")  # write(), chr(), memory, pointer
        self.binary_subscr()  # write(), chr(), memory[pointer]
        self.call_function()  # write(), chr(memory[pointer])
        self.call_method()  # write(chr(memory[pointer]))
        self.pop_top()  #

    def stdin_get_cell(self):
        self.nop()
        self.load_name("ord")  # ord()
        self.load_name("stdin")  # ord(), stdin
        self.load_method("read")  # ord(), read()
        self.load_const(1)  # ord(), read(), 1
        self.call_method()  # ord(), read(1)
        self.call_function()  # ord(read(1))
        self.load_name("memory")  # ord(read(1)), memory
        self.load_name("pointer")  # ord(read(1)), memory, pointer
        self.store_subscr()  #

    def push_to_jump_stack(self):
        self.nop()
        self._jump_stack.append(len(self.ops))

    def cond_jump_top_jump_stack(self):
        self.nop()
        self.load_name("memory")  # memory
        self.load_name("pointer")  # memory, pointer
        self.binary_subscr()  # memory[pointer]
        self.load_const(0)  # memory[pointer], 0
        self.compare_op(PyCmpOp.EQUAL)  # memory[pointer] == 0
        self.append_op(PyOpCode.POP_JUMP_IF_FALSE, self._jump_stack.pop())  #

    def terminate(self):
        self.load_const(None)  # None
        self.append_op(PyOpCode.RETURN_VALUE)  #

    def print_pointer(self):
        self.load_name("print")  # print()
        self.load_name("pointer")  # print(), pointer
        self.call_function()  # print(pointer)
        self.pop_top()  #

    def print_memory(self):
        self.load_name("print")  # print()
        self.load_name("memory")  # print(), memory
        self.call_function()  # print(memory)
        self.pop_top()  #

    def print_ops(self):
        max_len = max(len(op.op.name) for op in self.ops)
        for idx, op in enumerate(self.ops):
            possible_values = [
                self.names[op.value] if len(self.names) > op.value else None,
                self.constants[op.value] if len(self.constants) > op.value else None,
            ]
            possible_str = ", ".join(map(str, possible_values))
            print(f"{idx:03}: {op.op.name.ljust(max_len)} {op.value} ({possible_str}) ")
