# questlang/parser.py

from __future__ import annotations

from typing import List

from tokens import Token, TokenType
from ast_nodes import (
    Program,
    PlayerDecl,
    FieldInit,
    FuncDecl,
    Param,
    QuestDecl,
    BlockStmt,
    IfStmt,
    ReturnStmt,
    RewardStmt,
    LogStmt,
    LiteralExpr,
    IdentifierExpr,
    FieldAccessExpr,
    CallExpr,
    UnaryExpr,
    BinaryExpr,
    Expr,
    Stmt,
)


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.current = 0

    # =========================
    # Entry point
    # =========================

    def parse(self) -> Program:
        declarations = []

        while not self._is_at_end():
            declarations.append(self._declaration())

        return Program(declarations)

    # =========================
    # Declarations
    # =========================

    def _declaration(self):
        if self._match(TokenType.PLAYER):
            return self._player_decl()

        if self._match(TokenType.FUNC):
            return self._func_decl()

        if self._match(TokenType.QUEST):
            return self._quest_decl()

        token = self._peek()
        self._error_at(
            token,
            "Expected declaration. Valid top-level declarations are 'player', 'func', or 'quest'.",
        )

    def _player_decl(self) -> PlayerDecl:
        name = self._consume(TokenType.IDENTIFIER, "Expected player name after 'player'.")
        self._consume(TokenType.COLON, "Expected ':' after player name.")
        self._consume(TokenType.PLAYER_TYPE, "Expected 'Player' after ':' in player declaration.")
        self._consume(TokenType.LEFT_BRACE, "Expected '{' to start player declaration body.")

        fields: list[FieldInit] = []

        while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
            field_name = self._consume(TokenType.IDENTIFIER, "Expected field name in player declaration.")
            self._consume(TokenType.ASSIGN, "Expected '=' after player field name.")
            value = self._expression()
            self._consume(TokenType.SEMICOLON, "Expected ';' after player field initialization.")

            fields.append(FieldInit(field_name.lexeme, value))

        self._consume(TokenType.RIGHT_BRACE, "Expected '}' after player declaration body.")

        return PlayerDecl(name.lexeme, fields)

    def _func_decl(self) -> FuncDecl:
        name = self._consume(TokenType.IDENTIFIER, "Expected function name after 'func'.")
        self._consume(TokenType.LEFT_PAREN, "Expected '(' after function name.")

        params: list[Param] = []

        if not self._check(TokenType.RIGHT_PAREN):
            params.append(self._param())

            while self._match(TokenType.COMMA):
                params.append(self._param())

        self._consume(TokenType.RIGHT_PAREN, "Expected ')' after function parameters.")
        self._consume(TokenType.COLON, "Expected ':' before function return type.")

        return_type = self._type_name()

        body = self._block()

        return FuncDecl(name.lexeme, params, return_type, body)

    def _param(self) -> Param:
        name = self._consume(TokenType.IDENTIFIER, "Expected parameter name.")
        self._consume(TokenType.COLON, "Expected ':' after parameter name.")
        type_name = self._type_name()

        return Param(name.lexeme, type_name)

    def _quest_decl(self) -> QuestDecl:
        name = self._consume(TokenType.IDENTIFIER, "Expected quest name after 'quest'.")
        body = self._block()
        return QuestDecl(name.lexeme, body)

    def _type_name(self) -> str:
        if self._match(TokenType.TYPE_INT):
            return "int"

        if self._match(TokenType.TYPE_FLOAT):
            return "float"

        if self._match(TokenType.TYPE_BOOL):
            return "bool"

        if self._match(TokenType.TYPE_STRING):
            return "string"

        if self._match(TokenType.PLAYER_TYPE):
            return "Player"

        self._error_at(self._peek(), "Expected type name: int, float, bool, string, or Player.")

    # =========================
    # Blocks and statements
    # =========================

    def _block(self) -> BlockStmt:
        self._consume(TokenType.LEFT_BRACE, "Expected '{' to start block.")

        statements: list[Stmt] = []

        while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
            statements.append(self._statement())

        self._consume(TokenType.RIGHT_BRACE, "Expected '}' after block.")

        return BlockStmt(statements)

    def _statement(self) -> Stmt:
        if self._match(TokenType.IF):
            return self._if_stmt()

        if self._match(TokenType.RETURN):
            return self._return_stmt()

        if self._match(TokenType.REWARD):
            return self._reward_stmt()

        if self._match(TokenType.LOG):
            return self._log_stmt()

        token = self._peek()
        self._error_at(
            token,
            "Expected statement. Valid statements are 'if', 'return', 'reward', or 'log'.",
        )

    def _if_stmt(self) -> IfStmt:
        condition = self._expression()
        then_branch = self._block()

        else_branch = None
        if self._match(TokenType.ELSE):
            else_branch = self._block()

        return IfStmt(condition, then_branch, else_branch)

    def _return_stmt(self) -> ReturnStmt:
        value = self._expression()
        self._consume(TokenType.SEMICOLON, "Expected ';' after return value.")
        return ReturnStmt(value)

    def _reward_stmt(self) -> RewardStmt:
        target = self._consume(
            TokenType.IDENTIFIER,
            "Expected reward target after 'reward'. Use 'gold' or 'item'.",
        )

        if target.lexeme not in ("gold", "item"):
            self._error_at(
                target,
                "Expected reward target 'gold' or 'item'.",
            )

        value = self._expression()
        self._consume(TokenType.SEMICOLON, "Expected ';' after reward statement.")

        return RewardStmt(target.lexeme, value)

    def _log_stmt(self) -> LogStmt:
        self._consume(TokenType.LEFT_PAREN, "Expected '(' after 'log'.")
        value = self._expression()
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' after log argument.")
        self._consume(TokenType.SEMICOLON, "Expected ';' after log statement.")

        return LogStmt(value)

    # =========================
    # Expressions
    # Precedence from low to high:
    # ||, &&, == !=, comparisons, + -, * /, unary, postfix
    # =========================

    def _expression(self) -> Expr:
        return self._or()

    def _or(self) -> Expr:
        expr = self._and()

        while self._match(TokenType.OR_OR):
            operator = self._previous()
            right = self._and()
            expr = BinaryExpr(expr, operator.lexeme, right)

        return expr

    def _and(self) -> Expr:
        expr = self._equality()

        while self._match(TokenType.AND_AND):
            operator = self._previous()
            right = self._equality()
            expr = BinaryExpr(expr, operator.lexeme, right)

        return expr

    def _equality(self) -> Expr:
        expr = self._comparison()

        while self._match(TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL):
            operator = self._previous()
            right = self._comparison()
            expr = BinaryExpr(expr, operator.lexeme, right)

        return expr

    def _comparison(self) -> Expr:
        expr = self._term()

        while self._match(
            TokenType.LESS,
            TokenType.LESS_EQUAL,
            TokenType.GREATER,
            TokenType.GREATER_EQUAL,
        ):
            operator = self._previous()
            right = self._term()
            expr = BinaryExpr(expr, operator.lexeme, right)

        return expr

    def _term(self) -> Expr:
        expr = self._factor()

        while self._match(TokenType.PLUS, TokenType.MINUS):
            operator = self._previous()
            right = self._factor()
            expr = BinaryExpr(expr, operator.lexeme, right)

        return expr

    def _factor(self) -> Expr:
        expr = self._unary()

        while self._match(TokenType.STAR, TokenType.SLASH):
            operator = self._previous()
            right = self._unary()
            expr = BinaryExpr(expr, operator.lexeme, right)

        return expr

    def _unary(self) -> Expr:
        if self._match(TokenType.BANG, TokenType.MINUS):
            operator = self._previous()
            right = self._unary()
            return UnaryExpr(operator.lexeme, right)

        return self._postfix()

    def _postfix(self) -> Expr:
        expr = self._primary()

        while True:
            if self._match(TokenType.DOT):
                field = self._consume(TokenType.IDENTIFIER, "Expected field name after '.'.")
                expr = FieldAccessExpr(expr, field.lexeme)

            elif self._match(TokenType.LEFT_PAREN):
                args = []

                if not self._check(TokenType.RIGHT_PAREN):
                    args.append(self._expression())

                    while self._match(TokenType.COMMA):
                        args.append(self._expression())

                self._consume(TokenType.RIGHT_PAREN, "Expected ')' after function call arguments.")
                expr = CallExpr(expr, args)

            else:
                break

        return expr

    def _primary(self) -> Expr:
        if self._match(TokenType.INT_LITERAL):
            return LiteralExpr(self._previous().literal)

        if self._match(TokenType.FLOAT_LITERAL):
            return LiteralExpr(self._previous().literal)

        if self._match(TokenType.STRING_LITERAL):
            return LiteralExpr(self._previous().literal)

        if self._match(TokenType.BOOL_LITERAL):
            return LiteralExpr(self._previous().literal)

        if self._match(TokenType.IDENTIFIER):
            return IdentifierExpr(self._previous().lexeme)

        if self._match(TokenType.LEFT_PAREN):
            expr = self._expression()
            self._consume(TokenType.RIGHT_PAREN, "Expected ')' after expression.")
            return expr

        self._error_at(self._peek(), "Expected expression.")

    # =========================
    # Token helpers
    # =========================

    def _match(self, *types: TokenType) -> bool:
        for token_type in types:
            if self._check(token_type):
                self._advance()
                return True
        return False

    def _consume(self, token_type: TokenType, message: str) -> Token:
        if self._check(token_type):
            return self._advance()

        self._error_at(self._peek(), message)

    def _check(self, token_type: TokenType) -> bool:
        if self._is_at_end():
            return token_type == TokenType.EOF

        return self._peek().type == token_type

    def _advance(self) -> Token:
        if not self._is_at_end():
            self.current += 1

        return self._previous()

    def _is_at_end(self) -> bool:
        return self._peek().type == TokenType.EOF

    def _peek(self) -> Token:
        return self.tokens[self.current]

    def _previous(self) -> Token:
        return self.tokens[self.current - 1]

    def _error_at(self, token: Token, message: str):
        raise ParseError(
            f"ParseError line {token.line}, column {token.column}: {message}"
        )