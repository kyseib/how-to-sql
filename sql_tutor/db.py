"""The sample "Acme" database used by every lesson, exercise and the sandbox."""

import sqlite3

SCHEMA = """
CREATE TABLE departments (
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL UNIQUE,
    location  TEXT NOT NULL
);

CREATE TABLE employees (
    id             INTEGER PRIMARY KEY,
    first_name     TEXT NOT NULL,
    last_name      TEXT NOT NULL,
    email          TEXT UNIQUE,
    department_id  INTEGER REFERENCES departments(id),
    manager_id     INTEGER REFERENCES employees(id),
    title          TEXT NOT NULL,
    salary         INTEGER NOT NULL CHECK (salary > 0),
    hire_date      TEXT NOT NULL
);

CREATE TABLE customers (
    id           INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    email        TEXT,
    city         TEXT NOT NULL,
    country      TEXT NOT NULL,
    signup_date  TEXT NOT NULL
);

CREATE TABLE products (
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL UNIQUE,
    category  TEXT NOT NULL,
    price     REAL NOT NULL CHECK (price >= 0),
    stock     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE orders (
    id           INTEGER PRIMARY KEY,
    customer_id  INTEGER NOT NULL REFERENCES customers(id),
    employee_id  INTEGER REFERENCES employees(id),
    order_date   TEXT NOT NULL,
    status       TEXT NOT NULL
                 CHECK (status IN ('pending', 'shipped', 'delivered', 'cancelled'))
);

CREATE TABLE order_items (
    order_id    INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id  INTEGER NOT NULL REFERENCES products(id),
    quantity    INTEGER NOT NULL CHECK (quantity > 0),
    unit_price  REAL NOT NULL,
    PRIMARY KEY (order_id, product_id)
);
"""

SEED = """
INSERT INTO departments VALUES
 (1, 'Engineering', 'San Francisco'),
 (2, 'Sales',       'New York'),
 (3, 'Marketing',   'New York'),
 (4, 'Finance',     'Chicago'),
 (5, 'Support',     'Austin'),
 (6, 'Research',    'Boston');

INSERT INTO employees VALUES
 (1,  'Grace',    'Hopper',    'grace@acme.com',    1,    NULL, 'CEO',                250000, '2015-01-15'),
 (2,  'Alan',     'Turing',    'alan@acme.com',     1,    1,    'CTO',                210000, '2015-03-01'),
 (3,  'Ada',      'Lovelace',  'ada@acme.com',      1,    2,    'Senior Engineer',    165000, '2016-07-11'),
 (4,  'Edsger',   'Dijkstra',  'edsger@acme.com',   1,    2,    'Senior Engineer',    158000, '2017-02-20'),
 (5,  'Margaret', 'Hamilton',  'margaret@acme.com', 1,    3,    'Engineer',           132000, '2019-09-03'),
 (6,  'Dennis',   'Ritchie',   NULL,                1,    3,    'Engineer',           128000, '2020-05-18'),
 (7,  'Don',      'Draper',    'don@acme.com',      3,    1,    'Marketing Director', 175000, '2016-04-04'),
 (8,  'Peggy',    'Olson',     'peggy@acme.com',    3,    7,    'Copywriter',          92000, '2018-10-22'),
 (9,  'Michael',  'Scott',     'michael@acme.com',  2,    1,    'Sales Director',     180000, '2016-01-10'),
 (10, 'Joan',     'Holloway',  'joan@acme.com',     2,    9,    'Account Executive',   98000, '2018-03-14'),
 (11, 'Dwight',   'Schrute',   'dwight@acme.com',   2,    9,    'Account Executive',   87000, '2021-06-01'),
 (12, 'Jim',      'Halpert',   NULL,                2,    9,    'Account Executive',   87000, '2021-08-16'),
 (13, 'Oscar',    'Martinez',  'oscar@acme.com',    4,    1,    'CFO',                205000, '2015-06-30'),
 (14, 'Angela',   'Martin',    'angela@acme.com',   4,    13,   'Accountant',          78000, '2019-11-12'),
 (15, 'Roy',      'Trenneman', 'roy@acme.com',      5,    1,    'Support Lead',        82000, '2022-02-07'),
 (16, 'Maurice',  'Moss',      'moss@acme.com',     5,    15,   'Support Engineer',    76000, '2022-04-25'),
 (17, 'Sam',      'Porter',    'sam@acme.com',      NULL, 2,    'Contractor',          60000, '2023-03-01');

INSERT INTO customers VALUES
 (1,  'Northwind Traders', 'contact@northwind.com', 'Seattle',     'USA',     '2021-01-05'),
 (2,  'Contoso Ltd',       'info@contoso.com',      'London',      'UK',      '2021-02-17'),
 (3,  'Globex Corp',       'sales@globex.com',      'Springfield', 'USA',     '2021-05-23'),
 (4,  'Initech',           NULL,                    'Austin',      'USA',     '2021-08-30'),
 (5,  'Umbrella GmbH',     'kontakt@umbrella.de',   'Berlin',      'Germany', '2022-01-12'),
 (6,  'Stark Industries',  'tony@stark.com',        'New York',    'USA',     '2022-03-03'),
 (7,  'Wayne Enterprises', 'bruce@wayne.com',       'Gotham',      'USA',     '2022-06-19'),
 (8,  'Tyrell Corp',       NULL,                    'Los Angeles', 'USA',     '2022-09-09'),
 (9,  'Soylent SA',        'hello@soylent.fr',      'Paris',       'France',  '2023-02-14'),
 (10, 'Hooli',             'hr@hooli.xyz',          'Palo Alto',   'USA',     '2023-07-01'),
 (11, 'Aperture Labs',     'cave@aperture.com',     'Toronto',     'Canada',  '2024-01-20');

INSERT INTO products VALUES
 (1,  'Laptop Pro 15',               'Computers',   1899.00,  25),
 (2,  'Laptop Air 13',               'Computers',   1199.00,  40),
 (3,  'Desktop Tower',               'Computers',   1499.00,  10),
 (4,  '4K Monitor',                  'Accessories',  449.99,  60),
 (5,  'Mechanical Keyboard',         'Accessories',  129.50, 150),
 (6,  'Wireless Mouse',              'Accessories',   39.99, 300),
 (7,  'USB-C Hub',                   'Accessories',   59.00,   0),
 (8,  'Noise-Cancelling Headphones', 'Audio',        299.00,  75),
 (9,  'Bluetooth Speaker',           'Audio',         89.00, 120),
 (10, 'Office Suite License',        'Software',     249.00, 999),
 (11, 'Antivirus (1 yr)',            'Software',      49.00, 999),
 (12, 'Standing Desk',               'Furniture',    599.00,  15),
 (13, 'Ergonomic Chair',             'Furniture',    399.00,   0);

INSERT INTO orders VALUES
 (1,  1,  10,   '2023-01-15', 'delivered'),
 (2,  2,  10,   '2023-01-28', 'delivered'),
 (3,  3,  11,   '2023-02-10', 'delivered'),
 (4,  1,  10,   '2023-03-05', 'delivered'),
 (5,  5,  12,   '2023-03-22', 'cancelled'),
 (6,  6,  11,   '2023-04-18', 'delivered'),
 (7,  7,  12,   '2023-05-30', 'delivered'),
 (8,  2,  10,   '2023-06-11', 'delivered'),
 (9,  8,  11,   '2023-07-04', 'delivered'),
 (10, 9,  12,   '2023-08-19', 'delivered'),
 (11, 3,  11,   '2023-09-02', 'delivered'),
 (12, 6,  10,   '2023-10-27', 'delivered'),
 (13, 1,  12,   '2023-11-24', 'delivered'),
 (14, 4,  11,   '2023-12-15', 'cancelled'),
 (15, 7,  10,   '2024-01-09', 'delivered'),
 (16, 5,  12,   '2024-02-14', 'delivered'),
 (17, 11, 11,   '2024-03-03', 'shipped'),
 (18, 6,  10,   '2024-03-20', 'shipped'),
 (19, 2,  12,   '2024-04-01', 'pending'),
 (20, 9,  NULL, '2024-04-05', 'pending');

INSERT INTO order_items VALUES
 (1,  1,  2,  1899.00), (1,  6,  2,   39.99),
 (2,  2,  5,  1149.00), (2,  10, 5,  249.00),
 (3,  4,  3,   449.99), (3,  5,  3,  129.50),
 (4,  8,  4,   299.00),
 (5,  3,  1,  1499.00),
 (6,  1,  10, 1799.00), (6,  4,  10, 429.99), (6, 11, 10, 49.00),
 (7,  9,  6,    89.00), (7,  6,  6,   39.99),
 (8,  2,  3,  1199.00), (8,  7,  3,   59.00),
 (9,  3,  2,  1499.00), (9,  4,  4,  449.99),
 (10, 5,  8,   129.50), (10, 6,  8,   39.99),
 (11, 10, 20,  229.00),
 (12, 8,  15,  279.00), (12, 9,  5,   89.00),
 (13, 1,  1,  1899.00), (13, 13, 2,  399.00),
 (14, 2,  1,  1199.00),
 (15, 4,  2,   449.99), (15, 7,  4,   59.00),
 (16, 11, 25,   45.00), (16, 10, 25, 239.00),
 (17, 1,  3,  1899.00), (17, 5,  3,  129.50),
 (18, 2,  6,  1199.00),
 (19, 8,  2,   299.00), (19, 6,  2,   39.99),
 (20, 9,  1,    89.00);
"""

TABLE_NOTES = {
    "departments": "Company departments. Research has no employees yet.",
    "employees": "Staff. manager_id points at another employee (NULL for the CEO). "
                 "Some emails are NULL; Sam has no department.",
    "customers": "Companies that buy from Acme. Hooli has never ordered.",
    "products": "The catalogue. The Standing Desk has never been ordered.",
    "orders": "One row per order. employee_id is the sales rep (NULL for web orders).",
    "order_items": "Line items. unit_price is the price actually charged, "
                   "which can differ from products.price.",
}

_template = None


def _build_template():
    conn = sqlite3.connect(":memory:", isolation_level=None)
    conn.executescript(SCHEMA + SEED)
    return conn


def connect(sample=True):
    """Return a fresh in-memory connection, pre-loaded with the sample data.

    isolation_level=None puts the driver in autocommit mode so the learner's
    own BEGIN / COMMIT / ROLLBACK statements behave exactly as written.
    """
    global _template
    conn = sqlite3.connect(":memory:", isolation_level=None)
    if sample:
        if _template is None:
            _template = _build_template()
        _template.backup(conn)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def table_names(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def view_names(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'view' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def describe(conn, table):
    """Return (column, type, notnull, default, pk, references) tuples for a table."""
    fks = {}
    for row in conn.execute("SELECT * FROM pragma_foreign_key_list(?)", (table,)):
        # id, seq, table, from, to, on_update, on_delete, match
        fks[row[3]] = f"{row[2]}({row[4]})"
    cols = []
    for cid, name, ctype, notnull, default, pk in conn.execute(
        "SELECT * FROM pragma_table_info(?)", (table,)
    ):
        cols.append((name, ctype, bool(notnull), default, pk, fks.get(name)))
    return cols
