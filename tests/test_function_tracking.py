from conftest import run
from step_tracer.models import FunctionCall
from step_tracer.tracer import StepTracer


def test_builtin_function_call_recorded(tracer: StepTracer) -> None:
    ctx = run(tracer, "abs(-3)")
    call = next(
        e
        for e in ctx.execution_trace
        if isinstance(e, FunctionCall) and e.name == "abs"
    )
    assert call.name == "abs"
    assert call.return_value == 3
    assert call.arguments == {"_arg0": -3}


def test_user_defined_function_recorded(tracer: StepTracer) -> None:
    ctx = run(
        tracer,
        """
        def add(a, b):
            return a + b
        add(1, 2)
    """,
    )
    call = next(
        e
        for e in ctx.execution_trace
        if isinstance(e, FunctionCall) and e.name == "add"
    )
    assert call.func_def_line_num == 1
    assert call.arguments == {"a": 1, "b": 2}
    assert call.return_value == 3


def test_function_call_gets_own_scope(tracer: StepTracer) -> None:
    ctx = run(
        tracer,
        """
        def foo():
            pass
        foo()
    """,
    )
    call = next(
        e
        for e in ctx.execution_trace
        if isinstance(e, FunctionCall) and e.name == "foo"
    )
    assert call.func_scope_id is not None
    assert call.func_scope_id != 0


def test_return_call_in_binop(tracer: StepTracer) -> None:
    ctx = run(
        tracer,
        """
        def double(n):
            return n * 2
        def main():
            return 1 + double(3)
        main()
    """,
    )
    call = next(
        e
        for e in ctx.execution_trace
        if isinstance(e, FunctionCall) and e.name == "double"
    )
    assert call.arguments == {"n": 3}
    assert call.return_value == 6


def test_return_multiple_calls(tracer: StepTracer) -> None:
    ctx = run(
        tracer,
        """
        def inc(n):
            return n + 1
        def main():
            return inc(1) + inc(2)
        main()
    """,
    )
    calls = [
        e
        for e in ctx.execution_trace
        if isinstance(e, FunctionCall) and e.name == "inc"
    ]
    assert len(calls) == 2
    assert {c.arguments["n"] for c in calls} == {1, 2}


def test_return_nested_call_as_argument(tracer: StepTracer) -> None:
    ctx = run(
        tracer,
        """
        def double(n):
            return n * 2
        def main():
            return double(double(3))
        main()
    """,
    )
    calls = [
        e
        for e in ctx.execution_trace
        if isinstance(e, FunctionCall) and e.name == "double"
    ]
    assert len(calls) == 2
    return_values = {c.return_value for c in calls}
    assert return_values == {6, 12}


def test_nested_call_references_parent_execution(tracer: StepTracer) -> None:
    ctx = run(
        tracer,
        """
        def outer():
            abs(-1)
        outer()
    """,
    )
    outer_call = next(
        e
        for e in ctx.execution_trace
        if isinstance(e, FunctionCall) and e.name == "outer"
    )
    abs_call = next(
        e
        for e in ctx.execution_trace
        if isinstance(e, FunctionCall) and e.name == "abs"
    )
    assert abs_call.func_call_exec_ctx_id == outer_call.execution_id
