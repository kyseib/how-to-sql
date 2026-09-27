from ..model import Exercise, Lesson, Quiz

MODIFYING = Lesson(
    id="13-modifying-data",
    title="Changing data: INSERT, UPDATE, DELETE, UPSERT",
    summary="Writing rows safely, RETURNING, and INSERT ... ON CONFLICT.",
    pages=[
        """
        # INSERT

        Always list the columns explicitly. Your statement then survives
        columns being added or reordered, and anything you leave out gets its
        DEFAULT (or NULL):

        ```run
        INSERT INTO departments (name, location) VALUES ('Legal', 'Chicago');
        SELECT * FROM departments;
        ```

        `id` was filled in automatically: in SQLite an `INTEGER PRIMARY KEY`
        column auto-assigns the next id. (PostgreSQL: `GENERATED ALWAYS AS
        IDENTITY` or `SERIAL`; MySQL: `AUTO_INCREMENT`; SQL Server: `IDENTITY`.)

        Insert several rows in one statement — much faster than one at a time:

        ```sql
        INSERT INTO products (name, category, price, stock) VALUES
            ('Webcam',   'Accessories', 79.00, 30),
            ('Mic Stand','Audio',       25.00, 12);
        ```

        Or insert the result of a query:

        ```sql
        INSERT INTO archived_orders (id, customer_id, order_date)
        SELECT id, customer_id, order_date FROM orders WHERE order_date < '2024-01-01';
        ```
        """,
        """
        # UPDATE

        ```run
        UPDATE products SET price = price * 1.05, stock = stock + 10
        WHERE category = 'Audio';
        SELECT name, price, stock FROM products WHERE category = 'Audio';
        ```

        **An UPDATE or DELETE without WHERE changes every row.** Habits that
        prevent disasters:

        1. Write the `WHERE` first, as a `SELECT`, and check which rows
           come back. Then turn the SELECT into UPDATE/DELETE.
        2. Run risky changes inside a transaction (lesson 15), check the
           result, then COMMIT — or ROLLBACK.
        3. Check the "rows affected" count matches what you expected.

        The new value can come from a subquery:

        ```sql
        UPDATE products
        SET stock = stock - (SELECT SUM(quantity) FROM order_items
                             WHERE order_items.product_id = products.id)
        WHERE id IN (SELECT product_id FROM order_items);
        ```

        PostgreSQL and SQLite also support `UPDATE ... FROM other_table`,
        and MySQL/SQL Server support `UPDATE ... JOIN`.
        """,
        """
        # DELETE

        ```run
        DELETE FROM orders WHERE status = 'cancelled';
        SELECT COUNT(*) AS orders, (SELECT COUNT(*) FROM order_items) AS items FROM orders;
        ```

        Foreign keys control what happens to dependent rows. In this schema
        `order_items.order_id` is declared `ON DELETE CASCADE`, so deleting
        an order deletes its items too. Other options: `RESTRICT` / `NO
        ACTION` (refuse the delete — the default), `SET NULL`, `SET DEFAULT`.

        ```run
        DELETE FROM customers WHERE id = 1;  -- Northwind has orders: refused
        ```

        Removing every row: `DELETE FROM t;` (or `TRUNCATE TABLE t;` in
        PostgreSQL/MySQL/SQL Server, which is faster but can't be filtered).

        Many teams avoid deleting business data at all and use a **soft
        delete**: a `deleted_at` timestamp column that queries filter on.
        """,
        """
        # RETURNING

        `RETURNING` (PostgreSQL, SQLite 3.35+, MariaDB; SQL Server uses
        `OUTPUT`) returns the affected rows — handy for fetching generated
        ids or confirming exactly what changed:

        ```run
        UPDATE employees SET salary = salary + 5000 WHERE department_id = 5
        RETURNING id, first_name, salary;
        ```

        # UPSERT: insert or update

        "Insert this row, or update it if the key already exists" is called
        an upsert. Standard-ish syntax (PostgreSQL, SQLite):

        ```run
        INSERT INTO products (id, name, category, price, stock)
        VALUES (7, 'USB-C Hub', 'Accessories', 55.00, 200)
        ON CONFLICT (id) DO UPDATE
            SET price = excluded.price, stock = excluded.stock;
        SELECT * FROM products WHERE id = 7;
        ```

        `excluded` refers to the row you tried to insert.
        `ON CONFLICT DO NOTHING` silently skips duplicates. MySQL spells it
        `INSERT ... ON DUPLICATE KEY UPDATE`; SQL Server and Oracle use
        `MERGE`. Avoid SQLite/MySQL `REPLACE INTO`: it deletes and re-inserts
        the row, firing delete triggers and cascades.
        """,
    ],
    exercises=[
        Exercise(
            prompt="Add a department named 'Legal' located in 'Chicago'.",
            solution="INSERT INTO departments (name, location) VALUES ('Legal', 'Chicago');",
            check="SELECT id, name, location FROM departments;",
            hints=["INSERT INTO departments (name, location) VALUES (...);"],
        ),
        Exercise(
            prompt="Give every employee in department 5 (Support) a 10% raise.",
            solution="UPDATE employees SET salary = salary * 1.10 WHERE department_id = 5;",
            check="SELECT id, salary FROM employees;",
            hints=["UPDATE ... SET salary = salary * 1.10 WHERE ..."],
        ),
        Exercise(
            prompt="Set `stock` to 50 for every product that is out of stock (stock = 0).",
            solution="UPDATE products SET stock = 50 WHERE stock = 0;",
            check="SELECT id, stock FROM products;",
            hints=["UPDATE products SET ... WHERE stock = 0;"],
        ),
        Exercise(
            prompt="Delete all cancelled orders (their items are removed by the cascade).",
            solution="DELETE FROM orders WHERE status = 'cancelled';",
            check="SELECT (SELECT COUNT(*) FROM orders), (SELECT COUNT(*) FROM order_items);",
            hints=["DELETE FROM orders WHERE ..."],
        ),
        Exercise(
            prompt="In ONE upsert statement: set product 5's price to 119.50 (keep its other "
                   "values), and add a new product id 14 'Webcam', category 'Accessories', "
                   "price 79.00, stock 30.",
            solution="INSERT INTO products (id, name, category, price, stock) VALUES "
                     "(5, 'Mechanical Keyboard', 'Accessories', 119.50, 150), "
                     "(14, 'Webcam', 'Accessories', 79.00, 30) "
                     "ON CONFLICT (id) DO UPDATE SET price = excluded.price;",
            check="SELECT * FROM products;",
            hints=["Insert both rows; ON CONFLICT (id) DO UPDATE SET price = excluded.price",
                   "Product 5 is 'Mechanical Keyboard', 'Accessories', stock 150."],
        ),
        Exercise(
            prompt="A table `vip_customers (id, name)` exists and is empty. Fill it with "
                   "every customer who has placed 3 or more orders, using INSERT ... SELECT.",
            setup="CREATE TABLE vip_customers (id INTEGER PRIMARY KEY, name TEXT NOT NULL);",
            solution="INSERT INTO vip_customers (id, name) SELECT c.id, c.name FROM customers c "
                     "JOIN orders o ON o.customer_id = c.id GROUP BY c.id, c.name "
                     "HAVING COUNT(*) >= 3;",
            check="SELECT id, name FROM vip_customers;",
            hints=["Write the SELECT first: customers with COUNT(orders) >= 3.",
                   "Then prefix it with INSERT INTO vip_customers (id, name)."],
        ),
        Quiz(
            question="What is the safest first step before running "
                     "`DELETE FROM orders WHERE <condition>` on production?",
            options=["Run it and check the rows-affected count",
                     "Run SELECT * FROM orders WHERE <condition> to see what would be deleted",
                     "Drop the foreign keys", "Add LIMIT 1"],
            answer=1,
            explanation="Preview the exact rows with the same WHERE. Better still, also wrap "
                        "the delete in a transaction and verify before committing.",
        ),
    ],
)

DDL = Lesson(
    id="14-tables-constraints",
    title="Creating tables, types and constraints",
    summary="CREATE/ALTER/DROP, data types, keys, CHECK, DEFAULT, foreign keys.",
    pages=[
        """
        # CREATE TABLE

        ```sql
        CREATE TABLE suppliers (
            id          INTEGER PRIMARY KEY,
            name        TEXT    NOT NULL UNIQUE,
            country     TEXT    NOT NULL DEFAULT 'USA',
            rating      INTEGER CHECK (rating BETWEEN 1 AND 5),
            created_at  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        ```

        Each column has a name, a type, and optional **constraints**. The
        database enforces constraints on every write, so bad data is
        rejected no matter which application or person wrote it. That makes
        constraints the most reliable data-quality tool you have.

        - `PRIMARY KEY` — unique, non-null identifier for the row.
        - `NOT NULL` — a value is required.
        - `UNIQUE` — no two rows may share the value.
        - `CHECK (condition)` — the condition must not be false.
        - `DEFAULT value` — used when an INSERT omits the column.
        - `REFERENCES other(col)` — a foreign key (next page).
        """,
        """
        # Data types

        Standard types, and what to use them for:

            INTEGER / BIGINT        whole numbers, ids, counts
            NUMERIC(p, s) / DECIMAL exact decimals: MONEY. e.g. NUMERIC(12, 2)
            REAL / DOUBLE / FLOAT   approximate: measurements, science
            VARCHAR(n) / TEXT       strings (PostgreSQL: just use TEXT)
            BOOLEAN                 true/false (SQLite & old MySQL: 0/1)
            DATE / TIMESTAMP        dates and moments (TIMESTAMPTZ in PostgreSQL)
            UUID, JSON/JSONB, arrays, enums ... vendor-specific extras

        **Never store money in floating point.** `0.1 + 0.2` is not exactly
        `0.3` in binary floating point:

        ```run
        SELECT 0.1 + 0.2 = 0.3 AS equal, 0.1 + 0.2 AS actual;
        ```

        Use DECIMAL/NUMERIC, or store integer cents. (This sample database
        uses REAL prices for simplicity — don't copy that.)

        SQLite uses **type affinity**: a declared type is a preference, not a
        rule, and `'hello'` can be stored in an INTEGER column. Add `STRICT`
        after the closing parenthesis (`CREATE TABLE t (...) STRICT;`) to get
        real type checking like other databases.
        """,
        """
        # Constraints in action

        ```run
        CREATE TABLE reviews (
            id          INTEGER PRIMARY KEY,
            product_id  INTEGER NOT NULL REFERENCES products(id),
            rating      INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
            body        TEXT
        );
        INSERT INTO reviews (product_id, rating, body) VALUES (1, 5, 'Great laptop');
        ```

        ```run
        INSERT INTO reviews (product_id, rating) VALUES (1, 9);
        ```

        ```run
        INSERT INTO reviews (product_id, rating) VALUES (999, 4);
        ```

        The foreign key rejected a review for product 999, which doesn't exist.
        A foreign key guarantees **referential integrity**: no orphans.

        Foreign-key options: `ON DELETE CASCADE | SET NULL | RESTRICT` and
        the same for `ON UPDATE`. Index your foreign-key columns — joins
        and cascades use them. (SQLite only enforces foreign keys after
        `PRAGMA foreign_keys = ON`; this tutor turns it on for you.)

        Constraints can also be declared at table level, which is required
        for multi-column keys:

        ```sql
        CREATE TABLE order_items (
            order_id   INTEGER NOT NULL REFERENCES orders(id),
            product_id INTEGER NOT NULL REFERENCES products(id),
            quantity   INTEGER NOT NULL CHECK (quantity > 0),
            PRIMARY KEY (order_id, product_id)
        );
        ```
        """,
        """
        # Changing and removing tables

        ```sql
        ALTER TABLE customers ADD COLUMN phone TEXT;
        ALTER TABLE customers RENAME COLUMN phone TO phone_number;
        ALTER TABLE customers DROP COLUMN phone_number;   -- SQLite 3.35+
        ALTER TABLE customers RENAME TO clients;
        DROP TABLE IF EXISTS temp_import;
        ```

        SQLite's ALTER TABLE is limited (you can't add a constraint to an
        existing column; the documented workaround is to create a new table,
        copy the data, and swap). PostgreSQL, MySQL and SQL Server support
        `ALTER TABLE ... ADD CONSTRAINT`, `ALTER COLUMN ... TYPE`, etc.

        Create a table from a query (column types are inferred, constraints
        are not copied):

        ```run
        CREATE TABLE audio_products AS
        SELECT id, name, price FROM products WHERE category = 'Audio';
        SELECT * FROM audio_products;
        ```

        In real projects, schema changes are applied through **migrations**:
        numbered, version-controlled scripts (via tools like Flyway,
        Liquibase, Alembic, Rails/Django migrations) so every environment
        has the same schema.
        """,
    ],
    exercises=[
        Exercise(
            prompt="Create a table `suppliers` with columns: `id` INTEGER PRIMARY KEY, "
                   "`name` TEXT NOT NULL, `country` TEXT.",
            solution="CREATE TABLE suppliers (id INTEGER PRIMARY KEY, name TEXT NOT NULL, "
                     "country TEXT);",
            check="SELECT name, upper(type), \"notnull\", pk FROM pragma_table_info('suppliers');",
            hints=["CREATE TABLE suppliers (col type constraints, ...);"],
        ),
        Exercise(
            prompt="Add a column `phone` of type TEXT to the `customers` table.",
            solution="ALTER TABLE customers ADD COLUMN phone TEXT;",
            check="SELECT name, upper(type) FROM pragma_table_info('customers');",
            hints=["ALTER TABLE ... ADD COLUMN ..."],
        ),
        Exercise(
            prompt="Create a table `ratings` with: `id` INTEGER PRIMARY KEY; `product_id` "
                   "INTEGER, required, referencing products(id); `stars` INTEGER, required, "
                   "must be between 1 and 5.",
            solution="CREATE TABLE ratings (id INTEGER PRIMARY KEY, "
                     "product_id INTEGER NOT NULL REFERENCES products(id), "
                     "stars INTEGER NOT NULL CHECK (stars BETWEEN 1 AND 5));",
            probes=[
                "INSERT INTO ratings (product_id, stars) VALUES (1, 5);",
                "INSERT INTO ratings (product_id, stars) VALUES (1, 1);",
                "INSERT INTO ratings (product_id, stars) VALUES (1, 6);",
                "INSERT INTO ratings (product_id, stars) VALUES (1, 0);",
                "INSERT INTO ratings (product_id, stars) VALUES (1, NULL);",
                "INSERT INTO ratings (product_id, stars) VALUES (NULL, 3);",
                "INSERT INTO ratings (product_id, stars) VALUES (999, 3);",
            ],
            check="SELECT product_id, stars FROM ratings;",
            hints=["NOT NULL, REFERENCES products(id), CHECK (stars BETWEEN 1 AND 5)"],
        ),
        Exercise(
            prompt="Create a table `tags` with `id` INTEGER PRIMARY KEY and `name` TEXT that "
                   "is required and must be unique.",
            solution="CREATE TABLE tags (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);",
            probes=[
                "INSERT INTO tags (name) VALUES ('sale');",
                "INSERT INTO tags (name) VALUES ('new');",
                "INSERT INTO tags (name) VALUES ('sale');",
                "INSERT INTO tags (name) VALUES (NULL);",
            ],
            check="SELECT name FROM tags;",
            hints=["name TEXT NOT NULL UNIQUE"],
        ),
        Exercise(
            prompt="Create a table `expensive_products` containing the `name` and `price` "
                   "of every product costing more than 1000, using CREATE TABLE ... AS SELECT.",
            solution="CREATE TABLE expensive_products AS SELECT name, price FROM products "
                     "WHERE price > 1000;",
            check="SELECT * FROM expensive_products;",
            hints=["CREATE TABLE new_table AS SELECT ...;"],
        ),
        Quiz(
            question="Which type should store a product's price?",
            options=["FLOAT", "DOUBLE", "NUMERIC(10, 2) / DECIMAL", "TEXT"],
            answer=2,
            explanation="Exact decimal types avoid binary rounding errors. Integer cents "
                        "is the other good option.",
        ),
    ],
)

TRANSACTIONS = Lesson(
    id="15-transactions",
    title="Transactions and concurrency",
    summary="ACID, BEGIN/COMMIT/ROLLBACK, savepoints, isolation levels, locking.",
    pages=[
        """
        # Why transactions

        Transferring money is two updates: subtract from one account, add to
        another. If the program crashes between them, money vanishes. A
        **transaction** groups statements so they succeed or fail as a unit.

        ```run
        CREATE TABLE accounts (id INTEGER PRIMARY KEY, owner TEXT, balance NUMERIC);
        INSERT INTO accounts VALUES (1, 'alice', 500), (2, 'bob', 100);

        BEGIN;
        UPDATE accounts SET balance = balance - 200 WHERE id = 1;
        UPDATE accounts SET balance = balance + 200 WHERE id = 2;
        COMMIT;

        SELECT * FROM accounts;
        ```

        - `BEGIN` (or `START TRANSACTION`) opens a transaction.
        - `COMMIT` makes all of its changes permanent and visible to others.
        - `ROLLBACK` undoes everything since BEGIN.

        Outside an explicit transaction, most databases run in **autocommit**
        mode: every statement is its own transaction.
        """,
        """
        # ROLLBACK and SAVEPOINT

        ```run
        BEGIN;
        DELETE FROM order_items;
        SELECT COUNT(*) AS items_inside_transaction FROM order_items;
        ROLLBACK;
        SELECT COUNT(*) AS items_after_rollback FROM order_items;
        ```

        Savepoints are checkpoints inside a transaction that you can roll back
        to without abandoning the whole transaction:

        ```run
        BEGIN;
        UPDATE products SET price = price + 1 WHERE id = 1;
        SAVEPOINT before_risky;
        UPDATE products SET price = 0;              -- oops, no WHERE
        ROLLBACK TO before_risky;                   -- undo just the oops
        COMMIT;
        SELECT id, price FROM products WHERE id <= 3;
        ```

        # ACID

        - **Atomicity** — all or nothing.
        - **Consistency** — a transaction moves the database from one valid
          state to another; constraints hold at commit.
        - **Isolation** — concurrent transactions don't see each other's
          half-finished work (to a configurable degree).
        - **Durability** — once committed, data survives crashes.
        """,
        """
        # Isolation levels and anomalies

        When many users run transactions at once, these anomalies can occur:

        - **Dirty read** — reading another transaction's uncommitted changes.
        - **Non-repeatable read** — reading the same row twice in one
          transaction and getting different values, because someone
          committed an update in between.
        - **Phantom read** — re-running a query and getting new rows, because
          someone inserted matching rows in between.
        - **Lost update** — two transactions read a value, both modify it,
          and the second write overwrites the first.

        The standard isolation levels, from weakest to strongest:

            Level              dirty read   non-repeatable   phantom
            READ UNCOMMITTED   possible     possible         possible
            READ COMMITTED     prevented    possible         possible
            REPEATABLE READ    prevented    prevented        possible*
            SERIALIZABLE       prevented    prevented        prevented

            * PostgreSQL's REPEATABLE READ also prevents phantoms.

        Defaults: PostgreSQL, SQL Server and Oracle use READ COMMITTED; MySQL
        InnoDB uses REPEATABLE READ; SQLite is effectively SERIALIZABLE (it
        allows only one writer at a time). Stronger levels are safer but
        cause more blocking or retry errors.
        """,
        """
        # Preventing lost updates

        Two clerks both sell the last unit of stock:

            T1: SELECT stock FROM products WHERE id = 7;  -- sees 1
            T2: SELECT stock FROM products WHERE id = 7;  -- sees 1
            T1: UPDATE products SET stock = 0 WHERE id = 7;
            T2: UPDATE products SET stock = 0 WHERE id = 7;  -- sold twice!

        Fixes:

        - Do the check and change in one atomic statement:
          `UPDATE products SET stock = stock - 1 WHERE id = 7 AND stock > 0;`
          then check the rows-affected count.
        - Lock the row when reading: `SELECT ... FOR UPDATE` (PostgreSQL,
          MySQL, Oracle) makes other writers wait.
        - Optimistic locking: keep a `version` column and
          `UPDATE ... SET ..., version = version + 1 WHERE id = 7 AND version = 3`.
          If 0 rows were affected, someone else got there first; retry.

        Practical rules: keep transactions **short** (never wait for user
        input inside one), touch tables in a consistent order to avoid
        **deadlocks**, and be ready to retry when the database aborts a
        transaction due to a deadlock or serialization failure.
        """,
    ],
    exercises=[
        Exercise(
            prompt="An `accounts` table exists: (1, 'alice', 500) and (2, 'bob', 100). "
                   "In a transaction, move 150 from alice to bob, then commit.",
            setup="CREATE TABLE accounts (id INTEGER PRIMARY KEY, owner TEXT, balance NUMERIC);"
                  "INSERT INTO accounts VALUES (1, 'alice', 500), (2, 'bob', 100);",
            solution="BEGIN; UPDATE accounts SET balance = balance - 150 WHERE id = 1; "
                     "UPDATE accounts SET balance = balance + 150 WHERE id = 2; COMMIT;",
            check="SELECT id, balance FROM accounts;",
            hints=["BEGIN; two UPDATEs; COMMIT;"],
        ),
        Exercise(
            prompt="In one transaction: double every product's price, set a savepoint, "
                   "set every product's stock to 0, roll back to the savepoint (keeping the "
                   "price change but undoing the stock change), and commit.",
            solution="BEGIN; UPDATE products SET price = price * 2; SAVEPOINT s; "
                     "UPDATE products SET stock = 0; ROLLBACK TO s; COMMIT;",
            check="SELECT id, price, stock FROM products;",
            hints=["SAVEPOINT name; ... ROLLBACK TO name;",
                   "BEGIN; UPDATE ...; SAVEPOINT s; UPDATE ...; ROLLBACK TO s; COMMIT;"],
        ),
        Quiz(
            question="Which ACID property guarantees that a committed transaction survives "
                     "a power failure?",
            options=["Atomicity", "Consistency", "Isolation", "Durability"],
            answer=3,
        ),
        Quiz(
            question="Transaction A reads a row twice and gets different values because B "
                     "committed an update in between. What is this called?",
            options=["Dirty read", "Non-repeatable read", "Phantom read", "Deadlock"],
            answer=1,
            explanation="A dirty read would be seeing B's change before B committed. "
                        "Phantoms are about new rows appearing in a range query.",
        ),
        Quiz(
            question="Which isolation level prevents all three read anomalies?",
            options=["READ UNCOMMITTED", "READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE"],
            answer=3,
        ),
        Quiz(
            question="Which statement safely decrements stock without a lost update?",
            options=[
                "SELECT stock ...; then UPDATE products SET stock = <value read - 1> ...",
                "UPDATE products SET stock = stock - 1 WHERE id = 7 AND stock > 0",
                "DELETE and re-INSERT the product row",
                "Run the SELECT twice to be sure",
            ],
            answer=1,
            explanation="Reading and writing in one statement is atomic; the WHERE stops "
                        "stock going negative. Check rows affected to know if it succeeded.",
        ),
    ],
)

INDEXES = Lesson(
    id="16-indexes-performance",
    title="Indexes and query performance",
    summary="How indexes work, EXPLAIN, composite indexes, sargability, habits.",
    pages=[
        """
        # What an index is

        Without an index, finding rows with `customer_id = 3` means reading
        every row: a **full table scan**. An index is a separate, sorted data
        structure (usually a B-tree) mapping column values to row locations,
        like the index at the back of a book. Lookups become logarithmic
        instead of linear — the difference between microseconds and minutes
        on large tables.

        Ask the database how it plans to run a query. SQLite uses
        `EXPLAIN QUERY PLAN`; PostgreSQL/MySQL use `EXPLAIN` (and
        `EXPLAIN ANALYZE` to actually run it and show real timings).

        ```run
        EXPLAIN QUERY PLAN SELECT * FROM orders WHERE customer_id = 3;
        ```

        `SCAN orders` = read the whole table. Now add an index:

        ```run
        CREATE INDEX idx_orders_customer ON orders (customer_id);
        EXPLAIN QUERY PLAN SELECT * FROM orders WHERE customer_id = 3;
        ```

        `SEARCH ... USING INDEX` = jump straight to the matching rows.
        Primary keys and UNIQUE columns are indexed automatically.
        """,
        """
        # Composite indexes and the leftmost-prefix rule

        An index on several columns is sorted by the first column, then the
        second within it, like a phone book sorted by (last name, first name):

        ```run
        CREATE INDEX idx_emp_dept_salary ON employees (department_id, salary);
        EXPLAIN QUERY PLAN
        SELECT first_name FROM employees WHERE department_id = 2 AND salary > 90000;
        ```

        That index helps queries filtering on `department_id`, or on
        `department_id` **and** `salary`. It can't be used to search on
        `salary` alone — just as a phone book doesn't help you find everyone
        named "Ada".

        ```run
        EXPLAIN QUERY PLAN SELECT first_name FROM employees WHERE salary > 90000;
        ```

        Column order guideline: equality-filtered columns first, then the
        range or sort column.

        A **covering index** contains every column a query needs, so the
        table itself is never touched (`USING COVERING INDEX` in the plan).
        """,
        """
        # Sargable predicates

        A condition is **sargable** (Search ARGument ABLE) if an index can
        be used to evaluate it. Wrapping the indexed column in a function or
        expression usually defeats the index:

        ```run
        CREATE INDEX idx_orders_date ON orders (order_date);
        EXPLAIN QUERY PLAN SELECT id FROM orders WHERE strftime('%Y', order_date) = '2023';
        ```

        ```run
        EXPLAIN QUERY PLAN SELECT id FROM orders
        WHERE order_date >= '2023-01-01' AND order_date < '2024-01-01';
        ```

        The first plan must SCAN every index entry and run strftime on each
        one; the second SEARCHes just the matching range.

        Other common index killers:

        - `WHERE LOWER(email) = 'x'` — store normalized data, or create an
          **expression index**: `CREATE INDEX ... ON t (LOWER(email))`.
        - `WHERE name LIKE '%son'` — leading wildcard; a B-tree can't help.
          Full-text search indexes can.
        - `WHERE price * 1.2 > 100` — move the math: `price > 100 / 1.2`.
        - Comparing a column to a value of a different type, forcing an
          implicit conversion on every row.
        """,
        """
        # The cost of indexes, and performance habits

        Indexes aren't free: every INSERT, UPDATE and DELETE must also update
        each index, and they use disk and memory. Index what you filter,
        join and sort on — especially foreign keys — not every column.
        Low-selectivity columns (e.g. a boolean where 50% of rows are true)
        rarely benefit. Keep statistics fresh (`ANALYZE`) so the planner
        makes good choices.

        Habits that make queries fast:

        - Select only the columns you need; avoid `SELECT *` in application
          code (more I/O, prevents covering indexes, breaks when schemas change).
        - Filter as early as possible (WHERE rather than HAVING).
        - Avoid the **N+1 problem**: one query for a list, then one more
          query per item. Use a JOIN or `WHERE id IN (...)` instead.
        - Batch writes in transactions: inserting 10,000 rows in one
          transaction can be 100x faster than 10,000 autocommits.
        - Use keyset pagination instead of large OFFSETs.
        - Prefer `EXISTS` for "is there any?" checks over `COUNT(*) > 0`.
        - Read the plan (EXPLAIN) before guessing. Measure, don't assume.
        """,
    ],
    exercises=[
        Exercise(
            prompt="Create an index named `idx_employees_last_name` on employees(last_name).",
            solution="CREATE INDEX idx_employees_last_name ON employees (last_name);",
            check="SELECT name FROM pragma_index_info('idx_employees_last_name');",
            hints=["CREATE INDEX name ON table (column);"],
        ),
        Exercise(
            prompt="Create a composite index named `idx_orders_customer_date` on orders, "
                   "on customer_id then order_date.",
            solution="CREATE INDEX idx_orders_customer_date ON orders (customer_id, order_date);",
            check="SELECT seqno, name FROM pragma_index_info('idx_orders_customer_date');",
            ordered=True,
            hints=["Column order matters: (customer_id, order_date)."],
        ),
        Exercise(
            prompt="Return `id` and `order_date` of orders placed in March 2024, written so "
                   "an index on order_date could be used (no function on the column).",
            solution="SELECT id, order_date FROM orders "
                     "WHERE order_date >= '2024-03-01' AND order_date < '2024-04-01';",
            hints=["Use a half-open range: >= first day AND < first day of next month."],
        ),
        Quiz(
            question="Given an index on (last_name, first_name), which WHERE clause can NOT "
                     "use it to search?",
            options=["WHERE last_name = 'Smith'",
                     "WHERE last_name = 'Smith' AND first_name = 'Ann'",
                     "WHERE first_name = 'Ann'",
                     "WHERE last_name LIKE 'Sm%'"],
            answer=2,
            explanation="Leftmost-prefix rule: the index is sorted by last_name first. "
                        "(LIKE 'Sm%' is a prefix range, which can use it in many engines.)",
        ),
        Quiz(
            question="Why is `WHERE YEAR(created_at) = 2024` often slow on a large table?",
            options=["YEAR() is a slow function",
                     "Applying a function to the column prevents a normal index seek",
                     "Dates can't be indexed", "It returns too many rows"],
            answer=1,
            explanation="Rewrite as created_at >= '2024-01-01' AND created_at < '2025-01-01'.",
        ),
        Quiz(
            question="What is the main downside of adding many indexes to a table?",
            options=["SELECTs become slower", "Writes become slower and storage grows",
                     "Constraints stop working", "Queries return different results"],
            answer=1,
        ),
    ],
)

VIEWS_TRIGGERS = Lesson(
    id="17-views-triggers",
    title="Views and triggers",
    summary="Saved queries, and code that runs automatically on writes.",
    pages=[
        """
        # Views

        A view is a named, stored query that you can select from like a
        table:

        ```run
        CREATE VIEW customer_revenue AS
        SELECT c.id, c.name, SUM(oi.quantity * oi.unit_price) AS revenue
        FROM customers c
        JOIN orders o       ON o.customer_id = c.id
        JOIN order_items oi ON oi.order_id = o.id
        WHERE o.status <> 'cancelled'
        GROUP BY c.id, c.name;

        SELECT name, ROUND(revenue) AS revenue FROM customer_revenue
        ORDER BY revenue DESC LIMIT 3;
        ```

        Why use views:

        - **Reuse** — define business logic ("revenue excludes cancelled
          orders") once, instead of copying it into every report.
        - **Simplicity** — hide complex joins behind a clean interface.
        - **Security** — grant users access to a view exposing only some
          columns or rows, not the underlying table.

        A normal view stores no data; its query runs each time you use it.
        A **materialized view** (PostgreSQL, Oracle; "indexed view" in SQL
        Server) stores the result and must be refreshed — fast reads, stale
        data. Remove a view with `DROP VIEW name;`.
        """,
        """
        # Triggers

        A trigger runs SQL automatically when rows are inserted, updated or
        deleted. Inside it, `NEW` is the row after the change and `OLD` the
        row before.

        ```run
        CREATE TABLE audit_log (
            at TEXT DEFAULT CURRENT_TIMESTAMP, table_name TEXT, row_id INTEGER, detail TEXT
        );

        CREATE TRIGGER log_salary_change
        AFTER UPDATE OF salary ON employees
        FOR EACH ROW
        WHEN NEW.salary <> OLD.salary
        BEGIN
            INSERT INTO audit_log (table_name, row_id, detail)
            VALUES ('employees', NEW.id, OLD.salary || ' -> ' || NEW.salary);
        END;

        UPDATE employees SET salary = salary + 1000 WHERE id IN (14, 16);
        SELECT table_name, row_id, detail FROM audit_log;
        ```

        Good uses: audit trails, maintaining `updated_at` columns, enforcing
        rules that CHECK constraints can't express. Use sparingly: triggers
        are invisible in application code, run on every write, and make
        behaviour surprising. Syntax differs a lot between databases
        (PostgreSQL triggers call a separate trigger *function*).

        In SQLite a trigger can reject a change with
        `SELECT RAISE(ABORT, 'message');`.
        """,
    ],
    exercises=[
        Exercise(
            prompt="Create a view named `order_totals` with columns `order_id` and `total` "
                   "(sum of quantity × unit_price per order).",
            solution="CREATE VIEW order_totals AS SELECT order_id, SUM(quantity * unit_price) "
                     "AS total FROM order_items GROUP BY order_id;",
            check="SELECT order_id, total FROM order_totals;",
            hints=["CREATE VIEW order_totals AS SELECT ...;",
                   "Name the sum with AS total."],
        ),
        Exercise(
            prompt="A view `order_totals (order_id, total)` exists. Use it to list the "
                   "customer `name` and order `total` of the 3 largest orders, largest first.",
            setup="CREATE VIEW order_totals AS SELECT order_id, SUM(quantity * unit_price) "
                  "AS total FROM order_items GROUP BY order_id;",
            solution="SELECT c.name, t.total FROM order_totals t "
                     "JOIN orders o ON o.id = t.order_id JOIN customers c ON c.id = o.customer_id "
                     "ORDER BY t.total DESC LIMIT 3;",
            ordered=True,
            hints=["Join the view to orders, then to customers, like any table."],
        ),
        Exercise(
            prompt="A table `price_history (product_id, old_price, new_price)` exists. "
                   "Create a trigger that inserts a row into it whenever a product's price "
                   "changes.",
            setup="CREATE TABLE price_history (product_id INTEGER, old_price REAL, new_price REAL);",
            solution="CREATE TRIGGER track_price AFTER UPDATE OF price ON products "
                     "FOR EACH ROW WHEN NEW.price <> OLD.price BEGIN "
                     "INSERT INTO price_history (product_id, old_price, new_price) "
                     "VALUES (NEW.id, OLD.price, NEW.price); END;",
            probes=[
                "UPDATE products SET price = 10 WHERE id = 1;",
                "UPDATE products SET stock = 1 WHERE id = 2;",
                "UPDATE products SET price = price WHERE id = 3;",
                "UPDATE products SET price = 20 WHERE id IN (4, 5);",
            ],
            check="SELECT product_id, old_price, new_price FROM price_history;",
            hints=["CREATE TRIGGER name AFTER UPDATE OF price ON products FOR EACH ROW "
                   "WHEN ... BEGIN ...; END;",
                   "Only log when the price actually changed: WHEN NEW.price <> OLD.price"],
        ),
    ],
)

DESIGN = Lesson(
    id="18-design",
    title="Database design and normalization",
    summary="Modelling entities and relationships; 1NF, 2NF, 3NF; when to denormalize.",
    pages=[
        """
        # Entities, relationships, keys

        Designing a schema starts with the nouns of your domain (entities:
        customer, order, product) and how they relate:

        - **One-to-many** — a customer has many orders; an order has one
          customer. Put a foreign key on the "many" side
          (`orders.customer_id`).
        - **Many-to-many** — an order contains many products; a product
          appears in many orders. Use a **junction table** with a foreign key
          to each side (`order_items`), often with a composite primary key.
          Junction tables frequently carry their own data (quantity, price).
        - **One-to-one** — rare; a foreign key that is also UNIQUE. Used to
          split rarely-used or sensitive columns into a separate table.

        Keys: a **natural key** is real-world data (email, ISBN); a
        **surrogate key** is a meaningless generated id. Surrogate keys are
        the common default because real-world "unique" data changes (people
        change emails). Still put UNIQUE constraints on natural keys.
        """,
        """
        # Normalization

        Normalization removes redundancy so every fact is stored exactly
        once, preventing **update anomalies** (changing a fact in one place
        but not another).

        **1NF — atomic values, no repeating groups.** One value per cell.

            BAD:  customers(id, name, phones = '555-1234, 555-9876')
            BAD:  customers(id, name, phone1, phone2, phone3)
            GOOD: customer_phones(customer_id, phone)

        **2NF — no partial dependencies.** In a table with a composite key,
        every non-key column must depend on the *whole* key.

            BAD:  order_items(order_id, product_id, quantity, product_name)
                  -- product_name depends only on product_id
            GOOD: product_name lives in products

        **3NF — no transitive dependencies.** Non-key columns depend on the
        key, the whole key, and nothing but the key.

            BAD:  employees(id, name, department_id, department_name)
                  -- department_name depends on department_id, not on id
            GOOD: department_name lives in departments

        (BCNF, 4NF and 5NF go further; in practice, reaching 3NF is the goal.)
        """,
        """
        # When to denormalize

        Normalized schemas are the right default for transactional systems
        (OLTP). Deliberate denormalization is sometimes justified:

        - **Historical snapshots.** `order_items.unit_price` looks like it
          duplicates `products.price`, but it records the price *at the time
          of sale*. It's a different fact, and storing it is correct.
        - **Read performance.** Caching an aggregate like
          `customers.order_count`, at the cost of keeping it in sync
          (triggers or application code).
        - **Analytics (OLAP).** Data warehouses use **star schemas**: a large
          fact table (sales) surrounded by denormalized dimension tables
          (date, product, store), optimized for aggregation, not updates.

        Other design advice:

        - Use consistent names: plural or singular tables (pick one),
          `snake_case`, `<table>_id` for foreign keys.
        - Choose precise types; add NOT NULL unless a value is truly optional.
        - Put rules in constraints, not only in application code.
        - Avoid storing lists in strings and "EAV" (entity-attribute-value)
          tables unless you truly need open-ended attributes (consider JSON
          columns then).
        """,
    ],
    exercises=[
        Exercise(
            prompt="A `projects (id, name)` table exists. Create a junction table "
                   "`employee_projects` linking employees and projects (many-to-many): "
                   "columns `employee_id` and `project_id`, both required foreign keys, "
                   "and the pair as the composite primary key.",
            setup="CREATE TABLE projects (id INTEGER PRIMARY KEY, name TEXT NOT NULL);"
                  "INSERT INTO projects VALUES (1, 'Apollo'), (2, 'Gemini');",
            solution="CREATE TABLE employee_projects ("
                     "employee_id INTEGER NOT NULL REFERENCES employees(id), "
                     "project_id INTEGER NOT NULL REFERENCES projects(id), "
                     "PRIMARY KEY (employee_id, project_id));",
            probes=[
                "INSERT INTO employee_projects VALUES (1, 1);",
                "INSERT INTO employee_projects VALUES (1, 2);",
                "INSERT INTO employee_projects VALUES (2, 1);",
                "INSERT INTO employee_projects VALUES (1, 1);",
                "INSERT INTO employee_projects VALUES (99, 1);",
                "INSERT INTO employee_projects VALUES (1, 99);",
                "INSERT INTO employee_projects VALUES (NULL, 1);",
            ],
            check="SELECT employee_id, project_id FROM employee_projects;",
            hints=["Table-level constraint: PRIMARY KEY (employee_id, project_id)",
                   "Each column: INTEGER NOT NULL REFERENCES other_table(id)"],
        ),
        Quiz(
            question="A column `skills` stores values like 'sql, python, excel'. Which normal "
                     "form does this violate?",
            options=["1NF", "2NF", "3NF", "None"],
            answer=0,
            explanation="Multiple values in one cell. Use a separate employee_skills table.",
        ),
        Quiz(
            question="Table employees(id, name, department_id, department_location). Which "
                     "normal form is violated?",
            options=["1NF", "2NF", "3NF", "None"],
            answer=2,
            explanation="department_location depends on department_id (a non-key column), "
                        "not directly on the employee's id: a transitive dependency.",
        ),
        Quiz(
            question="How do you model a many-to-many relationship between students and "
                     "courses?",
            options=["A course_ids text column on students",
                     "A foreign key on students pointing to courses",
                     "A junction table enrollments(student_id, course_id)",
                     "Merge them into one table"],
            answer=2,
        ),
        Quiz(
            question="order_items stores unit_price even though products has price. Is this "
                     "a normalization mistake?",
            options=["Yes, it violates 2NF", "Yes, it violates 3NF",
                     "No: it records the price at the time of sale, a different fact",
                     "No: duplication is always fine"],
            answer=2,
        ),
    ],
)

LESSONS = [MODIFYING, DDL, TRANSACTIONS, INDEXES, VIEWS_TRIGGERS, DESIGN]
