from ..model import Exercise, Lesson, Quiz

APPLICATIONS = Lesson(
    id="19-sql-in-applications",
    title="SQL from application code, and security",
    summary="Drivers, parameterized queries, SQL injection, ORMs, permissions.",
    pages=[
        """
        # Talking to a database from code

        Applications send SQL through a driver. In Python:

        ```text
        import sqlite3
        conn = sqlite3.connect("shop.db")
        rows = conn.execute(
            "SELECT id, name FROM customers WHERE country = ?", ("USA",)
        ).fetchall()
        ```

        The `?` is a **placeholder**. The value is sent separately from the
        SQL text, so the database never interprets it as code. Placeholder
        style varies by driver: `?` (SQLite, JDBC), `%s` (psycopg, MySQL
        drivers), `$1` (PostgreSQL native), `:name` / `@name` (named styles).
        """,
        """
        # SQL injection

        Never build SQL by pasting user input into a string:

        ```text
        name = request.args["name"]
        sql = "SELECT * FROM customers WHERE name = '" + name + "'"   # VULNERABLE
        ```

        If a user types `x' OR '1'='1`, the query becomes:

        ```run
        SELECT id, name FROM customers WHERE name = 'x' OR '1'='1';
        ```

        ...and returns every customer. Worse inputs can read other tables
        (`' UNION SELECT ...`), bypass logins, or modify data. SQL injection
        has been one of the most common and damaging web vulnerabilities for
        decades.

        **The fix is always parameterized queries.** Escaping quotes by hand
        is error-prone; don't. Placeholders only work for *values*, not for
        table/column names or keywords like ASC/DESC. When those must be
        dynamic, choose them from a fixed whitelist in code.
        """,
        """
        # Permissions: least privilege

        Databases have users and roles. Grant each application only what it
        needs:

        ```sql
        CREATE ROLE reporting;
        GRANT SELECT ON orders, customers TO reporting;
        REVOKE DELETE ON orders FROM app_user;
        ```

        (SQLite has no users — it's a file; access is controlled by file
        permissions.) A web app's account should not be able to DROP tables.
        A read-only analytics account limits the damage of mistakes and
        attacks alike. Combine with views to expose only permitted columns.

        # ORMs and query builders

        ORMs (SQLAlchemy, Django ORM, ActiveRecord, Hibernate, Entity
        Framework, Prisma) map tables to objects and generate SQL for you.
        They speed up routine CRUD and parameterize automatically. But they
        can generate inefficient SQL — especially the **N+1 problem** from
        lazy loading related objects inside a loop. Know the SQL your ORM
        emits (turn on query logging), and drop to raw SQL for reporting and
        complex queries. Knowing SQL well makes you better at using ORMs.
        """,
        """
        # Operating a database

        A few operational essentials:

        - **Connection pooling** — opening connections is expensive; reuse
          them (PgBouncer, HikariCP, your framework's pool).
        - **Migrations** — version-controlled schema changes, applied the same
          way in every environment. Make them backward compatible (add a
          column, deploy code, then remove the old one later).
        - **Backups** — automated, and *restore-tested*. A backup you've
          never restored is a hope, not a backup.
        - **Monitoring** — watch slow-query logs, and review the plans of your
          most frequent and slowest queries.
        - **Secrets** — keep database credentials out of source code.
        """,
    ],
    exercises=[
        Exercise(
            prompt="An app builds: SELECT id, name FROM customers WHERE name = '<input>'. "
                   "Write the full query produced when an attacker enters "
                   "`nobody' OR 'a'='a` — and see what it returns.",
            solution="SELECT id, name FROM customers WHERE name = 'nobody' OR 'a'='a';",
            hints=["Paste the input between the quotes exactly as typed.",
                   "WHERE name = 'nobody' OR 'a'='a'"],
            explanation="The attacker's quote closed the string, and OR 'a'='a' made the "
                        "condition true for every row. A placeholder would have searched "
                        "for a customer literally named \"nobody' OR 'a'='a\".",
        ),
        Quiz(
            question="What is the correct defence against SQL injection?",
            options=["Escape single quotes in user input",
                     "Reject input containing SQL keywords",
                     "Pass user input as query parameters (placeholders)",
                     "Use a longer database password"],
            answer=2,
            explanation="Parameters keep data separate from code. Blacklists and manual "
                        "escaping are routinely bypassed.",
        ),
        Quiz(
            question="The user picks a sort column in the UI. How do you put it in the query?",
            options=["As a ? parameter: ORDER BY ?",
                     "Concatenate the user's string into ORDER BY",
                     "Map the choice to a column name from a fixed whitelist in code",
                     "Sort in SQL by all columns"],
            answer=2,
            explanation="Placeholders bind values, not identifiers; ORDER BY ? sorts by a "
                        "constant. Whitelisting is the safe approach.",
        ),
        Quiz(
            question="Code loads 100 orders, then runs one query per order to fetch its "
                     "customer. What is this called?",
            options=["The N+1 query problem", "A cartesian product", "A deadlock",
                     "Lazy evaluation"],
            answer=0,
            explanation="101 round-trips instead of 1 or 2. Use a JOIN or "
                        "WHERE id IN (...), or your ORM's eager-loading option.",
        ),
    ],
)

DIALECTS = Lesson(
    id="20-dialects-style",
    title="Dialects, style and effective habits",
    summary="How major databases differ; writing readable, correct SQL.",
    pages=[
        """
        # Dialect cheat sheet

            Feature          SQLite           PostgreSQL        MySQL             SQL Server
            ---------------  ---------------  ----------------  ----------------  ----------------
            first N rows     LIMIT n          LIMIT n           LIMIT n           TOP n / FETCH
            concat           a || b           a || b            CONCAT(a, b)      a + b / CONCAT
            auto id          INTEGER PRIMARY  GENERATED ...     AUTO_INCREMENT    IDENTITY(1,1)
                             KEY              AS IDENTITY
            boolean          0 / 1            BOOLEAN           TINYINT(1)        BIT
            ident quoting    "col"            "col"             `col`             [col] / "col"
            case-insens.     LIKE (ASCII)     ILIKE             LIKE (collation)  LIKE (collation)
            upsert           ON CONFLICT      ON CONFLICT       ON DUPLICATE KEY  MERGE
            string agg       GROUP_CONCAT     STRING_AGG        GROUP_CONCAT      STRING_AGG
            now              datetime('now')  NOW()             NOW()             GETDATE()
            if-null          IFNULL/COALESCE  COALESCE          IFNULL/COALESCE   ISNULL/COALESCE

        Prefer the standard forms (COALESCE, CASE, CAST, JOIN ... ON,
        FETCH FIRST where supported) when writing portable SQL.

        Identifier case: PostgreSQL folds unquoted names to lower case
        (`SELECT Name` means `name`), so `"Name"` and `Name` are different.
        Avoid quoted mixed-case identifiers; use snake_case.
        """,
        """
        # Writing readable SQL

        ```sql
        -- Revenue per country for 2023, delivered orders only
        WITH delivered AS (
            SELECT o.id, c.country
            FROM orders AS o
            JOIN customers AS c ON c.id = o.customer_id
            WHERE o.status = 'delivered'
              AND o.order_date >= '2023-01-01'
              AND o.order_date <  '2024-01-01'
        )
        SELECT d.country,
               SUM(oi.quantity * oi.unit_price) AS revenue
        FROM delivered AS d
        JOIN order_items AS oi ON oi.order_id = d.id
        GROUP BY d.country
        ORDER BY revenue DESC;
        ```

        - One clause per line; indent continuation lines consistently.
        - Consistent keyword case (UPPER is common).
        - Meaningful aliases (`o`, `c`, `oi` — not `a`, `b`, `c`).
        - Qualify every column when more than one table is involved.
        - CTEs for multi-step logic instead of deeply nested subqueries.
        - Explicit `JOIN ... ON`, never comma joins.
        - Explicit column lists in INSERT and in production SELECTs.
        - Comment the *why*, not the what.
        """,
        """
        # A workflow for writing a hard query

        1. **State the grain.** "One row per customer per month." Everything
           follows from this.
        2. **Find the tables** that hold the facts, and how they join.
        3. **Build incrementally.** Start from FROM + one JOIN, look at the
           rows, add the next join, add filters, then aggregate. Run it at
           every step.
        4. **Check row counts** after each join. Unexpected growth means
           fan-out; unexpected shrinkage means an inner join dropped rows
           (should it be LEFT?).
        5. **Sanity-check totals** against a simple known number
           (e.g. SUM over everything vs. sum of your groups).
        6. **Test edge cases:** NULLs, ties, empty groups, duplicates,
           boundaries of date ranges.
        """,
        """
        # Common mistakes checklist

        - `= NULL` instead of `IS NULL`.
        - `NOT IN (subquery)` where the subquery can return NULL.
        - Filtering the right table of a LEFT JOIN in WHERE.
        - Integer division (`5 / 2 = 2`).
        - `BETWEEN` on timestamps: `BETWEEN '2024-01-01' AND '2024-01-31'`
          misses everything after midnight on the 31st. Use `>= start AND
          < next_start`.
        - Summing after a one-to-many join (double counting).
        - Relying on row order without ORDER BY.
        - `COUNT(*)` vs `COUNT(col)` confusion with outer joins: count a
          column from the right table to get 0 for no matches.
        - `SELECT DISTINCT` hiding a bad join.
        - UPDATE/DELETE without WHERE (or with the wrong one).
        - Money in floating point.
        - Building SQL with string concatenation from user input.
        - Non-sargable filters (functions on indexed columns).
        """,
    ],
    exercises=[
        Quiz(
            question="How do you return only the first 10 rows in SQL Server?",
            options=["LIMIT 10", "SELECT TOP 10 ...", "ROWNUM <= 10", "FIRST 10"],
            answer=1,
            explanation="SQL Server also supports OFFSET 0 ROWS FETCH NEXT 10 ROWS ONLY.",
        ),
        Quiz(
            question="`WHERE created_at BETWEEN '2024-01-01' AND '2024-01-31'` on a timestamp "
                     "column: what's wrong?",
            options=["Nothing", "BETWEEN excludes the end date",
                     "It misses times after 00:00:00 on Jan 31",
                     "Timestamps can't be compared to strings"],
            answer=2,
            explanation="'2024-01-31 15:00' > '2024-01-31'. Use created_at >= '2024-01-01' AND "
                        "created_at < '2024-02-01'.",
        ),
        Quiz(
            question="After LEFT JOINing departments to employees, which gives 0 for a "
                     "department with no employees?",
            options=["COUNT(*)", "COUNT(e.id)", "SUM(1)", "COUNT(d.id)"],
            answer=1,
            explanation="The unmatched department still produces one row (with NULL "
                        "employee columns). COUNT(*) counts it as 1; COUNT(e.id) skips NULLs.",
        ),
        Exercise(
            prompt="Show every department's `name` and its number of employees, including "
                   "departments with 0 employees.",
            solution="SELECT d.name, COUNT(e.id) FROM departments d "
                     "LEFT JOIN employees e ON e.department_id = d.id GROUP BY d.id, d.name;",
            hints=["LEFT JOIN from departments, then GROUP BY.",
                   "COUNT(e.id), not COUNT(*), so empty departments show 0."],
        ),
    ],
)

CHALLENGES = Lesson(
    id="21-challenges",
    title="Final challenges",
    summary="Realistic problems that combine everything.",
    pages=[
        """
        # Put it all together

        These problems resemble real analytics and interview questions. Each
        needs several concepts at once. Use the workflow from lesson 20:
        state the grain, build incrementally, check counts.

        Useful reminders:

        - Revenue of a line item is `quantity * unit_price`.
        - "Real" sales usually exclude cancelled orders.
        - Use `\\schema` to look at table definitions at any time.
        - `\\expected` shows the target output if you're stuck on the shape.
        """,
    ],
    exercises=[
        Exercise(
            prompt="Sales rep leaderboard: for each employee who is the rep on at least one "
                   "non-cancelled order, show full name ('First Last'), number of "
                   "non-cancelled orders, and revenue from those orders. Highest revenue first.",
            solution="SELECT e.first_name || ' ' || e.last_name AS rep, "
                     "COUNT(DISTINCT o.id) AS orders, SUM(oi.quantity * oi.unit_price) AS revenue "
                     "FROM employees e JOIN orders o ON o.employee_id = e.id "
                     "JOIN order_items oi ON oi.order_id = o.id "
                     "WHERE o.status <> 'cancelled' GROUP BY e.id ORDER BY revenue DESC;",
            ordered=True,
            hints=["Joining order_items multiplies orders: use COUNT(DISTINCT o.id).",
                   "employees → orders → order_items, WHERE status <> 'cancelled', GROUP BY e.id"],
        ),
        Exercise(
            prompt="Best-seller per category: for each category, the product with the "
                   "largest total quantity sold on non-cancelled orders. Show category, "
                   "product name, and quantity. (Categories with no sales are omitted.)",
            solution="WITH sold AS (SELECT p.category, p.name, SUM(oi.quantity) AS qty "
                     "FROM products p JOIN order_items oi ON oi.product_id = p.id "
                     "JOIN orders o ON o.id = oi.order_id WHERE o.status <> 'cancelled' "
                     "GROUP BY p.id), ranked AS (SELECT *, RANK() OVER "
                     "(PARTITION BY category ORDER BY qty DESC) AS r FROM sold) "
                     "SELECT category, name, qty FROM ranked WHERE r = 1;",
            hints=["Step 1 (CTE): total quantity per product.",
                   "Step 2: rank within each category with a window function; keep rank 1."],
        ),
        Exercise(
            prompt="Monthly revenue for 2023 (non-cancelled orders): month as 'YYYY-MM', "
                   "revenue, and the change from the previous month (NULL for the first "
                   "month). Only months with non-cancelled sales; in month order.",
            solution="WITH m AS (SELECT strftime('%Y-%m', o.order_date) AS month, "
                     "SUM(oi.quantity * oi.unit_price) AS revenue FROM orders o "
                     "JOIN order_items oi ON oi.order_id = o.id WHERE o.status <> 'cancelled' "
                     "AND o.order_date >= '2023-01-01' AND o.order_date < '2024-01-01' "
                     "GROUP BY month) SELECT month, revenue, "
                     "revenue - LAG(revenue) OVER (ORDER BY month) FROM m ORDER BY month;",
            ordered=True,
            hints=["First aggregate revenue per month in a CTE.",
                   "Then revenue - LAG(revenue) OVER (ORDER BY month)."],
        ),
        Exercise(
            prompt="List the `name` of customers who have placed at least one order and "
                   "ALL of whose orders are delivered.",
            solution="SELECT c.name FROM customers c "
                     "WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id) "
                     "AND NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id "
                     "AND o.status <> 'delivered');",
            hints=["'All orders are X' = 'there is no order that is not X'.",
                   "EXISTS (any order) AND NOT EXISTS (an order with status <> 'delivered')",
                   "Alternative: GROUP BY customer HAVING SUM(status <> 'delivered') = 0"],
        ),
        Exercise(
            prompt="For each customer with orders, show `name`, first order date, most "
                   "recent order date, and the number of days between them.",
            solution="SELECT c.name, MIN(o.order_date), MAX(o.order_date), "
                     "julianday(MAX(o.order_date)) - julianday(MIN(o.order_date)) "
                     "FROM customers c JOIN orders o ON o.customer_id = c.id GROUP BY c.id;",
            hints=["MIN and MAX work on dates.",
                   "julianday(MAX(...)) - julianday(MIN(...))"],
        ),
        Exercise(
            prompt="Share of revenue by category (non-cancelled orders): category and its "
                   "percentage of total revenue rounded to 1 decimal, largest first.",
            solution="WITH r AS (SELECT p.category, SUM(oi.quantity * oi.unit_price) AS rev "
                     "FROM order_items oi JOIN products p ON p.id = oi.product_id "
                     "JOIN orders o ON o.id = oi.order_id WHERE o.status <> 'cancelled' "
                     "GROUP BY p.category) SELECT category, "
                     "ROUND(100.0 * rev / SUM(rev) OVER (), 1) AS pct FROM r ORDER BY pct DESC;",
            ordered=True,
            hints=["Compute revenue per category first.",
                   "SUM(rev) OVER () is the grand total on every row.",
                   "Multiply by 100.0 (not 100) to avoid integer division."],
        ),
        Exercise(
            prompt="Find employees who share their salary with at least one other employee: "
                   "show `first_name` and `salary`.",
            solution="SELECT first_name, salary FROM employees WHERE salary IN "
                     "(SELECT salary FROM employees GROUP BY salary HAVING COUNT(*) > 1);",
            hints=["Find duplicated salaries with GROUP BY ... HAVING COUNT(*) > 1.",
                   "Or: COUNT(*) OVER (PARTITION BY salary) > 1 in a CTE."],
        ),
        Exercise(
            prompt="Products that need reordering: show product `name`, current `stock`, "
                   "and units sold in 2024 (non-cancelled), for products whose 2024 sales "
                   "exceed their current stock.",
            solution="SELECT p.name, p.stock, SUM(oi.quantity) AS sold FROM products p "
                     "JOIN order_items oi ON oi.product_id = p.id JOIN orders o ON o.id = oi.order_id "
                     "WHERE o.status <> 'cancelled' AND o.order_date >= '2024-01-01' "
                     "GROUP BY p.id HAVING SUM(oi.quantity) > p.stock;",
            hints=["Filter orders to 2024 in WHERE, aggregate per product, compare in HAVING."],
        ),
    ],
)

LESSONS = [APPLICATIONS, DIALECTS, CHALLENGES]
