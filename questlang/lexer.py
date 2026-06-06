# questlang/lexer.py

from __future__ import annotations

from typing import List

from tokens import Token, TokenType, KEYWORDS


class LexerError(Exception):
    pass


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.tokens: List[Token] = []

        self.start = 0
        self.current = 0

        self.line = 1
        self.column = 1
        self.start_line = 1
        self.start_column = 1

    def scan_tokens(self) -> List[Token]:
        while not self._is_at_end():
            self.start = self.current
            self.start_line = self.line
            self.start_column = self.column
            self._scan_token()

        self.tokens.append(
            Token(
                TokenType.EOF,
                "",
                None,
                self.line,
                self.column,
            )
        )
        return self.tokens

    def _scan_token(self) -> None:
        c = self._advance()

        match c:
            case "(":
                self._add_token(TokenType.LEFT_PAREN)
            case ")":
                self._add_token(TokenType.RIGHT_PAREN)
            case "{":
                self._add_token(TokenType.LEFT_BRACE)
            case "}":
                self._add_token(TokenType.RIGHT_BRACE)
            case ",":
                self._add_token(TokenType.COMMA)
            case ".":
                self._add_token(TokenType.DOT)
            case ":":
                self._add_token(TokenType.COLON)
            case ";":
                self._add_token(TokenType.SEMICOLON)

            case "+":
                self._add_token(TokenType.PLUS)
            case "-":
                self._add_token(TokenType.MINUS)
            case "*":
                self._add_token(TokenType.STAR)

            case "/":
                if self._match("/"):
                    self._consume_line_comment()
                else:
                    self._add_token(TokenType.SLASH)

            case "=":
                if self._match("="):
                    self._add_token(TokenType.EQUAL_EQUAL)
                else:
                    self._add_token(TokenType.ASSIGN)

            case "!":
                if self._match("="):
                    self._add_token(TokenType.BANG_EQUAL)
                else:
                    self._add_token(TokenType.BANG)

            case "<":
                if self._match("="):
                    self._add_token(TokenType.LESS_EQUAL)
                else:
                    self._add_token(TokenType.LESS)

            case ">":
                if self._match("="):
                    self._add_token(TokenType.GREATER_EQUAL)
                else:
                    self._add_token(TokenType.GREATER)

            case "&":
                if self._match("&"):
                    self._add_token(TokenType.AND_AND)
                else:
                    self._error("Unexpected character '&'. Did you mean '&&'?")

            case "|":
                if self._match("|"):
                    self._add_token(TokenType.OR_OR)
                else:
                    self._error("Unexpected character '|'. Did you mean '||'?")

            case " " | "\r" | "\t":
                # Ignore whitespace.
                pass

            case "\n":
                # _advance already updated line and column.
                pass

            case '"':
                self._string()

            case _:
                if self._is_digit(c):
                    self._number()
                elif self._is_alpha(c):
                    self._identifier_or_keyword()
                else:
                    self._error(f"Unexpected character {c!r}.")

    def _identifier_or_keyword(self) -> None:
        while self._is_alpha_numeric(self._peek()):
            self._advance()

        text = self.source[self.start:self.current]
        token_type = KEYWORDS.get(text, TokenType.IDENTIFIER)

        literal = None
        if token_type == TokenType.BOOL_LITERAL:
            literal = True if text == "true" else False

        self._add_token(token_type, literal)

    def _number(self) -> None:
        while self._is_digit(self._peek()):
            self._advance()

        is_float = False

        if self._peek() == "." and self._is_digit(self._peek_next()):
            is_float = True
            self._advance()  # consume '.'

            while self._is_digit(self._peek()):
                self._advance()

        text = self.source[self.start:self.current]

        if is_float:
            self._add_token(TokenType.FLOAT_LITERAL, float(text))
        else:
            self._add_token(TokenType.INT_LITERAL, int(text))

    def _string(self) -> None:
        chars: list[str] = []

        while not self._is_at_end() and self._peek() != '"':
            c = self._advance()

            if c == "\n":
                self._error("Unterminated string literal.")

            if c == "\\":
                if self._is_at_end():
                    self._error("Unterminated escape sequence in string literal.")

                escaped = self._advance()

                match escaped:
                    case "n":
                        chars.append("\n")
                    case "t":
                        chars.append("\t")
                    case '"':
                        chars.append('"')
                    case "\\":
                        chars.append("\\")
                    case _:
                        self._error(f"Unknown escape sequence '\\{escaped}'.")
            else:
                chars.append(c)

        if self._is_at_end():
            self._error("Unterminated string literal.")

        self._advance()  # closing quote

        lexeme = self.source[self.start:self.current]
        literal = "".join(chars)

        self.tokens.append(
            Token(
                TokenType.STRING_LITERAL,
                lexeme,
                literal,
                self.start_line,
                self.start_column,
            )
        )

    def _consume_line_comment(self) -> None:
        while self._peek() != "\n" and not self._is_at_end():
            self._advance()

    def _add_token(self, token_type: TokenType, literal=None) -> None:
        text = self.source[self.start:self.current]
        self.tokens.append(
            Token(
                token_type,
                text,
                literal,
                self.start_line,
                self.start_column,
            )
        )

    def _advance(self) -> str:
        c = self.source[self.current]
        self.current += 1

        if c == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1

        return c

    def _match(self, expected: str) -> bool:
        if self._is_at_end():
            return False

        if self.source[self.current] != expected:
            return False

        self._advance()
        return True

    def _peek(self) -> str:
        if self._is_at_end():
            return "\0"
        return self.source[self.current]

    def _peek_next(self) -> str:
        if self.current + 1 >= len(self.source):
            return "\0"
        return self.source[self.current + 1]

    def _is_at_end(self) -> bool:
        return self.current >= len(self.source)

    @staticmethod
    def _is_digit(c: str) -> bool:
        return "0" <= c <= "9"

    @staticmethod
    def _is_alpha(c: str) -> bool:
        return ("a" <= c <= "z") or ("A" <= c <= "Z") or c == "_"

    @classmethod
    def _is_alpha_numeric(cls, c: str) -> bool:
        return cls._is_alpha(c) or cls._is_digit(c)

    def _error(self, message: str) -> None:
        raise LexerError(
            f"LexerError line {self.start_line}, column {self.start_column}: {message}"
        )