// Tests for the browser engine (web/engine.js), run with `npm test`.
// They check that the JavaScript grader agrees with the Python course content.

const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

const ROOT = path.resolve(__dirname, "..", "..");
const { Engine, execute } = require(path.join(ROOT, "web", "engine.js"));
const initSqlJs = require("sql.js");

const EXPECTED_EXAMPLE_ERRORS = new Set([
  "DELETE FROM customers WHERE id = 1;",
  "INSERT INTO reviews (product_id, rating) VALUES (1, 9);",
  "INSERT INTO reviews (product_id, rating) VALUES (999, 4);",
]);

let engine, course;

test.before(async () => {
  const out = fs.mkdtempSync(path.join(os.tmpdir(), "how-to-sql-"));
  execFileSync("python3", [path.join(ROOT, "tools", "build_web.py"), out], { stdio: "pipe" });
  course = JSON.parse(fs.readFileSync(path.join(out, "course.json"), "utf8"));
  const SQL = await initSqlJs();
  engine = new Engine(SQL, course);
});

function ex(lessonId, number) {
  return course.lessons.find((l) => l.id === lessonId).exercises[number - 1];
}

test("every reference solution passes and returns rows", () => {
  let n = 0;
  for (const lesson of course.lessons) {
    lesson.exercises.forEach((e, i) => {
      if (e.type !== "exercise") return;
      const v = engine.grade(e, e.solution);
      assert.ok(v.ok, `${lesson.id} #${i + 1}: ${v.message}`);
      assert.ok(engine.expected(e).result.rows.length > 0, `${lesson.id} #${i + 1} returns no rows`);
      n++;
    });
  }
  assert.ok(n > 40);
});

test("lesson examples run, except the deliberate error demos", () => {
  const failures = new Set();
  for (const lesson of course.lessons) {
    const db = engine.connect();
    for (const page of lesson.pages) {
      for (const block of page) {
        if (block.type !== "run") continue;
        try {
          execute(db, block.code);
        } catch (e) {
          failures.add(e.statement);
        }
      }
    }
    db.close();
  }
  assert.deepStrictEqual(failures, EXPECTED_EXAMPLE_ERRORS);
});

test("run blocks are numbered consecutively per lesson", () => {
  for (const lesson of course.lessons) {
    const idx = lesson.pages.flat().filter((b) => b.type === "run").map((b) => b.index);
    assert.deepStrictEqual(idx, idx.map((_, i) => i), lesson.id);
  }
});

test("grader feedback matches the Python grader's rules", () => {
  assert.ok(engine.grade(ex("01-intro", 3), "SELECT name AS n, city AS c FROM customers ORDER BY city").ok);

  let v = engine.grade(ex("03-order", 1), "SELECT name, price FROM products ORDER BY price");
  assert.match(v.message, /wrong order/);

  v = engine.grade(ex("01-intro", 3), "SELECT name FROM customers");
  assert.match(v.message, /Expected 2 column/);

  v = engine.grade(ex("01-intro", 3), "SELECT city, name FROM customers");
  assert.match(v.message, /different order/);

  v = engine.grade(ex("04-null", 1), "SELECT first_name, last_name FROM employees WHERE email = NULL");
  assert.ok(!v.ok);

  v = engine.grade(ex("05-expressions", 3), "SELECT first_name, ROUND(salary / 12, 2) FROM employees");
  assert.ok(!v.ok);

  v = engine.grade(ex("06-dates", 2),
    "SELECT first_name, CAST(strftime('%Y', hire_date) AS INTEGER) FROM employees");
  assert.ok(v.ok, v.message);

  v = engine.grade(ex("03-order", 6), "SELECT name, price * 0.9 FROM products WHERE category = 'Audio'");
  assert.match(v.message, /Column names/);

  v = engine.grade(ex("01-intro", 1), "SELEC * FROM products");
  assert.match(v.message, /^Error: .*syntax error/);

  v = engine.grade(ex("13-modifying-data", 2), "UPDATE employees SET salary = salary * 1.10;");
  assert.ok(!v.ok);

  v = engine.grade(ex("14-tables-constraints", 3),
    "CREATE TABLE ratings (id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL " +
    "REFERENCES products(id), stars INTEGER NOT NULL);");
  assert.match(v.message, /rejected/);

  v = engine.grade(ex("09-subqueries", 4),
    "SELECT first_name FROM employees WHERE id NOT IN " +
    "(SELECT manager_id FROM employees WHERE manager_id IS NOT NULL)");
  assert.ok(v.ok, v.message);

  v = engine.grade(ex("01-intro", 1), "SELECT 1;");
  assert.strictEqual(v.expected.rows.length, 13);
});

test("statement splitting handles strings, comments and triggers", () => {
  const db = engine.connect(false);
  let r = execute(db, "SELECT 'a;b'; -- c;d\nSELECT 2; /* x; */");
  assert.deepStrictEqual(r.map((x) => x.rows[0][0]), ["a;b", 2]);
  r = execute(db,
    "CREATE TABLE a(x); CREATE TABLE b(y); CREATE TRIGGER t AFTER INSERT ON a BEGIN " +
    "INSERT INTO b VALUES (1); INSERT INTO b VALUES (2); END; INSERT INTO a VALUES (0); " +
    "SELECT COUNT(*) FROM b");
  assert.strictEqual(r[r.length - 1].rows[0][0], 2);
  assert.strictEqual(execute(db, "-- only a comment").length, 0);
  assert.throws(() => execute(db, "SELECT 1; SELEC 2"), /syntax error/);
  db.close();
});

test("fresh connections are isolated and enforce foreign keys", () => {
  const a = engine.connect();
  a.exec("DELETE FROM order_items");
  const b = engine.connect();
  assert.strictEqual(execute(b, "SELECT COUNT(*) FROM order_items")[0].rows[0][0], 35);
  assert.throws(() => execute(b, "DELETE FROM customers WHERE id = 1"), /FOREIGN KEY/);
  a.close();
  b.close();
});
