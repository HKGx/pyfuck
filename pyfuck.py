import argparse
from bz2 import compress
from io import TextIOWrapper
from itertools import pairwise
from typing import Callable

from bfops import Context, OpCode, PyOpCode
from compile import compile_context

parser = argparse.ArgumentParser(description="PyFuck")
parser.add_argument("infile", type=argparse.FileType("r"))


def compress_str(string: str) -> list[tuple[str, int]]:
    """Compresses consecutive characters
    "aaabbbc" becomes "a3b3c1"

    Args:
        string (str): string to be compressed

    Returns:
        list[tuple[str, int]]: compressed string as a list of tuples
    """
    compressed = []
    current_char = string[0]
    current_count = 0
    for char in string:
        if char not in "><+-.,[]":
            continue
        if char == current_char:
            current_count += 1
        else:
            compressed.append((current_char, current_count))
            current_char = char
            current_count = 1
    compressed.append((current_char, current_count))
    return compressed


def parse_source(string: str, ctx: Context):
    CHAR_MAP = {
        ">": ctx.increment_pointer,
        "<": ctx.decrement_pointer,
        "+": ctx.increment_cell,
        "-": ctx.decrement_cell,
        ".": ctx.stdout_print_cell,
        ",": ctx.stdin_get_cell,
        "[": ctx.push_to_jump_stack,
        "]": ctx.cond_jump_top_jump_stack,
    }
    # join consecutive >, <, + and - to reduce the number of instructions
    compressed = compress_str(string)
    for char, count in compressed:
        if char in "><+-":
            CHAR_MAP[char](count)
        elif char in CHAR_MAP:
            for _ in range(count):
                CHAR_MAP[char]()


def main():
    args = parser.parse_args()
    file: TextIOWrapper = args.infile
    source = file.read()
    ctx = Context()
    ctx.init_program()
    parse_source(source, ctx)
    ctx.terminate()
    # ctx.print_ops()
    with open("out.pyc", "wb") as f:
        compile_context(f, ctx)
    print("Compilation ended. Output written to ./out.pyc")


if __name__ == "__main__":
    main()
