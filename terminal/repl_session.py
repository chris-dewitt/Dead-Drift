"""Terminal V2 Phase J.2.3 — a fake Python REPL that is real about syntax.

The point (spec + decision #5): a player who types real Python gets a reaction
that respects it — garbage raises a real `SyntaxError`, `2 + 2` actually
prints `4`, and an exploit *shape* (`import os`, `__class__`, `eval(...)`,
`os.system(...)`, `pickle`) is detected and rewarded. It NEVER executes
untrusted code: exploits are found by walking the AST, and harmless
expressions are evaluated by a hand-rolled arithmetic interpreter — there is
no `eval()`/`exec()` anywhere in this file. Safe *and* real.
"""
from __future__ import annotations

import ast
import operator
from dataclasses import dataclass, field


@dataclass
class ReplResult:
    output: list[str] = field(default_factory=list)
    exploit: bool = False
    exit: bool = False
    alarm: bool = False
    exploit_key: str = ""


# Attribute / name shapes that read as a sandbox escape or shell-out.
_EXPLOIT_ATTRS = {"__class__", "__subclasses__", "__bases__", "__mro__",
                  "__globals__", "__builtins__", "__import__", "__dict__",
                  "system", "popen", "spawn", "fork", "exec", "execve"}
_EXPLOIT_NAMES = {"eval", "exec", "compile", "__import__", "open", "globals",
                  "locals", "getattr", "setattr", "vars", "breakpoint",
                  "memoryview"}
_EXPLOIT_MODULES = {"os", "sys", "subprocess", "socket", "shutil", "pickle",
                    "ctypes", "importlib", "builtins", "pty", "code", "marshal"}

# Safe binary / unary / comparison operators for the arithmetic sandbox.
_BINOPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
}
# Largest str/list/tuple the sandbox will build. The terminal accepts ~78
# characters, which is enough for `"a" * 10**18` and `"%100000000s" % "x"`.
# Those used to allocate (or raise MemoryError) on the game thread and kill
# the process. Ordinary repeats (`"ab" * 3`) stay under this.
_MAX_RESULT = 10_000
_FORMAT_FLAGS = set("-#+0 ")
_FORMAT_TYPES = set("diouxXeEfFgGcrs")
_UNARYOPS = {ast.UAdd: operator.pos, ast.USub: operator.neg, ast.Not: operator.not_}
_CMPOPS = {
    ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
    ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
}


class _Unsafe(Exception):
    """Raised by the arithmetic evaluator when it meets a node it won't touch."""


def _seq_repeat_too_big(left, right, limit: int = _MAX_RESULT) -> bool:
    """True when `left * right` would build a str/list/tuple past `limit`.

    An empty sequence times any int is empty, which Python returns without
    allocating, so that stays allowed. Bool is an int subclass (`"a" * True`)
    and is a one-character repeat, not a bomb.
    """
    seq = count = None
    if isinstance(left, (str, list, tuple)) and type(right) is int:
        seq, count = left, right
    elif isinstance(right, (str, list, tuple)) and type(left) is int:
        seq, count = right, left
    else:
        return False
    if count <= 0 or len(seq) == 0:
        return False
    return count > limit or len(seq) > limit or len(seq) * count > limit


def _format_too_wide(fmt, value, limit: int = _MAX_RESULT) -> bool:
    """True when `fmt % value` would pad a field wider than `limit`.

    Literal widths (`%100000000s`) and star widths (`%*s` % (10**9, "x"))
    both allocate before the result is ever printed. Precision (`%.*s`) only
    truncates, so it is not a width. A malformed specifier returns False and
    the real formatter raises, which the caller turns into an error line.
    """
    if not isinstance(fmt, str):
        return False
    mapping = isinstance(value, dict)
    args = [] if mapping else (list(value) if isinstance(value, tuple) else [value])
    ai = 0
    i = 0
    n = len(fmt)
    while i < n:
        if fmt[i] != "%":
            i += 1
            continue
        if i + 1 < n and fmt[i + 1] == "%":
            i += 2
            continue
        i += 1
        keyed = False
        if i < n and fmt[i] == "(":
            end = fmt.find(")", i + 1)
            if end < 0:
                return False
            i = end + 1
            keyed = True
        while i < n and fmt[i] in _FORMAT_FLAGS:
            i += 1
        width = None
        if i < n and fmt[i] == "*":
            if mapping or ai >= len(args) or type(args[ai]) is not int:
                return False
            width = args[ai]
            ai += 1
            i += 1
        else:
            j = i
            while j < n and fmt[j].isdigit():
                j += 1
            if j > i:
                width = int(fmt[i:j])
                i = j
        if i < n and fmt[i] == ".":
            i += 1
            if i < n and fmt[i] == "*":
                if not mapping:
                    ai += 1
                i += 1
            else:
                while i < n and fmt[i].isdigit():
                    i += 1
        if i < n and fmt[i] in _FORMAT_TYPES:
            i += 1
            if not mapping and not keyed:
                ai += 1
        else:
            return False
        if isinstance(width, int) and abs(width) > limit:
            return True
    return False


class ReplSession:
    """A `>>>` prompt. Real syntax, safe arithmetic, AST-based exploit detection."""

    prompt = ">>> "

    def __init__(self, *, exploit_key: str = "repl_injection", motd: str = ""):
        self.exploit_key = exploit_key
        self.motd = motd

    def banner(self) -> list[str]:
        lines = ["Python 3.11 (compliance sandbox) — type `exit()` to leave."]
        if self.motd:
            lines.append(self.motd)
        return lines

    # ------------------------------------------------------------------
    def execute(self, line: str) -> ReplResult:
        src = (line or "").strip()
        if not src:
            return ReplResult()
        if src in ("exit", "exit()", "quit", "quit()"):
            return ReplResult(output=["now leaving the interpreter."], exit=True)

        try:
            tree = ast.parse(src)
        except SyntaxError as e:
            return ReplResult(output=[
                '  File "<stdin>", line 1',
                f"    {src}",
                f"SyntaxError: {e.msg}"])

        if self._is_exploit(tree):
            return ReplResult(
                output=["Traceback (most recent call last):",
                        '  File "<stdin>", line 1, in <module>',
                        "  ...sandbox boundary dissolved. that should not have worked."],
                exploit=True, exploit_key=self.exploit_key)

        # Real Python, not an exploit: try to actually evaluate simple math.
        if len(tree.body) == 1 and isinstance(tree.body[0], ast.Expr):
            try:
                value = self._safe_eval(tree.body[0].value)
            except _Unsafe:
                return ReplResult(output=["<object> — sandbox won't render that."])
            except ZeroDivisionError:
                return ReplResult(output=["Traceback (most recent call last):",
                                          "ZeroDivisionError: division by zero"])
            except OverflowError:
                return ReplResult(output=["OverflowError: result too large for the sandbox"])
            except MemoryError:
                # Backstop if a size check is missed. Never let it kill the run.
                return ReplResult(output=["MemoryError: result too large for the sandbox"])
            except TypeError as e:
                return ReplResult(output=[f"TypeError: {e}"])
            except ValueError as e:
                return ReplResult(output=[f"ValueError: {e}"])
            return ReplResult(output=[repr(value)])

        # Valid statement (assignment, loop, def…) but nothing to print.
        return ReplResult(output=[""])

    # ------------------------------------------------------------------
    def _is_exploit(self, tree: ast.AST) -> bool:
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name.split(".")[0] for a in node.names]
                else:
                    names = [(node.module or "").split(".")[0]]
                if any(n in _EXPLOIT_MODULES for n in names):
                    return True
                return True   # any import in a debt-collection REPL is a break-in
            if isinstance(node, ast.Attribute) and node.attr in _EXPLOIT_ATTRS:
                return True
            if isinstance(node, ast.Name) and node.id in _EXPLOIT_NAMES:
                return True
            if isinstance(node, ast.Call):
                fn = node.func
                if isinstance(fn, ast.Name) and fn.id in _EXPLOIT_NAMES:
                    return True
                if isinstance(fn, ast.Attribute) and fn.attr in _EXPLOIT_ATTRS:
                    return True
        return False

    # ------------------------------------------------------------------
    def _safe_eval(self, node: ast.AST):
        """Evaluate the arithmetic/literal subset by hand — no eval(), ever."""
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float, str, bool, complex)) or node.value is None:
                return node.value
            raise _Unsafe
        if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
            left, right = self._safe_eval(node.left), self._safe_eval(node.right)
            self._guard(node.op, left, right)
            return _BINOPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARYOPS:
            return _UNARYOPS[type(node.op)](self._safe_eval(node.operand))
        if isinstance(node, ast.BoolOp):
            vals = [self._safe_eval(v) for v in node.values]
            result = vals[0]
            for v in vals[1:]:
                result = (result and v) if isinstance(node.op, ast.And) else (result or v)
            return result
        if isinstance(node, ast.Compare):
            left = self._safe_eval(node.left)
            for op, comp in zip(node.ops, node.comparators):
                right = self._safe_eval(comp)
                if type(op) not in _CMPOPS or not _CMPOPS[type(op)](left, right):
                    return False
                left = right
            return True
        if isinstance(node, (ast.List, ast.Tuple)):
            vals = [self._safe_eval(e) for e in node.elts]
            return vals if isinstance(node, ast.List) else tuple(vals)
        raise _Unsafe

    @staticmethod
    def _guard(op, left, right) -> None:
        """Refuse cheap DoS: giant exponents, sequence repeats, format widths."""
        if isinstance(op, ast.Pow):
            try:
                if abs(right) > 128 or abs(left) > 10_000:
                    raise OverflowError
            except TypeError:
                raise _Unsafe
            return
        if isinstance(op, ast.Mult) and _seq_repeat_too_big(left, right):
            raise OverflowError
        if isinstance(op, ast.Mod) and _format_too_wide(left, right):
            raise OverflowError
