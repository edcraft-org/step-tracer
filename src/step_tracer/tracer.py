import ast
from typing import Any

from step_tracer.models import ExecutionContext
from step_tracer.step_tracer_utils import StepTracerUtils
from step_tracer.tracer_transformer import TracerTransformer


class StepTracer:
    def transform_code(self, source_code: str) -> str:
        """Transform source code to include execution tracking."""
        tree = ast.parse(source_code)
        transformer = TracerTransformer()
        new_tree = transformer.visit(tree)
        ast.fix_missing_locations(new_tree)
        return ast.unparse(new_tree)

    def execute_transformed_code(
        self, transformed_code: str, globals_dict: dict[str, Any] | None = None
    ) -> ExecutionContext:
        """Transform and execute code with tracing."""
        if globals_dict is None:
            globals_dict = {}

        exec_ctx = ExecutionContext()
        step_tracer_utils = StepTracerUtils()

        globals_dict.update(
            {
                "_step_tracer_exec_ctx": exec_ctx,
                "_step_tracer_utils": step_tracer_utils,
            }
        )

        exec(transformed_code, globals_dict)
        return exec_ctx
