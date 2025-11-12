"""
Safe Expression Parser

This module provides safe evaluation of mathematical expressions without the security
risks of using eval(). Only whitelisted mathematical operations are allowed.

Technologies: AST parsing, secure expression evaluation
"""

import ast
import operator
from typing import Dict, Any, Union
import logging

logger = logging.getLogger(__name__)


class SafeExpressionError(Exception):
    """Exception raised for unsafe or invalid expressions"""

    pass


class SafeExpressionParser:
    """
    Safe parser for mathematical expressions in metric formulas

    Replaces the unsafe eval() usage with AST-based parsing that only allows
    whitelisted mathematical operations.
    """

    # Allowed operators
    ALLOWED_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    # Allowed comparison operators (for conditional expressions)
    ALLOWED_COMPARISONS = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
    }

    # Allowed functions
    ALLOWED_FUNCTIONS = {
        "abs": abs,
        "min": min,
        "max": max,
        "round": round,
        "sum": sum,
        "len": len,
        "int": int,
        "float": float,
    }

    def __init__(self, max_depth: int = 10, max_nodes: int = 100):
        """
        Initialize safe expression parser

        Args:
            max_depth: Maximum AST depth to prevent deeply nested expressions
            max_nodes: Maximum number of nodes to prevent complex expressions
        """
        self.max_depth = max_depth
        self.max_nodes = max_nodes

    def evaluate(self, expression: str, namespace: Dict[str, Any]) -> Union[float, int, bool]:
        """
        Safely evaluate mathematical expression

        Args:
            expression: Mathematical expression string
            namespace: Dictionary of variable names to values

        Returns:
            Result of expression evaluation

        Raises:
            SafeExpressionError: If expression contains unsafe operations
        """
        try:
            # Parse expression into AST
            tree = ast.parse(expression.strip(), mode="eval")

            # Validate AST safety
            self._validate_ast(tree)

            # Evaluate the expression
            result = self._eval_node(tree.body, namespace, depth=0)

            logger.debug(f"Evaluated expression '{expression}' = {result}")
            return result

        except (SyntaxError, ValueError) as e:
            raise SafeExpressionError(f"Invalid expression syntax: {e}")
        except Exception as e:
            raise SafeExpressionError(f"Expression evaluation failed: {e}")

    def _validate_ast(self, tree: ast.AST) -> None:
        """
        Validate that AST only contains safe operations

        Args:
            tree: AST to validate

        Raises:
            SafeExpressionError: If AST contains unsafe operations
        """
        node_count = 0

        for node in ast.walk(tree):
            node_count += 1

            # Check node count limit
            if node_count > self.max_nodes:
                raise SafeExpressionError(f"Expression too complex (>{self.max_nodes} nodes)")

            # Check for disallowed node types
            disallowed_nodes = [ast.Import, ast.ImportFrom, ast.Global]

            # Add ast.Exec only if it exists (removed in Python 3.x)
            if hasattr(ast, "Exec"):
                disallowed_nodes.append(ast.Exec)

            if isinstance(node, tuple(disallowed_nodes)):
                raise SafeExpressionError(f"Import/exec statements not allowed")

            if isinstance(node, ast.Attribute):
                raise SafeExpressionError("Attribute access not allowed")

            if isinstance(node, ast.Subscript):
                raise SafeExpressionError("Subscript operations not allowed")

            if isinstance(node, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
                raise SafeExpressionError("Comprehensions not allowed")

            if isinstance(node, (ast.Lambda, ast.FunctionDef, ast.ClassDef)):
                raise SafeExpressionError("Function/class definitions not allowed")

            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id not in self.ALLOWED_FUNCTIONS:
                        raise SafeExpressionError(f"Function '{node.func.id}' not allowed")
                else:
                    raise SafeExpressionError("Only simple function calls allowed")

    def _eval_node(self, node: ast.AST, namespace: Dict[str, Any], depth: int = 0) -> Any:
        """
        Recursively evaluate AST node

        Args:
            node: AST node to evaluate
            namespace: Variable namespace
            depth: Current recursion depth

        Returns:
            Evaluated result

        Raises:
            SafeExpressionError: If evaluation fails or unsafe operation attempted
        """
        # Check depth limit
        if depth > self.max_depth:
            raise SafeExpressionError(f"Expression too deeply nested (>{self.max_depth})")

        # Handle different node types
        if isinstance(node, ast.Constant):  # Python 3.8+
            return node.value

        elif hasattr(ast, "Num") and isinstance(node, ast.Num):  # Python < 3.8
            return node.n

        elif hasattr(ast, "Str") and isinstance(node, ast.Str):  # Python < 3.8
            return node.s

        elif hasattr(ast, "NameConstant") and isinstance(node, ast.NameConstant):  # Python < 3.8
            return node.value

        elif isinstance(node, ast.Name):
            if node.id not in namespace:
                raise SafeExpressionError(f"Undefined variable: {node.id}")
            return namespace[node.id]

        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, namespace, depth + 1)
            right = self._eval_node(node.right, namespace, depth + 1)

            op_func = self.ALLOWED_OPERATORS.get(type(node.op))
            if not op_func:
                raise SafeExpressionError(f"Operator {type(node.op).__name__} not allowed")

            try:
                return op_func(left, right)
            except ZeroDivisionError:
                raise SafeExpressionError("Division by zero")
            except Exception as e:
                raise SafeExpressionError(f"Operation failed: {e}")

        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand, namespace, depth + 1)

            op_func = self.ALLOWED_OPERATORS.get(type(node.op))
            if not op_func:
                raise SafeExpressionError(f"Unary operator {type(node.op).__name__} not allowed")

            return op_func(operand)

        elif isinstance(node, ast.Compare):
            left = self._eval_node(node.left, namespace, depth + 1)

            result = True
            for op, right_node in zip(node.ops, node.comparators):
                right = self._eval_node(right_node, namespace, depth + 1)

                op_func = self.ALLOWED_COMPARISONS.get(type(op))
                if not op_func:
                    raise SafeExpressionError(f"Comparison {type(op).__name__} not allowed")

                result = result and op_func(left, right)
                left = right  # For chained comparisons

            return result

        elif isinstance(node, ast.Call):
            func_name = node.func.id
            if func_name not in self.ALLOWED_FUNCTIONS:
                raise SafeExpressionError(f"Function '{func_name}' not allowed")

            func = self.ALLOWED_FUNCTIONS[func_name]
            args = [self._eval_node(arg, namespace, depth + 1) for arg in node.args]

            # No keyword arguments allowed for security
            if node.keywords:
                raise SafeExpressionError("Keyword arguments not allowed")

            try:
                return func(*args)
            except Exception as e:
                raise SafeExpressionError(f"Function call failed: {e}")

        elif isinstance(node, ast.IfExp):
            test = self._eval_node(node.test, namespace, depth + 1)
            if test:
                return self._eval_node(node.body, namespace, depth + 1)
            else:
                return self._eval_node(node.orelse, namespace, depth + 1)

        elif isinstance(node, (ast.List, ast.Tuple)):
            return [self._eval_node(item, namespace, depth + 1) for item in node.elts]

        else:
            raise SafeExpressionError(f"Node type {type(node).__name__} not allowed")

    def validate_expression(self, expression: str) -> bool:
        """
        Validate expression without evaluation

        Args:
            expression: Expression to validate

        Returns:
            True if expression is safe, False otherwise
        """
        try:
            tree = ast.parse(expression.strip(), mode="eval")
            self._validate_ast(tree)
            return True
        except (SyntaxError, SafeExpressionError):
            return False


# Global parser instance for reuse
_parser = SafeExpressionParser()


def safe_eval(expression: str, namespace: Dict[str, Any]) -> Union[float, int, bool]:
    """
    Convenience function for safe expression evaluation

    Args:
        expression: Mathematical expression to evaluate
        namespace: Dictionary of variable names to values

    Returns:
        Evaluation result

    Raises:
        SafeExpressionError: If expression is unsafe or invalid
    """
    return _parser.evaluate(expression, namespace)


def is_safe_expression(expression: str) -> bool:
    """
    Check if expression is safe to evaluate

    Args:
        expression: Expression to check

    Returns:
        True if safe, False otherwise
    """
    return _parser.validate_expression(expression)


# Example usage and testing
if __name__ == "__main__":
    print("🔒 Testing Safe Expression Parser")
    print("=" * 50)

    # Test safe expressions
    safe_tests = [
        ("2 + 3", {}),
        ("x * 2", {"x": 5}),
        ("abs(x - y)", {"x": 3, "y": 7}),
        ("max(a, b, c)", {"a": 1, "b": 5, "c": 3}),
        ("total_revenue / customer_count", {"total_revenue": 1000, "customer_count": 10}),
        ("round(revenue * 1.1, 2)", {"revenue": 123.456}),
        ("x if x > 0 else 0", {"x": -5}),
        ("sum([1, 2, 3, 4])", {}),
    ]

    parser = SafeExpressionParser()

    print("✅ Testing safe expressions:")
    for expr, ns in safe_tests:
        try:
            result = parser.evaluate(expr, ns)
            print(f"  '{expr}' = {result}")
        except SafeExpressionError as e:
            print(f"  ❌ '{expr}' failed: {e}")

    # Test unsafe expressions
    unsafe_tests = [
        "__import__('os').system('echo hack')",
        "open('/etc/passwd').read()",
        "eval('2+2')",
        "exec('print(\"hack\")')",
        "total_mrr.__class__.__bases__[0]",
        "getattr(total_mrr, '__class__')",
        "[x for x in range(1000000)]",  # DoS attempt
        "lambda x: x",
        "def hack(): pass",
        "x.method()",
        "x[0]",
        "import os",
    ]

    print(f"\n🛡️ Testing unsafe expressions (should all fail):")
    for expr in unsafe_tests:
        try:
            result = parser.evaluate(expr, {"x": 1, "total_mrr": 100})
            print(f"  ❌ '{expr}' = {result} (SHOULD HAVE FAILED!)")
        except SafeExpressionError:
            print(f"  ✅ '{expr}' correctly blocked")
        except Exception as e:
            print(f"  ⚠️ '{expr}' failed with: {e}")

    print(f"\n🎉 Safe expression parser tests complete!")
