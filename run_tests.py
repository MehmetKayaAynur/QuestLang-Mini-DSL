# run_tests.py
# QuestLang Part 2 test runner

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent

VALID_FILES = [
    "valid1_dungeon.qst",
    "valid2_veteran.qst",
    "valid3_potion.qst",
]

INVALID_PARSE_FILES = [
    "invalid1_missing_semicolon.qst",
    "invalid2_missing_brace.qst",
    "invalid3_bad_param.qst",
    "invalid4_bad_reward.qst",
    "invalid5_bad_expression.qst",
]

TYPE_ERROR_FILES = [
    "type_error_bad_reward.qst",
]

# Optional files: if you add these later, the runner will test them automatically.
RUNTIME_ERROR_FILES = [
    "runtime_error_div_zero.qst",
    "runtime_error_negative_gold.qst",
    "runtime_error_empty_item.qst",
]


def find_main() -> Path:
    """Find main.py in either a flat layout or questlang/ package layout."""
    candidates = [
        ROOT / "questlang" / "main.py",
        ROOT / "main.py",
    ]

    for candidate in candidates:
        if candidate.exists():
            text = candidate.read_text(encoding="utf-8")
            if "--run" not in text:
                raise SystemExit(
                    f"Found {candidate}, but it does not support --run.\n"
                    "Use the Part 2 main.py version that imports Interpreter and handles --run."
                )
            return candidate

    raise SystemExit(
        "Could not find main.py. Expected either questlang/main.py or main.py."
    )


def find_source_file(filename: str, required: bool = True) -> Path | None:
    """Find a .qst file in examples/, root, or questlang/examples/."""
    candidates = [
        ROOT / "examples" / filename,
        ROOT / filename,
        ROOT / "questlang" / "examples" / filename,
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    if required:
        raise SystemExit(f"Missing test file: {filename}")
    return None


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def run_command(args: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def print_header(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def run_case(
    main_py: Path,
    title: str,
    source_file: Path,
    flags: list[str],
    expect_success: bool,
) -> bool:
    command = [sys.executable, str(main_py), str(source_file), *flags]
    code, stdout, stderr = run_command(command)

    passed = (code == 0) if expect_success else (code != 0)
    status = "PASS" if passed else "FAIL"
    expected = "success" if expect_success else "failure"

    print(f"\n--- {title}: {rel(source_file)} ---")
    print(f"Command: python {rel(main_py)} {rel(source_file)} {' '.join(flags)}".rstrip())
    print(f"Expected: {expected} | Exit code: {code} | Result: {status}")

    if stdout:
        print("STDOUT:")
        print(stdout)

    if stderr:
        print("STDERR:")
        print(stderr)

    return passed


def main() -> None:
    main_py = find_main()
    total = 0
    passed = 0

    print_header("QuestLang Part 2 Test Runner")
    print(f"Using main file: {rel(main_py)}")

    print_header("1) Valid programs: type checker")
    for filename in VALID_FILES:
        source = find_source_file(filename)
        total += 1
        if run_case(main_py, "TYPE CHECK", source, ["--type-check"], expect_success=True):
            passed += 1

    print_header("2) Valid programs: full interpreter execution")
    for filename in VALID_FILES:
        source = find_source_file(filename)
        total += 1
        if run_case(main_py, "RUN", source, ["--run"], expect_success=True):
            passed += 1

    print_header("3) Type error programs: rejected before execution")
    for filename in TYPE_ERROR_FILES:
        source = find_source_file(filename)
        total += 1
        if run_case(main_py, "TYPE ERROR", source, ["--type-check"], expect_success=False):
            passed += 1

    print_header("4) Malformed syntax programs: parser errors")
    for filename in INVALID_PARSE_FILES:
        source = find_source_file(filename)
        total += 1
        if run_case(main_py, "PARSE ERROR", source, [], expect_success=False):
            passed += 1

    existing_runtime_error_files = [
        path for name in RUNTIME_ERROR_FILES if (path := find_source_file(name, required=False))
    ]

    if existing_runtime_error_files:
        print_header("5) Runtime error programs: interpreter errors")
        for source in existing_runtime_error_files:
            total += 1
            if run_case(main_py, "RUNTIME ERROR", source, ["--run"], expect_success=False):
                passed += 1
    else:
        print_header("5) Runtime error programs: skipped")
        print("No optional runtime error .qst files found.")

    print_header("Summary")
    print(f"Passed {passed}/{total} test cases.")

    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
