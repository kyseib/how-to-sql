"""The cheat sheet shown from the main menu."""

PAGES = [
    """
    # Query skeleton (written order)

        WITH cte AS (...)                       -- optional named subqueries
        SELECT [DISTINCT] col, expr AS alias, agg(col), fn() OVER (...)
        FROM table t
        [INNER | LEFT | RIGHT | FULL | CROSS] JOIN other o ON o.key = t.key
        WHERE row_condition
        GROUP BY col, ...
        HAVING group_condition
        ORDER BY col [ASC | DESC] [NULLS FIRST | LAST], ...
        LIMIT n OFFSET m;

    # Evaluation order

        FROM/JOIN → WHERE → GROUP BY → HAVING → SELECT (windows) → DISTINCT
        → ORDER BY → LIMIT

    # Filtering

        =  <>  <  <=  >  >=        AND  OR  NOT   (AND binds tighter: use parens)
        x IN (1, 2, 3)             x BETWEEN lo AND hi      (inclusive)
        name LIKE 'A%'  '_'=1 char x IS NULL / IS NOT NULL
        EXISTS (subquery)          x IN (subquery)   -- beware NOT IN + NULL
    """,
    """
    # Aggregates and windows

        COUNT(*)  COUNT(col)  COUNT(DISTINCT col)  SUM  AVG  MIN  MAX
        GROUP_CONCAT(col, ', ')  / STRING_AGG(col, ', ')
        SUM(CASE WHEN cond THEN 1 ELSE 0 END)     COUNT(*) FILTER (WHERE cond)

        fn() OVER (PARTITION BY a ORDER BY b ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)
        ROW_NUMBER()  RANK()  DENSE_RANK()  NTILE(n)
        LAG(x [, n, default])  LEAD(x)  FIRST_VALUE(x)  LAST_VALUE(x)
        SUM(x) OVER (ORDER BY d)       -- running total

    # Expressions

        CASE WHEN c1 THEN v1 WHEN c2 THEN v2 ELSE v3 END
        COALESCE(a, b, ...)   NULLIF(a, b)   CAST(x AS INTEGER)
        a || b   UPPER  LOWER  LENGTH  SUBSTR(s, start, len)  INSTR  REPLACE  TRIM
        ROUND(x, n)  ABS  7 / 2 = 3 (integer!)  7 / 2.0 = 3.5
        date(d, '+7 days')  strftime('%Y-%m', d)  julianday(d2) - julianday(d1)
    """,
    """
    # Set operations and CTEs

        q1 UNION q2          -- deduplicated     q1 UNION ALL q2   -- keep all
        q1 INTERSECT q2      q1 EXCEPT q2

        WITH RECURSIVE r(n) AS (
            SELECT 1 UNION ALL SELECT n + 1 FROM r WHERE n < 10
        ) SELECT n FROM r;

    # Changing data

        INSERT INTO t (a, b) VALUES (1, 'x'), (2, 'y');
        INSERT INTO t (a, b) SELECT ... ;
        UPDATE t SET a = a + 1 WHERE ... ;            -- always check the WHERE
        DELETE FROM t WHERE ... ;
        INSERT ... ON CONFLICT (key) DO UPDATE SET a = excluded.a;
        ... RETURNING id, a;

    # Transactions

        BEGIN;  ...  COMMIT;   |   ROLLBACK;
        SAVEPOINT s;  ROLLBACK TO s;  RELEASE s;
    """,
    """
    # Defining structure

        CREATE TABLE t (
            id       INTEGER PRIMARY KEY,
            name     TEXT NOT NULL UNIQUE,
            qty      INTEGER NOT NULL DEFAULT 0 CHECK (qty >= 0),
            parent   INTEGER REFERENCES parent(id) ON DELETE CASCADE
        );
        ALTER TABLE t ADD COLUMN c TEXT;       ALTER TABLE t RENAME TO u;
        DROP TABLE IF EXISTS t;                CREATE TABLE t2 AS SELECT ...;
        CREATE [UNIQUE] INDEX idx ON t (a, b); DROP INDEX idx;
        CREATE VIEW v AS SELECT ...;           DROP VIEW v;
        CREATE TRIGGER trg AFTER UPDATE OF c ON t FOR EACH ROW
            BEGIN ... NEW.c ... OLD.c ...; END;

    # Performance

        EXPLAIN QUERY PLAN SELECT ...;   (PostgreSQL/MySQL: EXPLAIN [ANALYZE])
        Index columns used in WHERE / JOIN / ORDER BY; composite = leftmost prefix.
        Keep predicates sargable: no functions on indexed columns.
        Select only needed columns. Avoid N+1 queries. Batch writes in a transaction.

    # Safety

        Parameterize every value from outside:  WHERE id = ?   (never string concat)
        Preview UPDATE/DELETE with a SELECT using the same WHERE.
    """,
]
