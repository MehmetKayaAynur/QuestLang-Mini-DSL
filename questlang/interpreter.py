# questlang/interpreter.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ast_nodes import (
    Program,
    Decl,
    PlayerDecl,
    FuncDecl,
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


class RuntimeErrorQuestLang(Exception):
    pass


@dataclass
class PlayerValue:
    """Runtime representation of QuestLang's built-in Player record."""

    name: str
    fields: Dict[str, Any]
    inventory: List[str] = field(default_factory=list)

    def get_field(self, field_name: str) -> Any:
        if field_name not in self.fields:
            raise RuntimeErrorQuestLang(
                f"RuntimeError: Unknown Player field '{field_name}' on player '{self.name}'."
            )
        return self.fields[field_name]

    def add_gold(self, amount: int) -> int:
        if amount < 0:
            raise RuntimeErrorQuestLang(
                f"RuntimeError: reward gold cannot use a negative amount ({amount})."
            )
        self.fields["gold"] = self.fields.get("gold", 0) + amount
        return self.fields["gold"]

    def add_item(self, item_name: str) -> None:
        if item_name == "":
            raise RuntimeErrorQuestLang("RuntimeError: reward item cannot use an empty item name.")
        self.inventory.append(item_name)


class ReturnSignal(Exception):
    """Internal control-flow signal used to leave a function body."""

    def __init__(self, value: Any):
        self.value = value


class Interpreter:
    def __init__(self, program: Program):
        self.program = program
        self.players: Dict[str, PlayerValue] = {}
        self.functions: Dict[str, FuncDecl] = {}
        self.quests: Dict[str, QuestDecl] = {}
        self.default_player_name: Optional[str] = None
        self.output: List[str] = []

    def run(self) -> List[str]:
        """Execute the program and return the produced output lines."""
        self._collect_declarations()
        self._initialize_players()
        self._execute_quests()
        return self.output

    # =========================
    # Top-level execution
    # =========================

    def _collect_declarations(self) -> None:
        for decl in self.program.declarations:
            if isinstance(decl, PlayerDecl):
                if decl.name in self.players or decl.name in self.functions or decl.name in self.quests:
                    self._error(f"Duplicate global name '{decl.name}'.")
                # Player fields are initialized in a second pass so functions are already known.
                self.players[decl.name] = PlayerValue(decl.name, {})
                if self.default_player_name is None:
                    self.default_player_name = decl.name

            elif isinstance(decl, FuncDecl):
                if decl.name in self.players or decl.name in self.functions or decl.name in self.quests:
                    self._error(f"Duplicate global name '{decl.name}'.")
                self.functions[decl.name] = decl

            elif isinstance(decl, QuestDecl):
                if decl.name in self.players or decl.name in self.functions or decl.name in self.quests:
                    self._error(f"Duplicate global name '{decl.name}'.")
                self.quests[decl.name] = decl

            else:
                self._error(f"Unknown declaration node: {type(decl).__name__}.")

    def _initialize_players(self) -> None:
        empty_env: dict[str, Any] = {}

        for decl in self.program.declarations:
            if not isinstance(decl, PlayerDecl):
                continue

            player = self.players[decl.name]
            for field_init in decl.fields:
                player.fields[field_init.name] = self._eval_expr(field_init.value, empty_env)

    def _execute_quests(self) -> None:
        for decl in self.program.declarations:
            if not isinstance(decl, QuestDecl):
                continue

            try:
                self._execute_block(decl.body, env={})
            except ReturnSignal:
                self._error(f"return statement cannot be executed inside quest '{decl.name}'.")

    # =========================
    # Statements
    # =========================

    def _execute_block(self, block: BlockStmt, env: dict[str, Any]) -> None:
        for stmt in block.statements:
            self._execute_stmt(stmt, env)

    def _execute_stmt(self, stmt: Stmt, env: dict[str, Any]) -> None:
        if isinstance(stmt, IfStmt):
            condition = self._eval_expr(stmt.condition, env)
            self._require_bool(condition, "if condition")

            if condition:
                self._execute_block(stmt.then_branch, env.copy())
            elif stmt.else_branch is not None:
                self._execute_block(stmt.else_branch, env.copy())
            return

        if isinstance(stmt, ReturnStmt):
            raise ReturnSignal(self._eval_expr(stmt.value, env))

        if isinstance(stmt, RewardStmt):
            value = self._eval_expr(stmt.value, env)
            self._execute_reward(stmt.target, value)
            return

        if isinstance(stmt, LogStmt):
            value = self._eval_expr(stmt.value, env)
            if not isinstance(value, str):
                self._error(f"log expects a string value, got {self._runtime_type(value)}.")
            self.output.append(value)
            return

        self._error(f"Unknown statement node: {type(stmt).__name__}.")

    def _execute_reward(self, target: str, value: Any) -> None:
        player = self._default_player()

        if target == "gold":
            if not isinstance(value, int) or isinstance(value, bool):
                self._error(f"reward gold expects an int value, got {self._runtime_type(value)}.")
            new_total = player.add_gold(value)
            self.output.append(f"Rewarded {value} gold to {player.name} (gold={new_total})")
            return

        if target == "item":
            if not isinstance(value, str):
                self._error(f"reward item expects a string value, got {self._runtime_type(value)}.")
            player.add_item(value)
            self.output.append(f"Rewarded item '{value}' to {player.name}")
            return

        self._error(f"Unknown reward target '{target}'. Expected 'gold' or 'item'.")

    # =========================
    # Expressions
    # =========================

    def _eval_expr(self, expr: Expr, env: dict[str, Any]) -> Any:
        if isinstance(expr, LiteralExpr):
            return expr.value

        if isinstance(expr, IdentifierExpr):
            return self._lookup_identifier(expr.name, env)

        if isinstance(expr, FieldAccessExpr):
            obj = self._eval_expr(expr.obj, env)
            if not isinstance(obj, PlayerValue):
                self._error(
                    f"Cannot access field '{expr.field}' on {self._runtime_type(obj)} value."
                )
            return obj.get_field(expr.field)

        if isinstance(expr, CallExpr):
            return self._eval_call(expr, env)

        if isinstance(expr, UnaryExpr):
            return self._eval_unary(expr, env)

        if isinstance(expr, BinaryExpr):
            return self._eval_binary(expr, env)

        self._error(f"Unknown expression node: {type(expr).__name__}.")

    def _lookup_identifier(self, name: str, env: dict[str, Any]) -> Any:
        # Static lexical lookup: function parameters/local call environment first,
        # then global player values. Function names are only values in call position.
        if name in env:
            return env[name]

        if name in self.players:
            return self.players[name]

        if name in self.functions:
            self._error(f"Function '{name}' must be called with parentheses.")

        if name in self.quests:
            self._error(f"Quest name '{name}' cannot be used as a value.")

        self._error(f"Undefined identifier '{name}'.")

    def _eval_call(self, expr: CallExpr, env: dict[str, Any]) -> Any:
        if not isinstance(expr.callee, IdentifierExpr):
            self._error("Only named function calls are allowed in QuestLang.")

        function_name = expr.callee.name
        if function_name not in self.functions:
            self._error(f"Undefined function '{function_name}'.")

        func = self.functions[function_name]

        if len(expr.args) != len(func.params):
            self._error(
                f"Function '{function_name}' expects {len(func.params)} argument(s), "
                f"but got {len(expr.args)}."
            )

        call_env: dict[str, Any] = {}
        for param, arg_expr in zip(func.params, expr.args):
            call_env[param.name] = self._eval_expr(arg_expr, env)

        try:
            self._execute_block(func.body, call_env)
        except ReturnSignal as signal:
            return signal.value

        self._error(f"Function '{function_name}' finished without returning a value.")

    def _eval_unary(self, expr: UnaryExpr, env: dict[str, Any]) -> Any:
        value = self._eval_expr(expr.operand, env)

        if expr.operator == "!":
            self._require_bool(value, "operand of '!'")
            return not value

        if expr.operator == "-":
            if not self._is_number(value):
                self._error(f"Unary '-' expects a number, got {self._runtime_type(value)}.")
            return -value

        self._error(f"Unknown unary operator '{expr.operator}'.")

    def _eval_binary(self, expr: BinaryExpr, env: dict[str, Any]) -> Any:
        op = expr.operator

        # Runtime short-circuit semantics: the right side is evaluated only if needed.
        if op == "&&":
            left = self._eval_expr(expr.left, env)
            self._require_bool(left, "left operand of '&&'")
            if not left:
                return False
            right = self._eval_expr(expr.right, env)
            self._require_bool(right, "right operand of '&&'")
            return right

        if op == "||":
            left = self._eval_expr(expr.left, env)
            self._require_bool(left, "left operand of '||'")
            if left:
                return True
            right = self._eval_expr(expr.right, env)
            self._require_bool(right, "right operand of '||'")
            return right

        left = self._eval_expr(expr.left, env)
        right = self._eval_expr(expr.right, env)

        if op in ("+", "-", "*", "/"):
            self._require_numbers(left, right, f"operator '{op}'")

            if op == "+":
                return left + right
            if op == "-":
                return left - right
            if op == "*":
                return left * right
            if op == "/":
                if right == 0:
                    self._error("Division by zero.")
                return left / right

        if op in ("<", "<=", ">", ">="):
            self._require_numbers(left, right, f"operator '{op}'")
            if op == "<":
                return left < right
            if op == "<=":
                return left <= right
            if op == ">":
                return left > right
            if op == ">=":
                return left >= right

        if op == "==":
            return left == right

        if op == "!=":
            return left != right

        self._error(f"Unknown binary operator '{op}'.")

    # =========================
    # Helpers
    # =========================

    def _default_player(self) -> PlayerValue:
        if self.default_player_name is None:
            self._error("reward statement requires at least one declared player.")
        return self.players[self.default_player_name]

    def _require_bool(self, value: Any, context: str) -> None:
        if not isinstance(value, bool):
            self._error(f"{context} expects bool, got {self._runtime_type(value)}.")

    def _require_numbers(self, left: Any, right: Any, context: str) -> None:
        if not self._is_number(left) or not self._is_number(right):
            self._error(
                f"{context} expects numeric operands, got "
                f"{self._runtime_type(left)} and {self._runtime_type(right)}."
            )

    @staticmethod
    def _is_number(value: Any) -> bool:
        return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)

    @staticmethod
    def _runtime_type(value: Any) -> str:
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, int):
            return "int"
        if isinstance(value, float):
            return "float"
        if isinstance(value, str):
            return "string"
        if isinstance(value, PlayerValue):
            return "Player"
        return type(value).__name__

    def _error(self, message: str) -> None:
        if message.startswith("RuntimeError:"):
            raise RuntimeErrorQuestLang(message)
        raise RuntimeErrorQuestLang(f"RuntimeError: {message}")
