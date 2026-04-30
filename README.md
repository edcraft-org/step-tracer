# Step Tracer

A Python code execution tracer using AST (Abstract Syntax Tree) transformation to provide detailed insights into program execution.

## Overview

Step Tracer automatically instruments Python code to track its execution at a granular level. By transforming the AST of your Python code, it captures detailed information about function calls, variable changes, loop iterations, and conditional branches without requiring manual instrumentation.

## Features

- **Function Call Tracking**: Records function names, arguments, and return values
- **Variable Monitoring**: Tracks variable assignments, modifications, and their values at each execution point
- **Loop Analysis**: Captures loop execution details including iteration counts and per-iteration tracking
- **Branch Execution**: Records conditional statements (if/else) and their evaluation results
- **Scope Management**: Maintains scope hierarchy (global, function, class) throughout execution
- **Zero Manual Instrumentation**: Automatically transforms code via AST manipulation

## Installation

Using uv:

```bash
uv add git+https://github.com/edcraft-org/step-tracer.git
```

Using pip:

```bash
pip install git+https://github.com/edcraft-org/step-tracer.git
```

For a specific branch, tag, or commit:

```bash
uv add git+https://github.com/edcraft-org/step-tracer.git@branch-name
```

## Usage

### Basic Example

```python
from step_tracer import StepTracer

# Initialize the tracer
tracer = StepTracer()

# Your Python code as a string
source_code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

result = fibonacci(5)
"""

# Transform the code
transformed_code = tracer.transform_code(source_code)

# Execute and get execution context
exec_ctx = tracer.execute_transformed_code(transformed_code)

# Access execution trace
for execution in exec_ctx.execution_trace:
    print(f"Line {execution.line_number}: {execution.stmt_type}")

# Access variable snapshots
for var in exec_ctx.variables:
    print(f"{var.name} = {var.value} (line {var.line_number})")
```

## How It Works

Step Tracer uses Python's `ast` module to:

1. **Parse** the source code into an Abstract Syntax Tree
2. **Transform** the AST by injecting tracking calls at key points:
   - Before/after function calls
   - Around loop structures
   - After variable assignments
   - Around conditional branches
3. **Execute** the transformed code with an `ExecutionContext` that records all tracking events
4. **Return** a complete execution trace with variable snapshots

The transformation is transparent to the executed code, meaning the program's behavior remains unchanged.

## Data Structures

### ExecutionContext

The main container for execution data:

- `execution_trace`: List of all statement executions
- `variables`: List of all variable snapshots
- `scope_stack`: Current scope hierarchy
- `execution_stack`: Current execution stack

### Statement Types

- **StatementExecution**: Base class for all execution records
- **FunctionCall**: Captures function execution with arguments and return values
- **LoopExecution**: Records loop structure and iteration count
- **LoopIteration**: Individual loop iteration details
- **BranchExecution**: If/else conditional execution
- **VariableSnapshot**: Variable value at a specific execution point

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/edcraft-org/step-tracer.git
cd step_tracer

# Install dependencies
make install
```

### Running Tests

```bash
make test
```

### Code Quality

```bash
# Run linter
make lint

# Run type checker
make type-check

# Run all checks
make all-checks
```

## Design Notes

### Why `visit_Call` is not used for function call tracking

We are unable to define `visit_Call` on the `NodeTransformer` and instrument every call in one place, because of a fundamental constraint in Python's AST: **`ast.NodeTransformer` can only replace a node with another node of the same kind**.

A statement visitor (e.g. `visit_Return`) can return a *list* of statements, allowing new statements to be inserted before or after the original. But `visit_Call` must return an *expression* — it cannot emit extra statements to set up a temp variable or open a `with` block. Call tracking requires both: a statement that executes the call and captures the return value, and an expression that references that result.

Instead, the transformer uses a `extract_calls` helper that walks an arbitrary expression, replaces every `Call` node with a fresh temp variable, and returns the tracking statements to prepend. The statement-level visitors (`visit_Return`, `visit_Assign`, `visit_Expr`, etc.) call `extract_calls` on their expressions and emit the resulting statements.

### `self.x` assignments record the whole instance, not the attribute value

When an instance attribute is assigned (`self.x = val`), the tracer resolves the target to the base name `self` and records a deepcopy of the **entire object** as the snapshot value. The `access_path` will be `"self.x"` but `value` will be the full instance state at that point, not just `val`.

```python
class Point:
    def __init__(self, x, y):
        self.x = x   # snapshot: value=Point(x=x, y=<unset>), access_path="self.x"
        self.y = y   # snapshot: value=Point(x=x, y=y),       access_path="self.y"
```

### Class-body annotations without a value are not tracked

A bare annotation in a class body (`x: int`) does not produce a variable snapshot. Only annotated assignments that include a value (`x: int = 0`) are instrumented.

```python
class Foo:
    x: int        # NOT tracked — no value to snapshot
    y: int = 0    # tracked normally
```

## Known Limitations

### Function calls inside scope-creating expressions are not tracked

Calls that appear inside a **lambda**, **list/set/dict comprehension**, or **generator expression** are not instrumented. These constructs create their own inner scope, and the calls inside them only execute when that inner scope runs — which may be lazily, repeatedly, or never. The tracer cannot safely extract those calls out to the enclosing statement level without changing program semantics.

```python
# These calls will NOT appear in the execution trace:
squares = [compute(x) for x in data]   # call inside list comprehension
gen = (transform(x) for x in data)     # call inside generator expression
fn = lambda x: process(x)              # call inside lambda body
```

The outer expression itself (the comprehension or lambda) is still recorded when it is evaluated; only the calls *within* it are invisible to the tracer.

### Walrus operator (`:=`) assignments are not tracked

Variable assignments made via the walrus operator (`:=`) in expressions like `if (n := 10) > 5` are not captured in the variable snapshot list. The tracer only instruments standard assignment statements (`ast.Assign`, `ast.AugAssign`, `ast.AnnAssign`).

```python
# This assignment will NOT appear in variable snapshots:
if (n := 10) > 5:
    pass
```

### Class support is not implemented

Variables assigned in a **class body**, instance attributes set via `self`, and class attributes accessed through `cls` or the class name are not tracked. The tracer does not create a class scope, so class-level assignments are invisible to the variable snapshot list and the scope hierarchy.

```python
# None of these will appear in variable snapshots or the scope hierarchy:
class Foo:
    x = 10          # class-body variable — no class scope created

    def __init__(self):
        self.x = 1  # instance attribute — not recorded as a snapshot

    @classmethod
    def set_value(cls, v):
        cls.value = v  # class attribute via cls — not recorded
```

Similarly, mutating a class attribute from outside (`Foo.x = 99`) is not captured within the class's scope, and method scopes are not linked to a parent class scope in the scope tree.

## Requirements

- Python >= 3.12

## License

MIT License - see [LICENSE](LICENSE) file for details.
