from conftest import run
from step_tracer.models import BranchExecution
from step_tracer.tracer import StepTracer


def test_branch_condition_recorded(tracer: StepTracer) -> None:
    ctx = run(
        tracer,
        """
        x = 1
        if x > 0:
            pass
    """,
    )
    branch = next(e for e in ctx.execution_trace if isinstance(e, BranchExecution))
    assert branch.condition_str == "x > 0"
    assert branch.condition_result is True
