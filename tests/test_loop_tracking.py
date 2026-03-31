from conftest import run
from step_tracer.models import LoopExecution, LoopIteration
from step_tracer.tracer import StepTracer


def test_for_loop_records_execution_and_iterations(tracer: StepTracer) -> None:
    ctx = run(tracer, "for i in range(3): pass")
    loop = next(e for e in ctx.execution_trace if isinstance(e, LoopExecution))
    assert loop.loop_type == "for"
    assert loop.num_iterations == 3
    iterations = [e for e in ctx.execution_trace if isinstance(e, LoopIteration)]
    assert len(iterations) == 3
    assert all(it.loop_execution_id == loop.execution_id for it in iterations)


def test_for_loop_variable_recorded_each_iteration(tracer: StepTracer) -> None:
    ctx = run(tracer, "for i in range(3): pass")
    loop_var_values = [v.value for v in ctx.variables if v.name == "i"]
    assert loop_var_values == [0, 1, 2]


def test_while_loop_records_execution_and_iterations(tracer: StepTracer) -> None:
    ctx = run(
        tracer,
        """
        i = 0
        while i < 3:
            i += 1
    """,
    )
    loop = next(e for e in ctx.execution_trace if isinstance(e, LoopExecution))
    assert loop.loop_type == "while"
    assert loop.num_iterations == 3
