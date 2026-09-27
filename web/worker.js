/* Runs all SQL off the main thread, so a runaway query can be stopped by
 * terminating this worker (see Runner in app.js). */
importScripts("sql-wasm.js", "engine.js");

var engine = null;
var course = null;
var sandbox = null;

var ready = Promise.all([
  initSqlJs({ locateFile: function (file) { return file; } }),
  fetch("course.json").then(function (r) {
    if (!r.ok) throw new Error("could not load course.json (" + r.status + ")");
    return r.json();
  }),
]).then(function (loaded) {
  course = loaded[1];
  engine = new SQLEngine.Engine(loaded[0], course);
  sandbox = engine.connect();
  self.postMessage({ ready: true });
}, function (err) {
  self.postMessage({ initError: err.message });
});

function runBlocks(lesson) {
  var blocks = [];
  course.lessons[lesson].pages.forEach(function (page) {
    page.forEach(function (b) { if (b.type === "run") blocks.push(b.code); });
  });
  return blocks;
}

function attempt(db, sql) {
  try {
    return { results: SQLEngine.execute(db, sql) };
  } catch (e) {
    return { error: e.message, statement: e.statement };
  }
}

function exerciseOf(args) {
  return course.lessons[args.lesson].exercises[args.ex];
}

var handlers = {
  // Outputs of every runnable example in a lesson, executed in order on one database.
  lessonExamples: function (args) {
    var db = engine.connect();
    try {
      return runBlocks(args.lesson).map(function (sql) { return attempt(db, sql); });
    } finally {
      db.close();
    }
  },
  // Re-run one (possibly edited) example on the state its predecessors leave behind.
  runExample: function (args) {
    var db = engine.connect();
    try {
      runBlocks(args.lesson).slice(0, args.index).forEach(function (sql) { attempt(db, sql); });
      return attempt(db, args.sql);
    } finally {
      db.close();
    }
  },
  grade: function (args) { return engine.grade(exerciseOf(args), args.sql); },
  expected: function (args) { return engine.expected(exerciseOf(args)).result; },
  schema: function (args) {
    var db = engine.connect();
    try {
      if (args && args.lesson != null) {
        var ex = exerciseOf(args);
        if (ex.setup) SQLEngine.execute(db, ex.setup);
      }
      return SQLEngine.describe(db, course.tableNotes);
    } finally {
      db.close();
    }
  },
  sandboxRun: function (args) { return attempt(sandbox, args.sql); },
  sandboxReset: function () {
    sandbox.close();
    sandbox = engine.connect();
    return true;
  },
  sandboxSchema: function () { return SQLEngine.describe(sandbox, course.tableNotes); },
};

self.onmessage = function (event) {
  var msg = event.data;
  ready.then(function () {
    var result;
    try {
      result = handlers[msg.op](msg.args || {});
    } catch (e) {
      self.postMessage({ id: msg.id, error: e.message });
      return;
    }
    self.postMessage({ id: msg.id, result: result });
  });
};
