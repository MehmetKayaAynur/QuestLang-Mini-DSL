# questlang/tokens.py

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class TokenType(Enum):
    # Single-character tokens
    LEFT_PAREN = auto()      # (
    RIGHT_PAREN = auto()     # )
    LEFT_BRACE = auto()      # {
    RIGHT_BRACE = auto()     # }
    COMMA = auto()           # ,
    DOT = auto()             # .
    COLON = auto()           # :
    SEMICOLON = auto()       # ;

    PLUS = auto()            # +
    MINUS = auto()           # -
    STAR = auto()            # *
    SLASH = auto()           # /

    ASSIGN = auto()          # =
    BANG = auto()            # !

    LESS = auto()            # <
    GREATER = auto()         # >

    # One or two character tokens
    EQUAL_EQUAL = auto()     # ==
    BANG_EQUAL = auto()      # !=
    LESS_EQUAL = auto()      # <=
    GREATER_EQUAL = auto()   # >=
    AND_AND = auto()         # &&
    OR_OR = auto()           # ||

    # Literals
    IDENTIFIER = auto()
    INT_LITERAL = auto()
    FLOAT_LITERAL = auto()
    STRING_LITERAL = auto()
    BOOL_LITERAL = auto()

    # Keywords
    PLAYER = auto()          # player
    PLAYER_TYPE = auto()     # Player

    FUNC = auto()            # func
    RETURN = auto()          # return

    QUEST = auto()           # quest
    IF = auto()              # if
    ELSE = auto()            # else

    REWARD = auto()          # reward
    LOG = auto()             # log

    TYPE_INT = auto()        # int
    TYPE_FLOAT = auto()      # float
    TYPE_BOOL = auto()       # bool
    TYPE_STRING = auto()     # string

    EOF = auto()


KEYWORDS = {
    "player": TokenType.PLAYER,
    "Player": TokenType.PLAYER_TYPE,

    "func": TokenType.FUNC,
    "return": TokenType.RETURN,

    "quest": TokenType.QUEST,
    "if": TokenType.IF,
    "else": TokenType.ELSE,

    "reward": TokenType.REWARD,
    "log": TokenType.LOG,

    "true": TokenType.BOOL_LITERAL,
    "false": TokenType.BOOL_LITERAL,

    "int": TokenType.TYPE_INT,
    "float": TokenType.TYPE_FLOAT,
    "bool": TokenType.TYPE_BOOL,
    "string": TokenType.TYPE_STRING,
}


@dataclass(frozen=True)
class Token:
    type: TokenType
    lexeme: str
    literal: Any
    line: int
    column: int

    def __repr__(self) -> str:
        return (
            f"Token("
            f"type={self.type.name}, "
            f"lexeme={self.lexeme!r}, "
            f"literal={self.literal!r}, "
            f"line={self.line}, "
            f"column={self.column}"
            f")"
        )