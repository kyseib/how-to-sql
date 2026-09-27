"""Running SQL text against a connection and collecting the results."""

import sqlite3
import time
from dataclasses import dataclass, field

MAX_ROWS = 5000        # rows fetched per statement; protects the terminal
TIMEOUT_SECONDS = 5.0  # runaway queries (e.g. infinite recursive CTEs) are cut off


class SQLError(Exception):
    """A statement failed. `statement` is the SQL that caused it."""

    def __init__(self, message, statement=""):
        super().__init__(message)
        self.statement = statement


@dataclass
class Result:
    statement: str
    columns: list = field(default_factory=list)
    rows: list = field(default_factory=list)
    rowcount: int = -1
    truncated: bool = False

    @property
    def is_query(self):
        return bool(self.columns)


def split_statements(sql):
    """Split SQL text into complete statements.

    Uses sqlite3.complete_statement so that semicolons inside strings,
    comments, and CREATE TRIGGER ... BEGIN ... END bodies are handled.
    """
    statements = []
    start = 0
    for i, ch in enumerate(sql):
        if ch != ";":
            continue
        candidate = sql[start:i + 1]
        if sqlite3.complete_statement(candidate):
            if _has_code(candidate):
                statements.append(candidate.strip())
            start = i + 1
    tail = sql[start:]
    if _has_code(tail):
        statements.append(tail.strip())
    return statements


def _has_code(text):
    """True if text contains anything other than whitespace, ';' and comments."""
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch.isspace() or ch == ";":
            i += 1
        elif text.startswith("--", i):
            nl = text.find("\n", i)
            i = n if nl == -1 else nl + 1
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end == -1 else end + 2
        else:
            return True
    return False


def execute(conn, sql, timeout=TIMEOUT_SECONDS):
    """Execute every statement in `sql`; return a list of Result objects.

    Raises SQLError on the first failing statement. Statements before the
    failure have already been applied.
    """
    results = []
    deadline = [0.0]

    def watchdog():
        return 1 if time.monotonic() > deadline[0] else 0

    conn.set_progress_handler(watchdog, 10_000)
    try:
        for stmt in split_statements(sql):
            deadline[0] = time.monotonic() + timeout
            try:
                cur = conn.execute(stmt)
                if cur.description:
                    columns = [d[0] for d in cur.description]
                    rows = cur.fetchmany(MAX_ROWS + 1)
                    truncated = len(rows) > MAX_ROWS
                    results.append(Result(stmt, columns, rows[:MAX_ROWS], len(rows), truncated))
                    cur.close()
                else:
                    results.append(Result(stmt, rowcount=cur.rowcount))
            except sqlite3.OperationalError as exc:
                if str(exc) == "interrupted":
                    raise SQLError(
                        f"query cancelled after {timeout:g} seconds "
                        "(is a recursive CTE missing its stop condition?)", stmt
                    ) from None
                raise SQLError(str(exc), stmt) from None
            except sqlite3.Warning as exc:
                raise SQLError(str(exc), stmt) from None
            except sqlite3.Error as exc:
                raise SQLError(str(exc), stmt) from None
    finally:
        conn.set_progress_handler(None, 0)
    return results


def last_query(results):
    """The last result that produced a result set, or None."""
    for res in reversed(results):
        if res.is_query:
            return res
    return None
