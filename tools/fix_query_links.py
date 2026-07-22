#!/usr/bin/env python3
"""After Wayback recovery: rewrite links that target recovered query-string
URLs (e.g. href="noteky.cgi?c=noteread&id=..." or absolute origin forms) to
the sanitized local filenames the recovery saved them under.

Handles relative same-dir links (basename?query), absolute origin URLs,
'&amp;' entity form, and '%3F' percent-encoded '?'."""
import os, re, sys, json, urllib.parse

W = "/home/takano32/.cache/yays-recovery"
ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "/home/takano32/GitHub/yays")

by_pathq = {}   # "cgi-bin/noteky/noteky.cgi?c=.." -> sanitized rel path
by_baseq = {}   # "noteky.cgi?c=.." -> sanitized rel path (same-dir links)
for line in open(W + "/recover_state.jsonl"):
    rec = json.loads(line)
    if rec.get("status") != "ok":
        continue
    p = urllib.parse.urlparse(rec["orig"])
    if not p.query:
        continue
    path = urllib.parse.unquote(p.path)
    if not path.startswith("/~yays"):
        continue
    pathq = path[len("/~yays"):].lstrip("/") + "?" + p.query
    by_pathq[pathq] = rec["rel"]
    by_baseq[pathq.rsplit("/", 1)[-1]] = rec["rel"]

print(f"query-link map: {len(by_pathq)} URLs")

link_re = re.compile(r"""(href|src|action)(\s*=\s*)(["'])([^"']+)(["'])""",
                     re.IGNORECASE)
abs_re = re.compile(r"^https?://www14\.big\.or\.jp(?::80)?/(?:~|%7[Ee])yays/")

changed_files = rewrites = 0
for dirpath, dirs, files in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in (".git", "tools")]
    for name in files:
        if not name.lower().endswith((".html", ".htm")):
            continue
        fpath = os.path.join(dirpath, name)
        text = open(fpath, encoding="utf-8", errors="surrogateescape").read()

        def repl(m):
            global rewrites
            attr, eq, q1, val, q2 = m.groups()
            norm = val.replace("&amp;", "&").replace("%3F", "?").replace("%3f", "?")
            am = abs_re.match(norm)
            if am:
                pathq = urllib.parse.unquote(norm[am.end():])
                target = by_pathq.get(pathq)
                if target:
                    rel = os.path.relpath(os.path.join(ROOT, target), dirpath)
                    rewrites += 1
                    return f"{attr}{eq}{q1}{rel}{q2}"
            elif "?" in norm and "://" not in norm:
                base = norm.rsplit("/", 1)[-1]
                target = by_baseq.get(base)
                if target:
                    prefix = norm.rsplit("/", 1)[0] + "/" if "/" in norm else ""
                    rewrites += 1
                    return f"{attr}{eq}{q1}{prefix}{os.path.basename(target)}{q2}"
            return m.group(0)

        new = link_re.sub(repl, text)
        if new != text:
            open(fpath, "w", encoding="utf-8", errors="surrogateescape").write(new)
            changed_files += 1
print(f"rewrote {rewrites} links in {changed_files} files")
