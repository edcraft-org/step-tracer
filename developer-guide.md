# Classes

## Steps

### Statement Execution
This is the base class for recording steps.

| Attribute | Description |
| --------- | ----------- |
| execution_id | A unique identifer to distinguish steps. |
| scope_id | The scope in which the step was performed. |
| line_number | The line number in the given code in which the step occurred. |
| stmt_type | The type of step. e.g. function, loop |
| end_execution_id | The last step performed within the current step. |

**End Execution Id**: 
Within a step, there can be other steps performed. This attribute enables us to determine the substeps of the current step.

For example,
```python
if True:    # execution_id 1
    f(1)    # execution_id 2
    g(2)    # execution_id 3
```

The branch step includes the function call steps. The end execution id of the branch step would be 3, referring to the final step performed within the branch.


### Loop Execution
This records a loop.

| Attribute | Description |
| --------- | ----------- |
| loop_type | `for` or `while` |
| num_iterations | The number of loop iterations performed. |

**Code Improvement**: `loop_type` can be an Enum or Literal instead of a string.


### Loop Iteration
This records each loop iteration.

| Attribute | Description |
| --------- | ----------- |
| iteration_num | The order in which this iteration appeared. |
| loop_execution_id | The execution_id of its parent loop. |

```python
for i in range(2):
    pass
for j in range(2):
    pass
```

The above code translates to the following loop executions and iterations (ignoring other types of steps):
```
Loop Execution (for i in range(3))
    - execution_id: 1
├── Loop Iteration
    - execution_id: 2
    - iteration_num: 1
    - loop_execution_id: 1
├── Loop Iteration
    - execution_id: 3
    - iteration_num: 2
    - loop_execution_id: 1

Loop Execution (execution_id: 4): for j in range(2)
├── Loop Iteration
    - execution_id: 5
    - iteration_num: 1
    - loop_execution_id: 4
├── Loop Iteration
    - execution_id: 6
    - iteration_num: 2
    - loop_execution_id: 4
```

### Function Call
This records both function calls and method calls.

| Attribute | Description |
| --------- | ----------- |
| name      | The name of the function or method. For example, `obj1.method1()`'s name is `method1`. |
| func_full_name | The name of the function or method including the object. For example, `obj1.method1()`'s full name is `obj1.method1`. |
| func_call_exec_ctx_id | The execution id of the parent step in which this function was executed. |
| func_def_line_num | The line number in which the function is defined (if any). |
| func_scope_id | The id of the scope created by this function. |
| arugments | A dictionary of argument names and values passed to the function (if any). |
| return_value | The return value of the function (if any). |

```python
def foo(x):
    my_set.add(x)
    return 1
foo(1)
```

The following function calls will be recorded:
* Function Call
  * `execution_id`: `1`
  * `end_execution_id`: `2`
  * `name`: `foo`
  * `func_full_name`: `foo`
  * `func_call_exec_ctx_id`: `0`
  * `func_def_line_num`: `1`
  * `func_scope_id`: `1`
  * `arguments`: `{x: 1}`
  * `return_value`: `1`
* Function Call
  * `execution_id`: `2`
  * `end_execution_id`: `2`
  * `name`: `add`
  * `func_full_name`: `my_set.add`
  * `func_call_exec_ctx_id`: `1`
  * `func_def_line_num`: `None`
  * `func_scope_id`: `2`
  * `arguments`: `{_arg0: 1}`
  * `return_value`: `None`

If the function/method is user-defined, the arugment name will be recorded based on the function definition.
For external functions/methods, the names of the arguments will be recorded if the names are given (e.g. `method1(item1=1)`). If the argument name is unknown, the argument name will be recorded as `_argX`, where `X` is the position of the argument.

**Code Improvement**: Explore recording the arguments in a tuple. E.g. arguments for `add(1, 2)` would be `(1, 2)`. This avoids using `_argX` as the name of the argument and avoids recording the arguments in both `visit_FunctionDef` and `visit_Expr`. This also avoids inconsistent argument namings as function calls with the function defined can have proper names while other function calls would be using `_argX`.


### Branch Execution
This records branches.

| Attribute | Description |
| --------- | ----------- |
| condition_str | The branch condition. |
| condition_result | Whether the branch evaluates to True or False. |

```python
if check(x):
    allow(x)
else:
    deny(x)
```
* condition_str: `check(x)`
* condition_result: `True` / `False`

When `elif` is used,

```python
if x == 1:
    x += 1
elif x == 2:
    x += 3
else:
    x -= 1
```

The recorded steps will be equivalent to having the following code.

```python
if x == 1:
    x += 1
else:
    if x == 2:
        x += 3
    else:
        x -= 1
```


## Variables

Variables are recorded separately from the statement executions as variable values are not considered steps in code. It also allows for future extensions separate from statement executions.

Variable assignments are also not recorded as statement executions. Instead, the value of the assigned variable is recorded as a `VariableSnapshot`.


### Variable Snapshot
This records a variable's value at a specific point in execution. This allow us to observe the changes in a variable's value over the code execution.

| Attribute | Description |
| --------- | ----------- |
| var_id | A unique identifer to distinguish variable snapshots. |
| name | The variable name. |
| value | The variable value. The value will be deepcopied to avoid mutations. |
| access_path | The path to the part of the object that was modified. For example, in `lst[0] = 1`, the access path will be `lst[0]`. |
| line_number | The line number in the code in which the variable value was recorded. |
| scope_id | The scope that the variable belongs to. This distinguishes variables with the same name in different scopes. |
| execution_id | The id of the statement execution in which the variable value was recorded. |


## Scope

A scope represents the variable namespace. The program starts with a global scope. Each function call creates a scope. Currently, the support for scope is incomplete. Class scope is not supported.


## Execution Context

This class represents the data collected from running the Step Tracer.

| Attribute | Description |
| --------- | ----------- |
| execution_trace | A list containing all the statement executions recorded. |
| variables | A list containing all the variable snapshots recorded. |
| execution_stack | A stack to keep track of the current executions. |
| scope_stack | A stack to keep track of the current scopes. |
| _execution_counter | A counter used to obtain the unique identifer for statement executions. |
| _scope_counter | A counter used to obtain the unique identifier for scopes. |
| _var_id | A counter used to obtain the unique identifier for variable snapshots. |
| global_scope | The global scope of the program. |

**Stacks**:

The `execution_stack` and `scope_stack` enables us to know which execution statement or scope to return to.

```python
def func1():
    func2()

def func2():
    return

func1()
```

Calling `func1` leads to:
* `execution_stack`: [func1]
* `scope_stack`: [func1]

Then calling `func2` from `func1` leads to:
* `execution_stack`: [func1, func2]
* `scope_stack`: [func1, func2]

After `func2` completes, its execution and scopes are popped.
* `execution_stack`: [func1]
* `scope_stack`: [func1]
So the current execution is now `func1`.

**Code Improvements**:
* The `execution trace` and `variables` can be combined into one list as there is currently no need for them to be separated.
* The `current_execution` property to be modified to be similar to the `current_scope`, where there is a global statement execution.


### Methods

This section covers some methods that require more explanations.

**`track_stmt_exec`**: This function is used to return a `StatementExecutionTracker`, which is a context manager to ensure that the statement execution is always added and popped from the stacks when completed.

**`record_nonlocal_variable`**: A non-local variable belongs to the nearest enclosing function scope. Hence, it searches through the most recent function scopes to find the nearest enclosing function scope.


## Utilities

The `StepTracerUtils` under `step_tracer_utils.py` is used to hold methods used in the AST transformer.
* `safe_deepcopy`: used to call `copy.deepcopy` and catch any exceptions. Refer to documentation on `copy.deepcopy` for possible exceptions.


# AST Transformer

The AST transformer is used to inject execution tracking code. As it traverses through the code, it uses the methods from the `ExecutionContext` to store execution information.

| Attribute | Description |
| --------- | ----------- |
| exec_ctx_name | The name of the variable containing the `ExecutionContext`. |
| utils_name | The name of the variable containing the `StepTracerUtils`. |
| _tmp_counter | This counter is used to assign unique variable names to temporary variables. |
| _current_global_vars | Set of global variables. |
| _current_nonlocal_vars | Set of current nonlocal variables. |


## General Helper Functions

* `_name`: used to create an `ast.Name` node.

* `_attr`: used to create an `ast.Attribute` node.

* `_call`: used to create an `ast.Call` node.

* `_exec_ctx_attr`: used to access a method of the `ExecutionContext`.

* `_current_exec_attr`: used to access a method of the current statement execution.

* `_safe_copy`: used to call the `safe_deepcopy` method of the `StepTracerUtils`.

* `_get_temp_var_name`: used to generate a unique temporary variable name.

* `_wrap_with_ctx`: used to add a `with` statement to handle the stacks using `StatementExecutionTracker`.

There are many helper methods to construct nodes to add tracking nodes into the tree. There are two ways to add nodes:
1. Construct AST nodes (as the current code has done)
2. Write the code as a string and parse it into an AST


## Variable Tracking

Variables are tracked by taking snapshots of them. When a variable assignment is encountered, a snapshot is taken. Currently, the Step Tracer covers standard assignment, annotated assignment and augmented assignment. Assignments using the walrus operator `:=` is not handled. 

As variables can be mutated beyond assignment statements, variable snapshots are also taken in other parts:

* `visit_For`: variables in `for` loop target (e.g. `x` and `y` in `for x, y in enumerate(lst)`)

* `visit_Expr`: objects of method calls (e.g. `arr` after `arr.sort()`) as some methods may mutate the object

* `visit_FunctionDef`/`visit_AsyncFunctionDef`: arugments of user defined functions are tracked as some functions may mutate the arugments. `*args` and `**kwargs` are tracked as a whole.

    **Code Improvements**: Track each position item and each keyword argument individually.

* `visit_Expr`: positional arugments of non-user-defined function calls are also tracked if they are `ast.Name` nodes. 
    * **Other types of arugments are NOT tracked as `VariableSnapshot`**, such as `foo(obj.attr)`, `foo(arr[0])` etc. unless it's user defined.
    * **Arugments of method calls are NOT tracked as `VariableSnapshot`** (e.g. no `VariableSnapshot` is created for `x` in `lst.append(x)`) unless it's user defined.

    **Code Improvements**: It seems like the arugments are only tracked in `visit_Expr` and is missing in areas such as `visit_Return` as it is not handled within `extract_calls`. It might be more suitable to include this within the `_expand_call` function, which is used within the `extract_calls` function. Arugments of function calls should also be tracked more generally instead of limited to the above cases.


### visit_Assign


`visit_Assign` works with assignment statements like `x = 1` and `a, b = 1, 2`. 
It uses `extract_calls` on the `RHS` to handle function calls within the `RHS` (explained further in [function tracking](#function-tracking) section). For example, `x = f(y) + g(z)`.

Then, variable names are extracted from the `LHS` using `_extract_variable_names`. For each variable, a variable tracking node is added to take a `VariableSnapshot`.

As `ast.Assign` can have multiple targets, e.g. `a = b = 1`, this function iterates through each target to extract variables names and insert tracking nodes.

**Example:** Modified Code (Simplified)

```python
a = b = 1
record_variable('a', deepcopy(a), 'a', 1)
record_variable('b', deepcopy(b), 'b', 1)
```


### visit_AugAssign

`visit_AugAssign` works with augmented assignments like `x += 1`. It similar to `visit_Assign` but there is always only one target in an augmented assignment.

**Example:** Modified Code (Simplified)

```python
x += 1
record_variable('x', deepcopy(x), 'x', 2)
```


### visit_AnnAssign

`visit_AnnAssign` works with annotated assignments such as `x: int = 1`. For `ast.AnnAssign` nodes that do not have a value such as in `x: int`, a variable snapshot will not be taken.

**Code Improvement**: It might be better to take a variable snapshot even if the annotated assignment has no initialiser (`x: int`) as it better reflects that the value of the variable is `None` instead of non-existent.

**Example:** Modified Code (Simplified)

```python
x: int # no snapshot taken
y: int = 1
record_variable('y', deepcopy(y), 'y', 2)
```


### Helpers

`_extract_variable_names`: 

Looks through the left-hand side of an assignment (which may contain multiple variables) and extracts variable names that are being assigned to.
Returns: list of tuples `[(name, access_path), ...]`

```python
x = 1          # [("x", "x")]
a, b = 1, 2    # [("a", "a"), ("b", "b")]
obj.x = 1      # [("obj", "obj.x")]
```

`_get_base_name`:

Used to get the root variable name and the access path by recursively searching for the root variable.
Returns: `(root_variable_name, access_path)`

```python
obj.attr = 1                 # ("obj", "obj.attr")
arr[0] = 1                   # ("arr", "arr[0]")
user.profile.name = "Bob"    # ("user", "user.profile.name")
```

While `_extract_variable_names` only passes `ast.Attribute` or `ast.Subscript` to `_get_base_name`, the value of these nodes is any `ast.expr`, thats why the function can return None.

`_find_global_nonlocal`:

Recursively walks through the node and collects names declared with `global` and `nonlocal`.

It skips nested functions.

```python
def outer():
    x = 1

    def inner():
        nonlocal x # inner nonlocal does not belong to outer
```

`_create_variable_tracking_call`: 

Based on the type of variable (global/nonlocal/normal), the relevant method of the `ExecutionContext` is used. The variable is **deepcopied** and stored as a `VariableSnapshot`.

`_add_variable_tracking_calls`:

Given a list of variables, it creates a variable tracking call for each variable.


## Function Tracking

Function calls can appear in multiple types of statements, such as:
* `ast.Expr`: e.g. `foo()`, `arr.sort()`
* `ast.Assign`: e.g. `x = foo()`
* `ast.Return`: e.g. `foo()`

Hence, when we visit these nodes, we call the helper function `extract_calls` to add function tracking nodes.

While the function calls are `ast.Call` nodes, we are unable to use `visit_Call` because `visit_Call` can only replace the `ast.Call` node with another node of the same kind. However, the current implementation will return a list of statements from the visit functions.

**Code Improvement**: Explore using `visit_Call` by returning a call to a **lambda function** to track function calls instead. The current implementation depends heavily on adding `extract_calls` to relevant nodes, which is not ideal it is easily to miss some out. (Refer to [visit_While](#visit_while) for an example.)


### visit_Expr

`visit_Expr` is mainly used as an alternative to `visit_Call` as the value of an `ast.Expr` can be `ast.Call`. Hence, we extract and track function calls from the value of an `ast.Expr` node using `extract_calls`. Refer to `extract_calls` explanation at [helper functions](#helper-functions).

`visit_Expr` also adds variable tracking nodes. As covered in [variable tracking](#variable-tracking), it tracks the object of method calls and function arguments. In the code, each tuple in `vars_to_track` refers to `(name, access_path, line_number)`.

**Example**:

```python
x = []
x.append(1)
```

Modified code (simplified):

```python
x = []
record_variable(name='x', value=deepcopy(x), access_path='x', line_number=1)
with track_stmt_exec(create_function_call(
    line_number=2, name='append', func_full_name='x.append')):
    add_arg('_arg0', deepcopy(1))
    _tmp_0 = x.append(1)
    set_return_value(deepcopy(_tmp_0))
_tmp_0 # ensures that the result is available after the context manager exits
record_variable('x', deepcopy(x), 'x', 2)
```

When taking a `VariableSnapshot` of the method call object, the variable tracked and the access path used is always the base object. **Code Improvement**:  It may be more accurate to record the full path instead. More consideration can be done.

**Example:**

```python
class A:
    def f(self):
        pass

a = A()
a.attr = A()
a.attr.f()
```

Modified code for `a.attr.f()` (simplified):
```python
with track_stmt_exec(create_function_call(
    line_number=7, name='f', func_full_name='a.attr.f')):
    _tmp_2 = a.attr.f()
    set_return_value(deepcopy(_tmp_2))
_tmp_2
record_variable(name='a', value=deepcopy(a), access_path='a', line_number=7) # currently name = access_path = base object
```


### visit_Return

The function calls are extracted and tracking nodes are added using `extract_calls`. We visit `ast.Return` nodes as return statements can contain function calls. For example, `return foo(x)`.


### visit_FunctionDef / visit_AsyncFunctionDef

Uses `_transform_func_def` to extract function information.


### Helper Functions

`extract_calls`: used to find function calls from an expression and add tracking nodes.

Suppose we have

```python
f(1) + g(h())
```

Then this expression would become similar to
```python
_temp1 = f(1)
_temp2 = h()
_temp3 = g(_temp2)
_temp4 = _temp1 + _temp3
```

This extraction is required because for each function call, a `with` statement is added.

To find all the function calls, we follow these steps:
* If we encounter a function call,
    * Recurse into the function being called. For example, `f()()` recurses into `f()` to extract `f()`.
    * Recurse into positional arguments. For example, for `f(g(), h())`, `g()` and `h()` are extracted.
    * Recurse into keyword arugments. For example, for `f(a=g())`, `g()` is extracted.
* Else, traverse the child expressions of the node. For example, `a + f(x)` is a `BinOp` so we will recursively process the children `a` and `f(x)`.

For each extracted function call, tracking statements are created using the helper function `_expand_call`.

We **skip scope-creating expressions** such as lambda functions. For example, `lambda: f()` and `(x for x in f())`.

If we extracted them, the code behaviour would change. Example:

```python
_temp1 = f()
lambda: _temp1
```

For comprehensions, they have their own scope. For example, `x` only exists within the comprehension scope `[f(x) for x in lst]`.

If it is extracted, `x` will be referenced outside the scope and `f(x)` will only be executed once.

```python
_temp1 = foo(x)
[_temp1 for x in data]
```

**Purpose**:

Function calls were initially tracked using `visit_Expr` and checking for `ast.Call`. However, this approach is unable to identify and track function calls in nodes like `BinOp` (`f() + g()`). Hence, we need to be able to find function calls in other types of nodes using `extract_calls`. As explained in [function tracking](#function-tracking), we can exploring improving this approach.

---
`_expand_call`: extracts relevant information from `ast.Call` nodes.

A `FunctionCall` object is created and the metadata of the function call is recorded.

The positional arguments and keyword arguments are recorded individually. Unnamed arugments are recorded as `_arg{idx}`, where `{idx}` is the position of the argument.

The return value is recorded. It first assigns the return value to a temporary variable so that we only evaluation the expression once. The temporary variable is used to store the return value into the `FunctionCall` and used to return to the code.

Refer to the example given in [visit_Expr](#visit_expr).

---

`_transform_func_def`: extracts relevant information from function definitions.

**Global and nonlocal variables handling**:

* Saves the parent's scope information on `global` and `nonlocal` declarations.

* Scan the function body for `global` and `nonlocal` declarations.

* Store the `global` and `nonlocal` declarations as current scope's metadata.

* Restore parent's scope information when leaving the function.

* **Code Inprovement**: Use a proper scope class instead.

**Arguments**:

During the function call, `_expand_call` would have collected information about the arguments passed into it. However, it may lack information such as the names of the arguments.

```python
def foo(x, y):
    return x + y

foo(1, 2) # does not know the argument names
```

Within the function definition, we know the arugment name. Hence, we clear the argument values that was tracked using the function call and track the arugment values again using the known names.

**Code Improvement**: `*args` and `**kwargs` are currently tracked as a whole. It should instead track each position item and each keyword argument individually, similar to `_expand_call`.

**Example:**

```python
def f(a, b, /, c, d=1, *args, e, f=2, **kwargs):
    pass

f(1, 2, 3, 4, 5, e=6, g=7, h=8)
```

Modifed code (simplified):

```python
def f(a, b, /, c, d=1, *args, e, f=2, **kwargs):
    reset_args()
    set_func_def_line_num(1)
    
    add_arg('a', deepcopy(a))
    record_variable('a', deepcopy(a), 'a', 1)
    
    add_arg('b', deepcopy(b))
    record_variable('b', deepcopy(b), 'b', 1)
    
    add_arg('c', deepcopy(c))
    record_variable('c', deepcopy(c), 'c', 1)
    
    add_arg('d', deepcopy(d))
    record_variable('d', deepcopy(d), 'd', 1)
    
    add_arg('e', deepcopy(e))
    record_variable('e', deepcopy(e), 'e', 1)
    
    add_arg('f', deepcopy(f))
    record_variable('f', deepcopy(f), 'f', 1)
    
    add_arg('args', deepcopy(args)) # recorded as a whole
    record_variable('args', deepcopy(args), 'args', 1)
    
    add_arg('kwargs', deepcopy(kwargs)) # recorded as a whole
    record_variable('kwargs', deepcopy(kwargs), 'kwargs', 1)
    
    pass

with track_stmt_exec(create_function_call(4, 'f', 'f')):
    add_arg('_arg0', deepcopy(1)) # arugment name unknown
    add_arg('_arg1', deepcopy(2))
    add_arg('_arg2', deepcopy(3))
    add_arg('_arg3', deepcopy(4))
    add_arg('_arg4', deepcopy(5))
    add_arg('e', deepcopy(6))
    add_arg('g', deepcopy(7))
    add_arg('h', deepcopy(8))
    _tmp_0 = f(1, 2, 3, 4, 5, e=6, g=7, h=8)
    set_return_value(deepcopy(_tmp_0))
_tmp_0
```

---

* `_get_func_name`: gets function name, returns `<lambda_or_unknown>` if unable to find the name.

* `_get_func_full_name`: gets function full name recursively, returns `<lambda_or_unknown>` if unable to find the name.

The below helper functions are used to make the code more readable. They are used to construct the AST nodes to call relevant methods of the `ExecutionContext` and `FunctionCall`.

* `_create_func_call`: helper function to call the `create_function_call` method of the `ExecutionContext`.

* `_create_add_arg_call`: helper function to call the `add_arg` function of the `FunctionCall`. It deepcopies the arugment value.

* `_create_record_func_return_call`: helper function to call the `set_return_value` method of the `FunctionCall`. It deepcopies the return value.

* `_create_set_func_def_line_num_call`: helper function to call the `set_func_def_line_num` method of the `FunctionCall`.

* `_create_reset_args_call`: helper function to call the `_create_reset_args_call` method of the `FunctionCall`.


## Loop Tracking

### visit_While

Handles `while` loops:
* Add code within the loop body to create a `LoopIteration`.
* Add code to create a `LoopExecution` outside the loop.

**Example:**

```python
x = 10
while x > 5:
    x -= 1
```

Modifed code (simplified):

```python
x = 10
record_variable('x', deepcopy(x), line_number=1)

with tract_stmt_exec(create_loop_execution(
    line_number=2,
    loop_type='while')):
    while x > 5:
        with track_stmt_exec(create_loop_iteration()):
            x -= 1
            record_variable('x', deepcopy(x), 'x', line_number=3)
```

**Code Improvement**: Function calls in `while` loop condition are not handled. For example, for `while f(x)`, `f(x)` is not tracked. This can be improved together with improvements required in the [function tracking](#function-tracking) section.

**Example:**

```python
def f(x):
    return x > 5

x = 10

while f(x):
    x -= 1
```

Modifed code (simplified, loop only):

```python
with tract_stmt_exec(create_loop_execution(
    line_number=6,
    loop_type='while')):
    while f(x): # function call is NOT tracked
        with track_stmt_exec(create_loop_iteration()):
            x -= 1
            record_variable('x', deepcopy(x), 'x', line_number=7)

# NOTE: The modified code will not be able to execute as the modified code for function definition includes calls to functions that only work if a FunctionCall has been created. Hence, this is a bug.
```


### visit_For

Handles `for` loops
* Adds code within the loop body to create a `LoopIteration`.
* Adds code to create a `LoopExecution` outside the loop.
* Extracts variable names from the variable(s) that receive each value from the iteration and creates variable tracking nodes. For example, `x` and `y` from `for x, y in enumerate(lst)`.
* Extracts and tracks function calls from the expression that produces the iterable being looped over. The iterable refers to `enumerate(lst)` in the above example.


### Helper Functions

* `_create_loop_exec_call`: used to make a call to `execution_context.create_loop_execution` to store information about the loop execution.

* `_create_loop_iter_call`: used to make a call to `execution_context.create_loop_iteration` to store information about the loop iteration.


## Branch Tracking

### visit_If

Suppose we have a branch `if f(x)`. We create a temporary variable to store the results of `f(x)`. This ensures the expression `f(x)` is only evaluated once to use in storing the branch information and for the original branch. Evaluating the expression more than once may change the code behaviour.

Then we create a branch tracking call to store the branch evaluation results using the temporary variable. We also wrap the branch in a context manager.

The condition string will be stored the same as the given code. Given `if f(x) and g(x)`, the condition string will be `f(x) and g(x)`.

**Example:**

```python
def f(x):
    return x % 2 == 0

def g(x):
    return x % 3 == 0

x = 6

if f(x) and g(x):
    pass
```

Modified code (for the branch):
```python
_step_tracer_tmp_0 = f(x) and g(x)
with _step_tracer_exec_ctx.track_stmt_exec(
    _step_tracer_exec_ctx.create_branch_execution(
        9, 
        'f(x) and g(x)',
        _step_tracer_tmp_0
    )):
    if _step_tracer_tmp_0:
        pass
```


### Helpers

* `_create_branch_execution`: used to make a call to `execution_context.create_branch_execution` to store information about the branch.


## Display Information

The following code can display information helpful in understanding the Step Tracer. Recommended to start with small code snippets.


**Display modified code**:

```python
import textwrap

from step_tracer.tracer import StepTracer


tracer = StepTracer()

def display_modified_code(code: str) -> None:
    dedented = textwrap.dedent(code).strip()
    transformed = tracer.transform_code(dedented)
    print(transformed)

code = """
x = 1
"""
display_modified_code(code)
```


**Display AST Tree of original code**:

```python
import ast
import textwrap

def display_ast(code: str) -> None:
    dedented = textwrap.dedent(code).strip()
    tree = ast.parse(dedented)
    print(ast.dump(tree, indent=4))

code = """
x = set()
x.add(1)
"""

display_ast(code)
```


**Display Execution Context**:

```python
import textwrap

from step_tracer.models import ExecutionContext
from step_tracer.tracer import StepTracer


tracer = StepTracer()
    
def run(code: str) -> ExecutionContext:
    dedented = textwrap.dedent(code).strip()
    transformed = tracer.transform_code(dedented)
    return tracer.execute_transformed_code(transformed)

def display_execution_context(exec_ctx: ExecutionContext) -> None:
    for step in exec_ctx.execution_trace:
        print(step)
    
    for var in exec_ctx.variables:
        print(var)

code = """
lst = []
lst.append(1)
"""

exec_ctx = run(code)
display_execution_context(exec_ctx)
```
