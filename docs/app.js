/* How to SQL — browser UI. All SQL runs in worker.js (sql.js / SQLite WASM). */
(function () {
  "use strict";

  var TIMEOUT_MS = 5000;
  var DISPLAY_ROWS = 200;
  var STORAGE_KEY = "how-to-sql-progress";

  var course = null;
  var main = document.getElementById("main");
  var sidebar = document.getElementById("sidebar");

  // ── DOM helper ─────────────────────────────────────────────────────────

  function h(tag, attrs) {
    var el = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        var v = attrs[k];
        if (v == null || v === false) return;
        if (k === "class") el.className = v;
        else if (k === "html") el.innerHTML = v;
        else if (k === "text") el.textContent = v;
        else if (k.slice(0, 2) === "on") el.addEventListener(k.slice(2), v);
        else el.setAttribute(k, v === true ? "" : v);
      });
    }
    for (var i = 2; i < arguments.length; i++) append(el, arguments[i]);
    return el;
  }

  function append(el, child) {
    if (child == null || child === false) return;
    if (Array.isArray(child)) child.forEach(function (c) { append(el, c); });
    else el.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
  }

  function escapeHtml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  // ── SQL highlighting ───────────────────────────────────────────────────

  var KEYWORDS = new Set((
    "ABORT ACTION ADD AFTER ALL ALTER ALWAYS ANALYZE AND AS ASC AUTOINCREMENT BEFORE BEGIN " +
    "BETWEEN BY CASCADE CASE CAST CHECK COLLATE COLUMN COMMIT CONFLICT CONSTRAINT CREATE " +
    "CROSS CURRENT CURRENT_DATE CURRENT_TIME CURRENT_TIMESTAMP DEFAULT DEFERRABLE DEFERRED " +
    "DELETE DESC DISTINCT DO DROP EACH ELSE END ESCAPE EXCEPT EXCLUDE EXISTS EXPLAIN FILTER " +
    "FIRST FOLLOWING FOR FOREIGN FROM FULL GLOB GROUP GROUPS HAVING IF IGNORE IMMEDIATE IN " +
    "INDEX INNER INSERT INSTEAD INTERSECT INTO IS ISNULL JOIN KEY LAST LEFT LIKE LIMIT " +
    "MATERIALIZED NATURAL NO NOT NOTHING NOTNULL NULL NULLS OF OFFSET ON OR ORDER OTHERS " +
    "OUTER OVER PARTITION PLAN PRAGMA PRECEDING PRIMARY QUERY RAISE RANGE RECURSIVE " +
    "REFERENCES REINDEX RELEASE RENAME REPLACE RESTRICT RETURNING RIGHT ROLLBACK ROW ROWS " +
    "SAVEPOINT SELECT SET STRICT TABLE TEMP TEMPORARY THEN TIES TO TRANSACTION TRIGGER " +
    "UNBOUNDED UNION UNIQUE UPDATE USING VACUUM VALUES VIEW WHEN WHERE WINDOW WITH WITHOUT " +
    "TRUE FALSE INTEGER TEXT REAL BLOB NUMERIC"
  ).split(" "));

  var TOKEN = /(--[^\n]*|\/\*[\s\S]*?(?:\*\/|$))|('(?:[^']|'')*'?)|("(?:[^"]|"")*"?)|(\b\d+(?:\.\d+)?\b)|(\b[A-Za-z_][A-Za-z0-9_]*\b)/g;

  function highlight(sql) {
    var out = "", last = 0, m;
    TOKEN.lastIndex = 0;
    while ((m = TOKEN.exec(sql))) {
      out += escapeHtml(sql.slice(last, m.index));
      var t = escapeHtml(m[0]);
      if (m[1]) out += '<span class="tok-cmt">' + t + "</span>";
      else if (m[2]) out += '<span class="tok-str">' + t + "</span>";
      else if (m[4]) out += '<span class="tok-num">' + t + "</span>";
      else if (m[5] && KEYWORDS.has(m[5].toUpperCase())) out += '<span class="tok-kw">' + t + "</span>";
      else out += t;
      last = TOKEN.lastIndex;
    }
    return out + escapeHtml(sql.slice(last));
  }

  function codeBlock(sql) {
    return h("pre", { class: "sql", html: highlight(sql) });
  }

  // ── Editor: a textarea over a highlighted <pre> ────────────────────────

  function createEditor(value, opts) {
    opts = opts || {};
    var pre = h("pre", { "aria-hidden": "true" });
    var ta = h("textarea", {
      spellcheck: "false", autocapitalize: "off", autocomplete: "off",
      "aria-label": opts.label || "SQL editor",
      placeholder: opts.placeholder || "",
      rows: String(opts.rows || 5),
    });
    ta.value = value || "";
    var el = h("div", { class: "editor" }, pre, ta);

    function sync() {
      // Trailing newline keeps the overlay height in step with the textarea.
      pre.innerHTML = highlight(ta.value) + "\n";
      pre.scrollTop = ta.scrollTop;
      pre.scrollLeft = ta.scrollLeft;
      if (opts.onChange) opts.onChange(ta.value);
    }
    ta.addEventListener("input", sync);
    ta.addEventListener("scroll", function () {
      pre.scrollTop = ta.scrollTop;
      pre.scrollLeft = ta.scrollLeft;
    });
    ta.addEventListener("keydown", function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        if (opts.onRun) opts.onRun();
      } else if (e.key === "Tab" && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        var s = ta.selectionStart, end = ta.selectionEnd;
        ta.value = ta.value.slice(0, s) + "  " + ta.value.slice(end);
        ta.selectionStart = ta.selectionEnd = s + 2;
        sync();
      }
    });
    sync();
    return {
      el: el,
      get value() { return ta.value; },
      set value(v) { ta.value = v; sync(); },
      focus: function () { ta.focus(); },
    };
  }

  var KBD = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent) ? "⌘ Enter" : "Ctrl Enter";

  // ── Result rendering ───────────────────────────────────────────────────

  function cellText(v) {
    if (v === null) return "NULL";
    if (v instanceof Uint8Array) return "<" + v.length + " bytes>";
    if (typeof v === "number" && !Number.isInteger(v)) return String(Math.round(v * 1e6) / 1e6);
    return String(v);
  }

  function renderTable(result) {
    if (!result) return null;
    if (!result.columns.length) {
      var n = result.rowcount;
      return h("div", { class: "status-line",
        text: n > 0 ? "OK — " + n + " row" + (n === 1 ? "" : "s") + " affected" : "OK" });
    }
    var rows = result.rows.slice(0, DISPLAY_ROWS);
    var numeric = result.columns.map(function (_, i) {
      return rows.length > 0 && rows.every(function (r) { return r[i] === null || typeof r[i] === "number"; });
    });
    var table = h("table", { class: "result" },
      h("thead", null, h("tr", null, result.columns.map(function (c) { return h("th", { text: c, title: c }); }))),
      h("tbody", null, rows.map(function (r) {
        return h("tr", null, r.map(function (v, i) {
          var text = cellText(v);
          return h("td", { class: v === null ? "null" : numeric[i] ? "num" : null, text: text,
                           title: text.length > 40 ? text : null });
        }));
      })));
    var total = result.rows.length;
    var meta = total + (result.truncated ? "+" : "") + " row" + (total === 1 ? "" : "s") +
      (total > DISPLAY_ROWS ? " (showing first " + DISPLAY_ROWS + ")" : "");
    return h("div", null, h("div", { class: "table-wrap" }, table), h("div", { class: "result-meta", text: meta }));
  }

  function renderOutcome(outcome) {
    if (outcome.error) {
      return h("div", { class: "verdict err", text: "Error: " + outcome.error });
    }
    var queries = outcome.results.filter(function (r) { return r.columns.length; });
    if (queries.length) return h("div", null, queries.map(renderTable));
    if (outcome.results.length) return renderTable(outcome.results[outcome.results.length - 1]);
    return h("div", { class: "status-line", text: "Nothing to run." });
  }

  function renderSchema(tables) {
    return h("div", null, tables.map(function (t) {
      return h("div", { class: "panel schema-card" },
        h("h3", null, t.name + " ", h("span", { class: "muted", text: "(" + t.kind + ", " + t.rows + " rows)" })),
        t.note ? h("div", { class: "note", text: t.note }) : null,
        h("table", { class: "schema-cols" }, h("tbody", null, t.columns.map(function (c) {
          return h("tr", null, h("td", { text: c.name }), h("td", { text: c.type }), h("td", { text: c.flags }));
        }))));
    }));
  }

  // ── Worker with a watchdog ─────────────────────────────────────────────

  var Runner = {
    worker: null,
    ready: null,
    pending: {},
    seq: 0,
    restarted: 0,

    start: function () {
      var self = this;
      this.worker = new Worker("worker.js");
      this.ready = new Promise(function (resolve, reject) {
        self.worker.onmessage = function (e) {
          var msg = e.data;
          if (msg.ready) { resolve(); return; }
          if (msg.initError) { reject(new Error(msg.initError)); return; }
          var p = self.pending[msg.id];
          if (!p) return;
          delete self.pending[msg.id];
          clearTimeout(p.timer);
          if (msg.error) p.reject(new Error(msg.error));
          else p.resolve(msg.result);
        };
        self.worker.onerror = function (e) { reject(new Error(e.message || "worker failed to start")); };
      });
    },

    call: function (op, args) {
      var self = this;
      return this.ready.then(function () {
        return new Promise(function (resolve, reject) {
          var id = ++self.seq;
          var timer = setTimeout(function () {
            delete self.pending[id];
            self.restart();
            var err = new Error("Query cancelled after " + TIMEOUT_MS / 1000 +
              " seconds (is a recursive CTE missing its stop condition?)");
            err.timeout = true;
            reject(err);
          }, TIMEOUT_MS);
          self.pending[id] = { resolve: resolve, reject: reject, timer: timer };
          self.worker.postMessage({ id: id, op: op, args: args });
        });
      });
    },

    restart: function () {
      this.worker.terminate();
      var pending = this.pending;
      this.pending = {};
      Object.keys(pending).forEach(function (id) {
        clearTimeout(pending[id].timer);
        pending[id].reject(new Error("cancelled"));
      });
      this.restarted++;
      this.start();
    },
  };

  // Examples/sandbox helpers: turn a timeout into an error outcome.
  function run(op, args) {
    return Runner.call(op, args).catch(function (e) { return { error: e.message, timeout: e.timeout }; });
  }

  // ── Progress (localStorage; the page works without it) ──────────────────

  var progress = { done: new Set(), revealed: new Set() };

  function loadProgress() {
    try {
      var data = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
      progress.done = new Set(data.done || []);
      progress.revealed = new Set(data.revealed || []);
    } catch (e) { /* storage unavailable */ }
  }

  function saveProgress() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        done: Array.from(progress.done), revealed: Array.from(progress.revealed),
      }));
    } catch (e) { /* storage unavailable */ }
    renderSidebar();
  }

  var drafts = {};
  function loadDrafts() {
    try { drafts = JSON.parse(sessionStorage.getItem("how-to-sql-drafts") || "{}"); } catch (e) { drafts = {}; }
  }
  function saveDraft(id, value) {
    drafts[id] = value;
    try { sessionStorage.setItem("how-to-sql-drafts", JSON.stringify(drafts)); } catch (e) { /* ignore */ }
  }

  function exId(lesson, i) { return lesson.id + "#" + (i + 1); }

  function lessonCounts(lesson) {
    var got = 0;
    lesson.exercises.forEach(function (_, i) { if (progress.done.has(exId(lesson, i))) got++; });
    return [got, lesson.exercises.length];
  }

  function totalCounts() {
    var got = 0, total = 0;
    course.lessons.forEach(function (l) { var c = lessonCounts(l); got += c[0]; total += c[1]; });
    return [got, total];
  }

  function nextLessonIndex() {
    for (var i = 0; i < course.lessons.length; i++) {
      var c = lessonCounts(course.lessons[i]);
      if (c[0] < c[1]) return i;
    }
    return course.lessons.length - 1;
  }

  function firstOpenExercise(lesson) {
    for (var i = 0; i < lesson.exercises.length; i++) {
      if (!progress.done.has(exId(lesson, i))) return i;
    }
    return 0;
  }

  // ── Routing ────────────────────────────────────────────────────────────
  //   #/                           home
  //   #/lesson/3/2                 lesson 3, page 2
  //   #/lesson/3/exercise/4        lesson 3, exercise 4
  //   #/lesson/3/done              lesson summary
  //   #/sandbox  #/database  #/reference

  function go(hash) { location.hash = hash; }

  function parseRoute() {
    var parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
    if (parts[0] === "lesson") {
      var n = parseInt(parts[1], 10);
      if (n >= 1 && n <= course.lessons.length) {
        if (parts[2] === "exercise") {
          var k = parseInt(parts[3], 10) || 1;
          return { view: "exercise", lesson: n - 1, ex: Math.min(Math.max(k, 1), course.lessons[n - 1].exercises.length) - 1 };
        }
        if (parts[2] === "done") return { view: "done", lesson: n - 1 };
        var p = parseInt(parts[2], 10) || 1;
        return { view: "page", lesson: n - 1, page: Math.min(Math.max(p, 1), course.lessons[n - 1].pages.length) - 1 };
      }
    }
    if (parts[0] === "sandbox" || parts[0] === "database" || parts[0] === "reference") return { view: parts[0] };
    return { view: "home" };
  }

  var route = { view: "home" };

  function render() {
    route = parseRoute();
    document.body.classList.remove("nav-open");
    document.getElementById("menu-toggle").setAttribute("aria-expanded", "false");
    main.innerHTML = "";
    var view = {
      home: viewHome, page: viewPage, exercise: viewExercise, done: viewDone,
      sandbox: viewSandbox, database: viewDatabase, reference: viewReference,
    }[route.view];
    view(route);
    renderSidebar();
    window.scrollTo(0, 0);
    main.focus({ preventScroll: true });
  }

  function setTitle(t) { document.title = t ? t + " · How to SQL" : "How to SQL"; }

  // ── Sidebar ────────────────────────────────────────────────────────────

  function renderSidebar() {
    var c = totalCounts();
    document.getElementById("progress-summary").textContent = c[0] + " / " + c[1] + " exercises";
    sidebar.innerHTML = "";
    var current = route.lesson;
    append(sidebar, [
      h("a", { class: "nav-link" + (route.view === "home" ? " active" : ""), href: "#/" },
        h("span", { class: "nav-title", text: "Home" })),
      h("div", { class: "nav-section", text: "Lessons" }),
      course.lessons.map(function (l, i) {
        var cnt = lessonCounts(l);
        var complete = cnt[0] === cnt[1];
        return h("a", { class: "nav-link" + (i === current ? " active" : ""), href: "#/lesson/" + (i + 1) },
          h("span", { class: "nav-num", text: String(i + 1) }),
          h("span", { class: "nav-title", text: l.title }),
          h("span", { class: "nav-count" + (complete ? " complete" : ""), text: complete ? "✓" : cnt[0] + "/" + cnt[1] }));
      }),
      h("div", { class: "nav-section", text: "Tools" }),
      [["sandbox", "Sandbox"], ["database", "Sample database"], ["reference", "Cheat sheet"]].map(function (t) {
        return h("a", { class: "nav-link" + (route.view === t[0] ? " active" : ""), href: "#/" + t[0] },
          h("span", { class: "nav-title", text: t[1] }));
      }),
    ]);
  }

  // ── Home ───────────────────────────────────────────────────────────────

  function viewHome() {
    setTitle("");
    var c = totalCounts();
    var next = nextLessonIndex();
    append(main, [
      h("div", { class: "hero" },
        h("h1", { text: "How to SQL" }),
        h("p", { class: "lead", text: "An interactive SQL course. Every example and exercise runs on a real SQLite database inside your browser — nothing to install, nothing sent to a server." }),
        h("p", null, "21 lessons take you from your first ", h("code", { text: "SELECT" }),
          " through joins, window functions, transactions, indexing, database design and security. Each lesson ends with exercises that are checked automatically."),
        h("div", { class: "btn-row" },
          h("a", { class: "btn primary", href: "#/lesson/" + (next + 1) + (c[0] ? "/exercise/" + (firstOpenExercise(course.lessons[next]) + 1) : "") },
            c[0] ? "Continue: lesson " + (next + 1) : "Start lesson 1"),
          h("a", { class: "btn", href: "#/sandbox", text: "Open the sandbox" }),
          h("span", { class: "muted", text: c[0] + " of " + c[1] + " exercises complete" }))),
      h("div", { class: "lesson-grid" }, course.lessons.map(function (l, i) {
        var cnt = lessonCounts(l);
        return h("a", { class: "lesson-card", href: "#/lesson/" + (i + 1) },
          h("span", { class: "num", text: "Lesson " + (i + 1) }),
          h("span", { class: "title", text: l.title }),
          h("span", { class: "summary", text: l.summary }),
          h("div", { class: "bar", title: cnt[0] + " of " + cnt[1] + " done" },
            h("span", { style: "width:" + (cnt[1] ? 100 * cnt[0] / cnt[1] : 0) + "%" })));
      })),
      h("p", { class: "muted" }, "Progress is saved in this browser. ",
        h("button", { class: "btn small", onclick: function () {
          if (confirm("Erase all progress in this browser?")) {
            progress.done.clear();
            progress.revealed.clear();
            saveProgress();
            render();
          }
        } }, "Reset progress")),
    ]);
  }

  // ── Lesson pages ───────────────────────────────────────────────────────

  var exampleCache = {};  // lesson index -> Promise of outcomes

  function lessonExamples(lessonIndex) {
    if (!exampleCache[lessonIndex]) {
      exampleCache[lessonIndex] = run("lessonExamples", { lesson: lessonIndex }).then(function (res) {
        if (!Array.isArray(res)) { delete exampleCache[lessonIndex]; return []; }
        return res;
      });
    }
    return exampleCache[lessonIndex];
  }

  function stepsNav(lessonIndex, activePage, activeEx) {
    var lesson = course.lessons[lessonIndex];
    var base = "#/lesson/" + (lessonIndex + 1);
    return h("nav", { class: "steps", "aria-label": "Lesson sections" },
      lesson.pages.map(function (_, i) {
        return h("a", { class: "step" + (i === activePage ? " current" : ""), href: base + "/" + (i + 1),
                        title: "Page " + (i + 1), "aria-current": i === activePage ? "page" : null }, String(i + 1));
      }),
      lesson.exercises.map(function (ex, i) {
        var done = progress.done.has(exId(lesson, i));
        return h("a", { class: "step" + (i === activeEx ? " current" : "") + (done ? " done" : ""),
                        href: base + "/exercise/" + (i + 1), "aria-current": i === activeEx ? "page" : null,
                        title: (ex.type === "quiz" ? "Quiz " : "Exercise ") + (i + 1) + (done ? " (done)" : "") },
                 (ex.type === "quiz" ? "Q" : "E") + (i + 1));
      }));
  }

  function lessonHeader(lessonIndex, activePage, activeEx) {
    var lesson = course.lessons[lessonIndex];
    return [
      h("div", { class: "eyebrow", text: "Lesson " + (lessonIndex + 1) + " of " + course.lessons.length }),
      h("h1", { text: lesson.title }),
      h("p", { class: "lead", text: lesson.summary }),
      stepsNav(lessonIndex, activePage, activeEx),
    ];
  }

  function renderBlocks(blocks, lessonIndex) {
    return blocks.map(function (b) {
      if (b.type === "html") return h("div", { class: "block", html: b.html });
      if (b.type === "sql") return codeBlock(b.code);
      if (b.type === "code") return h("pre", { class: "plain", text: b.code });
      return exampleBlock(b, lessonIndex);
    });
  }

  function exampleBlock(block, lessonIndex) {
    var output = h("div", { class: "example-output", "aria-live": "polite" },
      h("span", { class: "muted", text: "Running…" }));
    var codeHolder = h("div", null, codeBlock(block.code));
    var editor = null;
    var editBtn, runBtn, resetBtn;

    function show(outcome) {
      output.innerHTML = "";
      append(output, renderOutcome(outcome));
    }

    function runEdited() {
      runBtn.disabled = true;
      run("runExample", { lesson: lessonIndex, index: block.index, sql: editor.value }).then(function (o) {
        runBtn.disabled = false;
        show(o);
      });
    }

    editBtn = h("button", { class: "btn small", onclick: function () {
      editor = createEditor(block.code, { onRun: runEdited, rows: Math.min(block.code.split("\n").length + 1, 14),
                                          label: "Edit example" });
      codeHolder.innerHTML = "";
      codeHolder.appendChild(editor.el);
      editBtn.hidden = true;
      runBtn.hidden = false;
      resetBtn.hidden = false;
      editor.focus();
    } }, "Edit & run");
    runBtn = h("button", { class: "btn small primary", hidden: true, onclick: runEdited, title: KBD }, "Run");
    resetBtn = h("button", { class: "btn small", hidden: true, onclick: function () {
      editor = null;
      codeHolder.innerHTML = "";
      codeHolder.appendChild(codeBlock(block.code));
      editBtn.hidden = false;
      runBtn.hidden = true;
      resetBtn.hidden = true;
      lessonExamples(lessonIndex).then(function (all) { if (all[block.index]) show(all[block.index]); });
    } }, "Reset");

    lessonExamples(lessonIndex).then(function (all) {
      if (!editor && all[block.index]) show(all[block.index]);
      else if (!editor) show({ error: "could not run this example" });
    });

    return h("div", { class: "example" }, codeHolder,
      h("div", { class: "example-bar" }, resetBtn, editBtn, runBtn), output);
  }

  function viewPage(r) {
    var lesson = course.lessons[r.lesson];
    var last = r.page === lesson.pages.length - 1;
    var base = "#/lesson/" + (r.lesson + 1);
    setTitle(lesson.title);
    append(main, [
      lessonHeader(r.lesson, r.page, -1),
      h("article", { class: "page" }, renderBlocks(lesson.pages[r.page], r.lesson)),
      h("div", { class: "pager" },
        r.page > 0
          ? h("a", { class: "btn", href: base + "/" + r.page }, "← Previous")
          : r.lesson > 0
            ? h("a", { class: "btn", href: "#/lesson/" + r.lesson }, "← Lesson " + r.lesson)
            : h("span"),
        last
          ? h("a", { class: "btn primary", href: base + "/exercise/" + (firstOpenExercise(lesson) + 1) }, "Exercises →")
          : h("a", { class: "btn primary", href: base + "/" + (r.page + 2) }, "Next →")),
    ]);
  }

  // ── Exercises ──────────────────────────────────────────────────────────

  function exercisePager(r) {
    var lesson = course.lessons[r.lesson];
    var base = "#/lesson/" + (r.lesson + 1);
    var isLast = r.ex === lesson.exercises.length - 1;
    return h("div", { class: "pager" },
      r.ex > 0
        ? h("a", { class: "btn", href: base + "/exercise/" + r.ex }, "← Previous")
        : h("a", { class: "btn", href: base + "/" + lesson.pages.length }, "← Lesson text"),
      h("a", { class: "btn", href: isLast ? base + "/done" : base + "/exercise/" + (r.ex + 2) },
        isLast ? "Finish lesson →" : "Skip →"));
  }

  function nextHref(r) {
    var lesson = course.lessons[r.lesson];
    var base = "#/lesson/" + (r.lesson + 1);
    return r.ex === lesson.exercises.length - 1 ? base + "/done" : base + "/exercise/" + (r.ex + 2);
  }

  function viewExercise(r) {
    var lesson = course.lessons[r.lesson];
    var ex = lesson.exercises[r.ex];
    setTitle(lesson.title);
    append(main, lessonHeader(r.lesson, -1, r.ex));
    if (ex.type === "quiz") viewQuiz(r, lesson, ex);
    else viewSqlExercise(r, lesson, ex);
    append(main, exercisePager(r));
  }

  function normSql(s) { return s.toLowerCase().replace(/;/g, " ").split(/\s+/).filter(Boolean).join(" "); }

  function viewSqlExercise(r, lesson, ex) {
    var id = exId(lesson, r.ex);
    var hintsShown = 0;
    var output = h("div", { "aria-live": "polite" });
    var extras = h("div");
    var hintBox = h("div");
    var busy = false;

    var editor = createEditor(drafts[id] || "", {
      rows: 7, onRun: submit, label: "Your SQL",
      placeholder: "Write your SQL here, then press Run (" + KBD + ")",
      onChange: function (v) { saveDraft(id, v); },
    });

    function panel(title, content, cls) {
      return h("div", { class: "panel" + (cls ? " " + cls : "") }, h("h3", { text: title }), content);
    }

    function submit() {
      if (busy) return;
      var sql = editor.value;
      if (!sql.trim()) { editor.focus(); return; }
      busy = true;
      runButton.disabled = true;
      output.innerHTML = "";
      append(output, h("p", { class: "muted", text: "Checking…" }));
      Runner.call("grade", { lesson: r.lesson, ex: r.ex, sql: sql }).then(showVerdict, function (e) {
        showVerdict({ ok: false, message: "Error: " + e.message });
      }).then(function () {
        busy = false;
        runButton.disabled = false;
      });
    }

    function showVerdict(v) {
      output.innerHTML = "";
      if (v.ok) {
        progress.done.add(id);
        saveProgress();
        var box = h("div", { class: "verdict ok", role: "status" }, v.message);
        if (ex.explanation) append(box, h("span", { class: "note", html: ex.explanation }));
        if (progress.revealed.has(id)) append(box, h("span", { class: "note", text: "You revealed the solution for this one — try it again from memory later." }));
        var nextBtn = h("a", { class: "btn primary", href: nextHref(r) }, "Next →");
        append(output, [
          box,
          h("div", { class: "btn-row" }, nextBtn),
          v.actual ? renderTable(v.actual) : null,
          normSql(editor.value) !== normSql(ex.solution)
            ? panel("Reference solution, for comparison", codeBlock(ex.solution.replace(/; /g, ";\n")))
            : null,
        ]);
        renderStepsOnly(r);
        nextBtn.focus({ preventScroll: true });
      } else {
        append(output, [
          h("div", { class: "verdict err", role: "alert" }, v.message,
            h("span", { class: "note", text: "Try again — use Hint, Expected output or Solution if you're stuck." })),
          v.actual ? renderTable(v.actual) : null,
        ]);
      }
    }

    function showHint() {
      if (hintsShown < ex.hints.length) {
        append(hintBox, panel("Hint " + (hintsShown + 1) + " of " + ex.hints.length,
          h("div", { html: ex.hints[hintsShown] }), "hint"));
        hintsShown++;
        if (hintsShown === ex.hints.length) hintButton.disabled = true;
      }
    }

    function showExpected() {
      Runner.call("expected", { lesson: r.lesson, ex: r.ex }).then(function (res) {
        extras.innerHTML = "";
        append(extras, panel(ex.check ? "After your SQL, this check should return" : "Expected output", [
          ex.check ? codeBlock(ex.check.trim()) : null, renderTable(res)]));
      });
    }

    function showSolution() {
      progress.revealed.add(id);
      saveProgress();
      extras.innerHTML = "";
      append(extras, panel("Reference solution", [
        codeBlock(ex.solution.replace(/; /g, ";\n")),
        h("div", { class: "btn-row" }, h("button", { class: "btn small", onclick: function () {
          editor.value = ex.solution.replace(/; /g, ";\n");
          saveDraft(id, editor.value);
          editor.focus();
        } }, "Copy into editor")),
      ]));
    }

    function showSchema() {
      Runner.call("schema", { lesson: r.lesson, ex: r.ex }).then(function (tables) {
        extras.innerHTML = "";
        append(extras, panel("Tables", renderSchema(tables)));
      });
    }

    var runButton = h("button", { class: "btn primary", onclick: submit, title: KBD }, "▶ Run");
    var hintButton = h("button", { class: "btn", onclick: showHint, disabled: !ex.hints.length }, "Hint");

    append(main, [
      h("div", { class: "eyebrow" }, "Exercise " + (r.ex + 1) + " of " + lesson.exercises.length,
        progress.done.has(id) ? h("span", { style: "color:var(--ok)" }, " · ✓ done") : null),
      h("div", { class: "prompt", html: ex.prompt }),
      ex.setup ? h("details", { class: "setup" }, h("summary", { text: "Setup already applied for this exercise" }),
        codeBlock(ex.setup.replace(/;\s*/g, ";\n").trim())) : null,
      editor.el,
      h("div", { class: "btn-row" }, runButton, hintButton,
        h("button", { class: "btn", onclick: showExpected }, "Expected output"),
        h("button", { class: "btn", onclick: showSolution }, "Solution"),
        h("button", { class: "btn", onclick: showSchema }, "Tables"),
        h("span", { class: "kbd-hint", text: KBD + " to run" })),
      hintBox,
      output,
      extras,
    ]);
    editor.focus();
  }

  // Refresh the step pills (done markers) without re-rendering the exercise.
  function renderStepsOnly(r) {
    var old = main.querySelector(".steps");
    if (old) old.replaceWith(stepsNav(r.lesson, -1, r.ex));
  }

  function viewQuiz(r, lesson, q) {
    var id = exId(lesson, r.ex);
    var feedback = h("div", { "aria-live": "polite" });
    var buttons = q.options.map(function (opt, i) {
      return h("button", { class: "option", onclick: function () { answer(i); } },
        h("span", { class: "letter", text: "abcdefgh"[i] + ")" }), h("span", { html: opt }));
    });

    function answer(i) {
      buttons.forEach(function (b, j) {
        b.disabled = true;
        if (j === q.answer) b.classList.add("correct");
        else if (j === i) b.classList.add("wrong");
      });
      var right = i === q.answer;
      if (right) {
        progress.done.add(id);
        saveProgress();
        renderStepsOnly(r);
      }
      var box = h("div", { class: "verdict " + (right ? "ok" : "err") },
        right ? "Correct!" : "Not quite.",
        q.explanation ? h("span", { class: "note", html: q.explanation }) : null);
      var nextBtn = h("a", { class: "btn primary", href: nextHref(r) }, "Next →");
      append(feedback, [box, h("div", { class: "btn-row" }, nextBtn,
        right ? null : h("button", { class: "btn", onclick: function () { render(); } }, "Try again"))]);
      nextBtn.focus({ preventScroll: true });
    }

    append(main, [
      h("div", { class: "eyebrow" }, "Quiz " + (r.ex + 1) + " of " + lesson.exercises.length,
        progress.done.has(id) ? h("span", { style: "color:var(--ok)" }, " · ✓ done") : null),
      h("div", { class: "prompt", html: q.question }),
      h("div", { class: "options" }, buttons),
      feedback,
    ]);
  }

  function viewDone(r) {
    var lesson = course.lessons[r.lesson];
    var c = lessonCounts(lesson);
    setTitle(lesson.title);
    var missing = lesson.exercises.map(function (_, i) { return i; })
      .filter(function (i) { return !progress.done.has(exId(lesson, i)); });
    append(main, [
      lessonHeader(r.lesson, -1, -1),
      h("div", { class: c[0] === c[1] ? "verdict ok" : "panel" },
        c[0] === c[1] ? "Lesson complete!" : "You've completed " + c[0] + " of " + c[1] + " exercises in this lesson."),
      missing.length ? h("p", null, "Still open: ", missing.map(function (i, k) {
        return [k ? ", " : "", h("a", { href: "#/lesson/" + (r.lesson + 1) + "/exercise/" + (i + 1),
          text: (lesson.exercises[i].type === "quiz" ? "Q" : "E") + (i + 1) })];
      })) : null,
      h("div", { class: "btn-row" },
        r.lesson + 1 < course.lessons.length
          ? h("a", { class: "btn primary", href: "#/lesson/" + (r.lesson + 2) }, "Next lesson: " + course.lessons[r.lesson + 1].title + " →")
          : h("a", { class: "btn primary", href: "#/sandbox" }, "You've reached the end — open the sandbox"),
        h("a", { class: "btn", href: "#/" }, "Home")),
    ]);
  }

  // ── Sandbox, database, reference ───────────────────────────────────────

  var sandboxHistory = [];

  function viewSandbox() {
    setTitle("Sandbox");
    var history = h("div", { "aria-live": "polite" });
    var extras = h("div");
    var editor = createEditor(drafts.sandbox || "SELECT * FROM employees LIMIT 5;", {
      rows: 8, onRun: submit, label: "Sandbox SQL", onChange: function (v) { saveDraft("sandbox", v); },
    });
    var runButton = h("button", { class: "btn primary", onclick: submit, title: KBD }, "▶ Run");

    function drawHistory() {
      history.innerHTML = "";
      append(history, sandboxHistory.map(function (item) {
        return h("div", { class: "history-item" }, codeBlock(item.sql), renderOutcome(item.outcome));
      }));
    }

    function submit() {
      var sql = editor.value;
      if (!sql.trim()) return;
      runButton.disabled = true;
      run("sandboxRun", { sql: sql }).then(function (outcome) {
        if (outcome.timeout) outcome.error += " The sandbox database was reset.";
        sandboxHistory.unshift({ sql: sql.trim(), outcome: outcome });
        sandboxHistory = sandboxHistory.slice(0, 20);
        runButton.disabled = false;
        drawHistory();
      });
    }

    append(main, [
      h("h1", { text: "Sandbox" }),
      h("p", { class: "lead", text: "Run any SQL against your own copy of the sample database. Changes persist until you reset or reload the page." }),
      editor.el,
      h("div", { class: "btn-row" }, runButton,
        h("button", { class: "btn", onclick: function () {
          Runner.call("sandboxSchema").then(function (t) {
            extras.innerHTML = "";
            append(extras, h("div", { class: "panel" },
              h("div", { class: "btn-row" }, h("strong", { text: "Tables" }),
                h("button", { class: "btn small", onclick: function () { extras.innerHTML = ""; } }, "Hide")),
              renderSchema(t)));
          });
        } }, "Tables"),
        h("button", { class: "btn", onclick: function () {
          run("sandboxReset").then(function () {
            sandboxHistory.unshift({ sql: "-- database reset", outcome: { results: [] } });
            drawHistory();
          });
        } }, "Reset database"),
        h("span", { class: "kbd-hint", text: KBD + " to run" })),
      extras,
      history,
    ]);
    drawHistory();
    editor.focus();
  }

  function viewDatabase() {
    setTitle("Sample database");
    var body = h("div", null, h("p", { class: "muted", text: "Loading…" }));
    append(main, [
      h("h1", { text: "The sample database" }),
      h("p", { class: "lead", text: "Acme, a small company: its departments, staff, customers, products and orders. Every lesson and exercise starts from this data." }),
      body,
    ]);
    Runner.call("schema").then(function (tables) {
      body.innerHTML = "";
      append(body, renderSchema(tables));
    });
  }

  function viewReference() {
    setTitle("Cheat sheet");
    append(main, [
      h("h1", { text: "Cheat sheet" }),
      h("article", { class: "page" }, course.reference.map(function (blocks) { return renderBlocks(blocks, -1); })),
    ]);
  }

  // ── Boot ───────────────────────────────────────────────────────────────

  function fail(message) {
    main.innerHTML = "";
    append(main, h("div", { class: "error-box" },
      h("strong", { text: "The course could not start. " }), message,
      h("p", { text: "It needs a modern browser with WebAssembly and Web Workers, and must be served over http(s), not opened as a file." })));
  }

  document.getElementById("menu-toggle").addEventListener("click", function () {
    var open = document.body.classList.toggle("nav-open");
    this.setAttribute("aria-expanded", String(open));
  });

  loadProgress();
  loadDrafts();
  Runner.start();

  Promise.all([
    fetch("course.json").then(function (r) {
      if (!r.ok) throw new Error("could not load course.json (" + r.status + ")");
      return r.json();
    }),
    Runner.ready,
  ]).then(function (loaded) {
    course = loaded[0];
    window.addEventListener("hashchange", render);
    render();
  }).catch(function (e) { fail(e.message); });
})();
