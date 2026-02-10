"""Comprehensive test suite for Docker sandbox execution."""

import pytest

from step_tracer import StepTracer
from step_tracer.sandbox import SandboxExecutionError


class TestBasicExecution:
    """Test basic sandboxed execution functionality."""

    def test_simple_variable_assignment(self) -> None:
        """Test that simple variable assignments are tracked in sandbox."""
        tracer = StepTracer()
        code = """
x = 10
y = 20
result = x + y
"""
        transformed = tracer.transform_code(code)
        exec_ctx = tracer.execute_transformed_code(transformed)

        # Verify variables were tracked
        var_names = [v.name for v in exec_ctx.variables]
        assert "x" in var_names
        assert "y" in var_names
        assert "result" in var_names

        # Verify values
        result_var = next(v for v in exec_ctx.variables if v.name == "result")
        assert result_var.value == 30

    def test_function_call_tracking(self) -> None:
        """Test that function calls are tracked in sandbox."""
        tracer = StepTracer()
        code = """
def add(a, b):
    return a + b

result = add(5, 3)
"""
        transformed = tracer.transform_code(code)
        exec_ctx = tracer.execute_transformed_code(transformed)

        # Verify function calls were tracked
        function_calls = [
            e for e in exec_ctx.execution_trace if e.stmt_type == "function"
        ]
        assert len(function_calls) > 0

        # Verify result
        result_var = next(v for v in exec_ctx.variables if v.name == "result")
        assert result_var.value == 8

    def test_loop_tracking(self) -> None:
        """Test that loops are tracked in sandbox."""
        tracer = StepTracer()
        code = """
total = 0
for i in range(5):
    total += i
"""
        transformed = tracer.transform_code(code)
        exec_ctx = tracer.execute_transformed_code(transformed)

        # Verify loop iterations
        loop_execs = [e for e in exec_ctx.execution_trace if e.stmt_type == "loop"]
        assert len(loop_execs) > 0

        # Verify final total (get last snapshot)
        total_vars = [v for v in exec_ctx.variables if v.name == "total"]
        assert len(total_vars) > 0
        assert total_vars[-1].value == 10

    def test_branch_tracking(self) -> None:
        """Test that branches are tracked in sandbox."""
        tracer = StepTracer()
        code = """
x = 15
if x > 10:
    result = "large"
else:
    result = "small"
"""
        transformed = tracer.transform_code(code)
        exec_ctx = tracer.execute_transformed_code(transformed)

        # Verify branch execution
        branch_execs = [e for e in exec_ctx.execution_trace if e.stmt_type == "branch"]
        assert len(branch_execs) > 0

        # Verify result
        result_var = next(v for v in exec_ctx.variables if v.name == "result")
        assert result_var.value == "large"


class TestErrorHandling:
    """Test error handling in sandbox."""

    def test_user_code_exception(self) -> None:
        """Test that user code exceptions are properly reported."""
        tracer = StepTracer()
        code = """
x = 10
y = 0
result = x / y  # Division by zero
"""
        transformed = tracer.transform_code(code)

        with pytest.raises(SandboxExecutionError) as exc_info:
            tracer.execute_transformed_code(transformed)

        assert "ZeroDivisionError" in str(exc_info.value)

    def test_invalid_syntax(self) -> None:
        """Test handling of invalid Python syntax."""
        tracer = StepTracer()

        # This will fail during transformation (ast.parse)
        with pytest.raises(SyntaxError):
            tracer.transform_code("def invalid syntax:")


class TestSerialization:
    """Test serialization of complex data structures."""

    def test_nested_data_structures(self) -> None:
        """Test serialization of nested lists and dicts."""
        tracer = StepTracer()
        code = """
data = {
    'numbers': [1, 2, 3],
    'nested': {
        'a': 10,
        'b': 20
    }
}
"""
        transformed = tracer.transform_code(code)
        exec_ctx = tracer.execute_transformed_code(transformed)

        data_var = next(v for v in exec_ctx.variables if v.name == "data")
        assert isinstance(data_var.value, dict)
        assert data_var.value["numbers"] == [1, 2, 3]
        assert data_var.value["nested"]["a"] == 10

    def test_custom_objects(self) -> None:
        """Test serialization of custom class instances."""
        tracer = StepTracer()
        code = """
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

p = Point(3, 4)
"""
        transformed = tracer.transform_code(code)
        exec_ctx = tracer.execute_transformed_code(transformed)

        # Custom objects should be serialized (repr)
        p_var = next(v for v in exec_ctx.variables if v.name == "p")
        assert isinstance(p_var.value, str)
        assert "Point object at" in p_var.value
