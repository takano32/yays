#!/usr/bin/env python3
"""Audit a mirrored static site: find broken internal links and leftover
absolute links back to the origin host."""
import os, re, sys, urllib.parse, collections

root = os.path.abspath(sys.argv[1])
attr_re = re.compile(
    r"""(?:href|src|background)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""",
    re.IGNORECASE)

broken = []          # (file, link, resolved_path)
origin_abs = []      # (file, link) absolute links back to origin host
external = collections.Counter()
checked = 0

for dirpath, _dirs, files in os.walk(root):
    for name in files:
        if not name.lower().endswith((".html", ".htm")):
            continue
        fpath = os.path.join(dirpath, name)
        try:
            text = open(fpath, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for m in attr_re.finditer(text):
            link = next(g for g in m.groups() if g is not None).strip()
            if not link or link.startswith(("#", "mailto:", "javascript:", "data:")):
                continue
            p = urllib.parse.urlparse(link)
            if p.scheme in ("http", "https"):
                if "www14.big.or.jp" in p.netloc:
                    origin_abs.append((os.path.relpath(fpath, root), link))
                else:
                    external[p.netloc] += 1
                continue
            if p.scheme:   # ftp: etc.
                external[p.scheme + ":" + p.netloc] += 1
                continue
            path = urllib.parse.unquote(p.path)
            if not path:   # pure fragment/query
                continue
            if path.startswith("/"):
                resolved = os.path.join(root, path.lstrip("/"))
            else:
                resolved = os.path.normpath(os.path.join(dirpath, path))
            checked += 1
            if os.path.isdir(resolved):
                if not os.path.exists(os.path.join(resolved, "index.html")):
                    broken.append((os.path.relpath(fpath, root), link, "dir w/o index"))
            elif not os.path.exists(resolved):
                broken.append((os.path.relpath(fpath, root), link,
                               os.path.relpath(resolved, root)))

print(f"internal links checked: {checked}")
print(f"\n=== BROKEN internal links: {len(broken)} ===")
for f, l, r in sorted(set(broken)):
    print(f"  {f}  ->  {l}")
print(f"\n=== absolute links back to origin (www14.big.or.jp): {len(origin_abs)} ===")
for f, l in sorted(set(origin_abs)):
    print(f"  {f}  ->  {l}")
print("\n=== external hosts referenced (count) ===")
for host, c in external.most_common():
    print(f"  {c:4d}  {host}")
