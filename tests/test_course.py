import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sql_tutor import checker, db, ui  # noqa: E402
from sql_tutor.engine import SQLError, execute, split_statements  # noqa: E402
from sql_tutor.lessons import LESSONS  # noqa: E402
from sql_tutor.model import Exercise, Quiz  # noqa: E402

# Lesson examples that are *meant* to fail, to demonstrate constraints.
EXPECTED_EXAMPLE_ERRORS = {
    "DELETE FROM customers WHERE id = 1;",
    "INSERT INTO reviews (product_id, rating) VALUES (1, 9);",
    "INSERT INTO reviews (product_id, rating) VALUES (999, 4);",
}


def all_exercises():
    for lesson in LESSONS:
        for i, ex in enumerate(lesson.exercises):
            yield lesson, i, ex


class ContentTests(unittest.TestCase):
    def test_lesson_ids_unique(self):
        ids = [lesson.id for lesson in LESSONS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_lesson_has_pages_and_exercises(self):
        for lesson in LESSONS:
            self.assertTrue(lesson.pages, lesson.id)
            self.assertTrue(lesson.exercises, lesson.id)

    def test_solutions_pass_and_return_data(self):
        for lesson, i, ex in all_exercises():
            if isinstance(ex, Quiz):
                continue
            with self.subTest(lesson=lesson.id, exercise=i + 1):
                verdict = checker.grade(ex, ex.solution)
                self.assertTrue(verdict.ok, verdict.message)
                result = checker.expected_outcome(ex).result
                self.assertIsNotNone(result)
                self.assertTrue(result.rows, "solution returns no rows")

    def test_ordered_exercises_sort(self):
        for lesson, i, ex in all_exercises():
            if isinstance(ex, Exercise) and ex.ordered and not ex.check:
                with self.subTest(lesson=lesson.id, exercise=i + 1):
                    self.assertIn("ORDER BY", ex.solution.upper())

    def test_quizzes_well_formed(self):
        for lesson, i, ex in all_exercises():
            if isinstance(ex, Quiz):
                with self.subTest(lesson=lesson.id, exercise=i + 1):
                    self.assertTrue(0 <= ex.answer < len(ex.options))
                    self.assertGreaterEqual(len(ex.options), 2)

    def test_lesson_examples_run(self):
        failures = set()
        for lesson in LESSONS:
            conn = db.connect()
            for page in lesson.pages:
                for kind, body in ui.split_blocks(page):
                    if kind != "run":
                        continue
                    try:
                        execute(conn, body)
                    except SQLError as exc:
                        failures.add(exc.statement)
        self.assertEqual(failures, EXPECTED_EXAMPLE_ERRORS)


class CheckerTests(unittest.TestCase):
    def ex(self, lesson_id, number):
        lesson = next(l for l in LESSONS if l.id == lesson_id)
        return lesson.exercises[number - 1]

    def test_column_names_ignored_by_default(self):
        ex = self.ex("01-intro", 3)
        self.assertTrue(checker.grade(ex, "SELECT name AS n, city AS c FROM customers").ok)

    def test_row_order_ignored_unless_asked(self):
        ex = self.ex("01-intro", 3)
        self.assertTrue(checker.grade(ex, "SELECT name, city FROM customers ORDER BY city").ok)

    def test_wrong_order_rejected_when_ordered(self):
        ex = self.ex("03-order", 1)
        verdict = checker.grade(ex, "SELECT name, price FROM products ORDER BY price")
        self.assertFalse(verdict.ok)
        self.assertIn("wrong order", verdict.message)

    def test_column_count_mismatch(self):
        verdict = checker.grade(self.ex("01-intro", 3), "SELECT name FROM customers")
        self.assertFalse(verdict.ok)
        self.assertIn("column", verdict.message)

    def test_swapped_columns_detected(self):
        verdict = checker.grade(self.ex("01-intro", 3), "SELECT city, name FROM customers")
        self.assertFalse(verdict.ok)
        self.assertIn("different order", verdict.message)

    def test_null_trap_rejected(self):
        verdict = checker.grade(self.ex("04-null", 1),
                                "SELECT first_name, last_name FROM employees WHERE email = NULL")
        self.assertFalse(verdict.ok)

    def test_integer_division_rejected(self):
        verdict = checker.grade(self.ex("05-expressions", 3),
                                "SELECT first_name, ROUND(salary / 12, 2) FROM employees")
        self.assertFalse(verdict.ok)

    def test_numeric_text_accepted_as_number(self):
        ex = self.ex("06-dates", 2)
        sql = "SELECT first_name, CAST(strftime('%Y', hire_date) AS INTEGER) FROM employees"
        self.assertTrue(checker.grade(ex, sql).ok)

    def test_alias_required_when_check_names(self):
        ex = self.ex("03-order", 6)
        verdict = checker.grade(ex, "SELECT name, price * 0.9 FROM products WHERE category = 'Audio'")
        self.assertFalse(verdict.ok)
        self.assertIn("Column names", verdict.message)

    def test_sql_error_reported(self):
        verdict = checker.grade(self.ex("01-intro", 1), "SELEC * FROM products")
        self.assertFalse(verdict.ok)
        self.assertTrue(verdict.message.startswith("Error"))

    def test_update_state_checked(self):
        ex = self.ex("13-modifying-data", 2)
        self.assertFalse(checker.grade(
            ex, "UPDATE employees SET salary = salary * 1.10;").ok)  # forgot WHERE

    def test_missing_constraint_caught_by_probe(self):
        ex = self.ex("14-tables-constraints", 3)
        weak = ("CREATE TABLE ratings (id INTEGER PRIMARY KEY, "
                "product_id INTEGER NOT NULL REFERENCES products(id), stars INTEGER NOT NULL);")
        verdict = checker.grade(ex, weak)
        self.assertFalse(verdict.ok)
        self.assertIn("rejected", verdict.message)

    def test_alternative_correct_solution(self):
        ex = self.ex("09-subqueries", 4)
        alt = ("SELECT first_name FROM employees WHERE id NOT IN "
               "(SELECT manager_id FROM employees WHERE manager_id IS NOT NULL)")
        self.assertTrue(checker.grade(ex, alt).ok)

    def test_learner_cannot_break_later_attempts(self):
        ex = self.ex("01-intro", 1)
        checker.grade(ex, "DROP TABLE order_items; DROP TABLE products;")
        self.assertTrue(checker.grade(ex, ex.solution).ok)


class EngineTests(unittest.TestCase):
    def test_split_respects_strings_and_comments(self):
        sql = "SELECT 'a;b'; -- c;d\nSELECT 2; /* x; */"
        self.assertEqual(split_statements(sql), ["SELECT 'a;b';", "-- c;d\nSELECT 2;"])

    def test_split_keeps_trigger_body_together(self):
        sql = ("CREATE TRIGGER t AFTER INSERT ON a BEGIN INSERT INTO b VALUES (1); "
               "INSERT INTO b VALUES (2); END; SELECT 1;")
        self.assertEqual(len(split_statements(sql)), 2)

    def test_statement_without_semicolon(self):
        self.assertEqual(split_statements("SELECT 1"), ["SELECT 1"])

    def test_runaway_query_is_cancelled(self):
        conn = db.connect(sample=False)
        with self.assertRaises(SQLError) as ctx:
            execute(conn, "WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM n) "
                          "SELECT COUNT(*) FROM n;", timeout=0.2)
        self.assertIn("cancelled", str(ctx.exception))

    def test_fresh_connections_are_isolated(self):
        a = db.connect()
        a.execute("DELETE FROM order_items")
        b = db.connect()
        self.assertEqual(b.execute("SELECT COUNT(*) FROM order_items").fetchone()[0], 35)


class EndToEndTests(unittest.TestCase):
    def test_scripted_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            progress = Path(tmp) / "progress.json"
            script = "\n".join([
                "e",                         # lesson 1 menu: exercises
                "SELECT * FROM products;",   # exercise 1
                "",                          # next
                "SELECT first_name FROM employees;",  # wrong
                "\\hint",
                "\\back",
                "b",                         # back to main menu
                "q",
            ]) + "\n"
            env = dict(os.environ, NO_COLOR="1")
            proc = subprocess.run(
                [sys.executable, "-m", "sql_tutor", "--lesson", "1",
                 "--progress-file", str(progress)],
                input=script, capture_output=True, text=True, cwd=ROOT, env=env, timeout=30,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("Correct!", proc.stdout)
            self.assertIn("Expected 3 column(s)", proc.stdout)
            self.assertIn("Hint 1/2", proc.stdout)
            self.assertEqual(json.loads(progress.read_text())["done"], ["01-intro#1"])

    def test_list(self):
        proc = subprocess.run([sys.executable, "-m", "sql_tutor", "--list"],
                              capture_output=True, text=True, cwd=ROOT, timeout=30)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(len(proc.stdout.strip().splitlines()), len(LESSONS))


if __name__ == "__main__":
    unittest.main()
