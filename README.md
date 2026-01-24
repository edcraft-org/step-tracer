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

### From GitHub

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

### From Local Source

Using uv:

```bash
uv add /path/to/step-tracer
```

Or in editable mode for development:

```bash
uv pip install -e /path/to/step-tracer
```

Using pip:

```bash
pip install /path/to/step-tracer
```

Or in editable mode for development:

```bash
pip install -e /path/to/step-tracer
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

## Use Cases

- **Educational Tools**: Visualize program execution for learning programming concepts
- **Debugging**: Understand complex execution flows and variable states
- **Code Analysis**: Analyze program behavior and execution patterns
- **Testing**: Verify execution paths and variable states
- **Performance Analysis**: Identify hot paths and iteration counts

## Requirements

- Python >= 3.12

## License

MIT License - see [LICENSE](LICENSE) file for details.
