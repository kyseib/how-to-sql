"""Build the static browser version of the course (for GitHub Pages).

    python3 tools/build_web.py _site          # after `npm ci`
    python3 -m http.server -d _site 8000      # preview at http://localhost:8000

The Python lesson modules stay the single source of truth: this script
exports them to course.json and copies the web app plus sql.js next to it.
"""

import argparse
import html
import json
import re
import shutil
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sql_tutor import __version__, db, reference  # noqa: E402
from sql_tutor.lessons import LESSONS  # noqa: E402
from sql_tutor.model import Quiz  # noqa: E402
from sql_tutor.ui import split_blocks  # noqa: E402

SQLJS_FILES = ["sql-wasm.js", "sql-wasm.wasm"]
_LIST_ITEM = re.compile(r"^(\s*)(- |\* |\d+\. )")


def inline(text):
    """Escape text, then apply `code` and **bold** markup."""
    out = html.escape(text, quote=False)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    return out


def text_to_html(text):
    parts = []
    for para in re.split(r"\n\s*\n", text.strip("\n")):
        if not para.strip():
            continue
        lines = para.split("\n")
        first = lines[0]
        if first.startswith("# "):
            parts.append(f"<h2>{inline(first[2:].strip())}</h2>")
        elif first.startswith("    "):
            body = textwrap.dedent(para)
            parts.append(f'<pre class="plain">{html.escape(body, quote=False)}</pre>')
        elif _LIST_ITEM.match(first):
            items = []
            for line in lines:
                if _LIST_ITEM.match(line):
                    items.append(line.strip())
                else:
                    items[-1] += " " + line.strip()
            ordered = not _LIST_ITEM.match(first).group(2).strip() in "-*"
            tag = "ol" if ordered else "ul"
            lis = "".join(
                f"<li>{inline(item[len(_LIST_ITEM.match(item).group(2)):])}</li>"
                for item in items)
            parts.append(f"<{tag}>{lis}</{tag}>")
        else:
            parts.append(f"<p>{inline(' '.join(l.strip() for l in lines))}</p>")
    return "\n".join(parts)


def page_blocks(page, counter):
    """Convert one markup page into a list of blocks for the web app.

    `counter` is a one-item list holding the lesson-wide index of the next
    runnable example; examples replay in that order in the browser.
    """
    blocks = []
    for kind, body in split_blocks(page):
        if kind == "text":
            blocks.append({"type": "html", "html": text_to_html(body)})
        elif kind in ("sql", "run"):
            code = textwrap.dedent(body).strip("\n")
            block = {"type": kind, "code": code}
            if kind == "run":
                block["index"] = counter[0]
                counter[0] += 1
            blocks.append(block)
        else:
            blocks.append({"type": "code", "code": textwrap.dedent(body).strip("\n")})
    return blocks


def export_exercise(ex):
    if isinstance(ex, Quiz):
        return {
            "type": "quiz",
            "question": inline(ex.question),
            "options": [inline(o) for o in ex.options],
            "answer": ex.answer,
            "explanation": inline(ex.explanation),
        }
    return {
        "type": "exercise",
        "prompt": inline(ex.prompt),
        "solution": ex.solution,
        "hints": [inline(h) for h in ex.hints],
        "ordered": ex.ordered,
        "checkNames": ex.check_names,
        "setup": ex.setup,
        "check": ex.check,
        "probes": list(ex.probes),
        "explanation": inline(ex.explanation),
    }


def export_lesson(lesson):
    counter = [0]
    return {
        "id": lesson.id,
        "title": lesson.title,
        "summary": lesson.summary,
        "pages": [page_blocks(p, counter) for p in lesson.pages],
        "exercises": [export_exercise(e) for e in lesson.exercises],
    }


def build_course():
    return {
        "version": __version__,
        "schema": db.SCHEMA,
        "seed": db.SEED,
        "tableNotes": db.TABLE_NOTES,
        "lessons": [export_lesson(l) for l in LESSONS],
        "reference": [page_blocks(p, [0]) for p in reference.PAGES],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", nargs="?", default="_site", help="output directory")
    parser.add_argument("--sqljs", default=str(ROOT / "node_modules" / "sql.js" / "dist"),
                        help="directory containing sql-wasm.js and sql-wasm.wasm")
    args = parser.parse_args(argv)

    out = Path(args.out)
    sqljs = Path(args.sqljs)
    missing = [f for f in SQLJS_FILES if not (sqljs / f).exists()]
    if missing:
        sys.exit(f"sql.js not found in {sqljs} (missing {', '.join(missing)}). Run `npm ci` first.")

    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / "web", out)
    for name in SQLJS_FILES:
        shutil.copy2(sqljs / name, out / name)
    (out / "course.json").write_text(json.dumps(build_course(), separators=(",", ":")))
    (out / ".nojekyll").write_text("")
    print(f"Built {out} ({len(LESSONS)} lessons)")


if __name__ == "__main__":
    main()
