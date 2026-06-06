# questlang/ast_nodes.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional


def _indent(level: int) -> str:
    return "  " * level


class ASTNode:
    def pretty(self, level: int = 0) -> str:
        raise NotImplementedError


# =========================
# Program and declarations
# =========================

@dataclass
class Program(ASTNode):
    declarations: List[Decl]

    def pretty(self, level: int = 0) -> str:
        lines = [_indent(level) + "Program"]
        for decl in self.declarations:
            lines.append(decl.pretty(level + 1))
        return "\n".join(lines)


class Decl(ASTNode):
    pass


@dataclass
class PlayerDecl(Decl):
    name: str
    fields: List[FieldInit]

    def pretty(self, level: int = 0) -> str:
        lines = [_indent(level) + f"PlayerDecl name={self.name}"]
        for field in self.fields:
            lines.append(field.pretty(level + 1))
        return "\n".join(lines)


@dataclass
class FieldInit(ASTNode):
    name: str
    value: Expr

    def pretty(self, level: int = 0) -> str:
        lines = [_indent(level) + f"FieldInit name={self.name}"]
        lines.append(self.value.pretty(level + 1))
        return "\n".join(lines)


@dataclass
class FuncDecl(Decl):
    name: str
    params: List[Param]
    return_type: str
    body: BlockStmt

    def pretty(self, level: int = 0) -> str:
        lines = [_indent(level) + f"FuncDecl name={self.name} return={self.return_type}"]

        if self.params:
            lines.append(_indent(level + 1) + "Params")
            for param in self.params:
                lines.append(param.pretty(level + 2))
        else:
            lines.append(_indent(level + 1) + "Params <empty>")

        lines.append(self.body.pretty(level + 1))
        return "\n".join(lines)


@dataclass
class Param(ASTNode):
    name: str
    type_name: str

    def pretty(self, level: int = 0) -> str:
        return _indent(level) + f"Param name={self.name} type={self.type_name}"


@dataclass
class QuestDecl(Decl):
    name: str
    body: BlockStmt

    def pretty(self, level: int = 0) -> str:
        lines = [_indent(level) + f"QuestDecl name={self.name}"]
        lines.append(self.body.pretty(level + 1))
        return "\n".join(lines)


# =========================
# Statements
# =========================

class Stmt(ASTNode):
    pass


@dataclass
class BlockStmt(Stmt):
    statements: List[Stmt]

    def pretty(self, level: int = 0) -> str:
        lines = [_indent(level) + "Block"]
        for stmt in self.statements:
            lines.append(stmt.pretty(level + 1))
        return "\n".join(lines)


@dataclass
class IfStmt(Stmt):
    condition: Expr
    then_branch: BlockStmt
    else_branch: Optional[BlockStmt]

    def pretty(self, level: int = 0) -> str:
        lines = [_indent(level) + "IfStmt"]
        lines.append(_indent(level + 1) + "Condition")
        lines.append(self.condition.pretty(level + 2))

        lines.append(_indent(level + 1) + "Then")
        lines.append(self.then_branch.pretty(level + 2))

        if self.else_branch is not None:
            lines.append(_indent(level + 1) + "Else")
            lines.append(self.else_branch.pretty(level + 2))

        return "\n".join(lines)


@dataclass
class ReturnStmt(Stmt):
    value: Expr

    def pretty(self, level: int = 0) -> str:
        lines = [_indent(level) + "ReturnStmt"]
        lines.append(self.value.pretty(level + 1))
        return "\n".join(lines)


@dataclass
class RewardStmt(Stmt):
    target: str
    value: Expr

    def pretty(self, level: int = 0) -> str:
        lines = [_indent(level) + f"RewardStmt target={self.target}"]
        lines.append(self.value.pretty(level + 1))
        return "\n".join(lines)


@dataclass
class LogStmt(Stmt):
    value: Expr

    def pretty(self, level: int = 0) -> str:
        lines = [_indent(level) + "LogStmt"]
        lines.append(self.value.pretty(level + 1))
        return "\n".join(lines)


# =========================
# Expressions
# =========================

class Expr(ASTNode):
    pass


@dataclass
class LiteralExpr(Expr):
    value: Any

    def pretty(self, level: int = 0) -> str:
        return _indent(level) + f"Literal value={self.value!r}"


@dataclass
class IdentifierExpr(Expr):
    name: str

    def pretty(self, level: int = 0) -> str:
        return _indent(level) + f"Identifier name={self.name}"


@dataclass
class FieldAccessExpr(Expr):
    obj: Expr
    field: str

    def pretty(self, level: int = 0) -> str:
        lines = [_indent(level) + f"FieldAccess field={self.field}"]
        lines.append(self.obj.pretty(level + 1))
        return "\n".join(lines)


@dataclass
class CallExpr(Expr):
    callee: Expr
    args: List[Expr]

    def pretty(self, level: int = 0) -> str:
        lines = [_indent(level) + "CallExpr"]
        lines.append(_indent(level + 1) + "Callee")
        lines.append(self.callee.pretty(level + 2))

        if self.args:
            lines.append(_indent(level + 1) + "Args")
            for arg in self.args:
                lines.append(arg.pretty(level + 2))
        else:
            lines.append(_indent(level + 1) + "Args <empty>")

        return "\n".join(lines)


@dataclass
class UnaryExpr(Expr):
    operator: str
    operand: Expr

    def pretty(self, level: int = 0) -> str:
        lines = [_indent(level) + f"UnaryExpr op='{self.operator}'"]
        lines.append(self.operand.pretty(level + 1))
        return "\n".join(lines)


@dataclass
class BinaryExpr(Expr):
    left: Expr
    operator: str
    right: Expr

    def pretty(self, level: int = 0) -> str:
        lines = [_indent(level) + f"BinaryExpr op='{self.operator}'"]
        lines.append(_indent(level + 1) + "Left")
        lines.append(self.left.pretty(level + 2))
        lines.append(_indent(level + 1) + "Right")
        lines.append(self.right.pretty(level + 2))
        return "\n".join(lines)