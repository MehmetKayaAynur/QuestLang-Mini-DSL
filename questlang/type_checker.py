# questlang/type_checker.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from ast_nodes import (
    Program,
    Decl,
    PlayerDecl,
    FieldInit,
    FuncDecl,
    Param,
    QuestDecl,
    BlockStmt,
    Stmt,
    IfStmt,
    ReturnStmt,
    RewardStmt,
    LogStmt,
    Expr,
    LiteralExpr,
    IdentifierExpr,
    FieldAccessExpr,
    CallExpr,
    UnaryExpr,
    BinaryExpr,
)


class TypeCheckError(Exception):
    pass


TypeName = str


PLAYER_FIELDS: dict[str, TypeName] = {
    "level": "int",
    "gold": "int",
    "hasKey": "bool",
}


@dataclass(frozen=True)
class FunctionInfo:
    name: str
    params: List[Param]
    return_type: TypeName
    decl: FuncDecl


class TypeChecker:
    def __init__(self, program: Program):
        self.program = program
        self.players: Dict[str, PlayerDecl] = {}
        self.functions: Dict[str, FunctionInfo] = {}
        self.quests: Dict[str, QuestDecl] = {}

    def check(self) -> None:
        self._collect_global_declarations()

        for decl in self.program.declarations:
            if isinstance(decl, PlayerDecl):
                self._check_player_decl(decl)
            elif isinstance(decl, FuncDecl):
                self._check_func_decl(decl)
            elif isinstance(decl, QuestDecl):
                self._check_quest_decl(decl)
            else:
                self._error(f"Unknown declaration node: {type(decl).__name__}")

    # =========================
    # Global symbol collection
    # =========================

    def _collect_global_declarations(self) -> None:
        used_names: set[str] = set()

        for decl in self.program.declarations:
            if isinstance(decl, PlayerDecl):
                self._declare_global_name(decl.name, "player", used_names)
                self.players[decl.name] = decl

            elif isinstance(decl, FuncDecl):
                self._declare_global_name(decl.name, "function", used_names)
                self.functions[decl.name] = FunctionInfo(
                    name=decl.name,
                    params=decl.params,
                    return_type=decl.return_type,
                    decl=decl,
                )

            elif isinstance(decl, QuestDecl):
                self._declare_global_name(decl.name, "quest", used_names)
                self.quests[decl.name] = decl

    def _declare_global_name(self, name: str, kind: str, used_names: set[str]) -> None:
        if name in used_names:
            self._error(f"Duplicate global name '{name}'.")
        used_names.add(name)

    # =========================
    # Declaration checking
    # =========================

    def _check_player_decl(self, decl: PlayerDecl) -> None:
        seen_fields: set[str] = set()
        env: dict[str, TypeName] = {}

        for field in decl.fields:
            if field.name not in PLAYER_FIELDS:
                allowed = ", ".join(PLAYER_FIELDS.keys())
                self._error(
                    f"Unknown Player field '{field.name}' in player '{decl.name}'. "
                    f"Allowed fields are: {allowed}."
                )

            if field.name in seen_fields:
                self._error(f"Duplicate Player field '{field.name}' in player '{decl.name}'.")

            seen_fields.add(field.name)

            expected_type = PLAYER_FIELDS[field.name]
            actual_type = self._check_expr(field.value, env)
            self._require_assignable(
                expected_type,
                actual_type,
                f"Player field '{field.name}' in player '{decl.name}'",
            )

        missing = set(PLAYER_FIELDS.keys()) - seen_fields
        if missing:
            missing_list = ", ".join(sorted(missing))
            self._error(f"Player '{decl.name}' is missing required field(s): {missing_list}.")

    def _check_func_decl(self, decl: FuncDecl) -> None:
        env: dict[str, TypeName] = {}

        for param in decl.params:
            if param.name in env:
                self._error(f"Duplicate parameter name '{param.name}' in function '{decl.name}'.")
            self._require_valid_type(param.type_name, f"parameter '{param.name}'")
            env[param.name] = param.type_name

        self._require_valid_type(decl.return_type, f"return type of function '{decl.name}'")

        self._check_block(
            decl.body,
            env,
            current_function=decl.name,
            expected_return_type=decl.return_type,
        )

        if not self._block_definitely_returns(decl.body):
            self._error(f"Function '{decl.name}' may finish without returning a value.")

    def _check_quest_decl(self, decl: QuestDecl) -> None:
        self._check_block(
            decl.body,
            env={},
            current_function=None,
            expected_return_type=None,
        )

    # =========================
    # Statement checking
    # =========================

    def _check_block(
        self,
        block: BlockStmt,
        env: dict[str, TypeName],
        current_function: Optional[str],
        expected_return_type: Optional[TypeName],
    ) -> None:
        for stmt in block.statements:
            self._check_stmt(stmt, env, current_function, expected_return_type)

    def _check_stmt(
        self,
        stmt: Stmt,
        env: dict[str, TypeName],
        current_function: Optional[str],
        expected_return_type: Optional[TypeName],
    ) -> None:
        if isinstance(stmt, IfStmt):
            condition_type = self._check_expr(stmt.condition, env)
            self._require_exact(
                "bool",
                condition_type,
                "if condition",
            )

            self._check_block(stmt.then_branch, env.copy(), current_function, expected_return_type)
            if stmt.else_branch is not None:
                self._check_block(stmt.else_branch, env.copy(), current_function, expected_return_type)
            return

        if isinstance(stmt, ReturnStmt):
            if current_function is None or expected_return_type is None:
                self._error("return statement is only allowed inside a function.")

            actual_type = self._check_expr(stmt.value, env)
            self._require_assignable(
                expected_return_type,
                actual_type,
                f"return value of function '{current_function}'",
            )
            return

        if isinstance(stmt, RewardStmt):
            if stmt.target == "gold":
                expected_type = "int"
            elif stmt.target == "item":
                expected_type = "string"
            else:
                self._error(f"Unknown reward target '{stmt.target}'. Expected 'gold' or 'item'.")

            actual_type = self._check_expr(stmt.value, env)
            self._require_assignable(
                expected_type,
                actual_type,
                f"reward {stmt.target}",
            )
            return

        if isinstance(stmt, LogStmt):
            actual_type = self._check_expr(stmt.value, env)
            self._require_exact("string", actual_type, "log argument")
            return

        self._error(f"Unknown statement node: {type(stmt).__name__}")

    # =========================
    # Expression checking
    # =========================

    def _check_expr(self, expr: Expr, env: dict[str, TypeName]) -> TypeName:
        if isinstance(expr, LiteralExpr):
            return self._literal_type(expr.value)

        if isinstance(expr, IdentifierExpr):
            return self._identifier_type(expr.name, env)

        if isinstance(expr, FieldAccessExpr):
            object_type = self._check_expr(expr.obj, env)
            if object_type != "Player":
                self._error(
                    f"Cannot access field '{expr.field}' on value of type '{object_type}'. "
                    "Field access is only defined for Player."
                )

            if expr.field not in PLAYER_FIELDS:
                allowed = ", ".join(PLAYER_FIELDS.keys())
                self._error(
                    f"Unknown Player field '{expr.field}'. Allowed fields are: {allowed}."
                )

            return PLAYER_FIELDS[expr.field]

        if isinstance(expr, CallExpr):
            return self._check_call_expr(expr, env)

        if isinstance(expr, UnaryExpr):
            operand_type = self._check_expr(expr.operand, env)

            if expr.operator == "!":
                self._require_exact("bool", operand_type, "operand of '!'")
                return "bool"

            if expr.operator == "-":
                if not self._is_numeric(operand_type):
                    self._error(f"Unary '-' expects int or float, got '{operand_type}'.")
                return operand_type

            self._error(f"Unknown unary operator '{expr.operator}'.")

        if isinstance(expr, BinaryExpr):
            return self._check_binary_expr(expr, env)

        self._error(f"Unknown expression node: {type(expr).__name__}")

    def _check_call_expr(self, expr: CallExpr, env: dict[str, TypeName]) -> TypeName:
        if not isinstance(expr.callee, IdentifierExpr):
            self._error("Only named function calls are allowed in QuestLang.")

        function_name = expr.callee.name
        if function_name not in self.functions:
            self._error(f"Undefined function '{function_name}'.")

        info = self.functions[function_name]

        if len(expr.args) != len(info.params):
            self._error(
                f"Function '{function_name}' expects {len(info.params)} argument(s), "
                f"but got {len(expr.args)}."
            )

        for index, (arg_expr, param) in enumerate(zip(expr.args, info.params), start=1):
            actual_type = self._check_expr(arg_expr, env)
            self._require_assignable(
                param.type_name,
                actual_type,
                f"argument {index} of function '{function_name}'",
            )

        return info.return_type

    def _check_binary_expr(self, expr: BinaryExpr, env: dict[str, TypeName]) -> TypeName:
        op = expr.operator

        # Short-circuit operators: type rules are checked for both operands statically.
        if op in ("&&", "||"):
            left_type = self._check_expr(expr.left, env)
            right_type = self._check_expr(expr.right, env)
            self._require_exact("bool", left_type, f"left operand of '{op}'")
            self._require_exact("bool", right_type, f"right operand of '{op}'")
            return "bool"

        left_type = self._check_expr(expr.left, env)
        right_type = self._check_expr(expr.right, env)

        if op in ("+", "-", "*", "/"):
            if not self._is_numeric(left_type) or not self._is_numeric(right_type):
                self._error(
                    f"Operator '{op}' expects numeric operands, got '{left_type}' and '{right_type}'."
                )

            if op == "/":
                return "float"

            if left_type == "float" or right_type == "float":
                return "float"
            return "int"

        if op in ("<", "<=", ">", ">="):
            if not self._is_numeric(left_type) or not self._is_numeric(right_type):
                self._error(
                    f"Operator '{op}' expects numeric operands, got '{left_type}' and '{right_type}'."
                )
            return "bool"

        if op in ("==", "!="):
            if self._types_compatible_for_equality(left_type, right_type):
                return "bool"
            self._error(
                f"Operator '{op}' cannot compare '{left_type}' with '{right_type}'."
            )

        self._error(f"Unknown binary operator '{op}'.")

    # =========================
    # Definite return analysis
    # =========================

    def _block_definitely_returns(self, block: BlockStmt) -> bool:
        return any(self._stmt_definitely_returns(stmt) for stmt in block.statements)

    def _stmt_definitely_returns(self, stmt: Stmt) -> bool:
        if isinstance(stmt, ReturnStmt):
            return True

        if isinstance(stmt, IfStmt):
            if stmt.else_branch is None:
                return False
            return (
                self._block_definitely_returns(stmt.then_branch)
                and self._block_definitely_returns(stmt.else_branch)
            )

        return False

    # =========================
    # Type helpers
    # =========================

    def _literal_type(self, value) -> TypeName:
        # bool must be checked before int because bool is a subclass of int in Python.
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, int):
            return "int"
        if isinstance(value, float):
            return "float"
        if isinstance(value, str):
            return "string"
        self._error(f"Unsupported literal value {value!r}.")

    def _identifier_type(self, name: str, env: dict[str, TypeName]) -> TypeName:
        if name in env:
            return env[name]

        if name in self.players:
            return "Player"

        if name in self.functions:
            self._error(f"Function '{name}' must be called with parentheses.")

        if name in self.quests:
            self._error(f"Quest name '{name}' cannot be used as a value.")

        self._error(f"Undefined identifier '{name}'.")

    def _require_valid_type(self, type_name: TypeName, context: str) -> None:
        if type_name not in {"int", "float", "bool", "string", "Player"}:
            self._error(f"Invalid type '{type_name}' for {context}.")

    def _require_exact(self, expected: TypeName, actual: TypeName, context: str) -> None:
        if expected != actual:
            self._error(f"Type error in {context}: expected '{expected}', got '{actual}'.")

    def _require_assignable(self, expected: TypeName, actual: TypeName, context: str) -> None:
        if self._is_assignable(expected, actual):
            return
        self._error(f"Type error in {context}: expected '{expected}', got '{actual}'.")

    def _is_assignable(self, expected: TypeName, actual: TypeName) -> bool:
        if expected == actual:
            return True

        # The only implicit coercion: int can be widened to float.
        if expected == "float" and actual == "int":
            return True

        return False

    @staticmethod
    def _is_numeric(type_name: TypeName) -> bool:
        return type_name in {"int", "float"}

    def _types_compatible_for_equality(self, left: TypeName, right: TypeName) -> bool:
        if left == right:
            return True
        return self._is_numeric(left) and self._is_numeric(right)

    def _error(self, message: str):
        raise TypeCheckError(f"TypeCheckError: {message}")
