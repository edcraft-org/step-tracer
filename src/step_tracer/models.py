from dataclasses import dataclass, field
from types import TracebackType
from typing import Any


@dataclass
class StatementExecution:
    """Base class for recording statement execution."""

    execution_id: int
    scope_id: int
    line_number: int
    stmt_type: str = field(default="statement", init=False)
    end_execution_id: int | None = field(default=None, init=False)

    def set_end_execution_id(self, end_execution_id: int) -> None:
        self.end_execution_id = end_execution_id


@dataclass
class LoopExecution(StatementExecution):
    """Records loop execution."""

    loop_type: str
    num_iterations: int = 0

    def __post_init__(self) -> None:
        self.stmt_type = "loop"

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


@dataclass
class LoopIteration(StatementExecution):
    """Records loop iteration."""

    iteration_num: int
    loop_execution_id: int

    def __post_init__(self) -> None:
        self.stmt_type = "loop_iteration"


@dataclass
class FunctionCall(StatementExecution):
    """Records function call execution."""

    name: str
    func_full_name: str
    func_call_exec_ctx_id: int
    func_def_line_num: int | None = None
    arguments: dict[str, Any] = field(default_factory=dict[str, Any])
    return_value: Any = None

    def __post_init__(self) -> None:
        self.stmt_type = "function"

    def reset_args(self) -> None:
        self.arguments = {}

    def add_arg(self, name: str, value: Any) -> None:
        self.arguments[name] = value

    def set_func_def_line_num(self, line_num: int) -> None:
        self.func_def_line_num = line_num

    def set_return_value(self, return_value: Any) -> None:
        self.return_value = return_value


@dataclass
class BranchExecution(StatementExecution):
    """Records if/else execution."""

    condition_str: str
    condition_result: bool

    def __post_init__(self) -> None:
        self.stmt_type = "branch"


class StatementExecutionTracker:
    """Context manager that ensures execution push/pop happen safely."""

    def __init__(
        self, exec_ctx: "ExecutionContext", execution: StatementExecution
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


@dataclass
class VariableSnapshot:
    """Records a variable's value at a specific point in execution."""

    var_id: int
    name: str
    value: Any
    access_path: str
    line_number: int
    scope_id: int
    execution_id: int
    stmt_type: str = "variable"


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


class ExecutionContext:
    """Manages overall program execution state."""

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
            value=value,
            access_path=access_path,
            line_number=line_number,
            scope_id=scope_id,
            execution_id=execution_id,
        )
        self.variables.append(snapshot)
