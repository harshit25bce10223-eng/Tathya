"""Bounded expression parser for the proof sandbox. Never executes input code."""
import ast
import math
import re
from typing import Any


def solve(goals: list[str], assumptions: list[str], numeric: list[dict[str, Any]], timeout: int) -> dict[str, Any]:
    from z3 import And, Bool, BoolVal, Not, Or, Real, RealVal, Solver, is_bool, sat, unsat

    if not 1 <= timeout <= 30:
        raise ValueError("Timeout must be between 1 and 30 seconds.")
    if len(goals) + len(assumptions) + len(numeric) > 100:
        raise ValueError("Use at most 100 constraints.")
    solver = Solver()
    solver.set(timeout=timeout * 1000)
    variables: dict[str, Any] = {}
    kinds: dict[str, str] = {}

    def variable(name: str, kind: str):
        if not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]{0,63}", name):
            raise ValueError("Use a short variable name containing letters, digits or underscores.")
        if name in kinds and kinds[name] != kind:
            raise ValueError(f"{name} cannot be both a number and a boolean.")
        kinds[name] = kind
        if name not in variables:
            variables[name] = Bool(name) if kind == "bool" else Real(name)
        return variables[name]

    def expression(node, kind="bool", depth=0):
        if depth > 12:
            raise ValueError("Expression is too complex.")
        if isinstance(node, ast.Name):
            return variable(node.id, kind)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return BoolVal(node.value)
            if isinstance(node.value, (int, float)) and math.isfinite(node.value):
                return RealVal(str(node.value))
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                return Not(expression(node.operand, "bool", depth + 1))
            if isinstance(node.op, ast.USub):
                return -expression(node.operand, "number", depth + 1)
        if isinstance(node, ast.BoolOp):
            values = [expression(v, "bool", depth + 1) for v in node.values]
            return And(*values) if isinstance(node.op, ast.And) else Or(*values)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult)):
            left = expression(node.left, "number", depth + 1)
            right = expression(node.right, "number", depth + 1)
            if isinstance(node.op, ast.Add): return left + right
            if isinstance(node.op, ast.Sub): return left - right
            return left * right
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            boolean = any(isinstance(n, ast.Constant) and isinstance(n.value, bool) for n in (node.left, node.comparators[0]))
            left = expression(node.left, "bool" if boolean else "number", depth + 1)
            right = expression(node.comparators[0], "bool" if boolean else "number", depth + 1)
            op = node.ops[0]
            if isinstance(op, ast.Eq): return left == right
            if isinstance(op, ast.NotEq): return left != right
            if isinstance(op, ast.Lt): return left < right
            if isinstance(op, ast.LtE): return left <= right
            if isinstance(op, ast.Gt): return left > right
            if isinstance(op, ast.GtE): return left >= right
        raise ValueError("Use variables, numeric comparisons, +, -, *, and boolean and/or/not. Natural-language statements are not proof constraints.")

    for text in goals + assumptions:
        if len(text) > 500:
            raise ValueError("Each expression must be at most 500 characters.")
        text = re.sub(r"\btrue\b", "True", text, flags=re.I)
        text = re.sub(r"\bfalse\b", "False", text, flags=re.I)
        try:
            value = expression(ast.parse(text, mode="eval").body)
            if not is_bool(value): raise ValueError("An expression must state a boolean condition.")
            solver.add(value)
        except (SyntaxError, TypeError) as exc:
            raise ValueError("Enter a valid comparison or boolean expression.") from exc
    for constraint in numeric:
        name = constraint.get("variable", "")
        op = constraint.get("operator", "")
        value = str(constraint.get("value", ""))
        if not re.fullmatch(r"[-+]?\d+(?:\.\d+)?", value):
            raise ValueError("Numeric constraints require a finite number.")
        left = variable(name, "number")
        right = RealVal(value)
        operations = {"eq": lambda: left == right, "neq": lambda: left != right,
                      "lt": lambda: left < right, "le": lambda: left <= right,
                      "gt": lambda: left > right, "ge": lambda: left >= right}
        if op not in operations: raise ValueError("Unsupported comparison operator.")
        solver.add(operations[op]())
    if not goals and not assumptions and not numeric:
        raise ValueError("Add at least one constraint.")
    result = solver.check()
    model = {name: str(solver.model().eval(var, model_completion=True)) for name, var in variables.items()} if result == sat else None
    return {"satisfiable": True if result == sat else False if result == unsat else None,
            "model": model, "proof": "These constraints conflict." if result == unsat else None,
            "timed_out": result not in (sat, unsat) and solver.reason_unknown() == "timeout",
            "error": solver.reason_unknown() if result not in (sat, unsat) else None}
