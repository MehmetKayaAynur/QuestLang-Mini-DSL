# QuestLang — CSE 341 Course Project Part 2

QuestLang is a small domain-specific language (DSL) for writing simple role-playing game quest logic. It supports player declarations, typed functions, quest blocks, conditional execution, rewards, logging, a type checker, and an interpreter.

The language was developed for the CSE 341 Concepts of Programming Languages course project.

## Author

Mehmet Kaya Aynur  
Student Number: 200104004023

## Project Structure

```text
questlang/
  tokens.py
  lexer.py
  ast_nodes.py
  parser.py
  type_checker.py
  interpreter.py
  main.py

examples/
  valid1_dungeon.qst
  valid2_veteran.qst
  valid3_potion.qst
  type_error_bad_reward.qst
  invalid1_missing_semicolon.qst
  invalid2_missing_brace.qst
  invalid3_bad_param.qst
  invalid4_bad_reward.qst
  invalid5_bad_expression.qst

run_tests.py
README.md
```

## Requirements

QuestLang is implemented in Python and does not require external packages.

Recommended version:

```bash
python --version
```

Python 3.10 or newer is recommended because the lexer uses Python `match` statements.

## How to Run

Run commands from the root project folder.

### 1. Dump tokens

```bash
python questlang/main.py examples/valid1_dungeon.qst --dump-tokens
```

### 2. Dump AST

```bash
python questlang/main.py examples/valid1_dungeon.qst --dump-ast
```

### 3. Type check a program

```bash
python questlang/main.py examples/valid1_dungeon.qst --type-check
```

Expected output:

```text
Type check successful.
```

### 4. Execute a program

```bash
python questlang/main.py examples/valid1_dungeon.qst --run
```

Example output:

```text
Player cannot enter dungeon
```

## Running the Test Suite

To run all Part 2 tests:

```bash
python run_tests.py
```

The test runner checks:

- the three valid example programs with `--type-check`
- the three valid example programs with `--run`
- the type error example
- the five malformed parser examples

Expected final result:

```text
Passed 12/12 test cases.
```

## Example Programs

### `valid1_dungeon.qst`

Demonstrates:

- player declaration
- function declaration
- function call
- field access
- Boolean expression
- `if/else`
- `reward gold`
- `log`

Expected run output:

```text
Player cannot enter dungeon
```

### `valid2_veteran.qst`

Demonstrates:

- player declaration
- Boolean function
- comparison expression
- `if` statement without `else`
- gold reward

Expected run output:

```text
Rewarded 200 gold to hero (gold=250)
Veteran bonus granted
```

### `valid3_potion.qst`

Demonstrates:

- field access with `p.gold`
- string literal
- `reward item`
- `if/else`

Expected run output:

```text
Rewarded item 'potion' to hero
Potion added to inventory
```

## Type Error Example

The file `examples/type_error_bad_reward.qst` contains:

```questlang
reward gold "potion";
```

This is syntactically valid but semantically invalid because `reward gold` requires an integer expression.

Expected output:

```text
TypeCheckError: Type error in reward gold: expected 'int', got 'string'.
```

## Language Summary

QuestLang has four primitive types:

```text
int, float, bool, string
```

It has one built-in structured type:

```text
Player
```

The `Player` type has the following fields:

```text
level  : int
gold   : int
hasKey : bool
```

The main top-level declarations are:

```questlang
player hero: Player {
    level = 5;
    gold = 20;
    hasKey = false;
}

func canEnterDungeon(p: Player): bool {
    return p.level >= 5 && p.hasKey == true;
}

quest DungeonEntry {
    if canEnterDungeon(hero) {
        reward gold 100;
        log("Dungeon quest completed");
    } else {
        log("Player cannot enter dungeon");
    }
}
```

## Type Checker

The type checker performs a semantic pass after parsing and before interpretation. It checks:

- duplicate global names
- valid `Player` fields
- missing or duplicate `Player` fields
- field initialization types
- function parameter types
- function call argument counts and types
- function return types
- `if` conditions as `bool`
- `log` arguments as `string`
- `reward gold` expressions as `int`
- `reward item` expressions as `string`
- field access only on `Player`
- operator operand types

QuestLang is strongly typed. The only implicit coercion rule is:

```text
int -> float
```

No implicit coercion is allowed from `float` to `int`, from `bool` to numeric types, from `string` to another type, or from `Player` to another type.

## Interpreter

The interpreter executes the AST after successful type checking.

Execution order:

1. collect global declarations
2. initialize player objects
3. execute quest declarations in source order

Runtime behavior:

- `log(expr)` appends text to the output
- `reward gold expr` adds gold to the default player
- `reward item expr` adds an item to the default player's inventory
- function calls create a new parameter environment
- return statements are handled using an internal return signal
- Boolean `&&` and `||` use short-circuit evaluation

In the current QuestLang subset, reward statements apply to the default player, which is the first player declared in the program.

## Error Handling

The implementation reports:

- lexer errors
- parser errors with line and column numbers
- type checker errors before execution
- runtime errors during interpretation

Examples of runtime errors handled by the interpreter include:

- division by zero
- undefined identifiers
- invalid field access
- function call errors
- negative gold rewards
- empty item rewards
- missing function return values

## Notes

The final implementation is intentionally small. QuestLang is not a full game engine or a general-purpose programming language. It focuses on a narrow quest-scripting domain so that the language design, type system, and interpreter behavior can be explained clearly.
