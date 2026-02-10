#!/usr/bin/env python3
"""
Sandbox execution script for step-tracer.
Reads transformed code from stdin, executes with tracing, returns JSON via stdout.
"""

import json
import sys
import traceback
from typing import Any

from step_tracer.models import ExecutionContext, InternalExecutionContext
from step_tracer.step_tracer_utils import StepTracerUtils


def main() -> None:
    """Main execution function."""
    result: dict[str, Any] = {"ok": False, "error": None, "execution_context": None}

    try:
        transformed_code = sys.stdin.read()

        if not transformed_code.strip():
            raise ValueError("No code provided on stdin")

        exec_ctx = InternalExecutionContext()
        step_tracer_utils = StepTracerUtils()

        globals_dict = {
            "_step_tracer_exec_ctx": exec_ctx,
            "_step_tracer_utils": step_tracer_utils,
        }

        exec(transformed_code, globals_dict)

        # Convert internal context to external Pydantic model
        external_ctx = ExecutionContext(
            execution_trace=exec_ctx.execution_trace,
            variables=exec_ctx.variables,
        )

        result["ok"] = True
        result["execution_context"] = external_ctx.model_dump(mode="json")

    except Exception as e:
        result["error"] = {
            "type": type(e).__name__,
            "message": str(e),
            "traceback": traceback.format_exc(),
        }

    print(json.dumps(result, ensure_ascii=False))  # noqa: T201


if __name__ == "__main__":
    main()
