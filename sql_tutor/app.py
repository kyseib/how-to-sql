"""The interactive course: menus, lesson pages, exercises and the sandbox."""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

from . import __version__, checker, db, reference, ui
from .engine import SQLError, execute
from .lessons import LESSONS, exercise_id
from .model import Quiz
from .ui import style

EXERCISE_HELP = """\
  Type SQL and end it with ';' (or press Enter on an empty line) to submit.
  \\hint          show the next hint
  \\expected      show the expected output
  \\solution      reveal the reference solution
  \\schema [t]    list tables, or describe table t
  \\next  \\prev   move between exercises (\\skip = \\next)
  \\back          back to the lesson menu
  \\help          this help
  Ctrl-C clears a half-typed query; Ctrl-D quits."""

SANDBOX_HELP = """\
  Any SQL runs against a private copy of the sample database.
  \\schema [t]    list tables, or describe table t
  \\reset         restore the original sample data
  \\back          return to the main menu
  \\help          this help"""


# ── Progress ─────────────────────────────────────────────────────────────

class Progress:
    def __init__(self, path):
        self.path = Path(path)
        self.done = set()
        self.revealed = set()
        try:
            data = json.loads(self.path.read_text())
            self.done = set(data.get("done", []))
            self.revealed = set(data.get("revealed", []))
        except (OSError, ValueError):
            pass

    def save(self):
        try:
            self.path.write_text(json.dumps(
                {"done": sorted(self.done), "revealed": sorted(self.revealed)}, indent=1))
        except OSError:
            pass  # progress is a convenience; never crash over it

    def mark(self, ex_id):
        self.done.add(ex_id)
        self.save()

    def reset(self):
        self.done.clear()
        self.revealed.clear()
        self.save()

    def lesson_counts(self, lesson):
        ids = [exercise_id(lesson, i) for i in range(len(lesson.exercises))]
        return sum(1 for i in ids if i in self.done), len(ids)


def default_progress_path():
    return os.environ.get("HOW_TO_SQL_PROGRESS",
                          str(Path.home() / ".how_to_sql_progress.json"))


# ── Shared display helpers ───────────────────────────────────────────────

def run_and_show(conn, sql, show_status=True):
    """Execute SQL and print its result sets. Returns True on success."""
    try:
        results = execute(conn, sql)
    except SQLError as exc:
        ui.print_error(f"Error: {exc}")
        return False
    queries = [r for r in results if r.is_query]
    for res in queries:
        ui.print_table(res)
    if not queries and results and show_status:
        ui.print_table(results[-1])
    return True


def show_schema(conn, table=None):
    tables = db.table_names(conn)
    views = db.view_names(conn)
    if table:
        name = table.strip().strip(";").strip('"')
        if name not in tables and name not in views:
            ui.print_error(f"No table or view named {name!r}. Tables: {', '.join(tables)}")
            return
        count = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
        kind = "view" if name in views else "table"
        print(f"\n  {style(name, 'bold')} ({kind}, {count} rows)")
        if name in db.TABLE_NOTES:
            print("  " + style(db.TABLE_NOTES[name], "grey"))
        columns = db.describe(conn, name)
        composite = sum(1 for c in columns if c[4]) > 1
        for col, ctype, notnull, default, pk, ref in columns:
            flags = []
            if pk:
                flags.append(f"PRIMARY KEY (part {pk})" if composite else "PRIMARY KEY")
            if notnull:
                flags.append("NOT NULL")
            if default is not None:
                flags.append(f"DEFAULT {default}")
            if ref:
                flags.append(f"→ {ref}")
            print(f"    {style(col.ljust(15), 'yellow')} {(ctype or '').ljust(9)} "
                  f"{style(' '.join(flags), 'grey')}")
        print()
        return
    print()
    for name in tables + views:
        cols = ", ".join(c[0] for c in db.describe(conn, name))
        label = name + (" (view)" if name in views else "")
        print(f"  {style(label.ljust(16), 'bold')} {cols}")
    print(style("\n  \\schema <table> for column types, keys and notes.\n", "grey"))


def render_page(page, conn):
    for kind, body in ui.split_blocks(page):
        if kind == "text":
            ui.render_text(body)
        elif kind == "sql":
            ui.print_sql(body)
            print()
        elif kind == "run":
            ui.print_sql(body)
            run_and_show(conn, body)
            print()
        else:
            for line in body.rstrip("\n").splitlines():
                print("  " + line)
            print()


# ── The application ──────────────────────────────────────────────────────

class App:
    def __init__(self, progress):
        self.progress = progress

    # main menu -------------------------------------------------------------

    def run(self, start_lesson=None):
        if start_lesson is not None:
            self.lesson_menu(LESSONS[start_lesson])
        while True:
            ui.clear()
            self.print_banner()
            self.print_lessons()
            print()
            print(f"  {style('c', 'bold')}  continue where you left off")
            print(f"  {style('s', 'bold')}  sandbox — write any SQL against the sample database")
            print(f"  {style('d', 'bold')}  describe the sample database")
            print(f"  {style('r', 'bold')}  reference / cheat sheet")
            print(f"  {style('x', 'bold')}  reset progress")
            print(f"  {style('q', 'bold')}  quit")
            choice = ui.ask(style("\n  Choose a lesson number or letter: ", "cyan")).strip().lower()
            if choice in ("q", "quit", "exit"):
                return
            if choice == "c":
                self.lesson_menu(self.next_lesson())
            elif choice == "s":
                self.sandbox()
            elif choice == "d":
                self.describe_database()
            elif choice == "r":
                self.pager("Reference", reference.PAGES, db.connect())
            elif choice == "x":
                if ui.ask("  Erase all progress? Type yes to confirm: ").strip().lower() == "yes":
                    self.progress.reset()
            elif choice.isdigit() and 1 <= int(choice) <= len(LESSONS):
                self.lesson_menu(LESSONS[int(choice) - 1])

    def print_banner(self):
        done = len(self.progress.done)
        total = sum(len(l.exercises) for l in LESSONS)
        print(style("  HOW TO SQL", "bold", "cyan") +
              style(f"  — an interactive SQL course  (v{__version__})", "grey"))
        print(style(f"  {done}/{total} exercises complete", "grey"))
        if sqlite3.sqlite_version_info < (3, 39):
            print(style(f"  Note: your SQLite is {sqlite3.sqlite_version}; a few examples "
                        "(RIGHT/FULL JOIN, IS DISTINCT FROM) need 3.39+.", "yellow"))
        ui.rule()

    def print_lessons(self):
        for n, lesson in enumerate(LESSONS, 1):
            got, total = self.progress.lesson_counts(lesson)
            filled = round(10 * got / total) if total else 0
            bar = style("█" * filled, "green") + style("░" * (10 - filled), "grey")
            mark = style("✓", "green") if total and got == total else " "
            print(f"  {n:>2}. {bar} {mark} {lesson.title.ljust(52)} "
                  f"{style(f'{got}/{total}', 'grey')}")

    def next_lesson(self):
        for lesson in LESSONS:
            got, total = self.progress.lesson_counts(lesson)
            if got < total:
                return lesson
        return LESSONS[-1]

    # lessons ---------------------------------------------------------------

    def lesson_menu(self, lesson):
        number = LESSONS.index(lesson) + 1
        while True:
            ui.clear()
            got, total = self.progress.lesson_counts(lesson)
            print(style(f"  Lesson {number}: {lesson.title}", "bold", "cyan"))
            print(style(f"  {lesson.summary}", "grey"))
            ui.rule()
            print(f"  {style('r', 'bold')}  read the lesson ({len(lesson.pages)} pages)")
            print(f"  {style('e', 'bold')}  exercises ({got}/{total} done)")
            if number < len(LESSONS):
                print(f"  {style('n', 'bold')}  next lesson: {LESSONS[number].title}")
            print(f"  {style('b', 'bold')}  back to the main menu")
            default = "e" if got and got < total else "r"
            choice = ui.ask(style(f"\n  Choice [{default}]: ", "cyan")).strip().lower() or default
            if choice == "r":
                if self.pager(f"Lesson {number}: {lesson.title}", lesson.pages, db.connect()):
                    self.exercises(lesson)
            elif choice == "e":
                self.exercises(lesson)
            elif choice == "n" and number < len(LESSONS):
                lesson = LESSONS[number]
                number += 1
            elif choice in ("b", "q"):
                return

    def pager(self, title, pages, conn):
        """Show pages one at a time. Returns True if the reader finished them all."""
        i = 0
        while 0 <= i < len(pages):
            ui.clear()
            print(style(f"  {title}", "bold", "cyan") +
                  style(f"   page {i + 1}/{len(pages)}", "grey"))
            ui.rule()
            render_page(pages[i], conn)
            ui.rule()
            nav = "Enter: next  b: back  q: leave"
            choice = ui.ask(style(f"  {nav} ", "grey")).strip().lower()
            if choice == "q":
                return False
            if choice == "b":
                i = max(0, i - 1)
            else:
                i += 1
        return True

    # exercises -------------------------------------------------------------

    def exercises(self, lesson):
        if not lesson.exercises:
            return
        ids = [exercise_id(lesson, i) for i in range(len(lesson.exercises))]
        i = next((n for n, ex_id in enumerate(ids) if ex_id not in self.progress.done), 0)
        while 0 <= i < len(lesson.exercises):
            ex = lesson.exercises[i]
            if isinstance(ex, Quiz):
                action = self.quiz(lesson, i, ex)
            else:
                action = self.exercise(lesson, i, ex)
            if action == "back":
                return
            if action == "prev":
                i = max(0, i - 1)
            else:
                i += 1
        got, total = self.progress.lesson_counts(lesson)
        ui.heading("End of exercises")
        print(f"  You've completed {got} of {total} exercises in this lesson.")
        if got == total:
            ui.print_ok("Lesson complete!")
        ui.pause()

    def exercise_header(self, lesson, i):
        ex_id = exercise_id(lesson, i)
        done = style("  ✓ done", "green") if ex_id in self.progress.done else ""
        ui.clear()
        print(style(f"  {lesson.title}", "grey"))
        print(style(f"  Exercise {i + 1} of {len(lesson.exercises)}", "bold", "cyan") + done)
        ui.rule()

    def exercise(self, lesson, i, ex):
        ex_id = exercise_id(lesson, i)
        self.exercise_header(lesson, i)
        ui.render_text(ex.prompt)
        if ex.setup:
            print(style("  Setup already applied for this exercise:", "grey"))
            ui.print_sql(ex.setup.replace(";", ";\n"), indent="    ")
            print()
        print(style("  \\help for commands", "grey"))
        hints_shown = 0
        expected = None
        while True:
            sql = ui.read_sql()
            if not sql:
                continue
            if sql.startswith("\\"):
                cmd, _, arg = sql[1:].partition(" ")
                cmd = cmd.lower()
                if cmd in ("next", "skip", "n"):
                    return "next"
                if cmd in ("prev", "p"):
                    return "prev"
                if cmd in ("back", "b", "q", "quit", "menu"):
                    return "back"
                if cmd in ("help", "h", "?"):
                    print(style(EXERCISE_HELP, "grey"))
                elif cmd == "hint":
                    if hints_shown < len(ex.hints):
                        print(style(f"  Hint {hints_shown + 1}/{len(ex.hints)}: ", "yellow") +
                              ui.inline(ex.hints[hints_shown]))
                        hints_shown += 1
                    else:
                        print(style("  No more hints. \\expected shows the target output; "
                                    "\\solution shows the answer.", "grey"))
                elif cmd == "expected":
                    if expected is None:
                        expected = checker.expected_outcome(ex).result
                    if ex.check:
                        print(style(f"  After your SQL, this check should return:\n  "
                                    f"{ex.check.strip()}", "grey"))
                    ui.print_table(expected)
                elif cmd == "solution":
                    ui.print_sql(ex.solution.replace("; ", ";\n"))
                    self.progress.revealed.add(ex_id)
                    self.progress.save()
                elif cmd in ("schema", "tables", "d"):
                    conn = db.connect()
                    if ex.setup:
                        execute(conn, ex.setup)
                    show_schema(conn, arg or None)
                elif cmd == "clear":
                    self.exercise_header(lesson, i)
                    ui.render_text(ex.prompt)
                else:
                    ui.print_error(f"Unknown command \\{cmd}. Type \\help.")
                continue

            verdict = checker.grade(ex, sql)
            if verdict.actual is not None:
                ui.print_table(verdict.actual, max_rows=15)
            if verdict.ok:
                ui.print_ok(verdict.message)
                if ex.explanation:
                    ui.print_info(ex.explanation)
                self.progress.mark(ex_id)
                if ex_id in self.progress.revealed:
                    print(style("  (solution was revealed — try it again later from memory)",
                                "grey"))
                self.show_solution_if_different(ex, sql)
                choice = ui.ask(style("  Enter: next exercise   r: retry this one   "
                                      "b: back ", "grey")).strip().lower()
                if choice == "r":
                    self.exercise_header(lesson, i)
                    ui.render_text(ex.prompt)
                    continue
                return "back" if choice == "b" else "next"
            ui.print_error(verdict.message)
            print(style("  Try again — \\hint, \\expected or \\solution if you're stuck.", "grey"))

    @staticmethod
    def show_solution_if_different(ex, sql):
        norm = lambda s: " ".join(s.lower().replace(";", " ").split())
        if norm(sql) != norm(ex.solution):
            print(style("  Reference solution, for comparison:", "grey"))
            ui.print_sql(ex.solution.replace("; ", ";\n"), indent="    ")

    def quiz(self, lesson, i, q):
        ex_id = exercise_id(lesson, i)
        self.exercise_header(lesson, i)
        print(style("  Quiz", "magenta", "bold"))
        ui.render_text(q.question)
        letters = "abcdefgh"
        for letter, option in zip(letters, q.options):
            print(f"  {style(letter + ')', 'bold')} {ui.inline(option)}")
        print(style("\n  Answer with a letter (\\next to skip, \\back to leave).", "grey"))
        while True:
            answer = ui.ask(style("answer> ", "cyan", "bold")).strip().lower()
            if answer in ("\\next", "\\skip", "\\n"):
                return "next"
            if answer in ("\\prev", "\\p"):
                return "prev"
            if answer in ("\\back", "\\b", "\\q", "q"):
                return "back"
            if len(answer) != 1 or answer not in letters[:len(q.options)]:
                continue
            if letters.index(answer) == q.answer:
                ui.print_ok("Correct!")
                self.progress.mark(ex_id)
            else:
                ui.print_error(f"Not quite. The answer is {letters[q.answer]}) "
                               f"{q.options[q.answer]}")
            if q.explanation:
                ui.print_info(q.explanation)
            choice = ui.ask(style("  Enter: next   b: back ", "grey")).strip().lower()
            return "back" if choice == "b" else "next"

    # sandbox & database overview ------------------------------------------

    def sandbox(self):
        conn = db.connect()
        ui.clear()
        print(style("  Sandbox", "bold", "cyan") +
              style("  — experiment freely; nothing here affects your progress", "grey"))
        ui.rule()
        print(style(SANDBOX_HELP, "grey"))
        show_schema(conn)
        while True:
            sql = ui.read_sql()
            if not sql:
                continue
            if sql.startswith("\\"):
                cmd, _, arg = sql[1:].partition(" ")
                cmd = cmd.lower()
                if cmd in ("back", "b", "q", "quit", "menu"):
                    return
                if cmd in ("schema", "tables", "d"):
                    show_schema(conn, arg or None)
                elif cmd == "reset":
                    conn = db.connect()
                    ui.print_ok("Sample database restored.")
                elif cmd in ("help", "h", "?"):
                    print(style(SANDBOX_HELP, "grey"))
                else:
                    ui.print_error(f"Unknown command \\{cmd}. Type \\help.")
                continue
            run_and_show(conn, sql)

    def describe_database(self):
        conn = db.connect()
        ui.clear()
        print(style("  The sample database", "bold", "cyan"))
        ui.rule()
        for table in db.table_names(conn):
            show_schema(conn, table)
        ui.pause()


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="how-to-sql",
        description="An interactive SQL course that runs in your terminal.")
    parser.add_argument("--lesson", type=int, metavar="N",
                        help="jump straight to lesson N")
    parser.add_argument("--sandbox", action="store_true",
                        help="open the SQL sandbox directly")
    parser.add_argument("--list", action="store_true", help="list lessons and exit")
    parser.add_argument("--no-color", action="store_true", help="disable colours")
    parser.add_argument("--progress-file", default=default_progress_path(),
                        help="where to store progress (default: %(default)s)")
    args = parser.parse_args(argv)

    if args.no_color:
        ui.USE_COLOR = False
    if args.list:
        for n, lesson in enumerate(LESSONS, 1):
            print(f"{n:>2}. {lesson.title} — {lesson.summary}")
        return
    if args.lesson is not None and not 1 <= args.lesson <= len(LESSONS):
        parser.error(f"--lesson must be between 1 and {len(LESSONS)}")

    app = App(Progress(args.progress_file))
    try:
        if args.sandbox:
            app.sandbox()
        else:
            app.run(None if args.lesson is None else args.lesson - 1)
    except ui.Quit:
        pass
    print(style("  Goodbye — keep querying!", "cyan"))


if __name__ == "__main__":
    main(sys.argv[1:])
