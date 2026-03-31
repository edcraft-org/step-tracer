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


def test_function_call_with_mutated_name_arg_records_updated_value(
    tracer: StepTracer,
) -> None:
    ctx = run(
        tracer,
        """
        def increment_first(lst):
            lst[0] += 1
        arr = [1, 2, 3]
        increment_first(arr)
    """,
    )
    arr_values = [v.value for v in ctx.variables if v.name == "arr" and v.scope_id == 0]
    assert [1, 2, 3] in arr_values  # recorded at assignment
    assert [2, 2, 3] in arr_values  # re-recorded after helper mutates it


def test_function_call_with_dict_arg_mutation_records_updated_value(
    tracer: StepTracer,
) -> None:
    ctx = run(
        tracer,
        """
        def add_key(d, key, val):
            d[key] = val
        data = {}
        add_key(data, "x", 42)
    """,
    )
    assert any(
        v.value == {"x": 42}
        for v in ctx.variables
        if v.name == "data" and v.scope_id == 0
    )


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


def test_nonlocal_variable_lands_in_outer_scope(tracer: StepTracer) -> None:
    ctx = run(
        tracer,
        """
        def outer():
            x = 1
            def inner():
                nonlocal x
                x = 99
            inner()
        outer()
    """,
    )
    outer_call = next(
        e
        for e in ctx.execution_trace
        if isinstance(e, FunctionCall) and e.name == "outer"
    )
    x_snapshots = [v for v in ctx.variables if v.name == "x"]
    # the x = 99 assignment should be recorded in outer's scope, not inner's
    assert all(v.scope_id == outer_call.func_scope_id for v in x_snapshots)


def test_global_keyword_variable_lands_in_global_scope(tracer: StepTracer) -> None:
    ctx = run(
        tracer,
        """
        x = 0
        def bump():
            global x
            x = 42
        bump()
    """,
    )
    x_snapshots = [v for v in ctx.variables if v.name == "x"]
    assert all(v.scope_id == 0 for v in x_snapshots)


def test_recursive_calls_each_get_own_scope(tracer: StepTracer) -> None:
    ctx = run(
        tracer,
        """
        def fact(n):
            if n <= 1:
                return 1
            return n * fact(n - 1)
        fact(3)
    """,
    )
    fact_calls = [
        e
        for e in ctx.execution_trace
        if isinstance(e, FunctionCall) and e.name == "fact"
    ]
    n_snapshots = [v for v in ctx.variables if v.name == "n"]
    assert len(fact_calls) == 3
    scope_ids = {v.scope_id for v in n_snapshots}
    assert len(scope_ids) == 3, "each recursive call should have its own scope"


def test_for_loop_variable_is_in_enclosing_scope(tracer: StepTracer) -> None:
    ctx = run(
        tracer,
        """
        for i in range(3):
            pass
    """,
    )
    i_snapshots = [v for v in ctx.variables if v.name == "i"]
    assert all(v.scope_id == 0 for v in i_snapshots)
    assert i_snapshots[-1].value == 2


def test_annotated_assignment_records_variable(tracer: StepTracer) -> None:
    ctx = run(tracer, "x: int = 5")
    var = next(v for v in ctx.variables if v.name == "x")
    assert var.value == 5
    assert var.scope_id == 0


def test_star_unpacking_records_all_variables(tracer: StepTracer) -> None:
    ctx = run(tracer, "a, *b, c = [1, 2, 3, 4, 5]")
    a_snap = next(v for v in ctx.variables if v.name == "a")
    b_snap = next(v for v in ctx.variables if v.name == "b")
    c_snap = next(v for v in ctx.variables if v.name == "c")
    assert a_snap.value == 1
    assert b_snap.value == [2, 3, 4]
    assert c_snap.value == 5


def test_nested_tuple_unpacking_records_all_variables(tracer: StepTracer) -> None:
    ctx = run(tracer, "(a, b), c = (1, 2), 3")
    a_snap = next(v for v in ctx.variables if v.name == "a")
    b_snap = next(v for v in ctx.variables if v.name == "b")
    c_snap = next(v for v in ctx.variables if v.name == "c")
    assert a_snap.value == 1
    assert b_snap.value == 2
    assert c_snap.value == 3
