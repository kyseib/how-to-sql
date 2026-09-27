/* SQL execution and grading for the browser build.
 *
 * A port of sql_tutor/engine.py and sql_tutor/checker.py on top of sql.js.
 * Loaded by worker.js (importScripts) and by the Node tests (require).
 */
(function (root) {
  "use strict";

  var MAX_ROWS = 5000;
  var NUMBER = /^-?\d+(\.\d+)?$/;

  function SQLError(message, statement) {
    var err = new Error(message);
    err.name = "SQLError";
    err.statement = statement || "";
    return err;
  }

  // ── Databases ──────────────────────────────────────────────────────────

  function Engine(SQL, course) {
    this.SQL = SQL;
    this.course = course;
    var template = new SQL.Database();
    template.exec(course.schema + course.seed);
    this.template = template.export();
    template.close();
  }

  Engine.prototype.connect = function (sample) {
    var db = sample === false ? new this.SQL.Database() : new this.SQL.Database(this.template);
    db.exec("PRAGMA foreign_keys = ON");
    return db;
  };

  // ── Execution ──────────────────────────────────────────────────────────

  function firstLine(text) {
    return String(text || "").trim().split("\n")[0];
  }

  /* Run every statement in `sql`; return [{statement, columns, rows, rowcount, truncated}].
   * Throws SQLError on the first failure (earlier statements stay applied). */
  function execute(db, sql) {
    var results = [];
    var it = db.iterateStatements(sql);
    for (;;) {
      var next;
      var remaining = it.getRemainingSQL();
      try {
        next = it.next();
      } catch (e) {
        throw SQLError(e.message, firstLine(remaining));
      }
      if (next.done) break;
      var stmt = next.value;
      var text = stmt.getSQL().trim();
      try {
        var columns = stmt.getColumnNames();
        var rows = [];
        var truncated = false;
        while (stmt.step()) {
          if (rows.length === MAX_ROWS) { truncated = true; break; }
          rows.push(stmt.get());
        }
        if (columns.length) {
          results.push({ statement: text, columns: columns, rows: rows, rowcount: rows.length,
                         truncated: truncated });
        } else {
          results.push({ statement: text, columns: [], rows: [], rowcount: db.getRowsModified(),
                         truncated: false });
        }
      } catch (e) {
        throw SQLError(e.message, text);
      }
    }
    return results;
  }

  function lastQuery(results) {
    for (var i = results.length - 1; i >= 0; i--) {
      if (results[i].columns.length) return results[i];
    }
    return null;
  }

  // ── Comparing results ──────────────────────────────────────────────────

  function normValue(v) {
    if (typeof v === "string" && NUMBER.test(v.trim())) v = Number(v);
    if (typeof v === "number") {
      v = Math.round(v * 100) / 100;
      if (v === 0) v = 0; // fold -0
    }
    if (v instanceof Uint8Array) v = "blob:" + Array.prototype.join.call(v, ",");
    return v;
  }

  function normRow(row) { return row.map(normValue); }
  function key(row) { return JSON.stringify(row); }

  function counts(rows) {
    var m = new Map();
    rows.forEach(function (r) { var k = key(r); m.set(k, (m.get(k) || 0) + 1); });
    return m;
  }

  function sameCounts(a, b) {
    if (a.size !== b.size) return false;
    for (var entry of a) { if (b.get(entry[0]) !== entry[1]) return false; }
    return true;
  }

  function valueOrder(x, y) {
    var kx = [x === null ? 1 : 0, typeof x], ky = [y === null ? 1 : 0, typeof y];
    if (kx[0] !== ky[0]) return kx[0] - ky[0];
    if (kx[1] !== ky[1]) return kx[1] < ky[1] ? -1 : 1;
    if (x === null) return 0;
    return x < y ? -1 : x > y ? 1 : 0;
  }

  function fmtValue(v) {
    if (v === null) return "NULL";
    return typeof v === "string" ? "'" + v + "'" : String(v);
  }

  function compare(actual, expected, ordered, checkNames) {
    if (!actual) return [false, "No result set was produced."];
    var na = actual.columns.length, ne = expected.columns.length;
    if (na !== ne) {
      return [false, "Expected " + ne + " column(s) but got " + na + ". Expected columns: " +
                     expected.columns.join(", ")];
    }
    if (checkNames) {
      var want = expected.columns.map(function (c) { return c.toLowerCase(); }).join("|");
      var got = actual.columns.map(function (c) { return c.toLowerCase(); }).join("|");
      if (want !== got) {
        return [false, "Column names should be: " + expected.columns.join(", ") + " (yours: " +
                       actual.columns.join(", ") + "). Use AS to name them."];
      }
    }
    var aRows = actual.rows.map(normRow), eRows = expected.rows.map(normRow);
    if (aRows.length !== eRows.length) {
      return [false, "Expected " + eRows.length + " row(s) but got " + aRows.length + "."];
    }
    var ca = counts(aRows), ce = counts(eRows);
    if (!sameCounts(ca, ce)) {
      var sortRow = function (r) { return r.slice().sort(valueOrder); };
      if (sameCounts(counts(aRows.map(sortRow)), counts(eRows.map(sortRow)))) {
        return [false, "The right values, but the columns are in a different order. Expected: " +
                       expected.columns.join(", ")];
      }
      var missing = null;
      for (var entry of ce) {
        if ((ca.get(entry[0]) || 0) < entry[1]) { missing = JSON.parse(entry[0]); break; }
      }
      return [false, "The rows don't match. For example, this expected row is missing:\n  (" +
                     missing.map(fmtValue).join(", ") + ")"];
    }
    if (ordered) {
      for (var i = 0; i < aRows.length; i++) {
        if (key(aRows[i]) !== key(eRows[i])) {
          return [false, "The right rows, but in the wrong order. Check your ORDER BY."];
        }
      }
    }
    return [true, ""];
  }

  // ── Grading ────────────────────────────────────────────────────────────

  Engine.prototype.runOutcome = function (ex, sql) {
    var db = this.connect();
    try {
      if (ex.setup) execute(db, ex.setup);
      var shown = lastQuery(execute(db, sql));
      if (!ex.check) return { result: shown, probes: [], shown: shown };
      try { db.exec("COMMIT"); } catch (e) { /* no transaction was open */ }
      var probes = ex.probes.map(function (probe) {
        try { execute(db, probe); return "ok"; } catch (e) { return e.message; }
      });
      return { result: lastQuery(execute(db, ex.check)), probes: probes, shown: shown };
    } finally {
      db.close();
    }
  };

  Engine.prototype.expected = function (ex) {
    return this.runOutcome(ex, ex.solution);
  };

  Engine.prototype.grade = function (ex, sql) {
    var expected, actual;
    try {
      expected = this.expected(ex);
    } catch (e) {
      return { ok: false, message: "(course bug) reference solution failed: " + e.message };
    }
    try {
      actual = this.runOutcome(ex, sql);
    } catch (e) {
      return { ok: false, message: "Error: " + e.message, expected: expected.result };
    }

    if (ex.check) {
      for (var i = 0; i < ex.probes.length; i++) {
        var probe = firstLine(ex.probes[i]), want = expected.probes[i], got = actual.probes[i];
        if (want === "ok" && got !== "ok") {
          return { ok: false, actual: actual.shown, expected: expected.result,
                   message: "This statement should succeed against your schema but failed:\n  " +
                            probe + "\n  → " + got };
        }
        if (want !== "ok" && got === "ok") {
          return { ok: false, actual: actual.shown, expected: expected.result,
                   message: "This statement should be rejected by your schema but was accepted:\n  " +
                            probe };
        }
      }
      var cmp = compare(actual.result, expected.result, ex.ordered, ex.checkNames);
      if (cmp[0]) {
        return { ok: true, message: "Correct! The database ended up in the expected state.",
                 actual: actual.shown, expected: expected.result };
      }
      return { ok: false, actual: actual.result, expected: expected.result,
               message: "The database is not in the expected state afterwards.\nChecked with: " +
                        ex.check.trim() + "\n" + cmp[1] };
    }

    if (!actual.result) {
      return { ok: false, expected: expected.result,
               message: "Your SQL ran but returned no result set. This exercise expects a query (SELECT ...)." };
    }
    var c = compare(actual.result, expected.result, ex.ordered, ex.checkNames);
    return { ok: c[0], message: c[0] ? "Correct!" : c[1], actual: actual.result,
             expected: expected.result };
  };

  // ── Schema description ────────────────────────────────────────────────

  function queryRows(db, sql, params) {
    var stmt = db.prepare(sql);
    var rows = [];
    try {
      if (params) stmt.bind(params);
      while (stmt.step()) rows.push(stmt.get());
    } finally {
      stmt.free();
    }
    return rows;
  }

  function describe(db, notes) {
    var objects = queryRows(db,
      "SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view') " +
      "AND name NOT LIKE 'sqlite_%' ORDER BY type, name");
    return objects.map(function (o) {
      var name = o[0];
      var fks = {};
      queryRows(db, "SELECT \"from\", \"table\", \"to\" FROM pragma_foreign_key_list(?)", [name])
        .forEach(function (r) { fks[r[0]] = r[1] + "(" + r[2] + ")"; });
      var cols = queryRows(db, "SELECT name, type, \"notnull\", dflt_value, pk FROM pragma_table_info(?)", [name]);
      var composite = cols.filter(function (c) { return c[4]; }).length > 1;
      var count = queryRows(db, "SELECT COUNT(*) FROM \"" + name.replace(/"/g, '""') + "\"")[0][0];
      return {
        name: name,
        kind: o[1],
        rows: count,
        note: (notes && notes[name]) || "",
        columns: cols.map(function (c) {
          var flags = [];
          if (c[4]) flags.push(composite ? "PRIMARY KEY (part " + c[4] + ")" : "PRIMARY KEY");
          if (c[2]) flags.push("NOT NULL");
          if (c[3] !== null) flags.push("DEFAULT " + c[3]);
          if (fks[c[0]]) flags.push("→ " + fks[c[0]]);
          return { name: c[0], type: c[1] || "", flags: flags.join(" ") };
        }),
      };
    });
  }

  var api = {
    Engine: Engine,
    execute: execute,
    lastQuery: lastQuery,
    compare: compare,
    describe: describe,
    MAX_ROWS: MAX_ROWS,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.SQLEngine = api;
})(typeof self !== "undefined" ? self : this);
