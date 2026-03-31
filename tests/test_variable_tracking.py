import pytest

from conftest import run
from step_tracer.models import FunctionCall
from step_tracer.tracer import StepTracer


def test_simple_assignment_records_variable(tracer: StepTracer) -> None:
    ctx = run(tracer, "x = 5")
    var = next(v for v in ctx.variables if v.name == "x")
    assert var.name == "x"
    assert var.value == 5
    assert var.scope_id == 0
    assert var.line_number == 1


def test_augmented_assignment_records_variable(tracer: StepTracer) -> None:
    ctx = run(
        tracer,
        """
        x = 1
        x += 10
    """,
    )
    values = [v.value for v in ctx.variables if v.name == "x"]
    assert values == [1, 11]


def test_tuple_unpacking_records_each_variable(tracer: StepTracer) -> None:
    ctx = run(tracer, "a, b = 1, 2")
    names = [v.name for v in ctx.variables]
    assert "a" in names
    assert "b" in names
    assert next(v for v in ctx.variables if v.name == "a").value == 1
    assert next(v for v in ctx.variables if v.name == "b").value == 2


def test_variable_in_function(tracer: StepTracer) -> None:
    ctx = run(
        tracer,
        """
        def foo():
            x = 42
        foo()
    """,
    )
    x_snap = next(v for v in ctx.variables if v.name == "x")
    foo_call = next(
        e
        for e in ctx.execution_trace
        if isinstance(e, FunctionCall) and e.name == "foo"
    )
    assert x_snap.scope_id == foo_call.func_scope_id
    assert x_snap.execution_id == foo_call.execution_id


def test_attribute_assignment_records_variable(tracer: StepTracer) -> None:
    ctx = run(
        tracer,
        """
        class Point:
            pass
        p = Point()
        p.x = 5
    """,
    )
    attr_snap = next(v for v in ctx.variables if v.access_path == "p.x")
    assert attr_snap.value.x == 5


def test_subscript_assignment_records_variable(tracer: StepTracer) -> None:
    ctx = run(
        tracer,
        """
        lst = [0, 1, 2]
        lst[1] = 99
    """,
    )
    item_snap = next(v for v in ctx.variables if v.access_path == "lst[1]")
    assert item_snap.value == [0, 99, 2]

@pytest.mark.skip(reason="Walrus operator support not implemented yet")
def test_walrus_operator_records_variable(tracer: StepTracer) -> None:
    ctx = run(
        tracer,
        """
        if (n := 10) > 5:
            pass
    """,
    )
    n_snap = next(v for v in ctx.variables if v.name == "n")
    assert n_snap.value == 10


def test_chained_assignment_records_all_targets(tracer: StepTracer) -> None:
    ctx = run(tracer, "a = b = 7")
    a_snap = next(v for v in ctx.variables if v.name == "a")
    b_snap = next(v for v in ctx.variables if v.name == "b")
    assert a_snap.value == 7
    assert b_snap.value == 7


def test_variable_value_preserves_type(tracer: StepTracer) -> None:
    ctx = run(
        tracer,
        """
        lst = [1, 2, 3]
        dct = {"key": "val"}
        flag = True
    """,
    )
    assert next(v for v in ctx.variables if v.name == "lst").value == [1, 2, 3]
    assert next(v for v in ctx.variables if v.name == "dct").value == {"key": "val"}
    assert next(v for v in ctx.variables if v.name == "flag").value is True


def test_variable_reassignment_records_new_value_with_same_name(
    tracer: StepTracer,
) -> None:
    ctx = run(
        tracer,
        """
        x = "hello"
        x = 42
    """,
    )
    snapshots = [v for v in ctx.variables if v.name == "x"]
    assert len(snapshots) == 2
    assert snapshots[0].value == "hello"
    assert snapshots[1].value == 42
