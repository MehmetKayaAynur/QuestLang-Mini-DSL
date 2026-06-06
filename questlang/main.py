# questlang/main.py

import sys

from lexer import Lexer, LexerError
from parser import Parser, ParseError
from type_checker import TypeChecker, TypeCheckError
from interpreter import Interpreter, RuntimeErrorQuestLang


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: python questlang/main.py <source-file> "
            "[--dump-tokens] [--dump-ast] [--type-check] [--run]"
        )
        sys.exit(1)

    path = sys.argv[1]
    dump_tokens = "--dump-tokens" in sys.argv
    dump_ast = "--dump-ast" in sys.argv
    type_check = "--type-check" in sys.argv
    run_program = "--run" in sys.argv

    try:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()

        lexer = Lexer(source)
        tokens = lexer.scan_tokens()

        if dump_tokens:
            for token in tokens:
                print(token)

        parser = Parser(tokens)
        program = parser.parse()

        if dump_ast:
            print(program.pretty())

        if type_check or run_program:
            checker = TypeChecker(program)
            checker.check()

            if type_check and not run_program:
                print("Type check successful.")

        if run_program:
            interpreter = Interpreter(program)
            output_lines = interpreter.run()
            for line in output_lines:
                print(line)

        if not dump_tokens and not dump_ast and not type_check and not run_program:
            print("Parse successful.")

    except FileNotFoundError:
        print(f"Error: file not found: {path}")
        sys.exit(1)

    except LexerError as e:
        print(e)
        sys.exit(1)

    except ParseError as e:
        print(e)
        sys.exit(1)

    except TypeCheckError as e:
        print(e)
        sys.exit(1)

    except RuntimeErrorQuestLang as e:
        print(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
