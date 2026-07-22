#!/usr/bin/env python3
"""Rewrite absolute links to the origin (www14.big.or.jp/~yays/...) into
relative paths — but only when the target exists in the local mirror.
Links to live CGIs / never-mirrored pages stay absolute so they still work
while the origin server is up."""
import os, re, sys, urllib.parse

root = os.path.abspath(sys.argv[1])
url_re = re.compile(
    r"""(["'])(https?://www14\.big\.or\.jp/~yays/?([^"']*?))(["'])""")

changed_files = 0
rewrites = 0
kept = {}

for dirpath, _dirs, files in os.walk(root):
    for name in files:
        if not name.lower().endswith((".html", ".htm", ".shtml")):
            continue
        fpath = os.path.join(dirpath, name)
        text = open(fpath, encoding="utf-8", errors="surrogateescape").read()

        def repl(m):
            global rewrites
            q1, full, tail, q2 = m.group(1), m.group(2), m.group(3), m.group(4)
            frag = ""
            path = tail
            for sep in ("#",):
                if sep in path:
                    path, _, f = path.partition(sep)
                    frag = sep + f
            if "?" in path:
                kept[full] = kept.get(full, 0) + 1
                return m.group(0)  # live CGI with query — keep absolute
            local = os.path.normpath(os.path.join(root, urllib.parse.unquote(path))) if path else root
            if path.endswith("/") or path == "":
                local = os.path.join(local, "index.html")
                relpath_target = local
            else:
                relpath_target = local
            if not os.path.exists(relpath_target):
                kept[full] = kept.get(full, 0) + 1
                return m.group(0)
            rel = os.path.relpath(relpath_target, dirpath)
            rewrites += 1
            return f"{q1}{rel}{frag}{q2}"

        new = url_re.sub(repl, text)
        if new != text:
            open(fpath, "w", encoding="utf-8", errors="surrogateescape").write(new)
            changed_files += 1

print(f"rewrote {rewrites} links in {changed_files} files")
print(f"\nkept absolute (no local target / live CGI): {len(kept)} distinct URLs")
for u, c in sorted(kept.items(), key=lambda x: -x[1])[:40]:
    print(f"  {c:3d}  {u}")
