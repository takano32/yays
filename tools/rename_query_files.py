#!/usr/bin/env python3
"""Rename files whose names contain ?/&/= (unservable or fragile on GitHub
Pages) and rewrite every reference to them in the HTML tree.

References produced by wget --convert-links look like:
    href="../cgi-bin/noteky/noteky.cgi%3Fc=noteread&amp;f=1&amp;...&amp;ff=on.html"
i.e. '?' is percent-encoded and '&' is an HTML entity. We only touch the
final path component, so ../ prefixes don't matter. All patterns are pure
ASCII, so byte-level replacement is safe in any file encoding.
"""
import os, sys

root = os.path.abspath(sys.argv[1])

renames = {}  # original basename -> safe basename
for dirpath, _dirs, files in os.walk(root):
    for name in files:
        if any(c in name for c in "?&="):
            safe = name.replace("?", "_").replace("&", "_").replace("=", "-")
            target = os.path.join(dirpath, safe)
            assert not os.path.exists(target), f"collision: {target}"
            os.rename(os.path.join(dirpath, name), target)
            renames[name] = safe
            print(f"renamed: {name}\n      -> {safe}")

if not renames:
    print("nothing to rename")
    sys.exit(0)

def variants(name):
    q = name.replace("?", "%3F")
    # longest/most-encoded first so partial forms never pre-empt full ones
    return [q.replace("&", "&amp;"),
            name.replace("&", "&amp;"),
            q,
            name]

changed = 0
for dirpath, _dirs, files in os.walk(root):
    for fname in files:
        if not fname.lower().endswith((".html", ".htm")):
            continue
        fpath = os.path.join(dirpath, fname)
        with open(fpath, "rb") as fh:
            data = fh.read()
        orig_data = data
        for oname, safe in renames.items():
            for v in variants(oname):
                data = data.replace(v.encode(), safe.encode())
        if data != orig_data:
            with open(fpath, "wb") as fh:
                fh.write(data)
            changed += 1
            print(f"refs rewritten: {os.path.relpath(fpath, root)}")
print(f"files changed: {changed}")
