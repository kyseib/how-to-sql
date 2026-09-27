"""Grading a learner's SQL against an exercise's reference solution."""

import re
from collections import Counter
from dataclasses import dataclass

from . import db
from .engine import SQLError, execute, last_query

_NUMBER = re.compile(r"^-?\d+(\.\d+)?$")


@dataclass
class Verdict:
    ok: bool
    message: str
    actual: object = None     # Result the learner produced (for display)
    expected: object = None   # Result the solution produced


@dataclass
class Outcome:
    result: object            # Result compared (query result or check result)
    probes: list              # "ok" / error text per probe
    shown: object = None      # what to display to the learner


def _norm_value(v):
    if isinstance(v, str) and _NUMBER.match(v.strip()):
        v = float(v)
    if isinstance(v, float):
        v = round(v, 2)
        if v == 0:
            v = 0.0  # fold -0.0
    return v


def _norm_row(row):
    return tuple(_norm_value(v) for v in row)


def run_outcome(exercise, sql):
    """Run `sql` for `exercise` on a fresh database. Raises SQLError."""
    conn = db.connect()
    try:
        if exercise.setup:
            execute(conn, exercise.setup)
        results = execute(conn, sql)
        shown = last_query(results)
        if not exercise.check:
            return Outcome(shown, [], shown)
        # Leave any transaction the learner left open, so probes run cleanly.
        if conn.in_transaction:
            conn.execute("COMMIT")
        probes = []
        for probe in exercise.probes:
            try:
                execute(conn, probe)
                probes.append("ok")
            except SQLError as exc:
                probes.append(str(exc))
        check = last_query(execute(conn, exercise.check))
        return Outcome(check, probes, shown)
    finally:
        conn.close()


def expected_outcome(exercise):
    return run_outcome(exercise, exercise.solution)


def grade(exercise, sql):
    try:
        expected = expected_outcome(exercise)
    except SQLError as exc:  # a bug in the course content, not the learner's fault
        return Verdict(False, f"(course bug) reference solution failed: {exc}")

    try:
        actual = run_outcome(exercise, sql)
    except SQLError as exc:
        return Verdict(False, f"Error: {exc}", expected=expected.result)

    if exercise.check:
        return _grade_state(exercise, actual, expected)
    return _grade_query(exercise, actual.result, expected.result)


def _grade_state(exercise, actual, expected):
    for probe, want, got in zip(exercise.probes, expected.probes, actual.probes):
        first_line = probe.strip().splitlines()[0]
        if want == "ok" and got != "ok":
            return Verdict(False, f"This statement should succeed against your schema but failed:\n"
                                  f"  {first_line}\n  -> {got}", actual.shown, expected.result)
        if want != "ok" and got == "ok":
            return Verdict(False, f"This statement should be rejected by your schema but was "
                                  f"accepted:\n  {first_line}", actual.shown, expected.result)
    ok, why = compare(actual.result, expected.result, exercise.ordered, exercise.check_names)
    if ok:
        return Verdict(True, "Correct! The database ended up in the expected state.",
                       actual.shown, expected.result)
    return Verdict(False, "The database is not in the expected state afterwards.\n"
                          f"Checked with: {exercise.check.strip()}\n{why}",
                   actual.result, expected.result)


def _grade_query(exercise, actual, expected):
    if actual is None:
        return Verdict(False, "Your SQL ran but returned no result set. "
                              "This exercise expects a query (SELECT ...).",
                       None, expected)
    ok, why = compare(actual, expected, exercise.ordered, exercise.check_names)
    if ok:
        return Verdict(True, "Correct!", actual, expected)
    return Verdict(False, why, actual, expected)


def compare(actual, expected, ordered, check_names):
    """Return (ok, explanation)."""
    if actual is None:
        return False, "No result set was produced."
    na, ne = len(actual.columns), len(expected.columns)
    if na != ne:
        return False, (f"Expected {ne} column(s) but got {na}. "
                       f"Expected columns: {', '.join(expected.columns)}")
    if check_names:
        want = [c.lower() for c in expected.columns]
        got = [c.lower() for c in actual.columns]
        if want != got:
            return False, (f"Column names should be: {', '.join(expected.columns)} "
                           f"(yours: {', '.join(actual.columns)}). Use AS to name them.")
    a_rows = [_norm_row(r) for r in actual.rows]
    e_rows = [_norm_row(r) for r in expected.rows]
    if len(a_rows) != len(e_rows):
        return False, f"Expected {len(e_rows)} row(s) but got {len(a_rows)}."
    if Counter(a_rows) != Counter(e_rows):
        # Maybe the columns are right but in a different order?
        if Counter(tuple(sorted(r, key=_single_key)) for r in a_rows) == \
                Counter(tuple(sorted(r, key=_single_key)) for r in e_rows):
            return False, ("The right values, but the columns are in a different order. "
                           f"Expected: {', '.join(expected.columns)}")
        missing = (Counter(e_rows) - Counter(a_rows))
        example = next(iter(missing))
        return False, (f"The rows don't match. For example, this expected row is missing:\n"
                       f"  {_fmt_row(example)}")
    if ordered and a_rows != e_rows:
        return False, "The right rows, but in the wrong order. Check your ORDER BY."
    return True, ""


def _single_key(v):
    return (v is None, str(type(v).__name__) if not isinstance(v, (int, float)) else "num",
            v if v is not None else 0)


def _fmt_row(row):
    return "(" + ", ".join("NULL" if v is None else repr(v) for v in row) + ")"
