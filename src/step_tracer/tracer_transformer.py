import ast


class TracerTransformer(ast.NodeTransformer):
    """AST transformer that injects execution tracking code."""

    def __init__(self) -> None:
        super().__init__()
        self.exec_ctx_name = "_step_tracer_exec_ctx"

    ### Loop Tracking Code

    def visit_For(self, node: ast.For) -> list[ast.stmt]:
        """Transform for loops to track iterations."""
        self.generic_visit(node)

        # track variables assigned in the for loop target
        variables = self._extract_variable_names(node.target)
        for var_name, access_path in variables:
            track_call = self._create_variable_tracking_call(
                var_name, access_path, node.lineno
            )
            node.body.insert(0, track_call)

        iteration_body = self._wrap_with_ctx(node.body, self._create_loop_iter_call())
        node.body = [iteration_body]

        stmts: list[ast.stmt] = [node]

        if isinstance(node.iter, ast.Call):
            expanded_nodes = self.expand_call(node.iter)
            node.iter = expanded_nodes[-1].value
            stmts = [*expanded_nodes, node]

        loop = self._wrap_with_ctx(
            stmts, self._create_loop_exec_call(node.lineno, "for")
        )

        return [loop]

    def visit_While(self, node: ast.While) -> list[ast.stmt]:
        """Transform while loops to track iterations."""
        self.generic_visit(node)

        iteration_body = self._wrap_with_ctx(node.body, self._create_loop_iter_call())
        node.body = [iteration_body]

        loop = self._wrap_with_ctx(
            [node], self._create_loop_exec_call(node.lineno, "while")
        )

        return [loop]

    def _create_loop_exec_call(self, lineno: int, loop_type: str) -> ast.Call:
        return ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=self.exec_ctx_name, ctx=ast.Load()),
                attr="create_loop_execution",
                ctx=ast.Load(),
            ),
            args=[ast.Constant(value=lineno), ast.Constant(value=loop_type)],
            keywords=[],
        )

    def _create_loop_iter_call(self) -> ast.Call:
        return ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=self.exec_ctx_name, ctx=ast.Load()),
                attr="create_loop_iteration",
                ctx=ast.Load(),
            ),
            args=[],
            keywords=[],
        )

    ### Function Tracking Code

    def visit_Expr(self, node: ast.Expr) -> list[ast.stmt]:
        self.generic_visit(node)

        if isinstance(node.value, ast.Call):
            expanded_nodes: list[ast.stmt] = list(self.expand_call(node.value))

            # variable tracking: handles method calls with mutatable objects
            if isinstance(node.value.func, ast.Attribute):
                obj_name = self._get_base_name(node.value.func)
                if obj_name:
                    var_tracking_call = self._create_variable_tracking_call(
                        obj_name[0], obj_name[0], node.lineno
                    )
                    expanded_nodes.append(var_tracking_call)

            return expanded_nodes

        return [node]

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Transform function definitions to track execution."""
        self.generic_visit(node)

        reset_args_call = self._create_reset_args_call()
        set_func_def_line_num_call = self._create_set_func_def_line_num_call(
            node.lineno
        )
        new_body: list[ast.stmt] = [reset_args_call, set_func_def_line_num_call]

        for arg in node.args.args:
            arg_value_expr = ast.Name(id=arg.arg, ctx=ast.Load())
            arg_tracking_call = self._create_add_arg_call(arg.arg, arg_value_expr)
            new_body.append(arg_tracking_call)

            var_tracking_call = self._create_variable_tracking_call(
                arg.arg, arg.arg, node.lineno
            )
            new_body.append(var_tracking_call)

        new_body.extend(node.body)
        node.body = new_body

        return node

    def expand_call(self, node: ast.Call) -> tuple[ast.With, ast.Expr]:
        """Transform function calls to track execution."""
        self.generic_visit(node)

        # Record function call
        func_name = self._get_func_name(node.func)
        func_full_name = self._get_func_full_name(node.func)
        create_func_call = self._create_func_call(node, func_name, func_full_name)

        # Record arguments
        arg_stmts: list[ast.Expr] = []

        for idx, arg in enumerate(node.args):
            arg_stmts.append(self._create_add_arg_call(f"_arg{idx}", arg))

        for kw in node.keywords:
            if kw.arg:
                arg_stmts.append(self._create_add_arg_call(kw.arg, kw.value))

        # Record return value
        tmp_ret_var = "_step_tracer_tmp_ret"
        temp_node = ast.Assign(
            targets=[ast.Name(id=tmp_ret_var, ctx=ast.Store())],
            value=node,
        )
        record_ret_node = self._create_record_func_return_call(
            ast.Name(id=tmp_ret_var, ctx=ast.Load())
        )

        new_node = ast.Expr(ast.Name(id=tmp_ret_var, ctx=ast.Load()))

        return (
            self._wrap_with_ctx(
                [*arg_stmts, temp_node, record_ret_node], create_func_call
            ),
            new_node,
        )

    def _create_func_call(
        self, node: ast.Call, func_name: str, func_full_name: str
    ) -> ast.Call:
        """Create a call to track a function call."""
        return ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=self.exec_ctx_name, ctx=ast.Load()),
                attr="create_function_call",
                ctx=ast.Load(),
            ),
            args=[
                ast.Constant(value=node.lineno),
                ast.Constant(value=func_name),
                ast.Constant(value=func_full_name),
            ],
            keywords=[],
        )

    def _create_add_arg_call(self, name: str, arg_value: ast.expr) -> ast.Expr:
        return ast.Expr(
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Attribute(
                        value=ast.Name(id=self.exec_ctx_name, ctx=ast.Load()),
                        attr="current_execution",
                        ctx=ast.Load(),
                    ),
                    attr="add_arg",
                    ctx=ast.Load(),
                ),
                args=[
                    ast.Constant(value=name),
                    ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id="_step_tracer_utils", ctx=ast.Load()),
                            attr="safe_deepcopy",
                            ctx=ast.Load(),
                        ),
                        args=[arg_value],
                        keywords=[],
                    ),
                ],
                keywords=[],
            )
        )

    def _create_record_func_return_call(self, return_value: ast.expr) -> ast.Expr:
        return ast.Expr(
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Attribute(
                        value=ast.Name(id=self.exec_ctx_name, ctx=ast.Load()),
                        attr="current_execution",
                        ctx=ast.Load(),
                    ),
                    attr="set_return_value",
                    ctx=ast.Load(),
                ),
                args=[
                    ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id="_step_tracer_utils", ctx=ast.Load()),
                            attr="safe_deepcopy",
                            ctx=ast.Load(),
                        ),
                        args=[return_value],
                        keywords=[],
                    ),
                ],
                keywords=[],
            )
        )

    def _create_set_func_def_line_num_call(self, line_num: int) -> ast.Expr:
        return ast.Expr(
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Attribute(
                        value=ast.Name(id=self.exec_ctx_name, ctx=ast.Load()),
                        attr="current_execution",
                        ctx=ast.Load(),
                    ),
                    attr="set_func_def_line_num",
                    ctx=ast.Load(),
                ),
                args=[ast.Constant(value=line_num)],
                keywords=[],
            )
        )

    # TODO: Refactor to reduce redundancy
    def _create_reset_args_call(self) -> ast.Expr:
        return ast.Expr(
            value=ast.Call(
                func=ast.Attribute(
                    value=ast.Attribute(
                        value=ast.Name(id=self.exec_ctx_name, ctx=ast.Load()),
                        attr="current_execution",
                        ctx=ast.Load(),
                    ),
                    attr="reset_args",
                    ctx=ast.Load(),
                ),
                args=[],
                keywords=[],
            )
        )

    def _get_func_name(self, func: ast.expr) -> str:
        if isinstance(func, ast.Name):
            return func.id
        elif isinstance(func, ast.Attribute):
            return func.attr
        else:
            return "<lambda_or_unknown>"

    def _get_func_full_name(self, func: ast.expr) -> str:
        if isinstance(func, ast.Name):
            return func.id
        elif isinstance(func, ast.Attribute):
            value_name = self._get_func_full_name(func.value)
            return f"{value_name}.{func.attr}"
        else:
            return "<lambda_or_unknown>"

    ### Variable Tracking Code

    def visit_Assign(self, node: ast.Assign) -> list[ast.stmt]:
        """Transform assignments to track variable changes."""
        self.generic_visit(node)

        statements: list[ast.stmt] = [node]

        if isinstance(node.value, ast.Call):
            expanded_nodes = self.expand_call(node.value)
            node.value = expanded_nodes[-1].value
            statements = list(expanded_nodes)
            statements[-1] = node

        for target in node.targets:
            variables = self._extract_variable_names(target)
            self._add_variable_tracking_calls(statements, variables, node.lineno)

        return statements

    def visit_AugAssign(self, node: ast.AugAssign) -> list[ast.stmt]:
        """Transform augmented assignments to track variable changes."""
        self.generic_visit(node)

        statements: list[ast.stmt] = [node]
        variables = self._extract_variable_names(node.target)
        self._add_variable_tracking_calls(statements, variables, node.lineno)

        return statements

    def visit_AnnAssign(self, node: ast.AnnAssign) -> list[ast.stmt]:
        """Transform annotated assignments to track variable changes."""
        self.generic_visit(node)

        if node.value is None:
            return [node]

        statements: list[ast.stmt] = [node]
        variables = self._extract_variable_names(node.target)
        self._add_variable_tracking_calls(statements, variables, node.lineno)

        return statements

    def _add_variable_tracking_calls(
        self, statements: list[ast.stmt], variables: list[tuple[str, str]], lineno: int
    ) -> None:
        for var_name, access_path in variables:
            track_call = self._create_variable_tracking_call(
                var_name, access_path, lineno
            )
            statements.append(track_call)

    def _extract_variable_names(self, target: ast.expr) -> list[tuple[str, str]]:
        """
        Extract all variable names from an assignment target.

        Returns a list of (var_name, access_path) tuples.
        """
        variables: list[tuple[str, str]] = []

        if isinstance(target, ast.Name):
            variables.append((target.id, target.id))
        elif isinstance(target, (ast.Tuple | ast.List)):
            for elt in target.elts:
                variables.extend(self._extract_variable_names(elt))
        elif isinstance(target, ast.Starred) and isinstance(target.value, ast.Name):
            variables.append((target.value.id, target.value.id))
        elif isinstance(target, (ast.Attribute | ast.Subscript)):
            base = self._get_base_name(target)
            if base:
                variables.append(base)

        return variables

    def _get_base_name(self, node: ast.expr) -> tuple[str, str] | None:
        """Extract the base name and access path."""
        if isinstance(node, ast.Name):
            return node.id, node.id
        elif isinstance(node, ast.Attribute):
            base = self._get_base_name(node.value)
            if base:
                base_name, access_path = base
                return base_name, f"{access_path}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            base = self._get_base_name(node.value)
            if base:
                base_name, access_path = base
                index = ast.unparse(node.slice)
                return base_name, f"{access_path}[{index}]"
        return None

    def _create_variable_tracking_call(
        self, var_name: str, access_path: str, line_no: int
    ) -> ast.stmt:
        return ast.parse(
            f"{self.exec_ctx_name}.record_variable({var_name!r}, _step_tracer_utils.safe_deepcopy({var_name}), {access_path!r}, {line_no})"
        ).body[0]

    # ### Conditional Tracking Code

    def visit_If(self, node: ast.If) -> list[ast.stmt]:
        self.generic_visit(node)

        temp_test_cond = ast.Assign(
            targets=[ast.Name(id="_step_tracer_temp", ctx=ast.Store())], value=node.test
        )

        branch_exec = self._create_branch_execution(
            node.lineno,
            node.test,
            ast.Name(id="_step_tracer_temp", ctx=ast.Load()),
        )

        new_if = ast.If(
            test=ast.Name(id="_step_tracer_temp", ctx=ast.Load()),
            body=node.body,
            orelse=node.orelse,
        )

        wrapped_if = self._wrap_with_ctx([new_if], branch_exec)

        return [temp_test_cond, wrapped_if]

    def _create_branch_execution(
        self, line_number: int, cond: ast.expr, temp_cond: ast.expr
    ) -> ast.Call:
        """Create a call to track an if else branch."""
        return ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=self.exec_ctx_name, ctx=ast.Load()),
                attr="create_branch_execution",
                ctx=ast.Load(),
            ),
            args=[
                ast.Constant(value=line_number),
                ast.Constant(value=ast.unparse(cond)),
                temp_cond,
            ],
            keywords=[],
        )

    ### General

    def _wrap_with_ctx(
        self, body: list[ast.stmt], create_stmt_exec_node: ast.Call
    ) -> ast.With:
        track_call = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id=self.exec_ctx_name, ctx=ast.Load()),
                attr="track_stmt_exec",
                ctx=ast.Load(),
            ),
            args=[create_stmt_exec_node],
            keywords=[],
        )

        return ast.With(
            items=[ast.withitem(context_expr=track_call)],
            body=body,
        )
