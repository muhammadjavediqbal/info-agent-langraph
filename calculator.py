"""
Calculator Tool
Safely evaluates math expressions using Python's ast module
(avoids the security risks of raw eval())
"""

import ast
import math
import operator
from langchain_core.tools import tool


# Safe operators whitelist
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}

# Safe math functions whitelist
SAFE_FUNCTIONS = {
    "sqrt": math.sqrt,
    "abs":  abs,
    "ceil": math.ceil,
    "floor": math.floor,
    "log":  math.log,
    "log2": math.log2,
    "log10": math.log10,
    "sin":  math.sin,
    "cos":  math.cos,
    "tan":  math.tan,
    "pi":   math.pi,
    "e":    math.e,
    "round": round,
    "pow":  pow,
}


def _safe_eval(node):
    """Recursively evaluate an AST node using only safe operators and functions."""
    if isinstance(node, ast.Constant):  # e.g. 42, 3.14
        return node.value

    elif isinstance(node, ast.Name):
        # Allow named constants like pi, e
        name = node.id
        if name in SAFE_FUNCTIONS:
            val = SAFE_FUNCTIONS[name]
            if callable(val):
                raise ValueError(f"'{name}' is a function, not a constant. Call it with ().")
            return val
        raise ValueError(f"Unknown name: '{name}'")

    elif isinstance(node, ast.Call):
        # Allow whitelisted math functions
        if isinstance(node.func, ast.Name) and node.func.id in SAFE_FUNCTIONS:
            func = SAFE_FUNCTIONS[node.func.id]
            if not callable(func):
                raise ValueError(f"'{node.func.id}' is not callable.")
            args = [_safe_eval(arg) for arg in node.args]
            return func(*args)
        raise ValueError(f"Function not allowed: '{ast.dump(node.func)}'")

    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Unsupported operator: {op_type}")
        left  = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return SAFE_OPERATORS[op_type](left, right)

    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Unsupported unary operator: {op_type}")
        operand = _safe_eval(node.operand)
        return SAFE_OPERATORS[op_type](operand)

    else:
        raise ValueError(f"Unsupported expression type: {type(node)}")


@tool
def calculator(expression: str) -> str:
    """
    Evaluate a mathematical expression and return the result.
    Supports: +, -, *, /, **, %, //
    Also supports: sqrt(), abs(), ceil(), floor(), log(), sin(), cos(), tan(), pi, e

    Examples:
        "2 + 2"           -> "4"
        "10 * (3 + 2)"    -> "50"
        "2 ** 10"         -> "1024"
        "sqrt(144)"       -> "12.0"
        "sin(pi / 2)"     -> "1.0"

    Args:
        expression: A mathematical expression as a string.

    Returns:
        The computed result as a plain string.
    """
    try:
        tree   = ast.parse(expression, mode="eval")
        result = _safe_eval(tree.body)

        # Format: suppress unnecessary trailing .0 for whole numbers
        if isinstance(result, float) and result.is_integer():
            formatted = str(int(result))
        else:
            formatted = str(result)

        return f"{expression} = {formatted}"

    except ZeroDivisionError:
        return "Error: Division by zero"
    except Exception as e:
        return f"Error evaluating '{expression}': {str(e)}"