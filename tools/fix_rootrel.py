#!/usr/bin/env python3
"""Fix root-relative links in Wayback-recovered raw pages.

  /~yays/foo/bar.html  -> relative path if the target exists locally,
                          else absolute https://www14.big.or.jp/~yays/...
  /cgi-bin/Count.cgi   -> absolute https://www14.big.or.jp/... (host CGIs)
  /anything-else       -> absolute origin URL (preserves behaviour while
                          the origin host is alive; avoids github.io root)
"""
import os, re, sys, urllib.parse

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "/home/takano32/GitHub/yays")
ORIGIN = "https://www14.big.or.jp"

link_re = re.compile(r"""(href|src|action|background)(\s*=\s*)(["'])(/[^"']*)(["'])""",
                     re.IGNORECASE)

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
            path = val
            frag = ""
            for sep in "#?":
                if sep in path:
                    path, _, rest = path.partition(sep)
                    frag = sep + rest
            norm = urllib.parse.unquote(path)
            if norm.startswith("/~yays") or norm.startswith("/%7Eyays"):
                rel_target = norm.split("yays", 1)[1].lstrip("/")
                local = os.path.join(ROOT, rel_target)
                if rel_target and os.path.exists(local) and not frag.startswith("?"):
                    rel = os.path.relpath(local, dirpath)
                    rewrites += 1
                    return f"{attr}{eq}{q1}{rel}{frag}{q2}"
            rewrites += 1
            return f"{attr}{eq}{q1}{ORIGIN}{val}{q2}"

        new = link_re.sub(repl, text)
        if new != text:
            open(fpath, "w", encoding="utf-8", errors="surrogateescape").write(new)
            changed_files += 1
print(f"rewrote {rewrites} root-relative links in {changed_files} files")
