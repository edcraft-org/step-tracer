from dataclasses import dataclass, field
from types import TracebackType
from typing import Any

from pydantic import BaseModel, Field


def safe_repr(obj: Any, max_len: int = 500) -> str:
    """
    Generate a safe repr with length limit.

    Args:
        obj: Object to represent
        max_len: Maximum length of repr string

    Returns:
        String representation, truncated if needed
    """
    try:
        r = repr(obj)
    except Exception:
        return f"<unrepr-able {type(obj).__name__}>"

    if len(r) > max_len:
        return r[:max_len] + "…"
    return r


def is_safe_value(value: Any) -> bool:
    """
    Check if a value is safe to store directly.

    Safe values include:
    - Primitives: None, bool, int, float, str
    - Collections: list, dict, set, tuple, frozenset (with safe contents)
    - Complex objects are stored as repr instead

    Args:
        value: The value to check

    Returns:
        True if the value is safe to store directly, False otherwise
    """
    # Primitives are always safe
    if value is None or isinstance(value, (bool, int, float, str)):
        return True

    # Recursively check lists, tuples and sets
    if isinstance(value, (list, tuple, set, frozenset)):
        return all(is_safe_value(item) for item in value)

    # Recursively check dicts
    if isinstance(value, dict):
        return all(isinstance(k, str) and is_safe_value(v) for k, v in value.items())

    # Everything else (custom objects, datetime, Path, etc.) -> not safe
    return False


class StatementExecution(BaseModel):
    """Base class for recording statement execution."""

    execution_id: int
    scope_id: int
    line_number: int
    stmt_type: str = "statement"
    end_execution_id: int | None = None

    model_config = {"frozen": False}

    def set_end_execution_id(self, end_execution_id: int) -> None:
        self.end_execution_id = end_execution_id


class LoopExecution(StatementExecution):
    """Records loop execution."""

    loop_type: str
    num_iterations: int = 0
    stmt_type: str = "loop"

    def start_iteration(self, execution_id: int, scope_id: int) -> "LoopIteration":
        iteration = LoopIteration(
            execution_id=execution_id,
            scope_id=scope_id,
            line_number=self.line_number,
            iteration_num=self.num_iterations,
            loop_execution_id=self.execution_id,
        )
        self.num_iterations += 1
        return iteration


class LoopIteration(StatementExecution):
    """Records loop iteration."""

    iteration_num: int
    loop_execution_id: int
    stmt_type: str = "loop_iteration"


class FunctionCall(StatementExecution):
    """Records function call execution."""

    name: str
    func_full_name: str
    func_call_exec_ctx_id: int
    func_def_line_num: int | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    return_value: Any = None
    stmt_type: str = "function"

    def reset_args(self) -> None:
        self.arguments = {}

    def add_arg(self, name: str, value: Any) -> None:
        """Add a function argument, converting unsafe values to repr."""
        self.arguments[name] = value if is_safe_value(value) else safe_repr(value)

    def set_func_def_line_num(self, line_num: int) -> None:
        self.func_def_line_num = line_num

    def set_return_value(self, return_value: Any) -> None:
        """Set the return value, converting unsafe values to repr."""
        self.return_value = (
            return_value if is_safe_value(return_value) else safe_repr(return_value)
        )


class BranchExecution(StatementExecution):
    """Records if/else execution."""

    condition_str: str
    condition_result: bool
    stmt_type: str = "branch"


class StatementExecutionTracker:
    """Context manager that ensures execution push/pop happen safely."""

    def __init__(
        self, exec_ctx: "InternalExecutionContext", execution: StatementExecution
    ) -> None:
        self.exec_ctx = exec_ctx
        self.execution = execution

    def __enter__(self) -> None:
        self.exec_ctx.push_execution(self.execution)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.exec_ctx.pop_execution()


class VariableSnapshot(BaseModel):
    """Records a variable's value at a specific point in execution."""

    var_id: int
    name: str
    value: Any
    access_path: str
    line_number: int
    scope_id: int
    execution_id: int
    stmt_type: str = "variable"

    model_config = {"arbitrary_types_allowed": True}


@dataclass
class Scope:
    """Represents a variable namespace."""

    scope_type: str  # 'global', 'function', 'class'
    scope_id: int
    parent: "Scope | None" = None
    children: list["Scope"] = field(default_factory=list["Scope"])

    def __post_init__(self) -> None:
        if self.parent:
            self.parent.children.append(self)


class InternalExecutionContext:
    """Internal runtime context managing program execution state with full tracking."""

    def __init__(self) -> None:
        self.execution_trace: list[StatementExecution] = []
        self.variables: list[VariableSnapshot] = []

        self.execution_stack: list[StatementExecution] = []
        self.scope_stack: list[Scope] = []

        self._execution_counter: int = 0  # 0 represents global scope
        self._scope_counter = 0
        self._var_id = 0

        self.global_scope = Scope("global", 0)
        self.scope_stack.append(self.global_scope)

    @property
    def current_execution(self) -> StatementExecution | None:
        return self.execution_stack[-1] if self.execution_stack else None

    @property
    def current_scope(self) -> Scope:
        return self.scope_stack[-1]

    def generate_execution_id(self) -> int:
        self._execution_counter += 1
        return self._execution_counter

    def generate_scope_id(self) -> int:
        self._scope_counter += 1
        return self._scope_counter

    def push_scope(self, scope: Scope) -> None:
        self.scope_stack.append(scope)

    def pop_scope(self) -> Scope:
        return self.scope_stack.pop()

    def push_execution(self, execution: StatementExecution) -> None:
        self.execution_trace.append(execution)
        self.execution_stack.append(execution)
        if isinstance(execution, FunctionCall):
            self.push_scope(
                Scope(
                    scope_type="function",
                    scope_id=self.generate_scope_id(),
                    parent=self.current_scope,
                )
            )

    def pop_execution(self) -> None:
        execution = self.execution_stack.pop()
        execution.set_end_execution_id(self._execution_counter)
        if isinstance(execution, FunctionCall):
            self.pop_scope()

    def track_stmt_exec(
        self, execution: StatementExecution
    ) -> StatementExecutionTracker:
        return StatementExecutionTracker(self, execution)

    def create_loop_execution(self, line_number: int, loop_type: str) -> LoopExecution:
        execution_id = self.generate_execution_id()
        scope_id = self.current_scope.scope_id
        loop_execution = LoopExecution(
            execution_id=execution_id,
            scope_id=scope_id,
            line_number=line_number,
            loop_type=loop_type,
        )
        return loop_execution

    def create_loop_iteration(self) -> LoopIteration:
        if isinstance(self.current_execution, LoopExecution):
            execution_id = self.generate_execution_id()
            scope_id = self.current_scope.scope_id
            iteration = self.current_execution.start_iteration(execution_id, scope_id)
            return iteration
        else:
            raise RuntimeError("No active loop execution to record iteration for.")

    def create_function_call(
        self, line_number: int, func_name: str, func_full_name: str
    ) -> FunctionCall:
        execution_id = self.generate_execution_id()
        scope_id = self.current_scope.scope_id
        func_call_exec_ctx_id = (
            self.current_execution.execution_id if self.current_execution else 0
        )
        function_execution = FunctionCall(
            execution_id=execution_id,
            scope_id=scope_id,
            line_number=line_number,
            name=func_name,
            func_full_name=func_full_name,
            func_call_exec_ctx_id=func_call_exec_ctx_id,
        )
        return function_execution

    def create_branch_execution(
        self, line_number: int, condition_str: str, condition_result: bool
    ) -> BranchExecution:
        execution_id = self.generate_execution_id()
        scope_id = self.current_scope.scope_id
        branch_execution = BranchExecution(
            execution_id=execution_id,
            scope_id=scope_id,
            line_number=line_number,
            condition_str=condition_str,
            condition_result=condition_result,
        )
        return branch_execution

    def record_variable(
        self, name: str, value: Any, access_path: str, line_number: int
    ) -> None:
        execution_id = (
            self.current_execution.execution_id if self.current_execution else 0
        )
        scope_id = self.current_scope.scope_id
        self._var_id += 1

        snapshot = VariableSnapshot(
            var_id=self._var_id,
            name=name,
            value=value if is_safe_value(value) else safe_repr(value),
            access_path=access_path,
            line_number=line_number,
            scope_id=scope_id,
            execution_id=execution_id,
        )
        self.variables.append(snapshot)


class ExecutionContext(BaseModel):
    """Output from code execution containing trace and variable snapshots."""

    execution_trace: list[StatementExecution]
    variables: list[VariableSnapshot]

    model_config = {"arbitrary_types_allowed": True}
