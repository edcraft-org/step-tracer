"""Step Tracer - Python code execution tracer using AST transformation."""

from importlib.metadata import version

__version__ = version("step-tracer")

from step_tracer.models import (
    BranchExecution,
    ExecutionContext,
    FunctionCall,
    LoopExecution,
    LoopIteration,
    Scope,
    StatementExecution,
    StatementExecutionTracker,
    VariableSnapshot,
)
from step_tracer.tracer import StepTracer

__all__ = [
    "__version__",
    "StepTracer",
    "ExecutionContext",
    "StatementExecution",
    "LoopExecution",
    "LoopIteration",
    "FunctionCall",
    "BranchExecution",
    "VariableSnapshot",
    "Scope",
    "StatementExecutionTracker",
]
