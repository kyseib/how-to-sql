"""Terminal rendering: colours, lesson markup, result tables and SQL input."""

import os
import re
import shutil
import sqlite3
import sys
import textwrap

try:  # line editing + history where available
    import readline  # noqa: F401
except ImportError:  # pragma: no cover - Windows without pyreadline
    pass

USE_COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ and os.environ.get("TERM") != "dumb"

_CODES = {
    "bold": "1", "dim": "2", "italic": "3", "under": "4",
    "red": "31", "green": "32", "yellow": "33", "blue": "34",
    "magenta": "35", "cyan": "36", "grey": "90",
}


def style(text, *names):
    if not USE_COLOR or not names:
        return text
    return "\033[" + ";".join(_CODES[n] for n in names) + "m" + text + "\033[0m"


def width():
    return max(40, min(shutil.get_terminal_size((88, 24)).columns, 100) - 2)


def clear():
    if USE_COLOR:
        print("\033[2J\033[H", end="")
    else:
        print()


def rule(char="─"):
    print(style(char * width(), "grey"))


def heading(text):
    print()
    print(style(text, "bold", "cyan"))
    rule()


# ── SQL syntax highlighting ──────────────────────────────────────────────

KEYWORDS = set("""
ABORT ACTION ADD AFTER ALL ALTER ALWAYS ANALYZE AND AS ASC AUTOINCREMENT BEFORE BEGIN
BETWEEN BY CASCADE CASE CAST CHECK COLLATE COLUMN COMMIT CONFLICT CONSTRAINT CREATE
CROSS CURRENT CURRENT_DATE CURRENT_TIME CURRENT_TIMESTAMP DEFAULT DEFERRABLE DEFERRED
DELETE DESC DISTINCT DO DROP EACH ELSE END ESCAPE EXCEPT EXCLUDE EXISTS EXPLAIN FILTER
FIRST FOLLOWING FOR FOREIGN FROM FULL GLOB GROUP GROUPS HAVING IF IGNORE IMMEDIATE IN
INDEX INNER INSERT INSTEAD INTERSECT INTO IS ISNULL JOIN KEY LAST LEFT LIKE LIMIT
MATERIALIZED NATURAL NO NOT NOTHING NOTNULL NULL NULLS OF OFFSET ON OR ORDER OTHERS
OUTER OVER PARTITION PLAN PRAGMA PRECEDING PRIMARY QUERY RAISE RANGE RECURSIVE
REFERENCES REINDEX RELEASE RENAME REPLACE RESTRICT RETURNING RIGHT ROLLBACK ROW ROWS
SAVEPOINT SELECT SET STRICT TABLE TEMP TEMPORARY THEN TIES TO TRANSACTION TRIGGER
UNBOUNDED UNION UNIQUE UPDATE USING VACUUM VALUES VIEW WHEN WHERE WINDOW WITH WITHOUT
TRUE FALSE INTEGER TEXT REAL BLOB NUMERIC
""".split())

_TOKEN = re.compile(
    r"(?P<comment>--[^\n]*|/\*.*?\*/)"
    r"|(?P<string>'(?:[^']|'')*')"
    r"|(?P<ident>\"(?:[^\"]|\"\")*\")"
    r"|(?P<number>\b\d+(?:\.\d+)?\b)"
    r"|(?P<word>\b[A-Za-z_][A-Za-z0-9_]*\b)",
    re.S,
)


def highlight(sql):
    if not USE_COLOR:
        return sql

    def repl(m):
        kind = m.lastgroup
        text = m.group(0)
        if kind == "comment":
            return style(text, "grey", "italic")
        if kind == "string":
            return style(text, "green")
        if kind == "number":
            return style(text, "magenta")
        if kind == "word" and text.upper() in KEYWORDS:
            return style(text, "blue", "bold")
        return text

    return _TOKEN.sub(repl, sql)


def print_sql(sql, indent="  "):
    for line in textwrap.dedent(sql).strip("\n").splitlines():
        print(indent + highlight(line))


# ── Lesson markup ────────────────────────────────────────────────────────
#
#   # Heading                  a section heading
#   plain paragraphs           re-wrapped to the terminal width
#   - item / 1. item           list items (continuation lines indented)
#   lines indented 4 spaces    printed verbatim (diagrams, tables)
#   `code`  **bold**           inline styles
#   ```sql ... ```             SQL shown with highlighting
#   ```run ... ```             SQL shown AND executed; its output is displayed
#   ```text ... ```            verbatim block

_FENCE = re.compile(r"^```(\w*)\n(.*?)^```\s*$", re.S | re.M)
_LIST_ITEM = re.compile(r"^(\s*)(- |\* |\d+\. )")


def inline(text):
    text = re.sub(r"`([^`]+)`", lambda m: style(m.group(1), "yellow"), text)
    text = re.sub(r"\*\*([^*]+)\*\*", lambda m: style(m.group(1), "bold"), text)
    return text


def _visible_len(word):
    return len(word.replace("**", "").replace("`", ""))


def wrap_markup(text, w, indent=0):
    """Wrap text by its *visible* width, keeping `code`/**bold** spans intact
    across line breaks (each line gets balanced markers)."""
    lines, cur, cur_len = [], [], 0
    for word in text.split():
        wl = _visible_len(word)
        if cur and cur_len + 1 + wl > w - indent:
            lines.append(" ".join(cur))
            cur, cur_len = [], 0
        cur.append(word)
        cur_len += wl + (1 if cur_len else 0)
    if cur:
        lines.append(" ".join(cur))
    out, carry = [], ""
    for line in lines:
        line = carry + line
        carry = ""
        if line.count("`") % 2:
            line += "`"
            carry = "`"
        if line.count("**") % 2:
            line += "**"
            carry += "**"
        out.append(line)
    return out


def split_blocks(page):
    """Yield ('text', str) and (fence_kind, str) blocks from a page."""
    page = textwrap.dedent(page).strip("\n") + "\n"
    pos = 0
    for m in _FENCE.finditer(page):
        if m.start() > pos:
            yield "text", page[pos:m.start()]
        yield (m.group(1) or "text"), m.group(2)
        pos = m.end()
    if pos < len(page):
        yield "text", page[pos:]


def render_text(text):
    w = width()
    for para in re.split(r"\n\s*\n", text.strip("\n")):
        if not para.strip():
            continue
        lines = para.split("\n")
        first = lines[0]
        if first.startswith("# "):
            print()
            print(style(first[2:].strip(), "bold", "cyan"))
            continue
        if first.startswith("    "):
            for line in lines:
                print(style(line, "dim") if line.strip().startswith("--") else line)
            print()
            continue
        if _LIST_ITEM.match(first):
            items = []
            for line in lines:
                if _LIST_ITEM.match(line):
                    items.append(line.strip())
                else:
                    items[-1] += " " + line.strip()
            for item in items:
                marker = _LIST_ITEM.match(item).group(2)
                body = item[len(marker):]
                bullet = "  • " if marker.strip() in "-*" else "  " + marker
                wrapped = wrap_markup(body, w, len(bullet)) or [""]
                print(bullet + inline(wrapped[0]))
                for cont in wrapped[1:]:
                    print(" " * len(bullet) + inline(cont))
            print()
            continue
        joined = " ".join(line.strip() for line in lines)
        for line in wrap_markup(joined, w):
            print(inline(line))
        print()


# ── Result tables ────────────────────────────────────────────────────────

def _cell(v, limit=60):
    if v is None:
        return "NULL"
    if isinstance(v, float):
        s = repr(round(v, 6))
    elif isinstance(v, bytes):
        s = f"<{len(v)} bytes>"
    else:
        s = str(v)
    s = s.replace("\n", "⏎")
    return s if len(s) <= limit else s[:limit - 1] + "…"


def print_table(result, max_rows=25, indent="  "):
    if result is None:
        return
    if not result.columns:
        if result.rowcount >= 0:
            n = result.rowcount
            print(indent + style(f"OK — {n} row{'s' if n != 1 else ''} affected", "grey"))
        else:
            print(indent + style("OK", "grey"))
        return
    rows = result.rows[:max_rows]
    cells = [[_cell(v) for v in row] for row in rows]
    headers = [_cell(c) for c in result.columns]
    widths = [len(h) for h in headers]
    for row in cells:
        for i, c in enumerate(row):
            widths[i] = max(widths[i], len(c))
    numeric = [
        all(isinstance(r[i], (int, float)) or r[i] is None for r in rows) and rows
        for i in range(len(headers))
    ]

    def fmt(values, raw=None):
        out = []
        for i, v in enumerate(values):
            padded = v.rjust(widths[i]) if numeric[i] else v.ljust(widths[i])
            if raw is not None and raw[i] is None:
                padded = style(padded, "grey")
            out.append(padded)
        return indent + "│ " + " │ ".join(out) + " │"

    line = lambda l, m, r: indent + l + m.join("─" * (x + 2) for x in widths) + r
    print(style(line("┌", "┬", "┐"), "grey"))
    print(style(fmt(headers), "bold"))
    print(style(line("├", "┼", "┤"), "grey"))
    for raw, row in zip(rows, cells):
        print(fmt(row, raw))
    print(style(line("└", "┴", "┘"), "grey"))
    total = len(result.rows)
    extra = f" (showing first {max_rows})" if total > max_rows else ""
    more = "+" if result.truncated else ""
    print(indent + style(f"{total}{more} row{'s' if total != 1 else ''}{extra}", "grey"))


def print_error(message):
    print(style("  ✗ " + message.replace("\n", "\n    "), "red"))


def print_ok(message):
    print(style("  ✓ " + message, "green", "bold"))


def print_info(message):
    print(style("  " + message.replace("\n", "\n  "), "grey"))


# ── Input ────────────────────────────────────────────────────────────────

class Quit(Exception):
    """Raised when the user presses Ctrl-D / Ctrl-C at a prompt."""


def ask(prompt):
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print()
        raise Quit() from None


def read_sql(prompt="sql> ", cont="...> "):
    """Read SQL until a complete statement (ending in ';') is entered.

    A line starting with a backslash is returned immediately as a command.
    An empty line on the first prompt returns ''. Entering a blank line on a
    continuation prompt submits what was typed, even without a ';'.
    """
    lines = []
    while True:
        try:
            line = input(style(prompt if not lines else cont, "cyan", "bold"))
        except KeyboardInterrupt:
            print()
            if lines:
                lines = []
                continue
            raise Quit() from None
        except EOFError:
            print()
            raise Quit() from None
        if not lines and line.strip().startswith("\\"):
            return line.strip()
        if not lines and not line.strip():
            return ""
        if lines and not line.strip():
            return "\n".join(lines)
        lines.append(line)
        text = "\n".join(lines)
        if sqlite3.complete_statement(text):
            return text


def pause(prompt="Press Enter to continue"):
    ask(style(f"  {prompt} ", "grey"))
