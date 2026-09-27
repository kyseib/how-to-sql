# How to SQL

An interactive SQL course that runs in your terminal. Read short lessons with
live examples, then solve exercises that are checked automatically against a
real database.

No installation or dependencies beyond Python 3.8+ (SQLite ships with Python).

```
python3 -m sql_tutor
```

Or install the `how-to-sql` command:

```
pip install .
how-to-sql
```

Options:

```
--lesson N          jump straight to lesson N
--sandbox           open the free-form SQL sandbox
--list              list the lessons
--no-color          plain output
--progress-file F   where progress is saved (default ~/.how_to_sql_progress.json,
                    or $HOW_TO_SQL_PROGRESS)
```

## Curriculum

| #  | Lesson | Covers |
|----|--------|--------|
| 1  | What SQL is & your first SELECT | relational model, statement families, SELECT |
| 2  | Filtering rows with WHERE | comparisons, AND/OR precedence, IN, BETWEEN, LIKE |
| 3  | Sorting, limiting, DISTINCT, aliases | ORDER BY, NULL ordering, LIMIT/OFFSET, keyset pagination |
| 4  | NULL and three-valued logic | IS NULL, COALESCE, NULLIF, negative-filter traps |
| 5  | Expressions, functions, CASE | integer division, string functions, CAST, CASE |
| 6  | Dates and times | ISO dates, date arithmetic, cross-dialect equivalents |
| 7  | Aggregation | COUNT variants, GROUP BY, HAVING, evaluation order, conditional aggregation |
| 8  | Joins | INNER, LEFT, anti-joins, ON vs WHERE, FULL, CROSS, self joins, fan-out |
| 9  | Subqueries | scalar, IN, EXISTS, correlated, derived tables, the NOT IN trap |
| 10 | Set operations | UNION [ALL], INTERSECT, EXCEPT |
| 11 | CTEs and recursion | WITH, recursive series, hierarchies, calendars |
| 12 | Window functions | PARTITION BY, ranking, running totals, frames, LAG/LEAD, top-N per group |
| 13 | Changing data | INSERT, UPDATE, DELETE, cascades, RETURNING, upsert |
| 14 | Tables and constraints | types, money, keys, CHECK, foreign keys, ALTER, migrations |
| 15 | Transactions | ACID, savepoints, isolation levels, anomalies, lost updates, deadlocks |
| 16 | Indexes and performance | B-trees, EXPLAIN, composite indexes, sargability, habits |
| 17 | Views and triggers | views, materialized views, audit triggers |
| 18 | Database design | relationships, keys, 1NF–3NF, denormalization, star schemas |
| 19 | SQL in applications | parameterized queries, SQL injection, least privilege, ORMs, N+1 |
| 20 | Dialects and style | SQLite/PostgreSQL/MySQL/SQL Server differences, style, workflow, mistakes |
| 21 | Final challenges | multi-concept analytics problems |

Plus a sandbox, a schema browser and a cheat sheet from the main menu.

## How exercises are graded

Each attempt runs on a fresh copy of the sample database, so nothing you do can
break later exercises. Your result is compared with the reference solution's:

- Column names are ignored unless the task asks for specific names.
- Row order is ignored unless the task asks for a specific order.
- Numbers are compared to 2 decimal places; numeric text (`'2023'`) matches numbers.
- For INSERT/UPDATE/DELETE/CREATE tasks, the resulting database state is
  checked, and constraint tasks are probed with inserts that must succeed or fail.

Exercise commands: `\hint`, `\expected`, `\solution`, `\schema [table]`,
`\next`, `\prev`, `\back`, `\help`.

## Engine notes

The course runs on SQLite. A few examples (RIGHT/FULL JOIN, `IS DISTINCT FROM`)
need SQLite 3.39+; check yours with
`python3 -c "import sqlite3; print(sqlite3.sqlite_version)"`. Dialect
differences for PostgreSQL, MySQL and SQL Server are called out throughout.

## Development

```
python3 -m unittest discover -s tests
```

The tests run every reference solution through the grader, execute every live
example in every lesson, and drive a scripted session end to end.

Lesson content lives in `sql_tutor/lessons/` as plain Python data (`Lesson`,
`Exercise`, `Quiz` from `sql_tutor/model.py`). Page markup: `# heading`,
`- lists`, 4-space-indented verbatim blocks, `` `code` ``, `**bold**`,
```` ```sql ```` (display) and ```` ```run ```` (display and execute) fences.
