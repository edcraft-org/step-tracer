import ast

from step_tracer.models import ExecutionContext
from step_tracer.tracer_transformer import TracerTransformer


class StepTracer:
    def transform_code(self, source_code: str) -> str:
        """Transform source code to include execution tracking."""
        tree = ast.parse(source_code)
        transformer = TracerTransformer()
        new_tree = transformer.visit(tree)
        ast.fix_missing_locations(new_tree)
        return ast.unparse(new_tree)

    def execute_transformed_code(self, transformed_code: str) -> ExecutionContext:
        """
        Execute transformed code in a Docker sandbox with strict isolation.

        Args:
            transformed_code: The transformed Python code to execute

        Returns:
            ExecutionContext with execution trace and variables

        Raises:
            SandboxTimeoutError: If execution exceeds timeout
            SandboxExecutionError: If execution fails
        """
        from step_tracer.sandbox import SandboxExecutor

        executor = SandboxExecutor()
        return executor.execute(transformed_code)
