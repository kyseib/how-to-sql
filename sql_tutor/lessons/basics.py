from ..model import Exercise, Lesson, Quiz

INTRO = Lesson(
    id="01-intro",
    title="What SQL is & your first SELECT",
    summary="Relational databases, tables, and reading data with SELECT.",
    pages=[
        """
        # What is SQL?

        SQL (Structured Query Language, pronounced "S-Q-L" or "sequel") is the
        language used to talk to **relational databases**: PostgreSQL, MySQL,
        SQLite, SQL Server, Oracle, Snowflake, BigQuery and many more. It was
        created at IBM in the 1970s and is an ISO standard, which is why the
        same core syntax works almost everywhere.

        A relational database stores data in **tables**. A table is like a
        spreadsheet with strict rules:

        - Each **column** has a name and a data type (integer, text, date...).
        - Each **row** is one record: one employee, one order, one product.
        - A **primary key** column (usually `id`) uniquely identifies each row.
        - A **foreign key** column holds the primary key of a row in another
          table, which is how tables relate to each other.

        SQL is **declarative**: you describe *what* result you want, and the
        database's query planner decides *how* to compute it (which indexes to
        use, in what order to read tables). This is very different from writing
        a loop in Python or JavaScript.
        """,
        """
        # The parts of the language

        SQL statements fall into a few families. You will learn all of them:

        - **DQL** (query): `SELECT` — read data. This is 80% of daily SQL.
        - **DML** (manipulation): `INSERT`, `UPDATE`, `DELETE` — change rows.
        - **DDL** (definition): `CREATE`, `ALTER`, `DROP` — change structure.
        - **TCL** (transactions): `BEGIN`, `COMMIT`, `ROLLBACK`.
        - **DCL** (control): `GRANT`, `REVOKE` — permissions.

        This course runs on **SQLite**, a real database engine embedded in the
        program, so every example is live. Almost everything you learn applies
        to other databases; where dialects differ, the lesson says so, and
        lesson 20 summarises the differences.
        """,
        """
        # The sample database

        Every lesson uses the database of a small company, Acme:

            departments   id, name, location
            employees     id, first_name, last_name, email, department_id,
                          manager_id, title, salary, hire_date
            customers     id, name, email, city, country, signup_date
            products      id, name, category, price, stock
            orders        id, customer_id, employee_id, order_date, status
            order_items   order_id, product_id, quantity, unit_price

        Relationships: `employees.department_id` → `departments.id`,
        `employees.manager_id` → `employees.id`, `orders.customer_id` →
        `customers.id`, `orders.employee_id` → `employees.id` (the sales rep),
        and `order_items` links orders to products.

        The simplest query reads a whole table. `*` means "all columns":

        ```run
        SELECT * FROM departments;
        ```
        """,
        """
        # Choosing columns

        List the columns you want, separated by commas. They come back in the
        order you list them:

        ```run
        SELECT name, price FROM products;
        ```

        A few ground rules:

        - Keywords are case-insensitive: `select` = `SELECT`. Writing keywords
          in UPPER CASE is a common convention that makes queries easier to read.
        - Whitespace and line breaks don't matter. Long queries are usually
          written with one clause per line.
        - A statement ends with a semicolon `;`.
        - `-- text` is a comment to the end of the line; `/* text */` can span
          lines.
        - Text values go in **single quotes**: `'Sales'`. Double quotes are for
          identifiers (table/column names), e.g. `"order"`.

        `SELECT` doesn't even need a table — it can evaluate expressions:

        ```run
        SELECT 2 + 3 AS answer, 'hello' || ' world' AS greeting;  -- || joins text
        ```
        """,
        """
        # How exercises work

        After the reading pages come exercises. Type your SQL at the `sql>`
        prompt. It can span several lines; it is submitted when a line ends
        with `;` (or when you press Enter on an empty line).

        Your query runs on a fresh copy of the database and its output is
        compared with the reference solution's output. Column names don't
        matter unless the task asks for specific names; row order doesn't
        matter unless the task asks for a specific order.

        Commands you can type instead of SQL:

            \\hint       show the next hint
            \\expected   show the expected output
            \\solution   reveal the reference solution
            \\schema     list tables     (\\schema employees for one table)
            \\skip       move to the next exercise
            \\back       return to the lesson menu
            \\help       show all commands

        Wrong answers cost nothing. Run exploratory queries freely.
        """,
    ],
    exercises=[
        Exercise(
            prompt="Show every column of every row in the `products` table.",
            solution="SELECT * FROM products;",
            hints=["`*` selects all columns.", "SELECT * FROM table_name;"],
        ),
        Exercise(
            prompt="List the `first_name`, `last_name` and `title` of every employee "
                   "(in that column order).",
            solution="SELECT first_name, last_name, title FROM employees;",
            hints=["Separate column names with commas.",
                   "SELECT col1, col2, col3 FROM employees;"],
        ),
        Exercise(
            prompt="Show the `name` and `city` of every customer.",
            solution="SELECT name, city FROM customers;",
            hints=["The table is called customers."],
        ),
        Quiz(
            question="`CREATE TABLE` belongs to which family of SQL statements?",
            options=["DQL (query)", "DML (manipulation)", "DDL (definition)", "TCL (transactions)"],
            answer=2,
            explanation="CREATE, ALTER and DROP define structure: Data Definition Language.",
        ),
        Quiz(
            question="How do you write the text value Sales in SQL?",
            options=['"Sales"', "'Sales'", "`Sales`", "Sales"],
            answer=1,
            explanation="Single quotes delimit string literals in standard SQL. Double "
                        "quotes delimit identifiers such as column names. (MySQL accepts "
                        "both by default, which causes confusion when you switch databases.)",
        ),
    ],
)

FILTERING = Lesson(
    id="02-where",
    title="Filtering rows with WHERE",
    summary="Comparisons, AND/OR/NOT, IN, BETWEEN, LIKE.",
    pages=[
        """
        # WHERE

        `WHERE` keeps only the rows for which a condition is true:

        ```run
        SELECT first_name, last_name, salary
        FROM employees
        WHERE salary > 150000;
        ```

        Comparison operators:

            =   equal             <>  not equal (!= also works)
            <   less than         <=  less than or equal
            >   greater than      >=  greater than or equal

        They work on numbers, text (alphabetical order) and ISO dates such as
        `'2023-06-01'`, which sort correctly as text.

        ```run
        SELECT name, category FROM products WHERE category = 'Audio';
        ```
        """,
        """
        # Combining conditions: AND, OR, NOT

        ```run
        SELECT name, price, stock
        FROM products
        WHERE category = 'Accessories' AND stock > 100;
        ```

        **Precedence trap:** `AND` binds tighter than `OR`, just like `*` binds
        tighter than `+`. This query does NOT mean what it looks like:

        ```sql
        -- Intended: cheap products in Audio or Software
        SELECT name FROM products
        WHERE category = 'Audio' OR category = 'Software' AND price < 100;
        -- Actually: Audio (any price)  OR  (Software AND price < 100)
        ```

        Use parentheses whenever you mix AND and OR:

        ```run
        SELECT name, category, price FROM products
        WHERE (category = 'Audio' OR category = 'Software') AND price < 100;
        ```

        `NOT` negates a condition: `WHERE NOT (price > 100)`.
        """,
        """
        # IN, BETWEEN, LIKE

        `IN` tests membership in a list — shorter than chaining ORs:

        ```run
        SELECT name, country FROM customers WHERE country IN ('UK', 'France');
        ```

        `BETWEEN a AND b` is **inclusive** on both ends
        (`x >= a AND x <= b`):

        ```run
        SELECT name, price FROM products WHERE price BETWEEN 49 AND 89;
        ```

        `LIKE` matches text patterns: `%` matches any sequence of characters
        (including none), `_` matches exactly one character.

        ```run
        SELECT name FROM products WHERE name LIKE 'Laptop%';
        ```

        Dialect notes: in SQLite and MySQL, LIKE is case-insensitive for
        ASCII letters. In PostgreSQL it is case-sensitive; use `ILIKE` there
        for case-insensitive matching. To match a literal `%` or `_`, use
        `LIKE '50\\%%' ESCAPE '\\'`.

        All of these can be negated: `NOT IN`, `NOT BETWEEN`, `NOT LIKE`.
        """,
    ],
    exercises=[
        Exercise(
            prompt="Show all columns for products in the 'Accessories' category.",
            solution="SELECT * FROM products WHERE category = 'Accessories';",
            hints=["WHERE category = '...'", "Text values need single quotes."],
        ),
        Exercise(
            prompt="List `first_name`, `last_name`, `salary` of employees earning "
                   "more than 150000.",
            solution="SELECT first_name, last_name, salary FROM employees WHERE salary > 150000;",
            hints=["Use the > operator. Numbers need no quotes."],
        ),
        Exercise(
            prompt="List `name` and `price` of products priced from 100 to 500 inclusive.",
            solution="SELECT name, price FROM products WHERE price BETWEEN 100 AND 500;",
            hints=["BETWEEN is inclusive.", "WHERE price BETWEEN 100 AND 500"],
        ),
        Exercise(
            prompt="List `name` and `country` of customers located in the UK, Germany "
                   "or France. Use IN.",
            solution="SELECT name, country FROM customers WHERE country IN ('UK', 'Germany', 'France');",
            hints=["WHERE country IN ('A', 'B', 'C')"],
        ),
        Exercise(
            prompt="List `first_name`, `last_name` of employees whose last name starts with 'H'.",
            solution="SELECT first_name, last_name FROM employees WHERE last_name LIKE 'H%';",
            hints=["LIKE with the % wildcard.", "'H%' means: H followed by anything."],
        ),
        Exercise(
            prompt="List the `id` and `order_date` of orders with status 'delivered' "
                   "placed on or after 2024-01-01.",
            solution="SELECT id, order_date FROM orders "
                     "WHERE status = 'delivered' AND order_date >= '2024-01-01';",
            hints=["Two conditions joined with AND.",
                   "ISO dates compare correctly as text: order_date >= '2024-01-01'"],
        ),
        Exercise(
            prompt="List the `name`, `category` and `price` of products that are in "
                   "'Computers' or 'Furniture' AND cost less than 1000.",
            solution="SELECT name, category, price FROM products "
                     "WHERE (category = 'Computers' OR category = 'Furniture') AND price < 1000;",
            hints=["Mixing AND with OR needs parentheses.",
                   "WHERE (a OR b) AND c — or use category IN (...)"],
        ),
    ],
)

SORTING = Lesson(
    id="03-order",
    title="Sorting, limiting, DISTINCT and aliases",
    summary="ORDER BY, LIMIT/OFFSET, DISTINCT, AS.",
    pages=[
        """
        # ORDER BY

        **Without ORDER BY, row order is undefined.** It may look stable,
        but it can change whenever data, indexes or the database version
        change. If order matters, say so.

        ```run
        SELECT name, price FROM products ORDER BY price DESC;
        ```

        `ASC` (ascending) is the default; `DESC` reverses. Sort by several
        keys by listing them: the second breaks ties in the first.

        ```run
        SELECT title, first_name, salary
        FROM employees
        ORDER BY title, salary DESC;
        ```

        NULLs: SQLite, MySQL and SQL Server put NULLs first when ascending;
        PostgreSQL and Oracle put them last. Be explicit with
        `ORDER BY x NULLS LAST` (supported by SQLite, PostgreSQL, Oracle).

        You can also sort by expressions (`ORDER BY price * stock`), by a
        column alias, or by column position (`ORDER BY 2`). Positions are
        fragile — avoid them outside quick exploration.
        """,
        """
        # LIMIT and OFFSET

        `LIMIT n` returns at most n rows. Combined with ORDER BY, it answers
        "top N" questions:

        ```run
        SELECT first_name, salary FROM employees ORDER BY salary DESC LIMIT 3;
        ```

        `OFFSET n` skips rows first — used for pagination:

        ```run
        SELECT id, name FROM products ORDER BY id LIMIT 5 OFFSET 5;  -- page 2
        ```

        Large OFFSETs are slow (the database still reads and discards the
        skipped rows). For deep pagination, use **keyset pagination**:
        remember the last id you showed and ask for
        `WHERE id > :last_id ORDER BY id LIMIT 5`.

        Dialects: SQL Server uses `SELECT TOP 3 ...` or
        `OFFSET 5 ROWS FETCH NEXT 5 ROWS ONLY`; Oracle and the SQL standard
        use `FETCH FIRST 3 ROWS ONLY`.
        """,
        """
        # DISTINCT

        `DISTINCT` removes duplicate rows from the result:

        ```run
        SELECT DISTINCT country FROM customers ORDER BY country;
        ```

        With several columns, DISTINCT applies to the *combination*:

        ```run
        SELECT DISTINCT department_id, title FROM employees WHERE department_id = 2;
        ```

        Warning: reaching for DISTINCT to "fix" duplicate rows after a join
        usually hides a mistake in the join. Understand where duplicates come
        from before removing them.
        """,
        """
        # Aliases with AS

        `AS` renames a column or expression in the output:

        ```run
        SELECT name AS product, price AS list_price, price * 0.8 AS sale_price
        FROM products
        WHERE category = 'Audio';
        ```

        Tables can be aliased too — essential once you join tables:
        `FROM employees AS e` (the AS is optional for tables: `FROM employees e`).

        Aliases containing spaces or reserved words need double quotes:
        `SELECT price AS "Unit Price"`.
        """,
    ],
    exercises=[
        Exercise(
            prompt="List product `name` and `price`, most expensive first.",
            solution="SELECT name, price FROM products ORDER BY price DESC;",
            ordered=True,
            hints=["ORDER BY ... DESC"],
        ),
        Exercise(
            prompt="Show the `id` and `order_date` of the 3 most recent orders, newest first.",
            solution="SELECT id, order_date FROM orders ORDER BY order_date DESC LIMIT 3;",
            ordered=True,
            hints=["Sort by order_date descending, then LIMIT."],
        ),
        Exercise(
            prompt="List each distinct product `category` once, sorted alphabetically.",
            solution="SELECT DISTINCT category FROM products ORDER BY category;",
            ordered=True,
            hints=["SELECT DISTINCT ..."],
        ),
        Exercise(
            prompt="List employees' `first_name`, `department_id`, `salary`, sorted by "
                   "department_id ascending, then salary highest first; break any "
                   "remaining ties by first_name.",
            solution="SELECT first_name, department_id, salary FROM employees "
                     "ORDER BY department_id, salary DESC, first_name;",
            ordered=True,
            hints=["ORDER BY takes a comma-separated list; each key can have its own direction."],
        ),
        Exercise(
            prompt="Show `name` and `price` of the 4th, 5th and 6th most expensive products "
                   "(most expensive first).",
            solution="SELECT name, price FROM products ORDER BY price DESC LIMIT 3 OFFSET 3;",
            ordered=True,
            hints=["Skip the first three rows with OFFSET.", "LIMIT 3 OFFSET 3"],
        ),
        Exercise(
            prompt="For products in the 'Audio' category, show two columns named exactly "
                   "`product` (the name) and `sale_price` (price reduced by 10%).",
            solution="SELECT name AS product, price * 0.9 AS sale_price FROM products "
                     "WHERE category = 'Audio';",
            check_names=True,
            hints=["price * 0.9", "Rename with AS: name AS product"],
        ),
    ],
)

NULLS = Lesson(
    id="04-null",
    title="NULL and three-valued logic",
    summary="What NULL means, IS NULL, COALESCE, NULLIF and the traps.",
    pages=[
        """
        # NULL means "unknown"

        `NULL` marks a missing or unknown value. It is not zero, not an
        empty string, not false. Two employees have no email on file:

        ```run
        SELECT first_name, email FROM employees WHERE id IN (5, 6, 12);
        ```

        Because NULL is unknown, **any comparison with NULL is itself
        unknown (NULL)** — even `NULL = NULL`. Is an unknown value equal to
        another unknown value? Unknown.

        ```run
        SELECT NULL = NULL AS a, NULL <> 1 AS b, 1 + NULL AS c, 'x' || NULL AS d;
        ```

        `WHERE` keeps rows only when the condition is TRUE, so rows where it is
        NULL disappear. `WHERE email = NULL` therefore returns nothing, ever.
        Use `IS NULL` / `IS NOT NULL`:

        ```run
        SELECT first_name, last_name FROM employees WHERE email IS NULL;
        ```
        """,
        """
        # Three-valued logic

        SQL logic has three values: TRUE, FALSE and UNKNOWN (NULL).

            AND      | TRUE     FALSE   NULL        OR       | TRUE   FALSE   NULL
            ---------+-------------------------     ---------+----------------------
            TRUE     | TRUE     FALSE   NULL        TRUE     | TRUE   TRUE    TRUE
            FALSE    | FALSE    FALSE   FALSE       FALSE    | TRUE   FALSE   NULL
            NULL     | NULL     FALSE   NULL        NULL     | TRUE   NULL    NULL

            NOT NULL is NULL.

        The consequence that bites everyone: a negative filter silently drops
        NULL rows. Sam has no department (`department_id` is NULL):

        ```run
        SELECT first_name, department_id FROM employees WHERE department_id <> 1;
        ```

        Sam is missing, because `NULL <> 1` is unknown. To include Sam:
        `WHERE department_id <> 1 OR department_id IS NULL`, or SQLite's
        NULL-safe operator `WHERE department_id IS NOT 1`. The standard spelling
        is `IS DISTINCT FROM` (PostgreSQL, SQLite 3.39+); MySQL uses `<=>`.
        """,
        """
        # Replacing NULLs: COALESCE and NULLIF

        `COALESCE(a, b, c, ...)` returns the first non-NULL argument:

        ```run
        SELECT name, COALESCE(email, '(no email)') AS contact FROM customers;
        ```

        `NULLIF(a, b)` returns NULL if a = b, otherwise a. Its classic use is
        avoiding division by zero:

        ```run
        SELECT name, stock, 1000 / NULLIF(stock, 0) AS ratio
        FROM products WHERE category = 'Furniture';
        ```

        Other places NULL matters (covered in later lessons):

        - Aggregates like `SUM` and `AVG` ignore NULLs; `COUNT(col)` counts
          only non-NULL values.
        - `NOT IN (subquery)` returns nothing if the subquery yields a NULL.
        - Outer joins produce NULLs for rows with no match.
        - UNIQUE constraints allow multiple NULLs in most databases.
        """,
    ],
    exercises=[
        Exercise(
            prompt="List `first_name` and `last_name` of employees who have no email.",
            solution="SELECT first_name, last_name FROM employees WHERE email IS NULL;",
            hints=["= NULL never matches. Use IS NULL."],
        ),
        Exercise(
            prompt="List the `id` and `order_date` of orders that have no sales rep "
                   "(`employee_id` is missing).",
            solution="SELECT id, order_date FROM orders WHERE employee_id IS NULL;",
            hints=["WHERE employee_id IS NULL"],
        ),
        Exercise(
            prompt="Show every customer's `name` and their email, but show the text "
                   "'no email' where email is missing.",
            solution="SELECT name, COALESCE(email, 'no email') FROM customers;",
            hints=["COALESCE returns its first non-NULL argument.",
                   "COALESCE(email, 'no email')"],
        ),
        Exercise(
            prompt="List the `first_name` of every employee NOT in department 1, "
                   "including employees who have no department.",
            solution="SELECT first_name FROM employees "
                     "WHERE department_id <> 1 OR department_id IS NULL;",
            hints=["department_id <> 1 alone drops the NULL row.",
                   "Add OR department_id IS NULL (or use IS NOT 1 in SQLite)."],
        ),
        Quiz(
            question="What does `SELECT NULL = NULL;` return?",
            options=["1 (true)", "0 (false)", "NULL", "An error"],
            answer=2,
            explanation="Comparing unknown to unknown gives unknown: NULL. Use IS NULL.",
        ),
        Quiz(
            question="A table has 10 rows; 3 have `bonus` NULL, 2 have bonus = 0. "
                     "How many rows does `WHERE bonus <> 0` return?",
            options=["8", "5", "7", "10"],
            answer=1,
            explanation="The 2 zero rows fail the test and the 3 NULL rows evaluate to "
                        "unknown, so only 10 - 2 - 3 = 5 rows are returned.",
        ),
    ],
)

EXPRESSIONS = Lesson(
    id="05-expressions",
    title="Expressions, functions and CASE",
    summary="Arithmetic, string and numeric functions, CAST, CASE.",
    pages=[
        """
        # Arithmetic

        `+ - * /` and `%` (remainder) work as expected, with one big trap:
        **dividing two integers gives an integer** in SQLite, PostgreSQL and
        SQL Server (MySQL returns a decimal).

        ```run
        SELECT 7 / 2 AS int_div, 7 / 2.0 AS real_div, 7 % 2 AS remainder,
               CAST(7 AS REAL) / 2 AS cast_div;
        ```

        So `salary / 12` truncates. Multiply by `1.0` or `CAST` one side to a
        real/decimal type when you want fractions.

        `ROUND(x, n)` rounds to n decimal places; `ABS(x)` gives the absolute
        value. Expressions can use any column:

        ```run
        SELECT name, price, stock, price * stock AS inventory_value
        FROM products ORDER BY inventory_value DESC LIMIT 5;
        ```
        """,
        """
        # String functions

        ```run
        SELECT first_name || ' ' || last_name AS full_name,
               UPPER(last_name)               AS upper,
               LENGTH(first_name)             AS len,
               SUBSTR(first_name, 1, 3)       AS first3,
               REPLACE(email, '@acme.com', '') AS handle
        FROM employees LIMIT 4;
        ```

        Common functions (SQLite names; most databases share them):

            ||  or CONCAT(a, b)    concatenate       (MySQL: CONCAT only)
            UPPER / LOWER          change case
            LENGTH(s)              number of characters   (SQL Server: LEN)
            SUBSTR(s, start, len)  substring, 1-based     (also SUBSTRING)
            INSTR(s, t)            position of t in s, 0 if absent
                                   (PostgreSQL: STRPOS / POSITION(t IN s))
            REPLACE(s, from, to)   replace all occurrences
            TRIM / LTRIM / RTRIM   strip whitespace (or given characters)

        Note that `'x' || NULL` is NULL. Wrap nullable columns in COALESCE
        when concatenating.
        """,
        """
        # Types and CAST

        `CAST(expr AS type)` converts between types:

        ```run
        SELECT CAST('42' AS INTEGER) + 1 AS n, CAST(3.99 AS INTEGER) AS truncated,
               CAST(2024 AS TEXT) || '!' AS txt, typeof(3.99) AS t;
        ```

        SQLite is loosely typed ("type affinity"): a column declared INTEGER
        will happily store text. Most other databases are strict and will
        reject `'abc'` in an integer column. Lesson 14 covers types in depth.
        """,
        """
        # CASE: if/else inside a query

        The **searched CASE** evaluates conditions top to bottom and returns
        the first match; `ELSE` is the fallback (NULL if omitted):

        ```run
        SELECT name, price,
               CASE
                   WHEN price >= 1000 THEN 'premium'
                   WHEN price >= 100  THEN 'mid-range'
                   ELSE 'budget'
               END AS tier
        FROM products;
        ```

        The **simple CASE** compares one expression against values:

        ```sql
        CASE status WHEN 'delivered' THEN 'done'
                    WHEN 'cancelled' THEN 'void'
                    ELSE 'open' END
        ```

        CASE works anywhere an expression does: SELECT, WHERE, ORDER BY,
        inside aggregates (very common — see lesson 7). A custom sort order:

        ```run
        SELECT id, status FROM orders
        ORDER BY CASE status WHEN 'pending' THEN 1 WHEN 'shipped' THEN 2 ELSE 3 END, id
        LIMIT 6;
        ```
        """,
    ],
    exercises=[
        Exercise(
            prompt="Show each employee's full name as one column: first name, a space, "
                   "last name (e.g. 'Grace Hopper').",
            solution="SELECT first_name || ' ' || last_name FROM employees;",
            hints=["Concatenate with ||", "first_name || ' ' || last_name"],
        ),
        Exercise(
            prompt="Show each product's `name` and its inventory value (price × stock).",
            solution="SELECT name, price * stock FROM products;",
            hints=["Multiply two columns with *."],
        ),
        Exercise(
            prompt="Show each employee's `first_name` and monthly salary (salary / 12) "
                   "rounded to 2 decimal places.",
            solution="SELECT first_name, ROUND(salary / 12.0, 2) FROM employees;",
            hints=["salary is an integer, so salary / 12 truncates.",
                   "Divide by 12.0, then ROUND(x, 2)."],
        ),
        Exercise(
            prompt="Show each product's `name` and a column named `tier`: 'premium' when "
                   "price >= 1000, 'mid' when price >= 100, otherwise 'budget'.",
            solution="SELECT name, CASE WHEN price >= 1000 THEN 'premium' "
                     "WHEN price >= 100 THEN 'mid' ELSE 'budget' END AS tier FROM products;",
            check_names=True,
            hints=["CASE WHEN ... THEN ... WHEN ... THEN ... ELSE ... END",
                   "Order the WHENs from highest threshold to lowest."],
        ),
        Exercise(
            prompt="For customers that have an email, show `name` and the email's domain "
                   "(the part after '@', e.g. 'contoso.com').",
            solution="SELECT name, SUBSTR(email, INSTR(email, '@') + 1) FROM customers "
                     "WHERE email IS NOT NULL;",
            hints=["INSTR(email, '@') gives the position of the @.",
                   "SUBSTR(s, start) with no length returns the rest of the string."],
        ),
        Exercise(
            prompt="Show product names in UPPER CASE together with their length, only for "
                   "names longer than 15 characters.",
            solution="SELECT UPPER(name), LENGTH(name) FROM products WHERE LENGTH(name) > 15;",
            hints=["Functions can be used in WHERE too."],
        ),
    ],
)

DATES = Lesson(
    id="06-dates",
    title="Dates and times",
    summary="Storing, formatting, and doing arithmetic with dates.",
    pages=[
        """
        # How dates are stored

        Most databases have dedicated types: `DATE`, `TIME`, `TIMESTAMP`
        (and PostgreSQL's `TIMESTAMPTZ`, which you should prefer for
        moments in time). SQLite has no date type; it stores dates as
        **ISO-8601 text** such as `'2024-03-20'` or `'2024-03-20 14:30:00'`.
        That format sorts and compares correctly as plain text, which is why
        `order_date >= '2024-01-01'` works.

        Golden rules, in any database:

        - Store timestamps in **UTC**; convert to local time for display.
        - Never store dates in ambiguous formats like `'03/04/24'`.
        - Filter with ranges, not by applying functions to the column
          (lesson 16 explains why this matters for speed):
          `order_date >= '2023-01-01' AND order_date < '2024-01-01'`.
        """,
        """
        # Date functions in SQLite

        ```run
        SELECT date('now')                            AS today,
               date('2024-01-31', '+1 month')         AS plus_month,
               date('2024-03-20', 'start of month')   AS month_start,
               date('2024-03-20', '-7 days')          AS week_ago,
               strftime('%Y', '2024-03-20')           AS year,
               strftime('%m', '2024-03-20')           AS month,
               strftime('%w', '2024-03-20')           AS weekday_0_sun;
        ```

        Note `'2024-01-31' + 1 month` gives March 2nd — month arithmetic is
        messy in every database; know your engine's rules.

        The difference between two dates, in days, uses `julianday`:

        ```run
        SELECT id, order_date,
               julianday('2024-12-31') - julianday(order_date) AS days_ago
        FROM orders ORDER BY id DESC LIMIT 3;
        ```
        """,
        """
        # The same things in other databases

            Task              PostgreSQL                    MySQL / SQL Server
            ----------------  ----------------------------  -----------------------------
            current date      CURRENT_DATE                  CURDATE() / GETDATE()
            add 7 days        d + INTERVAL '7 days'         DATE_ADD(d, INTERVAL 7 DAY)
                                                            / DATEADD(day, 7, d)
            year of date      EXTRACT(YEAR FROM d)          YEAR(d)
            truncate month    DATE_TRUNC('month', d)        DATE_FORMAT(d,'%Y-%m-01')
            days between      d2 - d1                       DATEDIFF(d2, d1)
            format            TO_CHAR(d, 'YYYY-MM')         DATE_FORMAT / FORMAT

        `EXTRACT(field FROM d)` and `CURRENT_DATE` are standard SQL and work
        in most engines (not SQLite, which uses strftime and date('now')).

        A very common pattern is grouping by month. In SQLite:
        `strftime('%Y-%m', order_date)`; in PostgreSQL:
        `DATE_TRUNC('month', order_date)`.
        """,
    ],
    exercises=[
        Exercise(
            prompt="List `id` and `order_date` of all orders placed in 2023. "
                   "Use a date range rather than a function on the column.",
            solution="SELECT id, order_date FROM orders "
                     "WHERE order_date >= '2023-01-01' AND order_date < '2024-01-01';",
            hints=["order_date >= 'start' AND order_date < 'start of next year'"],
        ),
        Exercise(
            prompt="Show each employee's `first_name` and the year they were hired.",
            solution="SELECT first_name, strftime('%Y', hire_date) FROM employees;",
            hints=["strftime('%Y', some_date)"],
        ),
        Exercise(
            prompt="For each order show `id` and its expected delivery date: 5 days after "
                   "`order_date`.",
            solution="SELECT id, date(order_date, '+5 days') FROM orders;",
            hints=["date(d, '+N days')"],
        ),
        Exercise(
            prompt="Show each customer's `name` and the whole number of days from their "
                   "`signup_date` to 2024-01-01 (negative if they signed up later).",
            solution="SELECT name, CAST(julianday('2024-01-01') - julianday(signup_date) "
                     "AS INTEGER) FROM customers;",
            hints=["julianday(a) - julianday(b) gives days as a real number.",
                   "CAST(... AS INTEGER) to drop the fraction."],
        ),
        Exercise(
            prompt="List `first_name` and `hire_date` of employees hired in the first half "
                   "of any year (January through June).",
            solution="SELECT first_name, hire_date FROM employees "
                     "WHERE CAST(strftime('%m', hire_date) AS INTEGER) <= 6;",
            hints=["strftime('%m', ...) gives the month as text like '03'.",
                   "Compare as text with <= '06', or CAST to INTEGER."],
        ),
    ],
)

LESSONS = [INTRO, FILTERING, SORTING, NULLS, EXPRESSIONS, DATES]
