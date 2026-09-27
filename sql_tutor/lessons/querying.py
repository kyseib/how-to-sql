from ..model import Exercise, Lesson, Quiz

AGGREGATION = Lesson(
    id="07-aggregation",
    title="Aggregation: GROUP BY and HAVING",
    summary="COUNT/SUM/AVG/MIN/MAX, grouping, HAVING, order of evaluation.",
    pages=[
        """
        # Aggregate functions

        Aggregates collapse many rows into one value:

        ```run
        SELECT COUNT(*) AS employees, SUM(salary) AS payroll,
               AVG(salary) AS average, MIN(salary) AS lowest, MAX(salary) AS highest
        FROM employees;
        ```

        The three COUNTs are different:

        - `COUNT(*)` counts rows.
        - `COUNT(email)` counts rows where email is NOT NULL.
        - `COUNT(DISTINCT department_id)` counts distinct non-NULL values.

        ```run
        SELECT COUNT(*), COUNT(email), COUNT(department_id),
               COUNT(DISTINCT department_id)
        FROM employees;
        ```

        `SUM`, `AVG`, `MIN`, `MAX` ignore NULLs too. `AVG(bonus)` averages
        only the known bonuses — if missing means zero, write
        `AVG(COALESCE(bonus, 0))`.
        """,
        """
        # GROUP BY

        `GROUP BY` splits rows into groups that share a value, then computes
        the aggregates once per group:

        ```run
        SELECT category, COUNT(*) AS products, AVG(price) AS avg_price
        FROM products
        GROUP BY category
        ORDER BY products DESC, category;
        ```

        You can group by several columns or by expressions:

        ```run
        SELECT strftime('%Y', order_date) AS year, status, COUNT(*) AS orders
        FROM orders GROUP BY year, status ORDER BY year, status;
        ```

        **The rule:** every column in SELECT must either be in GROUP BY or be
        inside an aggregate. `SELECT category, name, COUNT(*) ... GROUP BY
        category` is an error in PostgreSQL and SQL Server ("which name?").
        SQLite and old MySQL modes allow it and pick an arbitrary row's value —
        don't rely on that.
        """,
        """
        # HAVING vs WHERE

        `WHERE` filters rows **before** grouping. `HAVING` filters groups
        **after** aggregation, so it can use aggregates:

        ```run
        SELECT department_id, COUNT(*) AS headcount, AVG(salary) AS avg_salary
        FROM employees
        WHERE title <> 'CEO'           -- row filter
        GROUP BY department_id
        HAVING COUNT(*) >= 2           -- group filter
        ORDER BY avg_salary DESC;
        ```

        Put conditions in WHERE whenever possible: filtering early means less
        work for the grouping step.

        # Logical order of evaluation

        A SELECT is written in one order but evaluated in another:

            1. FROM / JOIN    pick the tables and combine them
            2. WHERE          filter rows
            3. GROUP BY       form groups
            4. HAVING         filter groups
            5. SELECT         compute output columns (and window functions)
            6. DISTINCT       remove duplicates
            7. ORDER BY       sort
            8. LIMIT/OFFSET   cut

        This explains many error messages: WHERE cannot use an alias defined
        in SELECT (it doesn't exist yet), but ORDER BY can.
        """,
        """
        # Conditional aggregation

        Put a CASE inside an aggregate to compute several filtered counts in
        one pass — the basis of most reporting queries and pivot tables:

        ```run
        SELECT
            COUNT(*)                                             AS total,
            SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) AS delivered,
            SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled,
            COUNT(*) FILTER (WHERE status IN ('pending', 'shipped')) AS open
        FROM orders;
        ```

        `FILTER (WHERE ...)` is standard SQL (PostgreSQL, SQLite); the CASE form
        works everywhere.

        Concatenating a group's values into one string:
        `GROUP_CONCAT(name, ', ')` in SQLite/MySQL, `STRING_AGG(name, ', ')`
        in PostgreSQL/SQL Server.

        ```run
        SELECT category, GROUP_CONCAT(name, ', ') AS names
        FROM products GROUP BY category;
        ```
        """,
    ],
    exercises=[
        Exercise(
            prompt="How many employees are there? Return a single number.",
            solution="SELECT COUNT(*) FROM employees;",
            hints=["COUNT(*)"],
        ),
        Exercise(
            prompt="What is the average product price, rounded to 2 decimals?",
            solution="SELECT ROUND(AVG(price), 2) FROM products;",
            hints=["ROUND(AVG(...), 2)"],
        ),
        Exercise(
            prompt="How many customers have an email address on file? Return one number.",
            solution="SELECT COUNT(email) FROM customers;",
            hints=["COUNT(column) skips NULLs."],
        ),
        Exercise(
            prompt="Show each product `category` and the number of products in it.",
            solution="SELECT category, COUNT(*) FROM products GROUP BY category;",
            hints=["GROUP BY category"],
        ),
        Exercise(
            prompt="From `order_items`, show each `product_id` and the total quantity sold.",
            solution="SELECT product_id, SUM(quantity) FROM order_items GROUP BY product_id;",
            hints=["SUM(quantity) grouped by product_id"],
        ),
        Exercise(
            prompt="List the `department_id`s whose average salary is above 100000 "
                   "(ignore employees without a department).",
            solution="SELECT department_id FROM employees WHERE department_id IS NOT NULL "
                     "GROUP BY department_id HAVING AVG(salary) > 100000;",
            hints=["Aggregate conditions go in HAVING.",
                   "WHERE department_id IS NOT NULL ... GROUP BY ... HAVING AVG(salary) > 100000"],
        ),
        Exercise(
            prompt="Show each order `status` with its number of orders, most common first; "
                   "break ties alphabetically by status.",
            solution="SELECT status, COUNT(*) FROM orders GROUP BY status "
                     "ORDER BY COUNT(*) DESC, status;",
            ordered=True,
            hints=["You can ORDER BY an aggregate or its alias."],
        ),
        Exercise(
            prompt="In one row, show the number of orders placed in 2023 and the number "
                   "placed in 2024 (two columns).",
            solution="SELECT SUM(CASE WHEN order_date LIKE '2023%' THEN 1 ELSE 0 END), "
                     "SUM(CASE WHEN order_date LIKE '2024%' THEN 1 ELSE 0 END) FROM orders;",
            hints=["Conditional aggregation: SUM(CASE WHEN ... THEN 1 ELSE 0 END)",
                   "Or COUNT(*) FILTER (WHERE ...)"],
        ),
    ],
)

JOINS = Lesson(
    id="08-joins",
    title="Joins",
    summary="INNER, LEFT, RIGHT, FULL, CROSS and self joins; join pitfalls.",
    pages=[
        """
        # Why joins exist

        Good schemas store each fact once. An employee row doesn't repeat the
        department's name and location; it stores `department_id`, and the
        name lives in `departments`. A **join** reassembles the pieces.

        ```run
        SELECT e.first_name, e.title, d.name AS department
        FROM employees AS e
        JOIN departments AS d ON d.id = e.department_id;
        ```

        `JOIN` (= `INNER JOIN`) pairs every row of the left table with every
        row of the right table for which the `ON` condition is true.
        The aliases `e` and `d` keep things short, and prefixing columns
        (`e.first_name`) is required whenever a name exists in both tables
        (both have `id` and `name`-like columns). Always prefix in joins.

        Notice Sam is missing: Sam's department_id is NULL, so no department
        matches, and an inner join drops unmatched rows.
        """,
        """
        # LEFT JOIN

        `LEFT JOIN` keeps **every** row from the left table. Where nothing on
        the right matches, the right-hand columns are NULL:

        ```run
        SELECT e.first_name, d.name AS department
        FROM employees e
        LEFT JOIN departments d ON d.id = e.department_id
        WHERE e.id >= 14;
        ```

        Flip it around to find departments with no employees — the
        **anti-join** pattern: left join, then keep rows where the right side
        is NULL.

        ```run
        SELECT d.name
        FROM departments d
        LEFT JOIN employees e ON e.department_id = d.id
        WHERE e.id IS NULL;
        ```

        **ON vs WHERE with outer joins.** A condition on the right table in
        `WHERE` throws away the NULL rows and silently turns your LEFT JOIN
        into an INNER JOIN. Put conditions about the right table in `ON`:

        ```run
        -- All departments, with their employees who earn over 150k (if any)
        SELECT d.name, e.first_name
        FROM departments d
        LEFT JOIN employees e ON e.department_id = d.id AND e.salary > 150000;
        ```
        """,
        """
        # Joining many tables

        Chain joins to follow relationships. Order → customer, order → items →
        products:

        ```run
        SELECT o.id AS order_id, c.name AS customer, p.name AS product,
               oi.quantity, oi.unit_price
        FROM orders o
        JOIN customers   c  ON c.id = o.customer_id
        JOIN order_items oi ON oi.order_id = o.id
        JOIN products    p  ON p.id = oi.product_id
        WHERE o.id IN (1, 2);
        ```

        **Fan-out:** joining a one-to-many relationship multiplies rows. The
        query above returns one row per *item*, not per order. If you then
        `SUM` an order-level value, you count it once per item. Always ask
        "what does one row of my result represent?" (its **grain**).

        Other syntax you'll meet:

        - `JOIN t USING (col)` when both columns have the same name.
        - `NATURAL JOIN` joins on all same-named columns — avoid; adding a
          column can silently change the join.
        - Old style: `FROM a, b WHERE a.x = b.x`. Works, but prefer explicit
          JOIN ... ON so a forgotten condition can't create a cross join.
        """,
        """
        # RIGHT, FULL and CROSS joins

        - `RIGHT JOIN` is a LEFT JOIN with the tables swapped. Most people
          just write LEFT JOIN and put the preserved table first.
        - `FULL OUTER JOIN` keeps unmatched rows from **both** sides.
          (SQLite 3.39+, PostgreSQL, SQL Server; not MySQL.)
        - `CROSS JOIN` returns every combination (rows × rows) — useful for
          generating grids, dangerous by accident.

        ```run
        SELECT e.first_name, d.name
        FROM employees e
        FULL OUTER JOIN departments d ON d.id = e.department_id
        WHERE e.id IS NULL OR d.id IS NULL;
        ```

        ```run
        SELECT s.size, c.color
        FROM (SELECT 'S' AS size UNION ALL SELECT 'M') s
        CROSS JOIN (SELECT 'red' AS color UNION ALL SELECT 'blue') c;
        ```
        """,
        """
        # Self joins

        A table can be joined to itself, using two aliases. `manager_id`
        points to another row of `employees`:

        ```run
        SELECT e.first_name AS employee, m.first_name AS manager
        FROM employees e
        LEFT JOIN employees m ON m.id = e.manager_id
        ORDER BY e.id
        LIMIT 6;
        ```

        LEFT JOIN keeps Grace, the CEO, who has no manager.

        Joins don't have to use `=`. A non-equi join matches on ranges, e.g.
        pairing each product with cheaper products in the same category:
        `JOIN products p2 ON p2.category = p1.category AND p2.price < p1.price`.
        """,
    ],
    exercises=[
        Exercise(
            prompt="List each employee's `first_name` and their department's `name`. "
                   "Employees without a department can be left out.",
            solution="SELECT e.first_name, d.name FROM employees e "
                     "JOIN departments d ON d.id = e.department_id;",
            hints=["JOIN departments d ON d.id = e.department_id"],
        ),
        Exercise(
            prompt="Same as before, but include every employee; show NULL as the department "
                   "name for anyone without one.",
            solution="SELECT e.first_name, d.name FROM employees e "
                     "LEFT JOIN departments d ON d.id = e.department_id;",
            hints=["LEFT JOIN keeps all rows of the left table."],
        ),
        Exercise(
            prompt="List the `name` of every department that has no employees.",
            solution="SELECT d.name FROM departments d "
                     "LEFT JOIN employees e ON e.department_id = d.id WHERE e.id IS NULL;",
            hints=["LEFT JOIN employees, then WHERE e.id IS NULL"],
        ),
        Exercise(
            prompt="List every employee's `first_name` next to their manager's `first_name`. "
                   "Include the CEO (manager shown as NULL).",
            solution="SELECT e.first_name, m.first_name FROM employees e "
                     "LEFT JOIN employees m ON m.id = e.manager_id;",
            hints=["Join employees to itself with two aliases.",
                   "LEFT JOIN employees m ON m.id = e.manager_id"],
        ),
        Exercise(
            prompt="List the order `id`, customer `name` and `order_date` of every order "
                   "placed by a customer in the USA.",
            solution="SELECT o.id, c.name, o.order_date FROM orders o "
                     "JOIN customers c ON c.id = o.customer_id WHERE c.country = 'USA';",
            hints=["Join orders to customers, filter on c.country."],
        ),
        Exercise(
            prompt="List the `name` of every product that has never been ordered.",
            solution="SELECT p.name FROM products p "
                     "LEFT JOIN order_items oi ON oi.product_id = p.id WHERE oi.order_id IS NULL;",
            hints=["Anti-join: LEFT JOIN order_items and keep the unmatched rows."],
        ),
        Exercise(
            prompt="Show each customer's `name` and total amount spent (sum of quantity × "
                   "unit_price) across all their non-cancelled orders, highest first. "
                   "Only customers who have spent something.",
            solution="SELECT c.name, SUM(oi.quantity * oi.unit_price) AS spent "
                     "FROM customers c JOIN orders o ON o.customer_id = c.id "
                     "JOIN order_items oi ON oi.order_id = o.id "
                     "WHERE o.status <> 'cancelled' GROUP BY c.id, c.name ORDER BY spent DESC;",
            ordered=True,
            hints=["customers → orders → order_items",
                   "Filter status in WHERE, GROUP BY the customer, SUM(quantity * unit_price)."],
        ),
        Exercise(
            prompt="List the order `id` and the sales rep's `first_name` for every order, "
                   "including orders without a rep.",
            solution="SELECT o.id, e.first_name FROM orders o "
                     "LEFT JOIN employees e ON e.id = o.employee_id;",
            hints=["orders.employee_id is the rep. Some are NULL."],
        ),
    ],
)

SUBQUERIES = Lesson(
    id="09-subqueries",
    title="Subqueries",
    summary="Scalar, IN, EXISTS, correlated and derived-table subqueries.",
    pages=[
        """
        # A query inside a query

        A subquery is a SELECT in parentheses used inside another statement.
        A **scalar subquery** returns one value and can go anywhere a value
        can:

        ```run
        SELECT name, price, (SELECT ROUND(AVG(price), 2) FROM products) AS avg_price
        FROM products
        WHERE price > (SELECT AVG(price) FROM products);
        ```

        (You can't write `WHERE price > AVG(price)`: aggregates aren't
        allowed in WHERE, which runs before grouping.)

        A subquery returning a column works with `IN`:

        ```run
        SELECT name FROM customers
        WHERE id IN (SELECT customer_id FROM orders WHERE status = 'pending');
        ```
        """,
        """
        # EXISTS and correlated subqueries

        A **correlated** subquery refers to the outer query's current row.
        `EXISTS` is true if the subquery returns at least one row:

        ```run
        SELECT c.name
        FROM customers c
        WHERE EXISTS (SELECT 1 FROM orders o
                      WHERE o.customer_id = c.id AND o.order_date >= '2024-01-01');
        ```

        Correlated subqueries can compute per-row comparisons, e.g. employees
        who earn more than their own department's average:

        ```run
        SELECT e.first_name, e.department_id, e.salary
        FROM employees e
        WHERE e.salary > (SELECT AVG(x.salary) FROM employees x
                          WHERE x.department_id = e.department_id);
        ```

        Conceptually it runs once per outer row; in practice the optimizer
        often rewrites it into a join.
        """,
        """
        # The NOT IN trap

        Who isn't anybody's manager? This looks right but returns nothing:

        ```run
        SELECT first_name FROM employees
        WHERE id NOT IN (SELECT manager_id FROM employees);
        ```

        The subquery contains a NULL (the CEO's manager_id).
        `x NOT IN (1, 2, NULL)` means `x <> 1 AND x <> 2 AND x <> NULL`, and
        `x <> NULL` is unknown, so the whole condition is never TRUE.

        Use `NOT EXISTS`, which has no such problem:

        ```run
        SELECT e.first_name FROM employees e
        WHERE NOT EXISTS (SELECT 1 FROM employees r WHERE r.manager_id = e.id);
        ```

        Rule of thumb: prefer `NOT EXISTS` over `NOT IN (subquery)`, or make
        sure the subquery filters out NULLs.
        """,
        """
        # Derived tables

        A subquery in `FROM` acts like a temporary table (it must be given an
        alias). Use it to aggregate in two steps — e.g. the average order
        value needs order totals first:

        ```run
        SELECT COUNT(*) AS orders, ROUND(AVG(total), 2) AS avg_order_value
        FROM (
            SELECT order_id, SUM(quantity * unit_price) AS total
            FROM order_items
            GROUP BY order_id
        ) AS order_totals;
        ```

        Deeply nested derived tables get hard to read. The next-but-one
        lesson shows CTEs (`WITH`), which express the same thing top to bottom.
        """,
    ],
    exercises=[
        Exercise(
            prompt="List `name` and `price` of products priced above the average product price.",
            solution="SELECT name, price FROM products WHERE price > (SELECT AVG(price) FROM products);",
            hints=["Compare with a scalar subquery: (SELECT AVG(price) FROM products)"],
        ),
        Exercise(
            prompt="List `first_name` and `salary` of the highest-paid employee(s). "
                   "Don't hard-code the number.",
            solution="SELECT first_name, salary FROM employees "
                     "WHERE salary = (SELECT MAX(salary) FROM employees);",
            hints=["WHERE salary = (SELECT MAX(salary) ...)"],
        ),
        Exercise(
            prompt="List the `name` of each customer who has at least one cancelled order. "
                   "Use IN or EXISTS (no JOIN).",
            solution="SELECT name FROM customers WHERE id IN "
                     "(SELECT customer_id FROM orders WHERE status = 'cancelled');",
            hints=["WHERE id IN (SELECT customer_id FROM orders WHERE ...)"],
        ),
        Exercise(
            prompt="List the `first_name` of employees who are nobody's manager.",
            solution="SELECT e.first_name FROM employees e WHERE NOT EXISTS "
                     "(SELECT 1 FROM employees r WHERE r.manager_id = e.id);",
            hints=["NOT IN fails here because manager_id contains NULL.",
                   "WHERE NOT EXISTS (SELECT 1 FROM employees r WHERE r.manager_id = e.id)"],
        ),
        Exercise(
            prompt="List `first_name` and `salary` of employees who earn more than the "
                   "average salary of their own department.",
            solution="SELECT e.first_name, e.salary FROM employees e WHERE e.salary > "
                     "(SELECT AVG(x.salary) FROM employees x WHERE x.department_id = e.department_id);",
            hints=["A correlated subquery: the inner query references e.department_id."],
        ),
        Exercise(
            prompt="What is the largest order total (sum of quantity × unit_price for one "
                   "order)? Return one number.",
            solution="SELECT MAX(total) FROM (SELECT order_id, SUM(quantity * unit_price) AS total "
                     "FROM order_items GROUP BY order_id) t;",
            hints=["First compute totals per order in a derived table, then take MAX.",
                   "SELECT MAX(total) FROM (SELECT ... GROUP BY order_id) t;"],
        ),
    ],
)

SET_OPS = Lesson(
    id="10-set-operations",
    title="Set operations: UNION, INTERSECT, EXCEPT",
    summary="Stacking and comparing result sets.",
    pages=[
        """
        # Combining result sets vertically

        Joins combine tables side by side. Set operations stack the results
        of two queries on top of each other:

        - `UNION` — rows from either query, duplicates removed.
        - `UNION ALL` — rows from either query, duplicates kept (faster:
          no de-duplication step). Use it unless you need de-duplication.
        - `INTERSECT` — rows present in both.
        - `EXCEPT` — rows in the first but not the second (Oracle: `MINUS`).

        ```run
        SELECT city FROM customers
        UNION
        SELECT location FROM departments
        ORDER BY 1;
        ```

        Rules: both queries must return the same number of columns with
        compatible types. Column names come from the first query. A single
        `ORDER BY` at the very end sorts the combined result.
        """,
        """
        # INTERSECT and EXCEPT

        Cities where Acme has both a customer and an office:

        ```run
        SELECT city FROM customers
        INTERSECT
        SELECT location FROM departments;
        ```

        Customers who signed up but never ordered:

        ```run
        SELECT id FROM customers
        EXCEPT
        SELECT customer_id FROM orders;
        ```

        Set operations compare whole rows and treat NULLs as equal to each
        other, unlike `=`. That makes `EXCEPT` a handy tool for diffing two
        tables: `(SELECT * FROM a EXCEPT SELECT * FROM b)` shows rows of a
        missing from b.
        """,
    ],
    exercises=[
        Exercise(
            prompt="Produce one list of every city that appears as a customer city or a "
                   "department location, without duplicates.",
            solution="SELECT city FROM customers UNION SELECT location FROM departments;",
            hints=["UNION removes duplicates."],
        ),
        Exercise(
            prompt="List the ids of products that have never been ordered, using EXCEPT.",
            solution="SELECT id FROM products EXCEPT SELECT product_id FROM order_items;",
            hints=["All product ids EXCEPT the ones in order_items."],
        ),
        Exercise(
            prompt="Build a contact list with columns (name, email, kind): employees with "
                   "their full name ('First Last') and kind 'employee', plus customers with "
                   "their name and kind 'customer'. Keep every row.",
            solution="SELECT first_name || ' ' || last_name, email, 'employee' FROM employees "
                     "UNION ALL SELECT name, email, 'customer' FROM customers;",
            hints=["A constant like 'employee' can be a column.",
                   "UNION ALL keeps every row."],
        ),
        Exercise(
            prompt="List the ids of customers who have both a delivered order and a "
                   "pending or shipped order.",
            solution="SELECT customer_id FROM orders WHERE status = 'delivered' INTERSECT "
                     "SELECT customer_id FROM orders WHERE status IN ('pending', 'shipped');",
            hints=["INTERSECT two customer_id lists."],
        ),
        Quiz(
            question="Why is `UNION ALL` usually faster than `UNION`?",
            options=["It uses indexes", "It skips removing duplicates",
                     "It runs the queries in parallel", "It isn't; they're identical"],
            answer=1,
            explanation="UNION must sort or hash the combined rows to remove duplicates.",
        ),
    ],
)

CTES = Lesson(
    id="11-ctes",
    title="Common table expressions (WITH) and recursion",
    summary="Readable multi-step queries; recursive CTEs for series and hierarchies.",
    pages=[
        """
        # WITH: naming a subquery

        A CTE gives a subquery a name, placed before the main query. Complex
        queries become a readable sequence of steps:

        ```run
        WITH order_totals AS (
            SELECT order_id, SUM(quantity * unit_price) AS total
            FROM order_items
            GROUP BY order_id
        ),
        big_orders AS (
            SELECT order_id, total FROM order_totals WHERE total > 10000
        )
        SELECT o.id, c.name, ROUND(b.total, 2) AS total
        FROM big_orders b
        JOIN orders o ON o.id = b.order_id
        JOIN customers c ON c.id = o.customer_id
        ORDER BY total DESC;
        ```

        Each CTE can use the ones defined before it, and the main query can
        reference a CTE several times. CTEs exist only for that one statement.
        """,
        """
        # Recursive CTEs

        `WITH RECURSIVE` lets a CTE refer to itself. It has two parts joined
        by `UNION ALL`:

        1. an **anchor** query that produces the starting rows;
        2. a **recursive** query that produces new rows from the previous
           iteration's rows. It repeats until it produces no rows.

        Counting to 5:

        ```run
        WITH RECURSIVE n(x) AS (
            SELECT 1                           -- anchor
            UNION ALL
            SELECT x + 1 FROM n WHERE x < 5    -- recursive step + stop condition
        )
        SELECT x FROM n;
        ```

        **Always include a stop condition.** Without `WHERE x < 5` it runs
        forever (this tutor cancels queries after 5 seconds).
        """,
        """
        # Walking a hierarchy

        The classic use: trees stored as parent pointers, like `manager_id`.
        Start at the CEO and repeatedly add the direct reports of the people
        found so far:

        ```run
        WITH RECURSIVE org(id, name, level, path) AS (
            SELECT id, first_name, 1, first_name
            FROM employees WHERE manager_id IS NULL
            UNION ALL
            SELECT e.id, e.first_name, org.level + 1, org.path || ' > ' || e.first_name
            FROM employees e
            JOIN org ON e.manager_id = org.id
        )
        SELECT level, path FROM org ORDER BY path;
        ```

        Recursive CTEs also generate calendars (every day in a range, so you
        can LEFT JOIN real data and show zero for missing days), traverse
        graphs (with a depth limit to avoid cycles), and explode bills of
        materials.
        """,
    ],
    exercises=[
        Exercise(
            prompt="Using a CTE named `order_totals` (order_id, total), list the `order_id` "
                   "and `total` of orders whose total exceeds 5000.",
            solution="WITH order_totals AS (SELECT order_id, SUM(quantity * unit_price) AS total "
                     "FROM order_items GROUP BY order_id) "
                     "SELECT order_id, total FROM order_totals WHERE total > 5000;",
            hints=["WITH order_totals AS (SELECT ... GROUP BY order_id) SELECT ... FROM order_totals WHERE ..."],
        ),
        Exercise(
            prompt="Use a recursive CTE to return the numbers 1 through 10, in order.",
            solution="WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM n WHERE x < 10) "
                     "SELECT x FROM n ORDER BY x;",
            ordered=True,
            hints=["Anchor: SELECT 1. Step: SELECT x + 1 FROM n WHERE x < 10."],
        ),
        Exercise(
            prompt="List the `first_name` of everyone who reports to Alan Turing (id 2), "
                   "directly or indirectly. Don't include Alan.",
            solution="WITH RECURSIVE reports(id, first_name) AS ("
                     "SELECT id, first_name FROM employees WHERE manager_id = 2 "
                     "UNION ALL SELECT e.id, e.first_name FROM employees e "
                     "JOIN reports r ON e.manager_id = r.id) SELECT first_name FROM reports;",
            hints=["Anchor: Alan's direct reports (manager_id = 2).",
                   "Recursive step: employees whose manager_id is in the CTE."],
        ),
        Exercise(
            prompt="Show every employee's `first_name` and their `level` in the org chart "
                   "(the CEO is level 1, the CEO's reports level 2, and so on).",
            solution="WITH RECURSIVE org(id, first_name, level) AS ("
                     "SELECT id, first_name, 1 FROM employees WHERE manager_id IS NULL "
                     "UNION ALL SELECT e.id, e.first_name, org.level + 1 FROM employees e "
                     "JOIN org ON e.manager_id = org.id) SELECT first_name, level FROM org;",
            hints=["Carry a level column: 1 in the anchor, org.level + 1 in the recursive step."],
        ),
        Exercise(
            prompt="For each month of 2023 show the month as 'YYYY-MM' and the number of "
                   "orders placed in it — including months with 0 orders — in month order.",
            solution="WITH RECURSIVE months(m) AS (SELECT '2023-01-01' UNION ALL "
                     "SELECT date(m, '+1 month') FROM months WHERE m < '2023-12-01') "
                     "SELECT strftime('%Y-%m', m), COUNT(o.id) FROM months "
                     "LEFT JOIN orders o ON strftime('%Y-%m', o.order_date) = strftime('%Y-%m', m) "
                     "GROUP BY m ORDER BY m;",
            ordered=True,
            hints=["Generate the 12 months with a recursive CTE, then LEFT JOIN orders.",
                   "COUNT(o.id) counts 0 for months with no match; COUNT(*) would count 1."],
        ),
    ],
)

WINDOWS = Lesson(
    id="12-window-functions",
    title="Window functions",
    summary="OVER, PARTITION BY, ranking, running totals, LAG/LEAD, frames.",
    pages=[
        """
        # Aggregates without collapsing

        GROUP BY collapses each group into one row. A **window function**
        computes over a set of related rows but keeps every row:

        ```run
        SELECT first_name, department_id, salary,
               AVG(salary) OVER (PARTITION BY department_id) AS dept_avg,
               salary - AVG(salary) OVER (PARTITION BY department_id) AS diff
        FROM employees
        WHERE department_id IN (1, 2);
        ```

        - `OVER (...)` makes a function a window function.
        - `PARTITION BY` splits rows into independent windows (like GROUP BY,
          without collapsing). Omit it and the window is the whole result.
        - `ORDER BY` inside OVER orders rows within each window.

        Window functions run after WHERE/GROUP BY/HAVING (step 5 in the
        evaluation order), so you **cannot filter on them in WHERE**. Wrap
        the query in a CTE or subquery and filter outside.
        """,
        """
        # Ranking

        ```run
        SELECT first_name, salary,
               ROW_NUMBER() OVER (ORDER BY salary DESC) AS row_num,
               RANK()       OVER (ORDER BY salary DESC) AS rnk,
               DENSE_RANK() OVER (ORDER BY salary DESC) AS dense
        FROM employees
        WHERE department_id = 2;
        ```

        Dwight and Jim tie at 87000:

        - `ROW_NUMBER` numbers rows uniquely (ties broken arbitrarily —
          add a tiebreaker column to make it deterministic).
        - `RANK` gives ties the same rank and leaves gaps (1, 2, 3, 3, 5).
        - `DENSE_RANK` gives ties the same rank without gaps (1, 2, 3, 3, 4).
        - `NTILE(n)` splits rows into n roughly equal buckets (quartiles etc).

        **Top-N per group** — one of the most-asked SQL interview questions:

        ```run
        WITH ranked AS (
            SELECT category, name, price,
                   ROW_NUMBER() OVER (PARTITION BY category ORDER BY price DESC) AS rn
            FROM products
        )
        SELECT category, name, price FROM ranked WHERE rn = 1;
        ```
        """,
        """
        # Running totals and moving averages

        With `ORDER BY` inside OVER, aggregate functions become cumulative:

        ```run
        SELECT id, order_date,
               COUNT(*) OVER (ORDER BY order_date) AS orders_so_far,
               COUNT(*) OVER (PARTITION BY strftime('%Y', order_date)
                              ORDER BY order_date) AS orders_this_year
        FROM orders
        WHERE order_date BETWEEN '2023-10-01' AND '2024-02-28';
        ```

        The **frame** clause controls exactly which rows are included:

        ```sql
        AVG(x) OVER (ORDER BY d ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)  -- 3-row moving avg
        SUM(x) OVER (ORDER BY d ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
        ```

        Gotcha: with ORDER BY and no frame, the default frame is
        `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`, which includes
        all rows **tied** with the current row. If the ORDER BY key has
        duplicates, a "running total" jumps by several rows at once. Use
        `ROWS` (or a unique ORDER BY) when you want row-by-row behaviour.
        """,
        """
        # LAG, LEAD, FIRST_VALUE

        `LAG(x)` reads x from the previous row in the window; `LEAD(x)` from
        the next row. Perfect for period-over-period changes:

        ```run
        SELECT id, order_date,
               LAG(order_date) OVER (ORDER BY order_date) AS previous,
               julianday(order_date)
                 - julianday(LAG(order_date) OVER (ORDER BY order_date)) AS days_gap
        FROM orders LIMIT 5;
        ```

        `LAG(x, n, default)` looks n rows back and uses default instead of NULL.
        `FIRST_VALUE(x)` / `LAST_VALUE(x)` / `NTH_VALUE(x, n)` read values
        from the window frame (LAST_VALUE usually needs the frame widened to
        `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING`).

        Repeating the same window? Name it:

        ```sql
        SELECT id, ROW_NUMBER() OVER w, LAG(id) OVER w
        FROM orders WINDOW w AS (PARTITION BY customer_id ORDER BY order_date);
        ```
        """,
    ],
    exercises=[
        Exercise(
            prompt="Show each employee's `first_name`, `department_id`, `salary`, and the "
                   "average salary of their department (as a 4th column).",
            solution="SELECT first_name, department_id, salary, "
                     "AVG(salary) OVER (PARTITION BY department_id) FROM employees;",
            hints=["AVG(salary) OVER (PARTITION BY department_id)"],
        ),
        Exercise(
            prompt="Show `first_name`, `salary` and a salary rank (1 = highest) using RANK, "
                   "so tied salaries share a rank.",
            solution="SELECT first_name, salary, RANK() OVER (ORDER BY salary DESC) FROM employees;",
            hints=["RANK() OVER (ORDER BY salary DESC)"],
        ),
        Exercise(
            prompt="Show each order's `id`, `order_date` and the running count of orders "
                   "up to and including that date.",
            solution="SELECT id, order_date, COUNT(*) OVER (ORDER BY order_date) FROM orders;",
            hints=["COUNT(*) OVER (ORDER BY order_date)"],
        ),
        Exercise(
            prompt="For each department (ignore employees with no department), show the "
                   "`department_id`, `first_name` and `salary` of its highest-paid employee.",
            solution="WITH r AS (SELECT department_id, first_name, salary, ROW_NUMBER() OVER "
                     "(PARTITION BY department_id ORDER BY salary DESC) AS rn FROM employees "
                     "WHERE department_id IS NOT NULL) "
                     "SELECT department_id, first_name, salary FROM r WHERE rn = 1;",
            hints=["Rank within each department with ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...).",
                   "You can't filter a window function in WHERE; use a CTE and filter rn = 1 outside."],
        ),
        Exercise(
            prompt="Show each order's `id`, `order_date` and the number of days since the "
                   "previous order (NULL for the first order).",
            solution="SELECT id, order_date, julianday(order_date) - "
                     "julianday(LAG(order_date) OVER (ORDER BY order_date)) FROM orders;",
            hints=["LAG(order_date) OVER (ORDER BY order_date) gives the previous date.",
                   "Subtract julianday() values."],
        ),
        Exercise(
            prompt="Number each customer's orders chronologically: show `customer_id`, "
                   "order `id`, and 1 for their first order, 2 for their second, etc.",
            solution="SELECT customer_id, id, ROW_NUMBER() OVER "
                     "(PARTITION BY customer_id ORDER BY order_date) FROM orders;",
            hints=["ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date)"],
        ),
    ],
)

LESSONS = [AGGREGATION, JOINS, SUBQUERIES, SET_OPS, CTES, WINDOWS]
